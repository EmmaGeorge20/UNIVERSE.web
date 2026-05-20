'''
Handels all functions relates to the chat 
'''

from flask import Blueprint, render_template, redirect, session, url_for
from db import get_connection
from extensions import socketio

try:
    from flask_socketio import emit, join_room
except ModuleNotFoundError:
    def emit(*args, **kwargs):
        return None

    def join_room(*args, **kwargs):
        return None

chat = Blueprint("chat", __name__)

@chat.route("/chat/<int:receiver_id>") # rout for chat
def chat_page(receiver_id):
    ''' 
    Opens a specific chat with the logges in user and the choosen reciver 

    Args: 
        receiver_id - takes receiver id from url to know witch receiver it is 
    
    Return: 
        render_template - Sends information to the choosen tamplate
    '''

    if "user_id" not in session: # if user is not logged in then it redirects to login page 
        return redirect(url_for("auth.login"))

    user_id = session["user_id"] # Takes the userer that is logged in and saves it as user_id

    chat_id = get_or_create_chat(user_id, receiver_id)


    conn = get_connection()
    cur = conn.cursor()

    cur.execute("select * from  get_chat_sidebar(%s)", (user_id,))
    chats = cur.fetchall()

    cur.execute("""
        SELECT sender_id, message, sent_at
        FROM messages
        WHERE chat_id = %s
        ORDER BY sent_at ASC
    """, (chat_id,))

    messages = cur.fetchall()

    cur.close()
    conn.close()

    room = get_room_name(user_id, receiver_id)

    return render_template(
        "chat.html",
        receiver_id=receiver_id,
        chat_id=chat_id,
        room=room,
        chats=chats,
        messages=messages,
        no_chats=False
    )


@chat.route("/chats")
def chats_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * from get_latest_chat(%s)", (user_id,))
    latest_chat = cur.fetchone()


    cur.close()
    conn.close()

    if latest_chat and latest_chat[0] is not None:
        return redirect(url_for("chat.chat_page", receiver_id=latest_chat[0]))
    
    return render_template(
        "chat.html",
        chats=[],
        receiver_id=None,
        chat_id=None,
        room=None,
        messages=[],
        no_chats=True
    )
   
@socketio.on("join_chat")  # starts when frontend (js) sends socketio.emit("join_chat")
def join_chat(data):
    '''Puts the user in a chatroom'''
    user_id = session.get("user_id")

    if not user_id:
        return

    receiver_id = data.get("receiver_id")
    room = get_room_name(user_id, receiver_id)

    join_room(room) # Puts the user in correct chat 

@socketio.on("send_message") # Starts when frontend (js) sends a new message
def handle_message(data):
    if "user_id" not in session:
        return

    sender_id = session["user_id"]
    receiver_id = data.get("receiver_id")
    message = data.get("message", "").strip()

    if not receiver_id or message == "":
        return

    chat_id = get_or_create_chat(sender_id, receiver_id)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO messages (chat_id, sender_id, message)
        VALUES (%s, %s, %s)
        RETURNING id, sent_at
    """, (chat_id, sender_id, message))

    saved_message = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    room = get_room_name(sender_id, receiver_id)

    emit("receive_message", {
        "id": saved_message[0],
        "chat_id": chat_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "message": message,
        "sent_at": str(saved_message[1])
    }, to=room)


def get_room_name(user1_id, user2_id):
    '''Creats a room name with user ids so that the chat can be saved and users can see old messages'''
    ids = sorted([int(user1_id), int(user2_id)])
    return f"chat_{ids[0]}_{ids[1]}"

def get_or_create_chat(user_id, receiver_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM chats
        WHERE
            (user1_id = %s AND user2_id = %s)
            OR
            (user1_id = %s AND user2_id = %s)
    """, (user_id, receiver_id, receiver_id, user_id))

    existing_chat = cur.fetchone()

    if existing_chat:
        chat_id = existing_chat[0]
    else:
        cur.execute("""
            INSERT INTO chats (user1_id, user2_id)
            VALUES (%s, %s)
            RETURNING id
        """, (user_id, receiver_id))

        chat_id = cur.fetchone()[0]
        conn.commit()

    cur.close()
    conn.close()

    return chat_id
