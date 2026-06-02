"""
app.py
This is the main entry point of the application.
It initializes the Flask app and registers all blueprints.
"""

import os
import time

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
        cur.execute("ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS image_filename VARCHAR(200)")
        cur.execute("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS image_filename VARCHAR(200)")
        cur.execute("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS external_link VARCHAR(500)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                category VARCHAR(50) NOT NULL,
                image_filename VARCHAR(200),
                external_link VARCHAR(500),
                created_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS marketplace_listings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                price NUMERIC(10,2) DEFAULT 0,
                category VARCHAR(50) NOT NULL,
                listing_type VARCHAR(20) NOT NULL,
                image_filename VARCHAR(200),
                created_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
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

    # Fetch all courses and check if user is already an approved tutor
    kurser = []
    existing_tutor = None
    existing_courses = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, course_code, course_name FROM courses ORDER BY course_code")
            kurser = cur.fetchall()

            cur.execute("SELECT t.id, t.status FROM tutors t JOIN users u ON u.id = t.user_id WHERE u.email = %s", (email,))
            row = cur.fetchone()
            if row:
                existing_tutor = {"id": row[0], "status": row[1]}
                cur.execute("""
                    SELECT c.id FROM tutor_courses tc
                    JOIN courses c ON c.id = tc.course_id
                    WHERE tc.tutor_id = %s
                """, (row[0],))
                existing_courses = [r[0] for r in cur.fetchall()]
            cur.close()
        finally:
            conn.close()

    if request.method == "POST":
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

                if existing_tutor and existing_tutor["status"] == "approved":
                    # Existing approved tutor — add new courses directly
                    tutor_id = existing_tutor["id"]
                    upload_folder = os.path.join("static", "uploads")
                    os.makedirs(upload_folder, exist_ok=True)

                    for kurs_id in valda_kurser:
                        cur.execute(
                            "INSERT INTO tutor_courses (tutor_id, course_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (tutor_id, int(kurs_id)),
                        )

                    if egen_kurs:
                        cur.execute(
                            "INSERT INTO courses (course_code, course_name) VALUES (%s, %s) ON CONFLICT (course_code) DO NOTHING RETURNING id",
                            (egen_kurs.upper(), egen_kurs.upper()),
                        )
                        result = cur.fetchone()
                        if not result:
                            cur.execute("SELECT id FROM courses WHERE course_code = %s", (egen_kurs.upper(),))
                            result = cur.fetchone()
                        if result:
                            cur.execute(
                                "INSERT INTO tutor_courses (tutor_id, course_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                (tutor_id, result[0]),
                            )

                    filer = request.files.getlist("intyg")
                    for fil in filer:
                        if fil and fil.filename:
                            fil.save(os.path.join(upload_folder, f"{tutor_id}_{fil.filename}"))

                    conn.commit()
                    cur.close()
                    return redirect(url_for("search"))

                else:
                    # New tutor application
                    cur.execute("SELECT id FROM tutors WHERE user_id = %s", (user_id,))
                    if cur.fetchone():
                        return redirect(url_for("search"))

                    bio = request.form.get("bio", "").strip()
                    filer = request.files.getlist("intyg")
                    upload_folder = os.path.join("static", "uploads")
                    os.makedirs(upload_folder, exist_ok=True)

                    cur.execute(
                        "INSERT INTO tutors (user_id, bio, rating, session_count, is_active, status) VALUES (%s, %s, 0.0, 0, FALSE, 'pending') RETURNING id",
                        (user_id, bio),
                    )
                    tutor_id = cur.fetchone()[0]

                    for kurs_id in valda_kurser:
                        cur.execute(
                            "INSERT INTO tutor_courses (tutor_id, course_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (tutor_id, int(kurs_id)),
                        )

                    if egen_kurs:
                        cur.execute(
                            "INSERT INTO courses (course_code, course_name) VALUES (%s, %s) ON CONFLICT (course_code) DO NOTHING RETURNING id",
                            (egen_kurs.upper(), egen_kurs.upper()),
                        )
                        result = cur.fetchone()
                        if not result:
                            cur.execute("SELECT id FROM courses WHERE course_code = %s", (egen_kurs.upper(),))
                            result = cur.fetchone()
                        if result:
                            cur.execute(
                                "INSERT INTO tutor_courses (tutor_id, course_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                (tutor_id, result[0]),
                            )

                    for fil in filer:
                        if fil and fil.filename:
                            fil.save(os.path.join(upload_folder, f"{tutor_id}_{fil.filename}"))

                    conn.commit()
                    cur.close()
                    return redirect(url_for("search"))

            finally:
                conn.close()

    return render_template("become_tutor.html", kurser=kurser, existing_tutor=existing_tutor, existing_courses=existing_courses)


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
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    upcoming = []
    past = []

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.id, c.status, c.meeting_time,
                        co.course_code, co.course_name,
                        sender.first_name, sender.last_name,
                        receiver.first_name, receiver.last_name,
                        c.sender_id
                FROM contracts c
                LEFT JOIN courses co ON co.id = c.course_id
                JOIN users sender ON sender.id = c.sender_id
                JOIN users receiver ON receiver.id = c.receiver_id
                WHERE (c.sender_id = %s OR c.receiver_id = %s)
                AND c.status = 'accepted'
                AND c.meeting_time > NOW()
                ORDER BY c.meeting_time ASC
            """, (user_id, user_id))
            for row in cur.fetchall():
                upcoming.append({
                    "id":            row[0],
                    "sender_id": row[9],
                    "status":        row[1],
                    "meeting_time":  row[2],
                    "course_code":   row[3],
                    "course_name":   row[4],
                    "sender_name":   f"{row[5]} {row[6]}",
                    "receiver_name": f"{row[7]} {row[8]}",
                })

            cur.execute("""
                SELECT c.id, c.status, c.meeting_time,
                       co.course_code, co.course_name,
                       sender.first_name, sender.last_name,
                       receiver.first_name, receiver.last_name,
                       c.sender_id
                FROM contracts c
                LEFT JOIN courses co ON co.id = c.course_id
                JOIN users sender ON sender.id = c.sender_id
                JOIN users receiver ON receiver.id = c.receiver_id
                WHERE (c.sender_id = %s OR c.receiver_id = %s)
                AND c.status = 'accepted'
                AND c.meeting_time < NOW()
                ORDER BY c.meeting_time DESC
            """, (user_id, user_id))
            for row in cur.fetchall():
                past.append({
                    "id":            row[0],
                    "status":        row[1],
                    "meeting_time":  row[2],
                    "course_code":   row[3],
                    "course_name":   row[4],
                    "sender_name":   f"{row[5]} {row[6]}",
                    "receiver_name": f"{row[7]} {row[8]}",
                    "sender_id":     row[9],
                })
            cur.close()
        finally:
            conn.close()
    return render_template("booking.html", upcoming=upcoming, past=past, user_id=user_id)


@app.route("/messages")
def messages():
    return render_template("page.html", title="Meddelanden")


@app.route("/help")
def help_page():
    return render_template("page.html", title="Hjälp")


@app.route("/marketplace")
def marketplace():
    category     = request.args.get("category", "").strip()
    listing_type = request.args.get("type", "").strip()
    min_price    = request.args.get("min_price", "").strip()
    max_price    = request.args.get("max_price", "").strip()
    q            = request.args.get("q", "").strip()

    listings = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            conditions = ["ml.is_active = TRUE"]
            params = []

            if category:
                conditions.append("ml.category = %s")
                params.append(category)
            if listing_type:
                conditions.append("ml.listing_type = %s")
                params.append(listing_type)
            if min_price:
                try:
                    conditions.append("ml.price >= %s")
                    params.append(float(min_price))
                except ValueError:
                    pass
            if max_price:
                try:
                    conditions.append("ml.price <= %s")
                    params.append(float(max_price))
                except ValueError:
                    pass
            if q:
                conditions.append("(ml.title ILIKE %s OR ml.description ILIKE %s)")
                params.extend([f"%{q}%", f"%{q}%"])

            where = " AND ".join(conditions)
            cur.execute(f"""
                SELECT ml.id, ml.user_id, ml.title, ml.description, ml.price,
                       ml.category, ml.listing_type, ml.image_filename,
                       ml.created_at, u.first_name, u.last_name
                FROM marketplace_listings ml
                JOIN users u ON u.id = ml.user_id
                WHERE {where}
                ORDER BY ml.created_at DESC
            """, params)

            for row in cur.fetchall():
                listings.append({
                    "id":             row[0],
                    "user_id":        row[1],
                    "title":          row[2],
                    "description":    row[3],
                    "price":          row[4],
                    "category":       row[5],
                    "listing_type":   row[6],
                    "image_filename": row[7],
                    "created_at":     row[8],
                    "seller_name":    f"{row[9]} {row[10]}",
                })
            cur.close()
        finally:
            conn.close()

    return render_template("marketplace.html",
        listings=listings,
        current_user_id=session.get("user_id"),
        category=category,
        listing_type=listing_type,
        min_price=min_price,
        max_price=max_price,
        q=q,
    )


@app.route("/marketplace/ny", methods=["GET", "POST"])
def marketplace_ny():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title        = request.form.get("title", "").strip()
        description  = request.form.get("description", "").strip()
        price_str    = request.form.get("price", "0").strip()
        category     = request.form.get("category", "").strip()
        listing_type = request.form.get("listing_type", "").strip()
        image        = request.files.get("image")

        try:
            price = float(price_str)
        except ValueError:
            price = 0.0

        image_filename = None
        if image and image.filename:
            ext = image.filename.rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png"):
                upload_dir = os.path.join("static", "uploads", "marketplace")
                os.makedirs(upload_dir, exist_ok=True)
                image_filename = f"{session['user_id']}_{int(time.time() * 1000)}.{ext}"
                image.save(os.path.join(upload_dir, image_filename))

        conn = get_connection()
        if conn is not None:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO marketplace_listings
                        (user_id, title, description, price, category, listing_type, image_filename)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (session["user_id"], title, description, price,
                      category, listing_type, image_filename))
                conn.commit()
                cur.close()
            finally:
                conn.close()

        return redirect(url_for("marketplace"))

    return render_template("marketplace_ny.html")


@app.route("/marketplace/ta-bort/<int:listing_id>", methods=["POST"])
def marketplace_ta_bort(listing_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM marketplace_listings WHERE id = %s AND user_id = %s",
                (listing_id, user_id),
            )
            conn.commit()
            cur.close()
        finally:
            conn.close()

    return redirect(url_for("marketplace"))


@app.route("/news")
def news():
    return render_template("page.html", title="Nyheter")


@app.route("/announcements")
def announcements():
    category = request.args.get("category", "").strip()
    q        = request.args.get("q", "").strip()
    announcements_list = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            conditions = ["a.is_active = TRUE"]
            params = []
            if category and category != "Alla":
                conditions.append("a.category = %s")
                params.append(category)
            if q:
                conditions.append("(a.title ILIKE %s OR a.description ILIKE %s)")
                params.extend([f"%{q}%", f"%{q}%"])
            where = " AND ".join(conditions)
            cur.execute(f"""
                SELECT a.id, a.user_id, a.title, a.description, a.category,
                       a.image_filename, a.external_link, a.created_at,
                       u.first_name, u.last_name
                FROM announcements a
                JOIN users u ON u.id = a.user_id
                WHERE {where}
                ORDER BY a.created_at DESC
            """, params)
            for row in cur.fetchall():
                announcements_list.append({
                    "id":             row[0],
                    "user_id":        row[1],
                    "title":          row[2],
                    "description":    row[3],
                    "category":       row[4],
                    "image_filename": row[5],
                    "external_link":  row[6],
                    "created_at":     row[7],
                    "poster_name":    f"{row[8]} {row[9]}",
                })
            cur.close()
        finally:
            conn.close()
    return render_template("announcements.html",
        announcements=announcements_list,
        current_user_id=session.get("user_id"),
        is_admin=session.get("admin"),
        active_category=category,
        q=q,
    )


@app.route("/announcements/new", methods=["GET", "POST"])
def announcements_new():
    user_id = session.get("user_id")
    admin_email = session.get("admin")

    # Resolve user_id for admins who log in separately
    if not user_id and admin_email:
        conn = get_connection()
        if conn is not None:
            try:
                cur = conn.cursor()
                cur.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
                row = cur.fetchone()
                if row:
                    user_id = row[0]
                cur.close()
            finally:
                conn.close()

    if not user_id:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category    = request.form.get("category", "").strip()
        link        = request.form.get("external_link", "").strip()
        image       = request.files.get("image")

        image_filename = None
        if image and image.filename:
            ext = image.filename.rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png"):
                upload_dir = os.path.join("static", "uploads", "announcements")
                os.makedirs(upload_dir, exist_ok=True)
                image_filename = f"{user_id}_{int(time.time() * 1000)}.{ext}"
                image.save(os.path.join(upload_dir, image_filename))

        conn = get_connection()
        if conn is not None:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO announcements
                        (user_id, title, description, category, image_filename, external_link)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, title, description, category,
                      image_filename, link or None))
                conn.commit()
                cur.close()
            finally:
                conn.close()

        return redirect(url_for("announcements"))

    return render_template("announcements_new.html")


@app.route("/announcements/delete/<int:announcement_id>", methods=["POST"])
def announcements_delete(announcement_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            if session.get("admin"):
                cur.execute("DELETE FROM announcements WHERE id = %s", (announcement_id,))
            else:
                cur.execute("DELETE FROM announcements WHERE id = %s AND user_id = %s",
                            (announcement_id, user_id))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    return redirect(url_for("announcements"))


# ── JSON search APIs ──────────────────────────────────────────────────────────

@app.route("/api/search/tutors")
def api_search_tutors():
    query = request.args.get("q", "").strip()
    tutors = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            if query:
                cur.execute("""
                    SELECT u.id, u.first_name, u.last_name, u.program,
                           array_agg(c.course_code) AS courses, t.bio
                    FROM tutors t
                    JOIN users u ON t.user_id = u.id
                    JOIN tutor_courses tc ON tc.tutor_id = t.id
                    JOIN courses c ON c.id = tc.course_id
                    WHERE t.is_active = TRUE
                      AND (c.course_code ILIKE %s OR c.course_name ILIKE %s)
                    GROUP BY u.id, u.first_name, u.last_name, u.program, t.bio
                    ORDER BY u.last_name ASC
                """, (f"%{query}%", f"%{query}%"))
            else:
                cur.execute("""
                    SELECT u.id, u.first_name, u.last_name, u.program,
                           array_agg(c.course_code) AS courses, t.bio
                    FROM tutors t
                    JOIN users u ON t.user_id = u.id
                    JOIN tutor_courses tc ON tc.tutor_id = t.id
                    JOIN courses c ON c.id = tc.course_id
                    WHERE t.is_active = TRUE
                    GROUP BY u.id, u.first_name, u.last_name, u.program, t.bio
                    ORDER BY u.last_name ASC
                """)
            for row in cur.fetchall():
                tutors.append({
                    "user_id":    row[0],
                    "first_name": row[1],
                    "last_name":  row[2],
                    "program":    row[3],
                    "kurser":     list(row[4]) if row[4] else [],
                    "bio":        row[5],
                })
            cur.close()
        finally:
            conn.close()
    return jsonify(tutors)


@app.route("/api/search/marketplace")
def api_search_marketplace():
    q            = request.args.get("q", "").strip()
    category     = request.args.get("category", "").strip()
    listing_type = request.args.get("type", "").strip()
    min_price    = request.args.get("min_price", "").strip()
    max_price    = request.args.get("max_price", "").strip()
    listings = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            conditions = ["ml.is_active = TRUE"]
            params = []
            if category:
                conditions.append("ml.category = %s")
                params.append(category)
            if listing_type:
                conditions.append("ml.listing_type = %s")
                params.append(listing_type)
            if min_price:
                try:
                    conditions.append("ml.price >= %s")
                    params.append(float(min_price))
                except ValueError:
                    pass
            if max_price:
                try:
                    conditions.append("ml.price <= %s")
                    params.append(float(max_price))
                except ValueError:
                    pass
            if q:
                conditions.append("(ml.title ILIKE %s OR ml.description ILIKE %s)")
                params.extend([f"%{q}%", f"%{q}%"])
            cur.execute(f"""
                SELECT ml.id, ml.user_id, ml.title, ml.description, ml.price,
                       ml.category, ml.listing_type, ml.image_filename,
                       ml.created_at, u.first_name, u.last_name
                FROM marketplace_listings ml
                JOIN users u ON u.id = ml.user_id
                WHERE {' AND '.join(conditions)}
                ORDER BY ml.created_at DESC
            """, params)
            for row in cur.fetchall():
                listings.append({
                    "id":             row[0],
                    "user_id":        row[1],
                    "title":          row[2],
                    "description":    row[3] or "",
                    "price":          float(row[4]) if row[4] is not None else 0,
                    "category":       row[5],
                    "listing_type":   row[6],
                    "image_filename": row[7],
                    "date":           row[8].strftime("%d %b %Y") if row[8] else "",
                    "seller_name":    f"{row[9]} {row[10]}",
                })
            cur.close()
        finally:
            conn.close()
    return jsonify(listings)


@app.route("/api/search/announcements")
def api_search_announcements():
    q        = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    items = []
    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            conditions = ["a.is_active = TRUE"]
            params = []
            if category and category != "Alla":
                conditions.append("a.category = %s")
                params.append(category)
            if q:
                conditions.append("(a.title ILIKE %s OR a.description ILIKE %s)")
                params.extend([f"%{q}%", f"%{q}%"])
            cur.execute(f"""
                SELECT a.id, a.user_id, a.title, a.description, a.category,
                       a.image_filename, a.external_link, a.created_at,
                       u.first_name, u.last_name
                FROM announcements a
                JOIN users u ON u.id = a.user_id
                WHERE {' AND '.join(conditions)}
                ORDER BY a.created_at DESC
            """, params)
            for row in cur.fetchall():
                items.append({
                    "id":             row[0],
                    "user_id":        row[1],
                    "title":          row[2],
                    "description":    row[3] or "",
                    "category":       row[4],
                    "image_filename": row[5],
                    "external_link":  row[6] or "",
                    "date":           f"{row[7].day} {row[7].strftime('%b')}" if row[7] else "",
                    "poster_name":    f"{row[8]} {row[9]}",
                })
            cur.close()
        finally:
            conn.close()
    return jsonify(items)


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
    socketio.run(app, debug=True, port=5001)
