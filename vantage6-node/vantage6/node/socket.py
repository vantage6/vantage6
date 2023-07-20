import logging

from socketio import ClientNamespace

from vantage6.common import logger_name
from vantage6.common.task_status import TaskStatus, has_task_failed


class NodeTaskNamespace(ClientNamespace):
    """Class that handles incoming websocket events."""

    # reference to the node objects, so a callback can edit the
    # node instance.
    node_worker_ref = None

    def __init__(self, *args, **kwargs):
        """ Handler for a websocket namespace. """
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(logger_name(__name__))

    def on_message(self, msg):
        """
        Receive messages over socket connection

        Parameters
        ---------
        msg: any
            A message that will be printed to the node logs. Usually a str.
        """
        self.log.info(msg)

    def on_connect(self):
        """ Actions to be taken on socket connect (or reconnect) event """
        self.log.info('(Re)Connected to the /tasks namespace')
        self.node_worker_ref.sync_task_queue_with_server()
        self.log.debug("Tasks synced again with the server...")
        self.node_worker_ref.share_node_details()

    def on_disconnect(self):
        """ Actions to be taken on socket disconnect event. """
        # self.node_worker_ref.socketIO.disconnect()
        self.log.info('Disconnected from the server')

    def on_new_task(self, task_id: int):
        """
        Actions to be taken when node is notified of new task by server

        Parameters
        ----------
        task_id: int
            ID of the new task
        """
        if self.node_worker_ref:
            self.node_worker_ref.get_task_and_add_to_queue(task_id)
            self.log.info(f'New task has been added task_id={task_id}')

        else:
            self.log.critical(
                'Node reference is not set in socket namespace; cannot create '
                'new task!'
            )

    def on_algorithm_status_change(self, data):
        """
        Actions to be taken when an algorithm container in the collaboration
        has changed its status.

        Parameters
        ----------
        data: Dict
            Dictionary with relevant data to the status change. Should include:
            job_id: int
                job_id of the algorithm container that changed status
            status: str
                New status of the algorithm container
        """
        status = data.get('status')
        job_id = data.get('job_id')
        if has_task_failed(status):
            # TODO handle run sequence at this node. Maybe terminate all
            #     containers with the same job_id?
            self.log.critical(
                f"A container on a node within your collaboration part of "
                f"job_id={job_id} has exited with status '{status}'"
            )
        # else: no need to do anything when a task has started/finished/... on
        # another node

    def on_expired_token(self):
        """
        Action to be taken when node is notified by server that its token
        has expired.
        """
        self.log.warning("Your token is no longer valid... reconnecting")
        self.node_worker_ref.socketIO.disconnect()
        self.log.debug("Old socket connection terminated")
        self.node_worker_ref.client.refresh_token()
        self.log.debug("Token refreshed")
        self.node_worker_ref.connect_to_socket()
        self.log.debug("Connected to socket")
        self.node_worker_ref.sync_task_queue_with_server()
        self.log.debug("Tasks synced again with the server...")

    def on_kill_containers(self, kill_info: dict):
        """
        Action to be taken when nodes are instructed by server to kill one or
        more tasks

        kill_info: dict
            A dictionary that contains information on which tasks should be
            killed. This information may instruct a node to kill all its tasks
            or include a list of which tasks should be killed.
        """
        self.log.info(f"Received instruction to kill task: {kill_info}")
        killed_ids = self.node_worker_ref.kill_containers(kill_info)
        for killed in killed_ids:
            self.emit(
                "algorithm_status_change",
                {
                    'run_id': killed.run_id,
                    'task_id': killed.task_id,
                    'collaboration_id':
                        self.node_worker_ref.client.collaboration_id,
                    'node_id': self.node_worker_ref.client.whoami.id_,
                    'status': TaskStatus.KILLED,
                    'organization_id':
                        self.node_worker_ref.client.whoami.organization_id,
                    'parent_id': killed.parent_id,
                },
                namespace='/tasks'
            )
