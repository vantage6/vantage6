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
        ResultStreams,
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
class ResultStreamBase(ServicesResources):
    """Base class for run resources"""

    def __init__(self, storage_adapter, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)
        self.storage_adapter = storage_adapter

class ResultStream(ResultStreamBase):
    """Resource for /api/resultstream/<id>"""

    def __init__(self, storage_adapter, socketio, mail, api, permissions, config):
      super().__init__(storage_adapter, socketio, mail, api, permissions, config)

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
  
class ResultStreams(ResultStreamBase):
  """Resource for /api/resultstream/<id>"""
      
  def __init__(self, storage_adapter, socketio, mail, api, permissions, config):
        super().__init__(storage_adapter, socketio, mail, api, permissions, config)

  @only_for(("node", "user", "container"))
  def post(self):
      if not self.storage_adapter:
            log.warning(
                "The large result store is not set to azure blob storage, result streaming is not available."
            )
            return {"msg": "Not implemented"}, HTTPStatus.NOT_IMPLEMENTED
      result_uuid = str(uuid.uuid4())

      def process_stream(stream):
            chunk_size = 4096
            total_bytes = b""
            while True:
                chunk = uwsgi.chunked_read(chunk_size)
                if not chunk:
                    break
                yield chunk
            return total_bytes


      try:
          self.storage_adapter.store_blob(result_uuid, process_stream(request.stream))
      except Exception as e:
          log.error(f"Error uploading result: {e}")
          return {"msg": "Error uploading result!"}, HTTPStatus.INTERNAL_SERVER_ERROR

      return {"uuid": result_uuid}, HTTPStatus.CREATED