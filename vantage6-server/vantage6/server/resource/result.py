import logging
from flask import request, Response, stream_with_context
from werkzeug.wsgi import LimitedStream

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


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class ResultStreamBase(ServicesResources):
    """Base class for run resources"""

    def __init__(self, storage_adapter, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)
        self.storage_adapter = storage_adapter

class ResultStream(ResultStreamBase):
    """
        Resource for /api/resultstream (POST)
        Resource for /api/resultstream/<id> (GET)
        This resource allows uploading and retrieving large results to the server.
        It supports both chunked and non-chunked uploads.
    """

    def __init__(self, storage_adapter, socketio, mail, api, permissions, config):
        super().__init__(storage_adapter, socketio, mail, api, permissions, config)

    @staticmethod
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
            ResultStream,
            api_base + "/resultstream",
            endpoint="result_stream_without_id",
            methods=("POST",),
            resource_class_kwargs=services,
        )
            
        api.add_resource(
            ResultStream,
            api_base + "/resultstream/<string:id>",
            endpoint="result_stream_with_id",
            methods=("GET",),
            resource_class_kwargs=services,
        )

    @staticmethod
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

    @only_for(("node", "user", "container"))
    def get(self, id):
        """
        Get the result of a run by its id.
        Parameters
        ----------
        id : str
            The id of the run to get the result for.    
        Returns
        -------
        Response
            A streaming response with the result data.
        HTTPStatus
            The HTTP status code indicating the result of the operation.

        """
        if not self.storage_adapter:
            log.warning(
                "The large result store is not set to azure blob storage, result streaming is not available."
            )
            return {"msg": "Not implemented"}, HTTPStatus.NOT_IMPLEMENTED
        try:
            log.debug(f"Streaming result for run id={id}")
            blob_stream = self.storage_adapter.stream_blob(id)
            if not blob_stream or not hasattr(blob_stream, "chunks"):
                log.error(f"Invalid blob_stream returned for id={id}")
                return {"msg": "Result not found or invalid stream!"}, HTTPStatus.NOT_FOUND
        except Exception as e:
            log.error(f"Error streaming result: {e}")
            return {"msg": "Error streaming result!"}, HTTPStatus.INTERNAL_SERVER_ERROR

        # Return a streaming response with the content type set to binary
        return Response(
            stream_with_context(self.generate_chunks(blob_stream)),
            content_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=result_{id}.bin"
            }
        )
        
    @only_for(("node", "user", "container"))
    def post(self):
        """
        Upload a result to the server.
        This method handles both chunked and non-chunked uploads.
        Returns
        -------
        dict
            A dictionary containing the UUID of the uploaded result.
        HTTPStatus
            The HTTP status code indicating the result of the operation.
        """
        log.info("Uploading result to the server")
        if not self.storage_adapter:
            log.warning(
                "The large result store is not set to azure blob storage, result streaming is not available."
            )
            return {"msg": "Not implemented"}, HTTPStatus.NOT_IMPLEMENTED
        result_uuid = str(uuid.uuid4())
        transfer_encoding = request.headers.get("Transfer-Encoding", "").lower()
        is_chunked = "chunked" in transfer_encoding
        try:
            if is_chunked:
                stream = WerkzeugChunkedStream(request.stream)
                self.storage_adapter.store_blob(result_uuid, stream)
            else:
                data = request.get_data()
                self.storage_adapter.store_blob(result_uuid, data)
        except Exception as e:
            log.error(f"Error uploading result: {e}")
            return {"msg": "Error uploading result!"}, HTTPStatus.INTERNAL_SERVER_ERROR

        return {"uuid": result_uuid}, HTTPStatus.CREATED

    def generate_chunks(self, blob_stream):
        for chunk in blob_stream.chunks():
            yield chunk
        log.debug("Finished streaming result chunks")
            
            
class WerkzeugChunkedStream:
    """A class to handle chunked reading using Werkzeug's LimitedStream."""

    def __init__(self, stream: LimitedStream, chunk_size=4096):
        self.stream = stream
        self.chunk_size = chunk_size

    def read(self, size=-1):
        log.debug(f"Reading chunks with size: {size}")
        if size <= 0:
            return self.stream.read()
        return self.stream.read(size)

    def __iter__(self):
        return self

    def __next__(self):
        chunk = self.stream.read(self.chunk_size)
        if not chunk:
            raise StopIteration
        return chunk
