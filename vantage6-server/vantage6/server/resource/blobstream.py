import logging
import uuid

# uwsgi is not available when running outside of a uwsgi process.
# (see https://uwsgi-docs.readthedocs.io/en/latest/PythonModule.html)
# This prevents a ModuleNotFoundError if this resource is loaded
# outside of such a server, e.g. when importing data in v6 dev create-demo-network.
try:
    import uwsgi  # type: ignore (built from source in Dockerfile)
except ImportError:
    uwsgi = None
from flask import g, request, Response, stream_with_context

from flask_restful import Api
from http import HTTPStatus

from vantage6.common import logger_name
from vantage6.common.task_status import has_task_finished
from vantage6.server.permission import RuleCollection, Operation as P, Scope
from vantage6.server.resource import (
    only_for,
    ServicesResources,
)
from vantage6.server.model import Run as db_Run, Task as db_Task


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the run resource.

    Parameters
    ----------
    api : Api
        Flask restful api instance
    api_base : str
        Base url of the api
    services : dict
        Dictionary with services required for the resource endpoints
    """
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        BlobStream,
        api_base + "/blobstream",
        endpoint="result_stream_without_id",
        methods=("POST",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        BlobStreamStatus,
        api_base + "/blobstream/status",
        endpoint="blob_stream_status",
        methods=("GET",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        BlobStream,
        api_base + "/blobstream/<string:id>",
        endpoint="blob_stream_with_id",
        methods=("GET",),
        resource_class_kwargs=services,
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class BlobStreamBase(ServicesResources):
    """
    Base class for run resources that require a storage adapter.
    This class provides methods for streaming large results from the storage adapter.
    """

    def __init__(self, socketio, storage_adapter, mail, api, permissions, config):
        super().__init__(socketio, storage_adapter, mail, api, permissions, config)
        self.r_run: RuleCollection = getattr(self.permissions, "run")
        self.r_task: RuleCollection = getattr(self.permissions, "task")
        self.storage_adapter = storage_adapter

    def get_run_by_input_or_result(self, id) -> db_Run | None:
        run = (
            g.session.query(db_Run)
            .filter((db_Run.input == id) | (db_Run.result == id))
            .first()
        )
        return run


class BlobStreamStatus(BlobStreamBase):
    """
    Resource for /api/blobstream/status (GET)
    Returns whether the blob store is enabled.
    """

    def __init__(self, socketio, storage_adapter, mail, api, permissions, config):
        super().__init__(socketio, storage_adapter, mail, api, permissions, config)

    @only_for(("node", "user", "container"))
    def get(self):
        """Get the status of the blob store
        ---

        description: >-
            Returns whether or not blob storage is enabled. \n

        responses:
          200:
              description: Ok
          401:
              description: Unauthorized

        security:
          - bearerAuth: []
        """
        log.debug("Checking if blob store is enabled")

        if self.storage_adapter:
            return {"blob_store_enabled": True}, HTTPStatus.OK
        else:
            return {"blob_store_enabled": False}, HTTPStatus.OK


class BlobStream(BlobStreamBase):
    """
    Resource for /api/blobstream/<id> (GET) and /api/blobstream (POST)
    This resource allows for streaming large results from blob Storage.
    """

    def __init__(self, socketio, storage_adapter, mail, api, permissions, config):
        super().__init__(socketio, storage_adapter, mail, api, permissions, config)

    @only_for(("node", "user", "container"))
    def get(self, id):
        """Stream the result or input with the given id from blob storage.
        ---

        description: >-
            Streams the result or input with the given id from blob storage.

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Blobstream|Global|View|❌|❌|View any blob|\n
            |Blobstream|Collaboration|View|✅|✅|View the blobs of your
            organization's collaborations|\n
            |Blobstream|Organization|View|❌|❌|View any blob from a task created by
            your organization|\n
            |Blobstream|Own|View|❌|❌|View any blob from a task created by you|\n

            Accessible to users.

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized
          404:
            description: Not Found
          500:
            description: Internal Server Error
          501:
            description: Not Implemented

        security:
        - bearerAuth: []

        tags: ["Algorithm"]
        """
        run = self.get_run_by_input_or_result(id)
        if not run:
            return {
                "msg": f"No run found with input or result id={id}"
            }, HTTPStatus.NOT_FOUND
        if not self.r_run.allowed_for_org(P.VIEW, run.task.init_org_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        if not self.storage_adapter:
            not_available_msg = "The large result store is not set to blob storage, result streaming is not available."
            log.warning(not_available_msg)
            return {"msg": not_available_msg}, HTTPStatus.NOT_IMPLEMENTED
        try:
            log.debug(f"Streaming result for run id={id}")
            blob_stream = self.storage_adapter.stream_blob(id)
        except Exception as e:
            log.error(f"Error streaming result: {e}")
            return {"msg": "Error streaming result!"}, HTTPStatus.INTERNAL_SERVER_ERROR

        def generate():
            for chunk in blob_stream.chunks():
                yield chunk

        return Response(
            stream_with_context(generate()),
            content_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=result_{id}.bin"},
        )

    @only_for(("node", "user", "container"))
    def post(self):
        """Post a result to the blob storage.
        blobs are streamed directly to the blob storage.
        This is useful for large results that cannot be loaded into memory at once.
        ---
        description: >-
          Stream and store blob to blob storage.

        requestBody:
          content:
            application/octet-stream

        responses:
          201:
            description: Created
          501:
            description: Not Implemented

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        if not self.storage_adapter:
            not_available_msg = "The large result store is not set to blob storage, result streaming is not available."
            log.warning(not_available_msg)
            return {"msg": not_available_msg}, HTTPStatus.NOT_IMPLEMENTED

        if g.user and not self.r_task.has_at_least_scope(Scope.COLLABORATION, P.CREATE):
            return {
                "msg": "You do not have permission to upload blobs. This requires permission to create tasks which you don't have."
            }, HTTPStatus.UNAUTHORIZED
        if g.container:
            container = g.container
            if has_task_finished(db_Task.get(container["task_id"]).status):
                log.warning(
                    f"Container from node={container['node_id']} "
                    f"attempts to upload blob for a sub-task of a completed "
                    f"task={container['task_id']}"
                )
                return {
                    "msg": "Cannot upload blob for a sub-task of a completed task."
                }, HTTPStatus.FORBIDDEN

        result_uuid = str(uuid.uuid4())
        transfer_encoding = request.headers.get("Transfer-Encoding", "").lower()
        is_chunked = "chunked" in transfer_encoding
        try:
            # Unfortunately, in the case of streams smaller than one chunk,
            # reverse proxies like nginx will automatically remove the chunked transfer encoding.
            # Therefore, we need to handle both chunked and non-chunked uploads. Exchanging uwsgi
            # to a different server might solve this issue.
            if is_chunked:
                stream = UwsgiChunkedStream()
                self.storage_adapter.store_blob(result_uuid, stream)
            else:
                data = request.get_data()
                self.storage_adapter.store_blob(result_uuid, data)
        except Exception as e:
            log.error(f"Error uploading result: {e}")
            return {"msg": "Error uploading result!"}, HTTPStatus.INTERNAL_SERVER_ERROR

        return {"uuid": result_uuid}, HTTPStatus.CREATED


class UwsgiChunkedStream:
    """
    Read data in chunks from uwsgi.
    """

    # TODO: Using uwsgi in python in combination with flask is not ideal.
    # It would be better to switch to a different server in the long term.
    #
    def __init__(self, chunk_size=4096):
        """
        Initialize the UwsgiChunkedStream.
        """
        self.chunk_size = chunk_size
        self._buffer = b""
        self._eof = False

    def read(self, size=-1):
        """
        Read data from the stream.
        """
        log.info(f"Reading with size: {size}")
        if size < 0:
            chunks = [self._buffer]
            self._buffer = b""
            while not self._eof:
                chunk = uwsgi.chunked_read(self.chunk_size)
                if not chunk:
                    self._eof = True
                    break
                chunks.append(chunk)
            return b"".join(chunks)

        while len(self._buffer) < size and not self._eof:
            chunk = uwsgi.chunked_read(self.chunk_size)
            if not chunk:
                self._eof = True
                break
            self._buffer += chunk

        result, self._buffer = self._buffer[:size], self._buffer[size:]
        return result
