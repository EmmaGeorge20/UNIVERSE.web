'''Contians socketio so that app.py and chat.py don't import things from each other in a cirkle'''

try:
    from flask_socketio import SocketIO
except ModuleNotFoundError:
    SocketIO = None

class SocketIOFallback:
    def init_app(self, app):
        return None

    def run(self, app, **kwargs):
        return app.run(**kwargs)

    def on(self, event):
        def decorator(func):
            return func
        return decorator

socketio = SocketIO() if SocketIO else SocketIOFallback()
