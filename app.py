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
                           array_agg(c.course_code) AS courses,
                           t.bio, t.rating, t.session_count
                    FROM tutors t
                    JOIN users u ON t.user_id = u.id
                    JOIN tutor_courses tc ON tc.tutor_id = t.id
                    JOIN courses c ON c.id = tc.course_id
                    WHERE t.is_active = TRUE
                      AND (c.course_code ILIKE %s OR c.course_name ILIKE %s)
                    GROUP BY u.first_name, u.last_name, u.program,
                             t.bio, t.rating, t.session_count
                    ORDER BY t.rating DESC
                    """,
                    (f"%{query}%", f"%{query}%"),
                )
            else:
                cur.execute(
                    """
                    SELECT u.first_name, u.last_name, u.program,
                           array_agg(c.course_code) AS courses,
                           t.bio, t.rating, t.session_count
                    FROM tutors t
                    JOIN users u ON t.user_id = u.id
                    JOIN tutor_courses tc ON tc.tutor_id = t.id
                    JOIN courses c ON c.id = tc.course_id
                    WHERE t.is_active = TRUE
                    GROUP BY u.first_name, u.last_name, u.program,
                             t.bio, t.rating, t.session_count
                    ORDER BY t.rating DESC
                    """
                )
            rows = cur.fetchall()
            for row in rows:
                tutors.append({
                    "first_name":    row[0],
                    "last_name":     row[1],
                    "program":       row[2],
                    "courses":       row[3],
                    "bio":           row[4],
                    "rating":        row[5],
                    "session_count": row[6],
                })
            cur.close()
        finally:
            conn.close()

    return render_template("search.html", tutors=tutors, query=query)


@app.route("/become-tutor", methods=["GET", "POST"])
def become_tutor():
    email = session.get("user")
    if not email:
        return redirect(url_for("auth.login"))

    courses = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, course_code, course_name FROM courses ORDER BY course_code")
            courses = cur.fetchall()
            cur.close()
        finally:
            conn.close()

    if request.method == "POST":
        bio = request.form.get("bio", "").strip()
        valda_kurser = request.form.getlist("courses")
        egen_kurs = request.form.get("egen_kurs", "").strip()
        filer = request.files.getlist("intyg")

        import os
        upload_folder = os.path.join("static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        conn = get_connection()
        if conn is not None:
            try:
                cur = conn.cursor()

                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                row = cur.fetchone()
                if not row:
                    return redirect(url_for("home"))
                user_id = row[0]

                cur.execute("SELECT id FROM tutors WHERE user_id = %s", (user_id,))
                if cur.fetchone():
                    return redirect(url_for("search"))

                cur.execute(
                    """
                    INSERT INTO tutors (user_id, bio, rating, session_count, is_active)
                    VALUES (%s, %s, 0.0, 0, FALSE)
                    RETURNING id
                    """,
                    (user_id, bio),
                )
                tutor_id = cur.fetchone()[0]

                for kurs_id in valda_kurser:
                    cur.execute(
                        """
                        INSERT INTO tutor_courses (tutor_id, course_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (tutor_id, int(kurs_id)),
                    )

                if egen_kurs:
                    cur.execute(
                        """
                        INSERT INTO courses (course_code, course_name)
                        VALUES (%s, %s)
                        ON CONFLICT (course_code) DO NOTHING
                        RETURNING id
                        """,
                        (egen_kurs.upper(), egen_kurs.upper()),
                    )
                    result = cur.fetchone()
                    if not result:
                        cur.execute(
                            "SELECT id FROM courses WHERE course_code = %s",
                            (egen_kurs.upper(),),
                        )
                        result = cur.fetchone()
                    if result:
                        cur.execute(
                            """
                            INSERT INTO tutor_courses (tutor_id, course_id)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                            """,
                            (tutor_id, result[0]),
                        )

                for fil in filer:
                    if fil and fil.filename:
                        filename = f"{tutor_id}_{fil.filename}"
                        fil.save(os.path.join(upload_folder, filename))

                conn.commit()
                cur.close()
            finally:
                conn.close()

        return redirect(url_for("search"))

    return render_template("become_tutor.html", courses=courses)


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