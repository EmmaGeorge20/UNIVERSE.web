"""
user_profile.py
This file handles all profile related routes including viewing profiles
and applying to become a tutor.
"""

import psycopg2.extras
from flask import Blueprint, render_template, request, redirect, url_for, session
from db import get_connection

profile_bp = Blueprint("profile", __name__)

def update_contact_details(email):
    phone = request.form.get("phone", "").strip()
    school = request.form.get("school", "").strip()
    program = request.form.get("program", "").strip()

    conn = get_connection()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET phone = %s,
                school = %s,
                program = %s
            WHERE email = %s
            """,
            (phone, school, program, email),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


@profile_bp.route("/profile", methods=["GET", "POST"])
def profile_page():
    """
    GET - Fetches the logged in user's information from the database
          and renders the profile page.
          Shows a login message if the user is not logged in.
    """
    email = session.get("user")
    if not email or email == "guest":
        return render_template("profile.html", login_required=True)

    if request.method == "POST":
        update_contact_details(email)
        return redirect(url_for("profile.profile_page"))

    user = {
        "first_name": "",
        "last_name": "",
        "email": email,
        "school": "UNI:VERSE",
        "program": "Student",
        "phone": "Ej angivet",
    }

    conn = get_connection()
    if conn is not None:
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
                user = row
            cur.close()
        finally:
            conn.close()

    return render_template("profile.html", user=user, login_required=False)

@profile_bp.route("/apply-tutor", methods=["GET", "POST"])
def apply_tutor():
    """
    GET  - Renders the tutor application page with available courses.
    POST - Saves the uploaded PDF and chosen course to the database
           for admin review.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("...")
    courses = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("apply_tutor.html", courses=courses)
