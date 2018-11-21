import logging

from pytaskmanager.server import db
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_socketio import join_room, send, leave_room, emit, Namespace
from flask import session, request


class DefaultSocketNamespace(Namespace):
    """ Class to define the different actions of the websocket.
    Needs to be attached to a SocketIO class which manages the
    connections.
    """

    log = logging.getLogger("socket.io")

    def on_connect(self):
        """New incomming connections are authenticated using their
        JWT authorization token which is obtained from the REST api.
        A session is created for each connected clients which lives 
        as long as the connection is active. There has not been made
        any difference between connecting and re-connecting.
        """
                
        self.log.info(f'Client connected: "{request.sid}"')

        # try to catch jwt authorization token.
        try:
            verify_jwt_in_request()
        except Exception as e:
            self.log.error("Could not connect client! No or Invalid JWT token?")
            self.log.exception(e)

        # get identity from token.
        user_or_node_id = get_jwt_identity()
        auth = db.Authenticatable.get(user_or_node_id)

        # define socket-session variables.
        session.type = auth.type
        session.name = auth.username if session.type == 'user' else auth.name
        self.log.info(f'Client identified as <{session.type}>: <{session.name}>')
        
        # join appropiate rooms, nodes join a specific collaboration room.
        # users do not belong to specific collaborations. 
        session.rooms = ['all_connections', 'all_'+session.type+'s']
        if session.type == 'node':
            session.rooms.append('collaboration_' + str(auth.collaboration_id))
        for room in session.rooms:
            self.__join_room_and_notify(room)

    def on_disconnect(self):
        for room in session.rooms:
            self.__leave_room_and_notify(room)
        self.log.info(f'{session.name} disconnected')

    def on_message(self, message):
        self.log.info('received message: ' + message)

    def on_error(self, e):
        self.log.error(e)

    def __join_room_and_notify(self, room):
        join_room(room)
        msg = f'<{session.name}> joined room <{room}>'
        self.log.info(msg)
        emit('message', msg, room=room)

    def __leave_room_and_notify(self, room):
        leave_room(room)
        msg = f'{session.name} left room {room}'
        self.log.info(msg)
        emit('message', msg, room=room)
