"""
auth.py
This file handles all authentication routes including login, logout and registration.
It uses Flask Blueprint to separate authentication logic from the main application.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session
from db import get_connection

auth = Blueprint("auth", __name__)

def valid_password(password):
    """
    Validates that the password meets the requirements:
    at least 8 characters, one letter and one digit.
    Returns True if valid, False otherwise.
    """
    if len(password) < 8:
        return False
    if not any(c.isalpha() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

@auth.route("/login", methods=["GET", "POST"])
def login():
    """
    GET  - Renders the login page.
    POST - Validates the user's credentials against the database.
           If correct, saves the user in the session and redirects to the homepage.
           If incorrect, displays an error message.
    """
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]
        if not valid_password(password):
            error = "Lösenordet måste vara minst 8 tecken, innehålla minst en bokstav och en siffra"
        else:
            conn = get_connection()
            if conn is None:
                error = "Kunde inte ansluta till databasen."
            else:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
                user = cur.fetchone()
                cur.close()
                conn.close()
                
                if user: 
                    session["user"] = email
                    session["role"] = role
                    return redirect(url_for("index"))
                else:
                    error = "Fel epost, lösenord eller kontotyp"

    return render_template("login.html", error=error)

@auth.route("/logout")
def logout():
    """
    Logs out the current user by removing them from the session.
    Redirects to the homepage after logout.
    """
    session.pop("user", None)
    session.pop("role", None)
    return redirect(url_for("index"))

@auth.route("/register", methods=["GET", "POST"])
def register():
    """
    GET  - Renders the registration page.
    POST - Validates the form data and creates a new user in the database.
           Checks if the email already exists before inserting.
           If successful, redirects to the login page.
           If failed, displays an error message.
    """
    error = None
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name  = request.form["last_name"]
        email      = request.form["email"]
        school     = request.form["school"]
        program    = request.form["program"]
        phone      = request.form["phone"]
        password   = request.form["password"]

        if not valid_password(password):
            error = "Lösenordet måste vara minst 8 tecken, innehålla minst en bokstav och en siffra."
        else:
            conn = get_connection()
            if conn is None:
                error = "Kunde inte ansluta till databasen."
            else:
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                    if cur.fetchone():
                        error = "Det finns redan ett konto med den e-postadressen."
                    else:
                        cur.execute("""
                            INSERT INTO users (first_name, last_name, email, school, program, phone, password)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (first_name, last_name, email, school, program, phone, password))
                        conn.commit()
                        session["user"] = email
                        return redirect(url_for("auth.login"))
                    cur.close()
                    conn.close()
                except Exception as e:
                    print("Fel vid registrering:", e)
                    error = "Något gick fel, försök igen."

    return render_template("register.html", error=error)
