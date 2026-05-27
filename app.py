"""
app.py
This is the main entry point of the application.
It initializes the Flask app and registers all blueprints.
"""

import os

from flask import Flask, redirect, render_template, request, session, url_for, jsonify
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

def run_migrations():
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE")
        conn.commit()
        cur.close()
        conn.close()

run_migrations()


@app.route("/")
def index():
    return redirect(url_for("home"))


@app.route("/home")
def home():
    logged_in = "user_id" in session
    return render_template("index.html", logged_in=logged_in)


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
                    SELECT u.id, u.first_name, u.last_name, u.program,
                           array_agg(c.course_code) AS courses,
                           t.bio
                    FROM tutors t
                    JOIN users u ON t.user_id = u.id
                    JOIN tutor_courses tc ON tc.tutor_id = t.id
                    JOIN courses c ON c.id = tc.course_id
                    WHERE t.is_active = TRUE
                      AND (c.course_code ILIKE %s OR c.course_name ILIKE %s)
                    GROUP BY u.id, u.first_name, u.last_name, u.program, t.bio
                    ORDER BY u.last_name ASC
                    """,
                    (f"%{query}%", f"%{query}%"),
                )
            else:
                cur.execute(
                    """
                    SELECT u.id, u.first_name, u.last_name, u.program,
                           array_agg(c.course_code) AS courses,
                           t.bio
                    FROM tutors t
                    JOIN users u ON t.user_id = u.id
                    JOIN tutor_courses tc ON tc.tutor_id = t.id
                    JOIN courses c ON c.id = tc.course_id
                    WHERE t.is_active = TRUE
                    GROUP BY u.id, u.first_name, u.last_name, u.program, t.bio
                    ORDER BY u.last_name ASC
                    """
                )
            rows = cur.fetchall()
            for row in rows:
                tutors.append({
                    "user_id":    row[0],
                    "first_name": row[1],
                    "last_name":  row[2],
                    "program":    row[3],
                    "kurser":     row[4],
                    "bio":        row[5],
                })
            cur.close()
        finally:
            conn.close()

    return render_template("search.html", tutors=tutors, query=query)

@app.route("/bli-handledare", methods=["GET", "POST"])
def bli_handledare():
    email = session.get("user")
    if not email:
        return redirect(url_for("auth.login"))

    kurser = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, course_code, course_name FROM courses ORDER BY course_code")
            kurser = cur.fetchall()
            cur.close()
        finally:
            conn.close()

    if request.method == "POST":
        bio = request.form.get("bio", "").strip()
        valda_kurser = request.form.getlist("kurser")
        egen_kurs = request.form.get("egen_kurs", "").strip()
        filer = request.files.getlist("intyg")

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
                    INSERT INTO tutors (user_id, bio, rating, session_count, is_active, status)
                    VALUES (%s, %s, 0.0, 0, FALSE, 'pending')
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

    return render_template("become_tutor.html", kurser=kurser)


def send_notification(user_id, message):
    """Sends an in-platform notification to a user."""
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                (user_id, message),
            )
            conn.commit()
            cur.close()
        finally:
            conn.close()


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        conn = get_connection()
        if conn is not None:
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, email FROM admins
                    WHERE email = %s AND password = %s
                    """,
                    (email, password),
                )
                admin = cur.fetchone()
                cur.close()
                if admin:
                    session["admin"] = email
                    return redirect(url_for("admin_dashboard"))
                else:
                    error = "Fel e-post eller lösenord."
            finally:
                conn.close()
    return render_template("admin_login.html", error=error)


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    applications = []
    students = []

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT t.id, u.id, u.first_name, u.last_name, u.email, u.program,
                       array_agg(DISTINCT c.course_code) AS courses, t.bio, t.status
                FROM tutors t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN tutor_courses tc ON tc.tutor_id = t.id
                LEFT JOIN courses c ON c.id = tc.course_id
                GROUP BY t.id, u.id, u.first_name, u.last_name, u.email, u.program, t.bio, t.status
                ORDER BY t.status ASC
                """
            )
            for row in cur.fetchall():
                applications.append({
                    "id":         row[0],
                    "user_id":    row[1],
                    "first_name": row[2],
                    "last_name":  row[3],
                    "email":      row[4],
                    "program":    row[5],
                    "kurser":     row[6],
                    "bio":        row[7],
                    "status":     row[8],
                })

            cur.execute(
                """
                SELECT id, first_name, last_name, email, program, school
                FROM users
                ORDER BY first_name ASC
                """
            )
            for row in cur.fetchall():
                students.append({
                    "id":         row[0],
                    "first_name": row[1],
                    "last_name":  row[2],
                    "email":      row[3],
                    "program":    row[4],
                    "school":     row[5],
                })

            cur.close()
        finally:
            conn.close()

    return render_template(
        "admin_dashboard.html",
        applications=applications,
        students=students,
    )


@app.route("/admin/godkann/<int:tutor_id>", methods=["POST"])
def admin_godkann(tutor_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE tutors SET is_active = TRUE, status = 'approved'
                WHERE id = %s RETURNING user_id
                """,
                (tutor_id,),
            )
            result = cur.fetchone()
            if result:
                send_notification(
                    result[0],
                    "🎉 Grattis! Din ansökan om att bli handledare har godkänts. Du kan nu börja erbjuda handledning."
                )
            conn.commit()
            cur.close()
        finally:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/neka/<int:tutor_id>", methods=["POST"])
def admin_neka(tutor_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE tutors SET is_active = FALSE, status = 'denied'
                WHERE id = %s RETURNING user_id
                """,
                (tutor_id,),
            )
            result = cur.fetchone()
            if result:
                send_notification(
                    result[0],
                    "Din ansökan om handledarroll har tyvärr nekats denna gång. Du är välkommen att ansöka igen."
                )
            conn.commit()
            cur.close()
        finally:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/ta-bort-student/<int:user_id>", methods=["POST"])
def admin_ta_bort_student(user_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            cur.close()
        finally:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/ta-bort-handledare/<int:tutor_id>", methods=["POST"])
def admin_ta_bort_handledare(tutor_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tutors WHERE id = %s", (tutor_id,))
            conn.commit()
            cur.close()
        finally:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


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
    is_tutor = False

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
                # Check if approved tutor
                cur.execute(
                    """
                    SELECT id FROM tutors
                    JOIN users u ON tutors.user_id = u.id
                    WHERE u.email = %s AND tutors.status = 'approved'
                    """,
                    (email,),
                )
                is_tutor = cur.fetchone() is not None

            cur.close()
        finally:
            conn.close()

    return render_template("profil.html", user=user, is_tutor=is_tutor)

@app.route("/notifications/count")
def notifications_count():
    email = session.get("user")
    if not email:
        return jsonify({"count": 0})

    count = 0
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = FALSE",
                    (row[0],),
                )
                count = cur.fetchone()[0]
            cur.close()
        finally:
            conn.close()

    return jsonify({"count": count})


@app.route("/notifications")
def notifications():
    email = session.get("user")
    if not email:
        return jsonify([])

    notifs = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            if row:
                user_id = row[0]
                cur.execute(
                    """
                    SELECT id, message, is_read, created_at
                    FROM notifications
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 10
                    """,
                    (user_id,),
                )
                for r in cur.fetchall():
                    notifs.append({
                        "id":         r[0],
                        "message":    r[1],
                        "is_read":    r[2],
                        "created_at": r[3].strftime("%d %b %H:%M"),
                    })
                cur.execute(
                    "UPDATE notifications SET is_read = TRUE WHERE user_id = %s",
                    (user_id,),
                )
                conn.commit()
            cur.close()
        finally:
            conn.close()

    return jsonify(notifs)

if __name__ == "__main__":
    socketio.run(app, debug=True)