import logging

from socketio import ClientNamespace

from vantage6.common import logger_name


class ClientSocketNamespace(ClientNamespace):
    """Class that handles incoming websocket events."""

    # reference to the node objects, so a callback can edit the
    # node instance.
    client_ref = None

    def __init__(self, *args, **kwargs):
        """ Handler for a websocket namespace.
        """
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(logger_name(__name__))

    def on_message(self, data):
        self.log.info(data)

    def on_connect(self):
        """On connect or reconnect"""
        self.log.info('(Re)Connected to the /tasks namespace')
        # self.client_ref.sync_task_queue_with_server()
        # self.log.debug("Tasks synced again with the server...")

    def on_disconnect(self):
        """ Server disconnects event."""
        # self.client_ref.socketIO.disconnect()
        self.log.info('Disconnected from the server')

    def on_new_task(self, task_id):
        """ New task event."""
        # if self.client_ref:
        #     self.client_ref.get_task_and_add_to_queue(task_id)
        #     self.log.info(f'New task has been added task_id={task_id}')

        # else:
        #     self.log.critical(
        #         'Task Master Node reference not set is socket namespace'
        #     )
        pass

    def on_container_failed(self, run_id):
        """A container in the collaboration has failed event.

        TODO handle run sequence at this node. Maybe terminate all
            containers with the same run_id?
        """
        # self.log.critical(
        #     f"A container on a node within your collaboration part of "
        #     f"run_id={run_id} has exited with a non-zero status_code"
        # )
        pass

    def on_expired_token(self, msg):
        # self.log.warning("Your token is no longer valid... reconnecting")
        # self.client_ref.socketIO.disconnect()
        # self.log.debug("Old socket connection terminated")
        # self.client_ref.server_io.refresh_token()
        # self.log.debug("Token refreshed")
        # self.client_ref.connect_to_socket()
        # self.log.debug("Connected to socket")
        # self.client_ref.sync_task_queue_with_server()
        # self.log.debug("Tasks synced again with the server...")
        pass
        # TODO implement
