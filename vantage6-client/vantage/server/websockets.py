import logging

from vantage.server import db
from vantage import server
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_socketio import join_room, send, leave_room, emit, Namespace
from flask import g, session, request

class DefaultSocketNamespace(Namespace):
    """Handlers for SocketIO events are different than handlers for routes and that 
    introduces a lot of confusion around what can and cannot be done in a SocketIO handler. 
    The main difference is that all the SocketIO events generated for a client occur in 
    the context of a single long running request.
    """

    log = logging.getLogger(__name__)

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
            self.__join_room_and_notify(request.sid)
            session.name = "no-sure-yet"
            emit("expired_token", "", room=request.sid)
            return

        # get identity from token.
        user_or_node_id = get_jwt_identity()
        session.auth = auth = db.Authenticatable.get(user_or_node_id)
        session.auth.status = 'online'
        session.auth.save()

        # It appears to be necessary to use the root socketio instance
        # otherwise events cannot be sent outside the current namespace.
        # In this case, only events to '/tasks' can be emitted otherwise.
        server.socketio.emit('node-status-changed', namespace='/admin')

        # define socket-session variables.
        session.type = auth.type
        session.name = auth.username if session.type == 'user' else auth.name
        self.log.info(f'Client identified as <{session.type}>: <{session.name}>')
        
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
        for room in session.rooms:
            self.__leave_room_and_notify(room)

        session.auth.status = 'offline'
        session.auth.save()

        # It appears to be necessary to use the root socketio instance
        # otherwise events cannot be sent outside the current namespace.
        # In this case, only events to '/tasks' can be emitted otherwise.
        self.log.warning('emitting to /admin')
        server.socketio.emit('node-status-changed', namespace='/admin')

        self.log.info(f'{session.name} disconnected')

    def on_message(self, message):
        self.log.info('received message: ' + message)

    def on_error(self, e):
        self.log.error(e)
    
    def on_join_room(self, room):
        self.__join_room_and_notify(room)

    def on_container_failed(self, node_id, status_code, result_id, collaboration_id):
        run_id = db.Result.get(result_id).task.run_id

        self.log.critical(
            f"A container in for run_id={run_id} and result_id={result_id}"
            f" within collaboration_id={collaboration_id} on node_id={node_id}"
            f" exited with status_code={status_code}."
        )
        # emit('message', "somewhere in the universe a container has crashed", room='all_connections')
        # print("collaboration_"+str(collaboration_id))
        
        room = "collaboration_"+str(collaboration_id)
        emit("container_failed", run_id, room=room)

    def on_ping(self, node_id):
        # self.log.debug(f"ping from id={node_id}")
        room = f"node_{node_id}"
        emit("pang","success!", room=room)

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


        