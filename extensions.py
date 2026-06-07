'''Contians socketio so that app.py and chat.py don't import things from each other in a cirkle'''

try:
    from flask_socketio import SocketIO
except ModuleNotFoundError:
    SocketIO = None

class SocketIOFallback:
    def init_app(self, app):
        """Fallback used when flask_socketio is not installed; does nothing."""
        return None

    def run(self, app, **kwargs):
        """Fallback used when flask_socketio is not installed; runs the app via Flask's normal run method."""
        return app.run(**kwargs)

    def on(self, event):
        """Fallback used when flask_socketio is not installed; returns a no-op decorator."""
        def decorator(func):
            """Returns the handler function unchanged."""
            return func
        return decorator

socketio = SocketIO() if SocketIO else SocketIOFallback()
