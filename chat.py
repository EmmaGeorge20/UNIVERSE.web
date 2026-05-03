from flask import Blueprint, render_template, request, redirect, jsonify, session, url_for
from db import get_connection

chat = Blueprint("chat", __name__)

@chat.route("/chat") # rout for chat
def chat_page():
    if "user_id" not in session:
        redirect(url_for(auth.login)) #If user is not logged in then they are moved to log in page

    return render_template(chat.html)