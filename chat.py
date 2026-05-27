'''
Handels all functions relates to the chat 
'''

from flask import Blueprint, render_template, redirect, session, url_for, jsonify
from db import get_connection
from flask_socketio import emit, join_room, leave_room
from extensions import socketio

chat = Blueprint("chat", __name__)

@chat.route("/chat/<int:receiver_id>") # rout for chat
def chat_page(receiver_id):
    ''' 
    Opens a specific chat with the logges in user and 
    the choosen reciver. If user is not logged in then 
    it open chat.html and shows tht the user needs to 
    log in. 

    Args: 
        receiver_id - takes receiver id from url to know 
                      witch receiver it is 
    
    Return: 
        render_template - Sends information to the choosen
                          tamplate
    '''

    if "user_id" not in session:
        return render_template(
        "chat.html",
        logged_in=False
    )

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

    cur.execute("""
                SELECT c.id, c.sender_id, co.course_code, co.course_name, c.meeting_time, c.status
                FROM contracts c
                LEFT JOIN courses co ON co.id = c.course_id
                WHERE c.chat_id = %s
                ORDER BY c.id ASC
    """, (chat_id,))
    contracts = cur.fetchall()

    cur.execute("SELECT id, course_code, course_name FROM courses")
    courses = cur.fetchall()

    cur.execute("""
        UPDATE messages SET is_read = TRUE
        WHERE chat_id = %s AND sender_id != %s
    """, (chat_id, user_id))
    conn.commit()

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
        no_chats=False, 
        logged_in=True,
        courses=courses,
        contracts=contracts
    )


@chat.route("/chats")
def chats_page():
    '''
    The route that the user uses if the go from the 
    nav-bar. Checks which chat was uses most
    recently and opens that one

    Return: 
        render_template - Sends information to the choosen
                          tamplate
    '''
    if "user_id" not in session:
        return render_template(
        "chat.html",
        logged_in=False
    )

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
        no_chats=True,
        logged_in=True
    )
   
@socketio.on("join_notification_room")
def join_notification_room(data):
    user_id = session.get("user_id")
    if user_id:
        join_room(f"notification_{user_id}")

@socketio.on("join_chat")  # starts when frontend (js) sends socketio.emit("join_chat")
def join_chat(data):
    '''
    Puts the user in a chatroom

    Args: 
        data - data from frontend, js, that 
               flask/socketIO needs 
    '''
    user_id = session.get("user_id")

    if not user_id:
        return
    
    old_room = session.get("current_room")

    if old_room:
        leave_room(old_room)
    
    receiver_id = data.get("receiver_id")
    room = get_room_name(user_id, receiver_id)

    join_room(room) # Puts the user in correct chat 

    session["current_room"] = room

@socketio.on("send_message") # Starts when frontend (js) sends a new message
def handle_message(data):
    '''
    Saves messages to the database and sends them out to all receivers

    Args:
        data - infromation from frontend that saved in the database and sent out to receivers
    '''
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

    emit("new_message_notification", {}, to=f"notification_{receiver_id}")


def get_room_name(user1_id, user2_id):
    '''
    Creats a room name with user ids so that the chat 
    can be saved and users can see old messages
    
    Returns: 
        chat_id - id that the chat has
    '''
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

@socketio.on("send_booking")
def handle_booking(data):
    """Saves a booking request and notfies the receiver."""
    if "user_id" not in session: 
        return 
    
    sender_id = session["user_id"]
    receiver_id = data.get("receiver_id")
    chat_id = data.get("chat_id")
    course_id = data.get("course_id", None)
    meeting_time = data.get("meeting_time")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO contracts (chat_id, sender_id, receiver_id, course_id, meeting_time)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (chat_id, sender_id, receiver_id, course_id, meeting_time))

    contract_id = cur.fetchone()[0]

    cur.execute("SELECT course_code, course_name FROM courses WHERE id = %s", (course_id,))
    course = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    room = get_room_name(sender_id, receiver_id)

    emit("receive_booking", {
        "contract_id": contract_id,
        "sender_id": sender_id,
        "meeting_time": meeting_time
    }, to=room)

@socketio.on("respond_booking")
def handle_booking_response(data):
    """Updates the contract status when accepted or rejected."""
    if "user_id" not in session:
        return

    contract_id = data.get("contract_id")
    status = data.get("status")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE contracts SET status = %s WHERE id = %s", (status, contract_id))
    conn.commit()

    cur.execute("SELECT sender_id, receiver_id FROM contracts WHERE id = %s", (contract_id,))
    contract = cur.fetchone()

    cur.close()
    conn.close()

    room = get_room_name(contract[0], contract[1])

    emit("booking_response", {
        "contract_id": contract_id,
        "status": status
    }, to=room)


@chat.route("/api/unread_messages_count")
def unread_messages_count():
    if "user_id" not in session:
        return jsonify({"count": 0})

    user_id = session["user_id"]
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM messages m
        JOIN chats c ON c.id = m.chat_id
        WHERE (c.user1_id = %s OR c.user2_id = %s)
          AND m.sender_id != %s
          AND m.is_read = FALSE
    """, (user_id, user_id, user_id))

    count = cur.fetchone()[0]
    cur.close()
    conn.close()

    return jsonify({"count": count})

