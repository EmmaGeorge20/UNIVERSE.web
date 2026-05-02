"""
app.py
This is the main entry point of the application.
It initializes the Flask app and registers all blueprints.
""" 

from flask import Flask, render_template
from auth import auth

app = Flask(__name__)
app.secret_key = "universe_secret"  # Secret key required for sessions to work

app.register_blueprint(auth)  # Register authentication routes

@app.route("/")
def index():
    """
    Renders the homepage.
    """
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)