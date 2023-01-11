import logging
from typing import Dict
import jwt

from flask import request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import Namespace, emit, join_room, leave_room

from vantage6.common import logger_name
from vantage6.common.task_status import has_task_failed
from vantage6.server import db
from vantage6.server.model.authenticable import Authenticatable
from vantage6.server.model.rule import Operation, Scope


class DefaultSocketNamespace(Namespace):
    """
    Handlers for SocketIO events are different than handlers for routes and
    that introduces a lot of confusion around what can and cannot be done in a
    SocketIO handler. The main difference is that all the SocketIO events
    generated for a client occur in the context of a single long running
    request.
    """
    socketio = None

    log = logging.getLogger(logger_name(__name__))

    def on_connect(self):
        """
        A new incomming connection request from a client.

        New incomming connections are authenticated using their
        JWT authorization token which is obtained from the REST api.
        A session is created for each connected clients which lives
        as long as the connection is active. There has not been made
        any difference between connecting and re-connecting.
        """

        self.log.info(f'Client connected: "{request.sid}"')

        # try to catch jwt authorization token.
        try:
            verify_jwt_in_request()

        except jwt.exceptions.ExpiredSignatureError:
            self.log.error("JWT has expired")
            emit("expired_token", room=request.sid)
            return

        except Exception as e:
            self.log.error("Couldn't connect client! No or Invalid JWT token?")
            self.log.exception(e)
            session.name = "not-sure-yet"
            self.__join_room_and_notify(request.sid)

            # FIXME: expired probably doesn't cover it ...
            emit("expired_token", room=request.sid)
            return

        # get identity from token.
        session.auth_id = get_jwt_identity()
        auth = db.Authenticatable.get(session.auth_id)
        auth.status = 'online'
        auth.save()

        # It appears to be necessary to use the root socketio instance
        # otherwise events cannot be sent outside the current namespace.
        # In this case, only events to '/tasks' can be emitted otherwise.
        if auth.type == 'node':
            self.socketio.emit('node-status-changed', namespace='/admin')

        # define socket-session variables.
        session.type = auth.type
        session.name = auth.username if session.type == 'user' else auth.name
        self.log.info(
            f'Client identified as <{session.type}>: <{session.name}>'
        )

        # join appropiate rooms
        session.rooms = []
        if session.type == 'node':
            self._add_node_to_rooms(auth)
            self.__alert_node_status(online=True, node=auth)
        elif session.type == 'user':
            self._add_user_to_rooms(auth)

        for room in session.rooms:
            self.__join_room_and_notify(room)

    @staticmethod
    def _add_node_to_rooms(node: Authenticatable):
        """ Connect node to appropriate websocket rooms """
        # node join rooms for all nodes and rooms for their collaboration
        session.rooms.append('all_nodes')
        session.rooms.append(f'collaboration_{node.collaboration_id}')
        session.rooms.append(
            f'collaboration_{node.collaboration_id}_organization_'
            f'{node.organization_id}')

    @staticmethod
    def _add_user_to_rooms(user: Authenticatable):
        # check for which collab rooms the user has permission to enter
        session.user = db.User.get(session.auth_id)
        if session.user.can('event', Scope.GLOBAL, Operation.VIEW):
            # user joins all collaboration rooms
            collabs = db.Collaboration.get()
            for collab in collabs:
                session.rooms.append(f'collaboration_{collab.id}')
        elif session.user.can(
                'event', Scope.COLLABORATION, Operation.VIEW):
            # user joins all collaboration rooms that their organization
            # participates in
            for collab in user.organization.collaborations:
                session.rooms.append(f'collaboration_{collab.id}')
        elif session.user.can('event', Scope.ORGANIZATION, Operation.VIEW):
            # user joins collaboration subrooms that include only messages
            # relevant to their own node
            for collab in user.organization.collaborations:
                session.rooms.append(
                    f'collaboration_{collab.id}_organization_'
                    f'{user.organization.id}'
                )

    def on_disconnect(self):
        """
        Client that disconnects needs to leave all rooms.
        """
        for room in session.rooms:
            # self.__leave_room_and_notify(room)
            self.__leave_room_and_notify(room)

        auth = db.Authenticatable.get(session.auth_id)
        auth.status = 'offline'
        auth.save()

        # It appears to be necessary to use the root socketio instance
        # otherwise events cannot be sent outside the current namespace.
        # In this case, only events to '/tasks' can be emitted otherwise.
        if session.type == 'node':
            self.log.warning('emitting to /admin')
            self.socketio.emit('node-status-changed', namespace='/admin')
            self.__alert_node_status(online=False, node=auth)

        self.log.info(f'{session.name} disconnected')

    def on_message(self, message: str):
        """
        An incomming message from any client.

        Parameters
        ----------
        message : str
            message that is going to be displayed in the server-log
        """
        self.log.info('received message: ' + message)

    def on_error(self, e: str):
        """
        An incomming error from any of the client.

        Parameters
        ----------
        e : str
            error message that is being displayed in the server log
        """
        self.log.error(e)

    def on_join_room(self, room: str):
        """
        Let clients join any room they like by specifying the name.

        Parameters
        ----------
        room : str
            name of the room the client wants to join
        """
        self.__join_room_and_notify(room)

    def on_algorithm_status_change(self, data: Dict):
        """
        An algorithm container has changed its status.

        This status change may be that the algorithm has finished, crashed,
        etc. Here we notify the collaboration of the change.

        Parameters
        ----------
        data: Dict
            Dictionary containing parameters on the updated algorithm status.
            It should contain:
            node_id : int
                node_id where the algorithm container was running
            status : int
                New status of the algorithm container
            result_id : int
                result_id for which the algorithm was running
            collaboration_id : int
                collaboration for which the algorithm was running
        """
        result_id = data.get('result_id')
        task_id = data.get('task_id')
        collaboration_id = data.get('collaboration_id')
        status = data.get('status')
        node_id = data.get('node_id')
        organization_id = data.get('organization_id')
        parent_id = data.get('parent_id')

        run_id = db.Result.get(result_id).task.run_id

        # log event in server logs
        msg = (f"A container for run_id={run_id} and result_id={result_id} "
               f"in collaboration_id={collaboration_id} on node_id={node_id}")
        if has_task_failed(status):
            self.log.critical(f"{msg} exited with status={status}.")
        else:
            self.log.info(f"{msg} has a new status={status}.")

        # emit task status change to other nodes/users in the collaboration
        emit(
            "algorithm_status_change", {
                "status": status,
                "result_id": result_id,
                "task_id": task_id,
                "run_id": run_id,
                "collaboration_id": collaboration_id,
                "node_id": node_id,
                "organization_id": organization_id,
                "parent_id": parent_id,
            }, room=f"collaboration_{collaboration_id}"
        )

    def __join_room_and_notify(self, room: str):
        """
        Joins room and notify other clients in this room.

        Parameters
        ----------
        room : str
            name of the room the client want to join
        """
        join_room(room)
        msg = f'{session.type.title()} <{session.name}> joined room <{room}>'
        self.log.info(msg)
        emit('message', msg, room=room)

    def __leave_room_and_notify(self, room: str):
        """
        Leave room and notify other clients in this room.

        Parameters
        ----------
        room : str
            name of the room the client is leaving
        """
        leave_room(room)
        msg = f'{session.name} left room {room}'
        self.log.info(msg)
        emit('message', msg, room=room)

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
        event = 'node-online' if online else 'node-offline'
        for room in session.rooms:
            self.socketio.emit(
                event,
                {
                    'id': node.id, 'name': node.name,
                    'org_id': node.organization.id
                },
                namespace='/tasks',
                room=room
            )
