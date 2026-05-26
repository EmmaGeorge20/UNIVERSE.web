"""
user_profile.py
This file handles all profile related routes including viewing profiles
and applying to become a tutor.
"""

import os

import psycopg2.extras
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

from db import get_connection

profile_bp = Blueprint("profile", __name__)
PROFILE_IMAGE_FOLDER = os.path.join("static", "uploads", "profile_images")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def image_extension(filename):
    if "." not in filename:
        return None
    extension = filename.rsplit(".", 1)[1].lower()
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return extension
    return None


def profile_image_key(email):
    user_id = session.get("user_id")
    if user_id:
        return f"user_{user_id}"
    return secure_filename(email).replace(".", "_").replace("@", "_")


def profile_image_path(email):
    key = profile_image_key(email)
    for extension in ALLOWED_IMAGE_EXTENSIONS:
        path = os.path.join(PROFILE_IMAGE_FOLDER, f"{key}.{extension}")
        if os.path.exists(path):
            return f"uploads/profile_images/{key}.{extension}"
    return None


def save_profile_image(email):
    image = request.files.get("profile_image")
    if not image or not image.filename:
        return

    extension = image_extension(image.filename)
    if extension is None:
        return

    os.makedirs(PROFILE_IMAGE_FOLDER, exist_ok=True)
    key = profile_image_key(email)

    for old_extension in ALLOWED_IMAGE_EXTENSIONS:
        old_path = os.path.join(PROFILE_IMAGE_FOLDER, f"{key}.{old_extension}")
        if os.path.exists(old_path):
            os.remove(old_path)

    image.save(os.path.join(PROFILE_IMAGE_FOLDER, f"{key}.{extension}"))

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


def update_about_text(email):
    session[f"profile_about_{email}"] = request.form.get("about_text", "").strip()


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
        if request.form.get("form_type") == "profile_image":
            save_profile_image(email)
        elif request.form.get("form_type") == "about_text":
            update_about_text(email)
        else:
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

    user["profile_image"] = profile_image_path(email)
    user["about_text"] = session.get(f"profile_about_{email}", "")

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
