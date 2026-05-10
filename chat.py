from flask import Blueprint, render_template, redirect, session, url_for
from db import get_connection
from flask_socketio import emit, send, join_room
from extensions import socketio

chat = Blueprint("chat", __name__)

@chat.route("/chat") # rout for chat
def chat_page():
    ''' Opens chat.html if user is logged in. Otherwise it redirects the user to login'''
    if "user_id" not in session:
        return redirect(url_for("auth.login")) #If user is not logged in then they are moved to log in page

    return render_template("chat.html", receiver_id = receiver_id)

@socketio.on("join_chat") 
def join_chat(data):
    '''Puts the user in a chatroom'''
    user_id = session.get("user_id")

    if not user_id:
        return

    receiver_id = data["receiver_id"]
    room = get_room_name(user_id, receiver_id)

    join_room(room)

@socketio.on("send_message")
def handle_message(data):
    sender_id = session.get("user_id")

    if not sender_id:
        return

    receiver_id = data["receiver_id"]
    message = data["message"].strip()

    if message == "":
        return
 
 # ska sättas i db men är utloggad 
    '''conn = get_connection() 
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO messages (sender_id, receiver_id, message)
        VALUES (%s, %s, %s)
        RETURNING id, sent_at
    """, (sender_id, receiver_id, message))

    saved_message = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    room = get_room_name(sender_id, receiver_id)

    emit("receive_message", {
        "id": saved_message[0],
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "message": message,
        "sent_at": str(saved_message[1])
    }, to=room)'''


def get_room_name(user1_id, user2_id):
    '''Creats a room name with user ids so that the chat can be saved and users can see old messages'''
    ids = sorted([int(user1_id), int(user2_id)])
    return f"chat_{ids[0]}_{ids[1]}"