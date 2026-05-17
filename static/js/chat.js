var socketio = io(); 

const chat = document.getElementById("chat");
const messageInput = document.getElementById("message");


socketio.emit("join_chat", {
    receiver_id: RECEIVER_ID
});

const sendMessage = () => {
    const message = messageInput.value.trim();

    if (message === "") {
        return;
    }

    socketio.emit("send_message", {
        receiver_id: RECEIVER_ID,
        message: message
    });

    messageInput.value = "";
};

socketio.on("receive_message", function(data) {
    addMessage(data);
});

function addMessage(data) {
    const msg = document.createElement("div");
    msg.classList.add("message");

    if (data.sender_id == CURRENT_USER_ID) {
        msg.classList.add("me");
    } else {
        msg.classList.add("other");
    }

    msg.textContent = data.message;

    chat.appendChild(msg);

    chat.scrollTop = chat.scrollHeight;
}

