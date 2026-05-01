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

#runner and debugger
if __name__ == "__main__":
    app.run(debug=True)

