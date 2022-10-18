import logging
from typing import Dict
import jwt

from flask import request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import Namespace, emit, join_room, leave_room

from vantage6.common import logger_name
from vantage6.server import db


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
            emit("expired_token", "", room=request.sid)
            return

        except Exception as e:
            self.log.error("Couldn't connect client! No or Invalid JWT token?")
            self.log.exception(e)
            session.name = "no-sure-yet"
            self.__join_room_and_notify(request.sid)

            # FIXME: expired probably doesn't cover it ...
            emit("expired_token", "", room=request.sid)
            return

        # get identity from token.
        session.auth_id = get_jwt_identity()
        auth = db.Authenticatable.get(session.auth_id)
        auth.status = 'online'
        auth.save()


        # define socket-session variables.
        session.type = auth.type
        session.name = auth.username if session.type == 'user' else auth.name
        self.log.info(
            f'Client identified as <{session.type}>: <{session.name}>'
        )

        # It appears to be necessary to use the root socketio instance
        # otherwise events cannot be sent outside the current namespace.
        # In this case, only events to '/tasks' can be emitted otherwise.
        if session.type == 'node':
            self.socketio.emit('node-status-changed', namespace='/admin')

        # join appropiate rooms, nodes join a specific collaboration room.
        # users do not belong to specific collaborations.
        session.rooms = ['all_connections', 'all_'+session.type+'s']

        if session.type == 'node':
            session.rooms.append('collaboration_' + str(auth.collaboration_id))
            session.rooms.append('node_' + str(auth.id))
        elif session.type == 'user':
            session.rooms.append('user_'+str(auth.id))

        for room in session.rooms:
            self.__join_room_and_notify(room)

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

    def on_container_failed(self, data: Dict):
        """
        An algorithm container has crashed at a node.

        This event notifies all nodes, and users that a container has crashed
        in their collaboration.

        Parameters
        ----------
        node_id : int
            node_id where the algorithm container was running
        status_code : int
            status code from the container
        result_id : int
            result_id for which the container was running
        collaboration_id : int
            collaboration for which the task was running
        """
        result_id = data.get('result_id')
        collaboration_id = data.get('collaboration_id')
        status_code = data.get('status_code')
        node_id = data.get('node_id')

        run_id = db.Result.get(result_id).task.run_id

        self.log.critical(
            f"A container in for run_id={run_id} and result_id={result_id}"
            f" within collaboration_id={collaboration_id} on node_id={node_id}"
            f" exited with status_code={status_code}."
        )

        room = "collaboration_"+str(collaboration_id)
        emit("container_failed", run_id, room=room)

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
