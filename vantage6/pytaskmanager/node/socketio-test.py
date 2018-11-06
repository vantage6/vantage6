#!/usr/bin/env python3
from socketIO_client import SocketIO, SocketIONamespace, LoggingNamespace

# import logging
# logging.getLogger().setLevel(logging.DEBUG)
# logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
# logging.basicConfig()

class Namespace(SocketIONamespace):
    def on_connect(self):
        print('on_connect')

    def on_disconnect(self):
        print('on_disconnect')

    def on_reconnect(self):
        print('on_reconnect')

    def on_my_event(self, *args):
        print('on_my_event', args)

    def on_message(self, *args):
        print('on_message', args)
        
    def on_event(self, *args):
        print('on_event', args)
    

# Setup socketIO connection to localhost:5000
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1NDE1MTMwMDgsIm5iZiI6MTU0MTUxMzAwOCwianRpIjoiYTkyNTI3NWQtNDhmOS00NjA0LWE3M2QtZGFhOGIwZGRlYmY5IiwiZXhwIjoxNTQxNTEzOTA4LCJpZGVudGl0eSI6MSwiZnJlc2giOmZhbHNlLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl9jbGFpbXMiOnsidHlwZSI6InVzZXIiLCJyb2xlcyI6WyJhZG1pbiJdfX0.A5FoBxLjr8p_azF2SKDvzmMyo2xYOGX1QBbsc4lXoZg"
headers = {
    "Authorization": f"Bearer {token}",
}
socketIO = SocketIO('127.0.0.1', 5000, Namespace, headers=headers)
print(f'I am connected: {socketIO.connected}')

# Listen / connect event handlers
# socketIO.on('connect', on_connect)
# socketIO.on('disconnect', on_disconnect)
# socketIO.on('reconnect', on_reconnect)
# socketIO.on('my event', on_my_event)
# socketIO.on('message', on_message)

# socketIO.emit('my event')
# socketIO.send('this sends a regular message (it just creates an event with type "message")')

socketIO.emit('join')

socketIO.wait(seconds=5)

