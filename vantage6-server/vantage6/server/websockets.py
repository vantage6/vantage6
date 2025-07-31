import datetime as dt
import logging
from socket import SocketIO

import jwt
from flask import request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import Namespace, emit, join_room, leave_room

from vantage6.common import logger_name
from vantage6.common.enum import RunStatus
from vantage6.common.globals import AuthStatus

from vantage6.backend.common.metrics import Metrics

from vantage6.server import db
from vantage6.server.model.authenticatable import Authenticatable
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.model.dataframe_to_be_deleted_at_node import (
    DataframeToBeDeletedAtNode,
)
from vantage6.server.model.rule import Operation, Scope

ALL_NODES_ROOM = "all_nodes"


class DefaultSocketNamespace(Namespace):
    """
    This is the default SocketIO namespace. It is used for all the long-running
    socket communication between the server and the clients. The clients of the
    socket connection are nodes and users.

    When socket communication is received from one of the clients, the
    functions in this class are called to execute the corresponding action.
    """

    log = logging.getLogger(logger_name(__name__))

    def __init__(self, namespace, socketio, metrics: Metrics) -> None:
        super().__init__(namespace)
        self.socketio = socketio
        self.metrics = metrics

    def _is_node(self) -> bool:
        if session.type != "node":
            self.log.warn(
                "Only nodes can send algorithm updates! "
                f"{session.type} {session.auth_id} is not allowed."
            )
        return session.type == "node"

    def on_connect(self) -> None:
        """
        A new incoming connection request from a client.

        New connections are authenticated using their JWT authorization token
        which is obtained from the REST API. A session is created for each
        connected client, and lives as long as the connection is active.
        Each client is assigned to rooms based on their permissions.

        Nodes that are connecting are also set to status 'online'.


        Note
        ----
        Note that reconnecting clients are treated the same as new clients.

        """
        self.log.info(f'Client connected: "{request.sid}"')

        # try to catch jwt authorization token.
        try:
            verify_jwt_in_request()

        except jwt.exceptions.ExpiredSignatureError:
            self.log.error("JWT has expired")
            emit("expired_token", room=request.sid)
            return

        except jwt.exceptions.InvalidSignatureError:
            self.log.error("Invalid JWT signature")
            emit("invalid_token", room=request.sid)
            return

        except Exception as exc:
            self.log.error("Couldn't connect client! No or Invalid JWT token?")
            self.log.exception(exc)
            return

        # get identity from token.
        session.auth_id = get_jwt_identity()
        auth = db.Authenticatable.get_by_keycloak_id(session.auth_id)
        auth.status = AuthStatus.ONLINE.value
        auth.save()

        # It appears to be necessary to use the root socketio instance
        # otherwise events cannot be sent outside the current namespace.
        # In this case, only events to '/tasks' can be emitted otherwise.
        if auth.type == "node":
            self.socketio.emit("node-status-changed", namespace="/admin")

        # define socket-session variables.
        session.type = auth.type
        session.name = auth.username if session.type == "user" else auth.name
        self.log.info("Client identified as <%s>: <%s>", session.type, session.name)

        # join appropiate rooms
        session.rooms = []
        if session.type == "node":
            # Ensure that node syncs on initial connection
            emit("sync", room=request.sid)
            # Add node to rooms and alert other clients of that
            self._add_node_to_rooms(auth)
            self.__alert_node_status(online=True, node=auth)
            # send dataframe deletion instructions to node
            self._send_dataframe_deletion_instructions(auth)
        elif session.type == "user":
            self._add_user_to_rooms(auth)

        for room in session.rooms:
            self.__join_room_and_notify(room)

        # cleanup (e.g. database session)
        self.__cleanup()

    @staticmethod
    def _add_node_to_rooms(node: Authenticatable) -> None:
        """
        Connect node to appropriate websocket rooms

        Parameters
        ----------
        node: Authenticatable
            Node that is to be added to the rooms
        """
        # node join rooms for all nodes and rooms for their collaboration
        session.rooms.append(ALL_NODES_ROOM)
        session.rooms.append(f"collaboration_{node.collaboration_id}")
        session.rooms.append(
            f"collaboration_{node.collaboration_id}_organization_{node.organization_id}"
        )

    @staticmethod
    def _add_user_to_rooms(user: Authenticatable) -> None:
        """
        Connect user to appropriate websocket rooms

        Parameters
        ----------
        user: Authenticatable
            User that is to be added to the rooms
        """
        # check for which collab rooms the user has permission to enter
        session.user = db.User.get_by_keycloak_id(session.auth_id)
        if session.user.can("event", Scope.GLOBAL, Operation.RECEIVE):
            # user joins all collaboration rooms
            collabs = db.Collaboration.get()
            for collab in collabs:
                session.rooms.append(f"collaboration_{collab.id}")
        elif session.user.can("event", Scope.COLLABORATION, Operation.RECEIVE):
            # user joins all collaboration rooms that their organization
            # participates in
            for collab in user.organization.collaborations:
                session.rooms.append(f"collaboration_{collab.id}")
        elif session.user.can("event", Scope.ORGANIZATION, Operation.RECEIVE):
            # user joins collaboration subrooms that include only messages
            # relevant to their own node
            for collab in user.organization.collaborations:
                session.rooms.append(
                    f"collaboration_{collab.id}_organization_{user.organization.id}"
                )

    def _send_dataframe_deletion_instructions(self, node: Authenticatable) -> None:
        """
        Send dataframe deletion instructions to a node.
        """
        for dataframe_to_delete in DataframeToBeDeletedAtNode.get_by_node_id(node.id):
            send_delete_dataframe_event(
                self.socketio,
                dataframe_to_delete.dataframe_name,
                dataframe_to_delete.session_id,
                node.collaboration_id,
            )

    def on_disconnect(self) -> None:
        """
        Client that disconnects is removed from all rooms they were in.

        If nodes disconnect, their status is also set to offline and users may
        be alerted to that. Also, any information on the node (e.g.
        configuration) is removed from the database.
        """
        if not self.__is_identified_client():
            self.log.debug("Client disconnected before identification")
            return

        for room in session.rooms:
            # self.__leave_room_and_notify(room)
            self.__leave_room_and_notify(room)

        auth = db.Authenticatable.get_by_keycloak_id(session.auth_id)
        auth.status = AuthStatus.OFFLINE.value
        auth.save()

        # It appears to be necessary to use the root socketio instance
        # otherwise events cannot be sent outside the current namespace.
        # In this case, only events to '/tasks' can be emitted otherwise.
        if session.type == "node":
            self.log.warning("emitting to /admin")
            self.socketio.emit("node-status-changed", namespace="/admin")
            self.__alert_node_status(online=False, node=auth)

            # delete any data on the node stored on the server (e.g.
            # configuration data)
            self.__clean_node_data(auth)

        self.log.info(f"{session.name} disconnected")

        # cleanup (e.g. database session)
        self.__cleanup()

    def on_message(self, message: str) -> None:
        """
        On receiving a message from a client, log it.

        Parameters
        ----------
        message: str
            Message that is going to be displayed in the server log
        """
        self.log.info("received message: " + message)

    def on_error(self, e: str) -> None:
        """
        An receiving an error from a client, log it.

        Parameters
        ----------
        e: str
            Error message that is being displayed in the server log
        """
        self.log.error(e)

    def on_algorithm_status_change(self, data: dict) -> None:
        """
        An algorithm container has changed its status. This status change may
        be that the algorithm has finished, crashed, etc. Here we notify the
        collaboration of the change.

        Parameters
        ----------
        data: Dict
            Dictionary containing parameters on the updated algorithm status.
            It should look as follows:

            .. code:: python

                {
                    # node_id where algorithm container was running
                    "node_id": 1,
                    # new status of algorithm container
                    "status": "active",
                    # result_id for which the algorithm was running
                    "result_id": 1,
                    # collaboration_id for which the algorithm was running
                    "collaboration_id": 1
                }
        """
        if not self._is_node():
            return

        run_id = data.get("run_id")
        task_id = data.get("task_id")
        collaboration_id = data.get("collaboration_id")
        status = data.get("status")
        node_id = data.get("node_id")
        organization_id = data.get("organization_id")
        parent_id = data.get("parent_id")

        run: db.Run = db.Run.get(run_id)
        job_id = run.task.job_id

        # log event in server logs
        msg = (
            f"A container for job_id={job_id} and run_id={run_id} "
            f"in collaboration_id={collaboration_id} on node_id={node_id}"
        )
        if RunStatus.has_failed(status):
            self.log.critical(f"{msg} exited with status={status}.")
        else:
            self.log.info(f"{msg} has a new status={status}.")

        # notify nodes that there is a new task available if there are tasks dependent
        # on this one
        dependent_tasks = run.task.required_by
        if status == RunStatus.COMPLETED and dependent_tasks:
            self.log.debug(
                f"{len(dependent_tasks)} dependent tasks ready to be executed"
            )
            for task in dependent_tasks:
                emit(
                    "new_task_update",
                    {"id": task.id, "parent_id": task.parent_id},
                    room=f"collaboration_{task.collaboration_id}",
                )

        # emit task status change to other nodes/users in the collaboration
        emit(
            "algorithm_status_change",
            {
                "status": status,
                "run_id": run_id,
                "task_id": task_id,
                "job_id": job_id,
                "collaboration_id": collaboration_id,
                "node_id": node_id,
                "organization_id": organization_id,
                "parent_id": parent_id,
            },
            room=f"collaboration_{collaboration_id}",
        )

        # cleanup (e.g. database session)
        self.__cleanup()

    def on_node_info_update(self, node_config: dict) -> None:
        """
        A node sends information about its configuration and other properties.
        Store this in the database for the duration of the node's session.

        Parameters
        ----------
        node_config: dict
            Dictionary containing the node's configuration.
        """
        # only allow nodes to send this event
        if not self._is_node():
            return

        node = db.Node.get_by_keycloak_id(session.auth_id)

        # delete any old data that may be present (if cleanup on disconnect
        # failed)
        self.__clean_node_data(node=node)

        # store (new) node config
        to_store = []
        for k, v in node_config.items():
            # add single item or list of items
            if isinstance(v, list):
                to_store.extend(
                    [db.NodeConfig(node_id=node.id, key=k, value=i) for i in v]
                )
            elif isinstance(v, dict):
                for inner_key, inner_val in v.items():
                    if isinstance(inner_val, list):
                        to_store.extend(
                            [
                                db.NodeConfig(node_id=node.id, key=inner_key, value=val)
                                for val in inner_val
                            ]
                        )
                    else:
                        to_store.append(
                            db.NodeConfig(
                                node_id=node.id, key=inner_key, value=inner_val
                            )
                        )
            else:
                to_store.append(db.NodeConfig(node_id=node.id, key=k, value=v))

        node.config = to_store
        node.save()

        # cleanup (e.g. database session)
        self.__cleanup()

    def on_ping(self) -> None:
        """
        A client sends a ping to the server. The server detects who sent the
        ping and sets them as online.
        """
        auth = db.Authenticatable.get_by_keycloak_id(session.auth_id)
        auth.status = AuthStatus.ONLINE.value
        auth.last_seen = dt.datetime.now(dt.timezone.utc)
        auth.save()

    def on_dataframe_deleted(self, data: dict) -> None:
        """
        A dataframe has been deleted at a node.
        """
        self.log.info(
            "Instruction to delete dataframe %s was executed by node %s",
            data["df_name"],
            data["node_id"],
        )
        df_to_be_deleted = DataframeToBeDeletedAtNode.get_by_multiple_keys(
            data["df_name"], data["session_id"], data["node_id"]
        )
        df_to_be_deleted.delete()

    def __join_room_and_notify(self, room: str) -> None:
        """
        Joins room and notify other clients in this room.

        Parameters
        ----------
        room : str
            name of the room the client want to join
        """
        join_room(room)
        msg = f"{session.type.title()} <{session.name}> joined room <{room}>"
        self.log.info(msg)
        self.__notify_room_join_or_leave(room, msg)

    def __leave_room_and_notify(self, room: str) -> None:
        """
        Leave room and notify other clients in this room.

        Parameters
        ----------
        room : str
            name of the room the client is leaving
        """
        leave_room(room)
        msg = f"{session.name} left room {room}"
        self.log.info(msg)
        self.__notify_room_join_or_leave(room, msg)

    @staticmethod
    def __notify_room_join_or_leave(room: str, msg: str) -> None:
        """
        Notify a room that one of its clients is joining or leaving

        """
        # share message with other users and nodes, except for all_nodes. That
        # room must never be notified for join or leave events since it
        # contains nodes from different collaborations that shouldn't
        # know about each other.
        if room != ALL_NODES_ROOM:
            emit("message", msg, room=room)

    def __alert_node_status(self, online: bool, node: Authenticatable) -> None:
        """
        Send status update of nodes when they change on/offline status

        Parameters
        ----------
        online: bool
            Whether node is coming online or not
        node: Authenticatable
            The node SQLALchemy object
        """
        event = "node-online" if online else "node-offline"
        for room in session.rooms:
            self.socketio.emit(
                event,
                {"id": node.id, "name": node.name, "org_id": node.organization.id},
                namespace="/tasks",
                room=room,
            )

    def on_algorithm_log(self, data: dict) -> None:
        """
        Handle log messages from algorithm containers and log them in the server logs.

        Parameters
        ----------
        data: Dict
            Dictionary containing log message details.
            It should look as follows:

            .. code:: python

                {
                    "collaboration_id": 1,
                    "run_id": 1,
                    "task_id": 1,
                    "log": "Log message"
                }
        """
        if not self._is_node():
            return

        collaboration_id = data.get("collaboration_id")
        run_id = data.get("run_id")
        task_id = data.get("task_id")
        log_message = data.get("log")

        run = db.Run.get(run_id)
        self._append_log(log_message, run)
        run.save()

        emit(
            "algorithm_log",
            {"run_id": run_id, "task_id": task_id, "log": log_message},
            room=f"collaboration_{collaboration_id}",
        )

        self.__cleanup()

    def _append_log(self, log_message, run):
        if run.log:
            if not run.log.endswith("\n"):
                run.log += "\n"
            run.log += log_message
        else:
            run.log = log_message

    def on_node_metrics_update(self, data: dict) -> None:
        """
        Handle metrics sent by nodes and update Prometheus metrics.

        Parameters
        ----------
        data: dict
            Dictionary containing node metrics.
        """
        if not self._is_node():
            return

        node = db.Node.get(session.auth_id)

        os_label = data.pop("os", "unknown")
        platform_label = data.pop("platform", "unknown")
        for metric_name, value in data.items():
            try:
                self.metrics.set_metric(
                    metric_name=metric_name,
                    value=value,
                    labels={
                        "node_id": node.id,
                        "os": os_label,
                        "platform": platform_label,
                    },
                )
            except ValueError as e:
                self.log.warning(f"Invalid metric data: {e}")
            except Exception as e:
                self.log.error(f"Failed to process metric '{metric_name}': {e}")

        self.log.info(f"Updated metrics for node {node.id}")

    @staticmethod
    def __is_identified_client() -> bool:
        """
        Check if client has been identified as an authenticated user or node

        Returns
        -------
        bool
            True if client has been identified, False otherwise
        """
        return hasattr(session, "auth_id")

    @staticmethod
    def __clean_node_data(node: db.Node) -> None:
        """
        Remove any information from the database that the node shared about
        e.g. its configuration

        Parameters
        ----------
        node: db.Node
            The node SQLALchemy object
        """
        for conf in node.config:
            conf.delete()

    @staticmethod
    def __cleanup() -> None:
        """Cleanup database connections"""
        DatabaseSessionManager.clear_session()


def send_delete_dataframe_event(
    socketio: SocketIO, dataframe_name: str, session_id: int, collaboration_id: int
) -> None:
    """
    Send a socket event to the nodes to delete a dataframe.

    Parameters
    ----------
    socketio: SocketIO
        SocketIO instance
    dataframe_name: str
        Name of the dataframe to delete
    session_id: int
        ID of the session that contains the dataframe
    collaboration_id: int
        ID of the collaboration that contains the dataframe
    """
    socketio.emit(
        "delete_dataframe",
        {"df_name": dataframe_name, "session_id": session_id},
        namespace="/tasks",
        room=f"collaboration_{collaboration_id}",
    )
