import logging
import uwsgi
from flask import request, Response, stream_with_context

from flask_restful import Api
from http import HTTPStatus

from vantage6.common import logger_name
from vantage6.server.permission import (
    RuleCollection,
    PermissionManager,
    Scope as S,
    Operation as P,
)
from vantage6.server.resource import (
    only_for,
    ServicesResources,
)

import uuid

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
    
    api.add_resource(
        BlobStream,
        api_base + "/blobstream/delete/<string:id>",
        endpoint="result_stream_delete_with_id",
        methods=("DELETE",),
        resource_class_kwargs=services,
    )
    
    api.add_resource(
        BlobStream,
        api_base + "/blobstream/delete_container",
        endpoint="result_stream_delete_container",
        methods=("DELETE",),
        resource_class_kwargs=services,
    )

# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager):
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """
    add = permissions.appender(module_name)

    add(scope=S.GLOBAL, operation=P.VIEW, description="view any run")
    add(
        scope=S.COLLABORATION,
        operation=P.VIEW,
        assign_to_container=True,
        assign_to_node=True,
        description="view runs of your organizations " "collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.VIEW,
        description="view any run of a task created by your organization",
    )
    add(
        scope=S.OWN,
        operation=P.VIEW,
        description="view any run of a task created by you",
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class BlobStreamBase(ServicesResources):
    """
    Base class for run resources that require a storage adapter. 
    This class provides methods for streaming large results from the storage adapter, 
    in this case Azure Blob Storage.
    """

    def __init__(self, socketio, mail, api, permissions, config, storage_adapter=None):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)
        self.storage_adapter = storage_adapter

class BlobStreamStatus(BlobStreamBase):
    """
    Resource for /api/blobstream/status (GET)
    Returns whether the blob store is enabled.
    """
    def __init__(self, socketio, mail, api, permissions, config, storage_adapter=None):
        super().__init__(socketio, mail, api, permissions, config, storage_adapter=storage_adapter)

    @only_for(("node", "user", "container"))
    def get(self):
        if self.storage_adapter:
            return {"blob_store_enabled": True}, HTTPStatus.CREATED
        else:
            return {"blob_store_enabled": False}, HTTPStatus.CREATED

class BlobStream(BlobStreamBase):
    """
    Resource for /api/blobstream/<id> (GET) and /api/blobstream (POST)
    This resource allows for streaming large results from Azure Blob Storage.
    """
    def __init__(self, socketio, mail, api, permissions, config, storage_adapter=None):
        super().__init__(socketio, mail, api, permissions, config, storage_adapter=storage_adapter)

    @only_for(("node", "user", "container"))
    def get(self, id):
        if not self.storage_adapter:
            log.warning(
                "The large result store is not set to azure blob storage, result streaming is not available."
            )
            return {"msg": "Not implemented"}, HTTPStatus.NOT_IMPLEMENTED
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
            headers={
                "Content-Disposition": f"attachment; filename=result_{id}.bin"
            }
        )
               
    @only_for(("node", "user", "container"))
    def post(self):
        if not self.storage_adapter:
                log.warning(
                    "The large result store is not set to azure blob storage, result streaming is not available."
                )
                return {"msg": "Not implemented"}, HTTPStatus.NOT_IMPLEMENTED
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
    
    @only_for(("node", "user", "container"))
    def delete(self, id):
        if not self.storage_adapter:
            log.warning(
                "The large result store is not set to azure blob storage, result streaming is not available."
            )
            return {"msg": "Not implemented"}, HTTPStatus.NOT_IMPLEMENTED
        try:
            log.debug(f"Deleting result for run id={id}")
            self.storage_adapter.delete_blob(id)
        except Exception as e:
            log.error(f"Error deleting result: {e}")
            return {"msg": "Error deleting result!"}, HTTPStatus.INTERNAL_SERVER_ERROR

        return HTTPStatus.OK
    
    # @only_for(("node", "user", "container"))
    # def delete_container(self):
    #     if not self.storage_adapter:
    #         log.warning(
    #             "The large result store is not set to azure blob storage, result streaming is not available."
    #         )
    #         return {"msg": "Not implemented"}, HTTPStatus.NOT_IMPLEMENTED
    #     try:
    #         log.debug(f"Deleting blob storage container for {self.container.name}")
    #         self.storage_adapter.delete_container()
    #     except Exception as e:
    #         log.error(f"Error deleting result: {e}")
    #         return {"msg": "Error deleting result!"}, HTTPStatus.INTERNAL_SERVER_ERROR

    #     return HTTPStatus.OK

class UwsgiChunkedStream:
    """
    A stream for reading data in chunks from uwsgi.
    This is useful for handling large uploads without loading everything into memory at once.
    """
    #TODO: Using uwsgi in python in combination with flask is not very stable. Need to find an other solution to stream large data files.
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