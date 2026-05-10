from flask import Blueprint, render_template, redirect, session, url_for
from db import get_connection
from flask_socketio import emit, send, join_room
from extensions import socketio

chat = Blueprint("chat", __name__)

@chat.route("/chat/<int:receiver_id>") # rout for chat
def chat_page(receiver_id):
    ''' Opens chat.html if user is logged in. Otherwise it redirects the user to login'''

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT ON (u.id)
            u.id,
            u.username,
            m.message,
            m.sent_at

        FROM messages m

        JOIN users u
            ON (
                (u.id = m.sender_id AND m.receiver_id = %s)
                OR
                (u.id = m.receiver_id AND m.sender_id = %s)
            )

        WHERE u.id != %s

        ORDER BY u.id, m.sent_at DESC
    """, (user_id, user_id, user_id))

    chats = cur.fetchall()
    
    cur.execute("""
        SELECT sender_id, receiver_id, message, sent_at
        FROM messages
        WHERE
            (sender_id = %s AND receiver_id = %s)
            OR
            (sender_id = %s AND receiver_id = %s)
        ORDER BY sent_at ASC
    """, (user_id, receiver_id, receiver_id, user_id))

    messages = cur.fetchall()

    cur.close()
    conn.close()

    room = get_room_name(user_id, receiver_id)

    return render_template(
        "chat.html",
        receiver_id=receiver_id,
        room=room,
        chats=chats,
        messages=messages
    )

@chat.route("/chats")
def chats_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            CASE
                WHEN sender_id = %s THEN receiver_id
                ELSE sender_id
            END AS other_user_id
        FROM messages
        WHERE sender_id = %s OR receiver_id = %s
        ORDER BY sent_at DESC
        LIMIT 1
    """, (user_id, user_id, user_id))

    latest_chat = cur.fetchone()

    cur.close()
    conn.close()

    if latest_chat:
        return redirect(url_for("chat.chat_page", receiver_id=latest_chat[0]))
    
    return render_template(
    "chat.html",
    chats=[],
    receiver_id=None,
    room=None,
    no_chats=True
)

    return render_template("chat.html", chats=[], receiver_id=None, room=None)
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
 

    conn = get_connection() 
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
    }, to=room)


def get_room_name(user1_id, user2_id):
    '''Creats a room name with user ids so that the chat can be saved and users can see old messages'''
    ids = sorted([int(user1_id), int(user2_id)])
    return f"chat_{ids[0]}_{ids[1]}"