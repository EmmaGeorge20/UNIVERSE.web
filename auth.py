from flask import Blueprint, render_template, request, redirect, url_for, session
from db import get_connection

auth = Blueprint("auth", __name__)

#Kollar om lösenordet stämer lverens med kraven, minst 8 tecken, minst en bokstav och minst en siffra
def valid_password(password):
    if len(password) < 8: # Kontrollerar minst 8 tecken
        return False
    if not any(c.isalpha() for c in password): # Kontrollerar minst en bokstav
        return False
    if not any(c.isdigit() for c in password): # Kontrollerar minst en siffra
        return False
    return True

# Route till inloggningssidan, tar emot både GET och POST
@auth.route("/login", methods=["GET", "POST"])
def login():
    error= None  # Inget felmeddelande från början
    if request.method == "POST":  # Körs när användaren skickar formuläret
        email = request.form["email"]  # Hämtar e-post från formuläret
        password = request.form["password"]  # Hämtar lösenord från formuläret
        role = request.form["role"]  # Hämtar kontotyp från formuläret
        if not valid_password(password):  # Kontrollerar lösenordskraven innan inloggning
            error = "Lösenordet måste vara minst 8 tecken, innehålla minst en bokstav och en siffra"
        else:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
            user = cur.fetchone()
            cur.close()
            conn.close() 
            
            if user: 
                session["user"] = email   # Sparar användaren som inloggad i sessionen
                session["role"] = role   # Sparar kontotypen i sessionen
                return redirect(url_for("index"))
            else:
                error = "Fel epost, lösenord eller kontotyp"  # Visar felmeddelande felmeddelande

    return render_template("login.html", error=error)  # Laddar inloggningssidan

# Route för utloggning, loggar användaren ut från sessionen och skickar tillbaka till startsidan
@auth.route("/logout")
def logout():
    session.pop("user", None)  # Tar bort användaren från sessionen
    return redirect(url_for("index")) # Skickar tillbaka till startsidan