
"""
app.py
This is the main entry point of the application.
It initializes the Flask app and registers all blueprints.
"""

from flask import Flask, redirect, render_template, request, session, url_for
from auth import auth
from user_profile import profile_bp
from db import get_connection
from chat import chat
from extensions import socketio

app = Flask(__name__)
app.secret_key = "universe_secret"

socketio.init_app(app)

app.register_blueprint(auth)
app.register_blueprint(profile_bp)
app.register_blueprint(chat)


@app.route("/")
def index():
    return redirect(url_for("startup"))


@app.route("/startup")
def startup():
    return render_template("startup.html")


@app.route("/home")
def home():
    return render_template("index.html")


@app.route("/search")
def search():
    """
    Renders the tutor search page.
    Optionally filters by ?q=course query parameter.
    """
    query = request.args.get("q", "").strip()
    tutors = []

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            if query:
                cur.execute(
                    """
                    SELECT u.first_name, u.last_name, u.program,
                           array_agg(k.kurskod) AS kurser,
                           h.bio, h.betyg, h.antal_sessioner
                    FROM handledare h
                    JOIN users u ON h.user_id = u.id
                    JOIN handledare_kurser hk ON hk.handledare_id = h.id
                    JOIN kurser k ON k.id = hk.kurs_id
                    WHERE h.ar_aktiv = TRUE
                      AND (k.kurskod ILIKE %s OR k.kursnamn ILIKE %s)
                    GROUP BY u.first_name, u.last_name, u.program,
                             h.bio, h.betyg, h.antal_sessioner
                    ORDER BY h.betyg DESC
                    """,
                    (f"%{query}%", f"%{query}%"),
                )
            else:
                cur.execute(
                    """
                    SELECT u.first_name, u.last_name, u.program,
                           array_agg(k.kurskod) AS kurser,
                           h.bio, h.betyg, h.antal_sessioner
                    FROM handledare h
                    JOIN users u ON h.user_id = u.id
                    JOIN handledare_kurser hk ON hk.handledare_id = h.id
                    JOIN kurser k ON k.id = hk.kurs_id
                    WHERE h.ar_aktiv = TRUE
                    GROUP BY u.first_name, u.last_name, u.program,
                             h.bio, h.betyg, h.antal_sessioner
                    ORDER BY h.betyg DESC
                    """
                )
            rows = cur.fetchall()
            for row in rows:
                tutors.append({
                    "first_name":      row[0],
                    "last_name":       row[1],
                    "program":         row[2],
                    "kurser":          row[3],
                    "bio":             row[4],
                    "betyg":           row[5],
                    "antal_sessioner": row[6],
                })
            cur.close()
        finally:
            conn.close()

    return render_template("search.html", tutors=tutors, query=query)


@app.route("/booking")
def booking():
    return render_template("page.html", title="Bokningar")


@app.route("/messages")
def messages():
    return render_template("page.html", title="Meddelanden")


@app.route("/help")
def help_page():
    return render_template("page.html", title="Hjälp")


@app.route("/marketplace")
def marketplace():
    return render_template("page.html", title="Marknad")


@app.route("/news")
def news():
    return render_template("page.html", title="Nyheter")


@app.route("/community")
def community():
    return render_template("page.html", title="Community")


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


if __name__ == "__main__":
    socketio.run(app, debug=True)
