'''Contians socketio so that app.py and chat.py don't import things from each other in a cirkle'''

from flask_socketio import SocketIO

socketio = SocketIO()