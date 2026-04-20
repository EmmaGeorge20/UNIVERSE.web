#imports
from flask import Flask, render_template

app = Flask(__name__)

#routes to webbpages
@app.route("/")
def index():
    return render_template("home.html")



#runner and debugger
if __name__ in "__main__":
    app.run(debug=True)