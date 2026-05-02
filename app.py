#imports
from flask import Flask, render_template, request, redirect, url_for, session 
from auth import auth

app = Flask(__name__)
# Hemlig nyckel som behövs för att session ska fungera
app.secret_key = "universe_secret"

app.register_blueprint(auth)

#routes to webbpages
@app.route("/")
def index(): 
    return render_template("index.html")

<<<<<<< Updated upstream
=======

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
@app.route("/login", methods=["GET", "POST"])
def login():
    error= None  # Inget felmeddelande från början
    if request.method == "POST":  # Körs när användaren skickar formuläret
        email = request.form["email"]  # Hämtar e-post från formuläret
        password = request.form["password"]  # Hämtar lösenord från formuläret
        role = request.form["role"]  # Hämtar kontotyp från formuläret
        if not valid_password(password):  # Kontrollerar lösenordskraven innan inloggning
            error = "Lösenordet måste vara minst 8 tecken, innehålla minst en bokstav och en siffra"
        elif email in users and users[email]["password"] == password and users[email]["role"] == role: # Kontrollerar om email, lösenord och kontotyp stämmer överens
            session["user"] = email   # Sparar användaren som inloggad i sessionen
            session["role"] = role   # Sparar kontotypen i sessionen
            return redirect(url_for("index"))
        else:
            error = "Fel epost, lösenord eller kontotyp"  # Visar felmeddelande felmeddelande
    return render_template("login.html", error=error)  # Laddar inloggningssidan

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if not valid_password(password):
            error = "Lösenordet måste vara minst 8 tecken, innehålla minst en bokstav och en siffra"
        elif email in users:
            error = "Det finns redan ett konto med den e-posten"
        else:
            users[email] = {"password": password, "role": "student"}
            session["user"] = email
            session["role"] = "student"
            return redirect(url_for("index"))

    return render_template("register.html", error=error)

# Route för utloggning, loggar användaren ut från sessionen och skickar tillbaka till startsidan
@app.route("/logout")
def logout():
    session.pop("user", None)  # Tar bort användaren från sessionen
    return redirect(url_for("index")) # Skickar tillbaka till startsidan


>>>>>>> Stashed changes
#runner and debugger
if __name__ == "__main__":
    app.run(debug=True)
