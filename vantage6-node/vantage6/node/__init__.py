""" Node

A node in its simplest would retrieve a task from the central server by
an API call, run this task and finally return the results to the central
server again.

The node application is seperated in 4 threads:
- main thread, waits for new tasks to be added to the queue and
    run the tasks
- listening thread, listens for incommin websocket messages. Which
    are handled by NodeTaskNamespace.
- speaking thread, waits for results from docker to return and posts
    them at the central server
- proxy server thread, provides an interface for master containers
    to post tasks and retrieve results
"""
import sys
import os
import random
import time
import datetime
import logging
import queue
import json

from pathlib import Path
from threading import Thread
from socketio import ClientNamespace, Client as SocketIO
from gevent.pywsgi import WSGIServer
from enum import Enum

from vantage6.common.docker_addons import (
    ContainerKillListener, check_docker_running
)
from vantage6.common.globals import VPN_CONFIG_FILE
from vantage6.node.globals import NODE_PROXY_SERVER_HOSTNAME
from vantage6.node.server_io import NodeClient
from vantage6.node.proxy_server import app
from vantage6.node.util import logger_name
from vantage6.node.docker.docker_manager import DockerManager
from vantage6.node.docker.network_manager import IsolatedNetworkManager
from vantage6.node.docker.vpn_manager import VPNManager


class VPNConnectMode(Enum):
    FIRST_TRY = 1
    REFRESH_KEYPAIR = 2
    REFRESH_COMPLETE = 3


class NodeTaskNamespace(ClientNamespace):
    """Class that handles incoming websocket events."""

    # reference to the node objects, so a callback can edit the
    # node instance.
    node_worker_ref = None

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
        self.node_worker_ref.sync_task_queue_with_server()
        self.log.debug("Tasks synced again with the server...")

    def on_disconnect(self):
        """ Server disconnects event."""
        # self.node_worker_ref.socketIO.disconnect()
        self.log.info('Disconnected from the server')

    def on_new_task(self, task_id):
        """ New task event."""
        if self.node_worker_ref:
            self.node_worker_ref.get_task_and_add_to_queue(task_id)
            self.log.info(f'New task has been added task_id={task_id}')

        else:
            self.log.critical(
                'Task Master Node reference not set is socket namespace'
            )

    def on_container_failed(self, run_id):
        """A container in the collaboration has failed event.

        TODO handle run sequence at this node. Maybe terminate all
            containers with the same run_id?
        """
        self.log.critical(
            f"A container on a node within your collaboration part of "
            f"run_id={run_id} has exited with a non-zero status_code"
        )

    def on_expired_token(self, msg):
        self.log.warning("Your token is no longer valid... reconnecting")
        self.node_worker_ref.socketIO.disconnect()
        self.log.debug("Old socket connection terminated")
        self.node_worker_ref.server_io.refresh_token()
        self.log.debug("Token refreshed")
        self.node_worker_ref.connect_to_socket()
        self.log.debug("Connected to socket")
        self.node_worker_ref.sync_task_queue_with_server()
        self.log.debug("Tasks synced again with the server...")


# ------------------------------------------------------------------------------
class Node(object):
    """Node to handle incomming computation requests.

    The main steps this application follows: 1) retrieve (new) tasks
    from the central server, 2) kick-off docker algorithm containers
    based on this task and 3) retrieve the docker results and post
    them to the central server.

    TODO: read allowed repositories from the config file
    """

    def __init__(self, ctx):
        """ Initialize a new Node instance.

            Authenticates to the central server, setup encrpytion, a
            websocket connection, retrieving task that were posted while
            offline, preparing dataset for usage and finally setup a
            local proxy server.

            :param ctx: application context, see utils
        """
        self.log = logging.getLogger(logger_name(__name__))

        self.ctx = ctx

        # Initialize the node. If it crashes, shut down the parts that started
        # already
        try:
            self.initialize()
        except Exception as e:
            self.cleanup()
            raise

    def initialize(self):
        # check if docker is running, otherwise exit with error
        check_docker_running()

        self.config = self.ctx.config
        self.queue = queue.Queue()
        self._using_encryption = None

        # initialize Node connection to the server
        self.server_io = NodeClient(
            host=self.config.get('server_url'),
            port=self.config.get('port'),
            path=self.config.get('api_path')
        )

        self.log.info(f"Connecting server: {self.server_io.base_path}")

        # Authenticate with the server, obtaining a JSON Web Token.
        # Note that self.authenticate() blocks until it succeeds.
        self.log.debug("Authenticating")
        self.authenticate()

        # Setup encryption
        self.setup_encryption()

        # Thread for proxy server for algorithm containers, so they can
        # communicate with the central server.
        self.log.info("Setting up proxy server")
        t = Thread(target=self.__proxy_server_worker, daemon=True)
        t.start()

        # Create a long-lasting websocket connection.
        self.log.debug("Creating websocket connection with the server")
        self.connect_to_socket()

        # setup docker isolated network manager
        isolated_network_mgr = \
            IsolatedNetworkManager(self.ctx.docker_network_name)

        # Setup tasks dir
        self._set_task_dir(self.ctx)

        # Setup VPN connection
        self.vpn_manager = self.setup_vpn_connection(
            isolated_network_mgr, self.ctx)

        # setup the docker manager
        self.log.debug("Setting up the docker manager")
        self.__docker = DockerManager(
            ctx=self.ctx,
            isolated_network_mgr=isolated_network_mgr,
            vpn_manager=self.vpn_manager,
            tasks_dir=self.__tasks_dir
        )

        # Connect the node to the isolated algorithm network *only* if we're
        # running in a docker container.
        if self.ctx.running_in_docker:
            isolated_network_mgr.connect(
                container_name=self.ctx.docker_container_name,
                aliases=[NODE_PROXY_SERVER_HOSTNAME]
            )

        # Thread for sending results to the server when they come available.
        self.log.debug("Start thread for sending messages (results)")
        t = Thread(target=self.__speaking_worker, daemon=True)
        t.start()

        # listen forever for incoming messages, tasks are stored in
        # the queue.
        self.log.debug("Starting thread for incoming messages (tasks)")
        t = Thread(target=self.__listening_worker, daemon=True)
        t.start()

        self.log.info('Init complete')

    def __proxy_server_worker(self):
        """ Proxy algorithm container communcation.

            A proxy for communication between algorithms and central
            server.
        """
        # supply the proxy server with a destination (the central server)
        # we might want to not use enviroment vars
        os.environ["SERVER_URL"] = self.server_io.host
        os.environ["SERVER_PORT"] = self.server_io.port
        os.environ["SERVER_PATH"] = self.server_io.path

        if self.ctx.running_in_docker:
            # NODE_PROXY_SERVER_HOSTNAME points to the name of the proxy
            # when running in the isolated docker network.
            default_proxy_host = NODE_PROXY_SERVER_HOSTNAME
        else:
            # If we're running non-dockerized, assume that the proxy is
            # accessible from within the docker algorithm container on
            # host.docker.internal.
            default_proxy_host = 'host.docker.internal'

        # If PROXY_SERVER_HOST was set in the environment, it overrides our
        # value.
        proxy_host = os.environ.get("PROXY_SERVER_HOST", default_proxy_host)
        os.environ["PROXY_SERVER_HOST"] = proxy_host

        proxy_port = int(os.environ.get("PROXY_SERVER_PORT", 8080))

        # 'app' is defined in vantage6.node.proxy_server
        # app.debug = True
        app.config["SERVER_IO"] = self.server_io

        # this is where we try to find a port for the proxyserver
        for try_number in range(5):
            self.log.info(
                f"Starting proxyserver at '{proxy_host}:{proxy_port}'")
            http_server = WSGIServer(('0.0.0.0', proxy_port), app)

            try:
                http_server.serve_forever()

            except OSError as e:
                self.log.debug(f'Error during attempt {try_number}')
                self.log.debug(f'{type(e)}: {e}')

                if e.errno == 48:
                    proxy_port = random.randint(2048, 16384)
                    self.log.critical(
                        f"Retrying with a different port: {proxy_port}")
                    os.environ['PROXY_SERVER_PORT'] = str(proxy_port)

                else:
                    raise

            except Exception as e:
                self.log.error('Proxyserver could not be started or crashed!')
                self.log.error(e)

    def sync_task_queue_with_server(self):
        """ Get all unprocessed tasks from the server for this node."""
        assert self.server_io.cryptor, "Encrpytion has not been setup"

        # request open tasks from the server
        tasks = self.server_io.get_results(state="open", include_task=True)
        self.log.debug(tasks)
        for task in tasks:
            self.queue.put(task)

        self.log.info(f"received {self.queue._qsize()} tasks")

    def __start_task(self, taskresult):
        """Start a task.

            Start the docker image and notify the server that the task
            has been started.

            :param taskresult: an empty taskresult
        """
        task = taskresult['task']
        self.log.info("Starting task {id} - {name}".format(**task))

        # notify that we are processing this task
        self.server_io.set_task_start_time(taskresult["id"])

        token = self.server_io.request_token_for_container(
            task["id"],
            task["image"]
        )
        token = token["container_token"]

        # create a temporary volume for each run_id
        # FIXME: why is docker_temporary_volume_name() in ctx???
        vol_name = self.ctx.docker_temporary_volume_name(task["run_id"])
        self.__docker.create_volume(vol_name)

        # For some reason, if the key 'input' consists of JSON, it is
        # automatically marshalled? This causes trouble, so we'll serialize it
        # again.
        # FIXME: should probably find & fix the root cause?
        if type(taskresult['input']) == dict:
            taskresult['input'] = json.dumps(taskresult['input'])

        # Run the container. This adds the created container/task to the list
        # __docker.active_tasks
        vpn_ports = self.__docker.run(
            result_id=taskresult["id"],
            image=task["image"],
            docker_input=taskresult['input'],
            tmp_vol_name=vol_name,
            token=token,
            database=task.get('database', 'default')
        )

        if vpn_ports:
            # Save port of VPN client container at which it redirects traffic
            # to the algorithm container. First delete any existing port
            # assignments in case algorithm has crashed
            self.server_io.request(
                'port', params={'result_id': taskresult['id']}, method="DELETE"
            )
            for port in vpn_ports:
                port['result_id'] = taskresult['id']
                self.server_io.request('port', method='POST', json=port)

            # Save IP address of VPN container
            node_id = self.server_io.whoami.id_
            node_ip = self.vpn_manager.get_vpn_ip()
            self.server_io.request(
                f"node/{node_id}", json={"ip": node_ip}, method="PATCH"
            )

    def __listening_worker(self):
        """ Listen for incoming (websocket) messages from the server.

            Runs in a separate thread. Received events are dispatched
            through the appropriate action_handler for a channel.
        """
        self.log.debug("Listening for incoming messages")

        # FIXME: while True in combination with a wait() call that never exits
        #   makes joining the tread (to terminate) difficult?
        while True:
            # incoming messages are handled by the action_handler instance
            # which is attached when the socket connection was made. wait()
            # is blocks forever (if no time is specified).
            try:
                self.socketIO.wait()
            except Exception as e:
                self.log.error('Listening thread had an exception')
                self.log.debug(e)

    def __speaking_worker(self):
        """ Sending messages to central server.

            Routine that is in a seperate thread sending results
            to the server when they come available.

            TODO change to a single request, might need to reconsider
                the flow
        """
        self.log.debug("Waiting for results to send to the server")

        while True:
            try:
                results = self.__docker.get_result()

                # notify all of a crashed container
                if results.status_code:
                    self.socketIO.emit(
                        'container_failed',
                        data={
                            'node_id': self.server_io.whoami.id_,
                            'status_code': results.status_code,
                            'result_id': results.result_id,
                            'collaboration_id': self.server_io.collaboration_id
                        },
                        namespace='/tasks'
                    )

                self.log.info(
                    f"Sending result (id={results.result_id}) to the server!")

                # FIXME: why are we retrieving the result *again*? Shouldn't we
                # just store the task_id when retrieving the task the first time?
                response = self.server_io.request(f"result/{results.result_id}")
                task_id = response.get("task").get("id")

                if not task_id:
                    self.log.error(
                        f"task_id of result (id={results.result_id}) "
                        f"could not be retrieved"
                    )
                    return

                response = self.server_io.request(f"task/{task_id}")
                initiator_id = response.get("initiator")

                if not initiator_id:
                    self.log.error(
                        f"Initiator id from task (id={task_id})could not be "
                        f"retrieved"
                    )

                self.server_io.patch_results(
                    id=results.result_id,
                    initiator_id=initiator_id,
                    result={
                        'result': results.data,
                        'log': results.logs,
                        'finished_at': datetime.datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                self.log.error('Speaking thread had an exception')
                self.log.debug(e)

    def authenticate(self):
        """ Authenticate to the central server

            Authenticate with the server using the api-key. If the
            server rejects for any reason we keep trying.
        """
        api_key = self.config.get("api_key")

        success = False
        i = 0
        while i < 10:
            i = i + 1
            try:
                self.server_io.authenticate(api_key)

            except Exception as e:
                msg = 'Authentication failed. Retrying in 10 seconds!'
                self.log.warning(msg)
                self.log.debug(e)
                time.sleep(10)

            else:
                # This is only executed if try-block executed without error.
                success = True
                break

        if success:
            self.log.info(f"Node name: {self.server_io.name}")
        else:
            self.log.critical('Unable to authenticate. Exiting')
            exit(1)

    def private_key_filename(self):
        """Get the path to the private key."""

        # FIXME: Code duplication: vantage6/cli/node.py uses a lot of the same
        #   logic. Suggest moving this to ctx.get_private_key()
        filename = self.config['encryption']["private_key"]

        # filename may be set to an empty string
        if not filename:
            filename = 'private_key.pem'

        # If we're running dockerized, the location may have been overridden
        filename = os.environ.get('PRIVATE_KEY', filename)

        # If ctx.get_data_file() receives an absolute path, its returned as-is
        fullpath = Path(self.ctx.get_data_file(filename))

        return fullpath

    def setup_encryption(self):
        """Setup encryption ... or don't."""
        encrypted_collaboration = self.server_io.is_encrypted_collaboration()
        encrypted_node = self.config['encryption']["enabled"]

        if encrypted_collaboration != encrypted_node:
            # You can't force it if it just ain't right, you know?
            raise Exception("Expectations on encryption don't match?!")

        if encrypted_collaboration:
            self.log.warn('Enabling encryption!')
            private_key_file = self.private_key_filename()
            self.server_io.setup_encryption(private_key_file)

        else:
            self.log.warn('Disabling encryption!')
            self.server_io.setup_encryption(None)

    def _set_task_dir(self, ctx) -> None:
        """
        Set the task dir

        Parameters
        ----------
        ctx: DockerNodeContext or NodeContext
            Context object containing settings
        """
        # If we're in a 'regular' context, we'll copy the dataset to our data
        # dir and mount it in any algorithm container that's run; bind mounts
        # on a folder will work just fine.
        #
        # If we're running in dockerized mode we *cannot* bind mount a folder,
        # because the folder is in the container and not in the host. We'll
        # have to use a docker volume instead. This means:
        #  1. we need to know the name of the volume so we can pass it along
        #  2. need to have this volume mounted so we can copy files to it.
        #
        #  Ad 1: We'll use a default name that can be overridden by an
        #        environment variable.
        #  Ad 2: We'll expect `ctx.data_dir` to point to the right place. This
        #        is OK, since ctx will be a DockerNodeContext.
        #
        #  This also means that the volume will have to be created & mounted
        #  *before* this node is started, so we won't do anything with it here.

        # We'll create a subfolder in the data_dir. We need this subfolder so
        # we can easily mount it in the algorithm containers; the root folder
        # may contain the private key, which which we don't want to share.
        # We'll only do this if we're running outside docker, otherwise we
        # would create '/data' on the data volume.
        if not ctx.running_in_docker:
            self.__tasks_dir = ctx.data_dir / 'data'
            os.makedirs(self.__tasks_dir, exist_ok=True)
            self.__vpn_dir = ctx.data_dir / 'vpn'
            os.makedirs(self.__vpn_dir, exist_ok=True)
        else:
            self.__tasks_dir = ctx.data_dir
            self.__vpn_dir = ctx.vpn_dir

    def setup_vpn_connection(
            self, isolated_network_mgr: IsolatedNetworkManager, ctx
    ) -> VPNManager:
        """
        Setup container which has a VPN connection

        Returns
        -------
        VPNManager
            Manages the VPN connection
        """
        ovpn_file = os.path.join(self.__vpn_dir, VPN_CONFIG_FILE)

        self.log.debug("Setting up VPN client container")
        vpn_volume_name = self.ctx.docker_vpn_volume_name \
            if ctx.running_in_docker else self.__vpn_dir
        vpn_manager = VPNManager(
            isolated_network_mgr=isolated_network_mgr,
            node_name=self.ctx.name,
            vpn_volume_name=vpn_volume_name,
            vpn_subnet=self.config.get('vpn_subnet')
        )
        # if vpn config doesn't exist, get it and write to disk
        if not os.path.isfile(ovpn_file):
            self._connect_vpn(vpn_manager, VPNConnectMode.REFRESH_COMPLETE,
                              ovpn_file)
        else:
            self._connect_vpn(vpn_manager, VPNConnectMode.FIRST_TRY, ovpn_file)

        return vpn_manager

    def _connect_vpn(self, vpn_manager: VPNManager,
                     connect_mode: VPNConnectMode, ovpn_file: str) -> None:
        """
        Connect to the VPN by starting up a VPN client container. If no VPN
        config file exists, we only try once after first obtaining a config
        file. If a VPN config file already exists, we first try to connect,
        then try to refresh the keypair, and finally try to renew the entire
        config file, until a connection is established.

        Parameters
        ----------
        vpn_manager: VPNManager
            Manages the VPN connection
        connect_mode: VPNConnectMode
            Specifies which parts of a config file to refresh before attempting
            to connect
        ovpn_file: str
            Path to the VPN configuration file
        """
        do_try = True
        if connect_mode == VPNConnectMode.FIRST_TRY:
            self.log.debug("Using existing config file to connect to VPN")
            next_mode = VPNConnectMode.REFRESH_KEYPAIR
        elif connect_mode == VPNConnectMode.REFRESH_KEYPAIR:
            self.log.debug("Refreshing VPN keypair...")
            do_try = self.server_io.refresh_vpn_keypair(ovpn_file=ovpn_file)
            next_mode = VPNConnectMode.REFRESH_COMPLETE
        elif connect_mode == VPNConnectMode.REFRESH_COMPLETE:
            self.log.debug("Requesting new VPN configuration file...")
            do_try = self._get_vpn_config_file(ovpn_file)
            next_mode = None  # if new config file doesn't work, give up

        if do_try:
            # try connecting to VPN
            try:
                vpn_manager.connect_vpn()
            except Exception as e:
                self.log.debug("Could not connect to VPN.")
                self.log.debug(f"Exception: {e}")
                # try again in another fashion
                if next_mode:
                    self._connect_vpn(vpn_manager, next_mode, ovpn_file)

    def _get_vpn_config_file(self, ovpn_file: str) -> bool:
        """
        Obtain VPN configuration file from the server

        Parameters
        ----------
        ovpn_file: str
            Path to the VPN configuration file

        Returns
        -------
        bool
            Whether or not configuration file was successfully obtained
        """
        # get the ovpn configuration from the server
        success, ovpn_config = self.server_io.get_vpn_config()
        if not success:
            self.log.warn("Obtaining VPN configuration file not successful!")
            self.log.warn("Disabling node-to-node communication via VPN")
            return False

        # write ovpn config to node docker volume
        with open(ovpn_file, 'w') as f:
            f.write(ovpn_config)
        return True

    def connect_to_socket(self):
        """ Create long-lasting websocket connection with the server.

            The connection is used to receive status updates, such as
            new tasks.
        """

        self.socketIO = SocketIO(request_timeout=60)

        self.socketIO.register_namespace(NodeTaskNamespace('/tasks'))
        NodeTaskNamespace.node_worker_ref = self

        self.socketIO.connect(
            url=f'{self.server_io.host}:{self.server_io.port}',
            headers=self.server_io.headers,
        )

        # Log the outcome
        while not self.socketIO.connected:
            self.log.debug('Waiting for socket connection...')
            time.sleep(1)

        self.log.info(f'Connected to host={self.server_io.host} on port='
                      f'{self.server_io.port}')

    def get_task_and_add_to_queue(self, task_id):
        """Fetches (open) task with task_id from the server.

            The `task_id` is delivered by the websocket-connection.
        """

        # fetch (open) result for the node with the task_id
        tasks = self.server_io.get_results(
            include_task=True,
            state='open',
            task_id=task_id
        )

        # in the current setup, only a single result for a single node
        # in a task exists.
        for task in tasks:
            self.queue.put(task)

    def run_forever(self):
        """Forever check self.queue for incoming tasks (and execute them)."""
        kill_listener = ContainerKillListener()
        try:
            while True:
                # blocking untill a task comes available
                # timeout specified, else Keyboard interupts are ignored
                self.log.info("Waiting for new tasks....")

                while not kill_listener.kill_now:
                    try:
                        task = self.queue.get(timeout=1)
                        # if no item is returned, the Empty exception is
                        # triggered, thus break statement is not reached
                        break

                    except queue.Empty:
                        pass

                    except Exception as e:
                        self.log.debug(e)

                if kill_listener.kill_now:
                    raise InterruptedError

                # if task comes available, attempt to execute it
                try:
                    self.__start_task(task)
                except Exception as e:
                    self.log.exception(e)

        except (KeyboardInterrupt, InterruptedError):
            self.log.info("Vnode is interrupted, shutting down...")
            self.cleanup()
            sys.exit()

    def cleanup(self):
        if hasattr(self, 'socketIO') and self.socketIO:
            self.socketIO.disconnect()
        if hasattr(self, 'vpn_manager') and self.vpn_manager:
            self.vpn_manager.exit_vpn()
        if hasattr(self, '_Node__docker') and self.__docker:
            self.__docker.cleanup()


# ------------------------------------------------------------------------------
def run(ctx):
    """ Start the node."""
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("engineio.client").setLevel(logging.WARNING)

    # initialize node, connect to the server using websockets
    node = Node(ctx)

    # put the node to work, executing tasks that are in the que
    node.run_forever()
