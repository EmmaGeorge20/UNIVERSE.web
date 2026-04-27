#imports
from flask import Flask, render_template

app = Flask(__name__)

#routes to webbpages
@app.route("/")
def index():
    return render_template("home.html")



#runner and debugger
<<<<<<< Updated upstream
if __name__ in "__main__":
    app.run(debug=True)
=======
if __name__ == "__main__":
    app.run(debug=True, port=5001)
>>>>>>> Stashed changes
