"""
app.py
This is the main entry point of the application.
It initializes the Flask app and registers all blueprints.
""" 

from flask import Flask, redirect, render_template, session, url_for
from auth import auth
from user_profile import profile_bp

app = Flask(__name__)
app.secret_key = "universe_secret"  # Secret key required for sessions to work

app.register_blueprint(auth)  # Register authentication routes
app.register_blueprint(profile_bp)


@app.route("/")
def index():
    """
    Redirects to the startup page.
    """
    return redirect(url_for("startup"))

@app.route("/startup")
def startup():
    """
    Renders the startup page.
    """
    return render_template("startup.html")

@app.route("/guest")
def guest():
    """
    Allows users to continue as guest.
    """
    session["user"] = "guest"
    return redirect(url_for("home"))

@app.route("/home")
def home():
    """
    Renders the homepage.
    """
    return render_template("index.html")

@app.route("/booking")
def booking():
    """
    Renders the bookings page placeholder.
    """
    return render_template("page.html", title="Bokningar")

@app.route("/search")
def search():
    """
    Renders the course search page placeholder.
    """
    return render_template("page.html", title="Sök")

@app.route("/messages")
def messages():
    """
    Renders the messages page placeholder.
    """
    return render_template("page.html", title="Meddelanden")

@app.route("/help")
def help_page():
    """
    Renders the help page placeholder.
    """
    return render_template("page.html", title="Hjälp")

@app.route("/marketplace")
def marketplace():
    """
    Renders the marketplace page placeholder.
    """
    return render_template("page.html", title="Marknad")

@app.route("/news")
def news():
    """
    Renders the news page placeholder.
    """
    return render_template("page.html", title="Nyheter")

@app.route("/community")
def community():
    """
    Renders the community page placeholder.
    """
    return render_template("page.html", title="Community")

if __name__ == "__main__":
    app.run(debug=True)