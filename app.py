"""
app.py
This is the main entry point of the application.
It initializes the Flask app and registers all blueprints.
""" 

from flask import Flask, redirect, render_template, session, url_for
from auth import auth
from user_profile import profile_bp
from chat import chat
from extensions import socketio

app = Flask(__name__)
app.secret_key = "universe_secret"  # Secret key required for sessions to work

socketio.init_app(app) #Connects Flask with socket server

app.register_blueprint(auth)  # Register authentication routes
app.register_blueprint(profile_bp)

app.register_blueprint(chat)  # Chat routes

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

<<<<<<< Updated upstream
=======

@app.route("/profile")
def profile():
    email = session.get("user")
    if not email:
        return redirect(url_for("auth.login"))

    user = {}

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT first_name, last_name, email, school, program, phone
                FROM users
                WHERE email = %s
                """,
                (email,),
            )
            row = cur.fetchone()
            if row:
                user = {
                    "first_name": row[0],
                    "last_name":  row[1],
                    "email":      row[2],
                    "school":     row[3],
                    "program":    row[4],
                    "phone":      row[5],
                }
            cur.close()
        finally:
            conn.close()

    return render_template("profil.html", user=user)

@app.route("/bli-handledare", methods=["GET", "POST"])
def bli_handledare():
    """
    Renders the become a tutor form.
    Only accessible to logged in users.
    """
    email = session.get("user")
    if not email:
        return redirect(url_for("auth.login"))

    kurser = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, kurskod, kursnamn FROM kurser ORDER BY kurskod")
            kurser = cur.fetchall()
            cur.close()
        finally:
            conn.close()

    if request.method == "POST":
        bio = request.form.get("bio", "").strip()
        valda_kurser = request.form.getlist("kurser")
        egen_kurs = request.form.get("egen_kurs", "").strip()

        conn = get_connection()
        if conn is not None:
            try:
                cur = conn.cursor()

                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                row = cur.fetchone()
                if not row:
                    return redirect(url_for("home"))
                user_id = row[0]

                cur.execute("SELECT id FROM handledare WHERE user_id = %s", (user_id,))
                if cur.fetchone():
                    return redirect(url_for("search"))

                cur.execute(
                    """
                    INSERT INTO handledare (user_id, bio, betyg, antal_sessioner, ar_aktiv)
                    VALUES (%s, %s, 0.0, 0, TRUE)
                    RETURNING id
                    """,
                    (user_id, bio),
                )
                handledare_id = cur.fetchone()[0]

                for kurs_id in valda_kurser:
                    cur.execute(
                        """
                        INSERT INTO handledare_kurser (handledare_id, kurs_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (handledare_id, int(kurs_id)),
                    )

                if egen_kurs:
                    cur.execute(
                        """
                        INSERT INTO kurser (kurskod, kursnamn)
                        VALUES (%s, %s)
                        ON CONFLICT (kurskod) DO NOTHING
                        RETURNING id
                        """,
                        (egen_kurs.upper(), egen_kurs.upper()),
                    )
                    result = cur.fetchone()
                    if not result:
                        cur.execute(
                            "SELECT id FROM kurser WHERE kurskod = %s",
                            (egen_kurs.upper(),),
                        )
                        result = cur.fetchone()
                    if result:
                        cur.execute(
                            """
                            INSERT INTO handledare_kurser (handledare_id, kurs_id)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                            """,
                            (handledare_id, result[0]),
                        )

                conn.commit()
                cur.close()
            finally:
                conn.close()

        return redirect(url_for("search"))

    return render_template("bli_handledare.html", kurser=kurser)


>>>>>>> Stashed changes
if __name__ == "__main__":
    socketio.run(app, debug=True)
