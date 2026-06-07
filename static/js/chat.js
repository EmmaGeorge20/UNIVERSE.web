// chat.js
// Handles real-time messaging and booking requests on the chat page via Socket.IO.

var socketio = io();

const chat = document.getElementById("chat");
const messageInput = document.getElementById("message");


// Joins the Socket.IO room for the chat with the selected receiver
socketio.emit("join_chat", {
    receiver_id: RECEIVER_ID
});

function scrollToBottom() {
    if (chat) {
        chat.scrollTop = chat.scrollHeight;
    }
}

window.addEventListener("load", scrollToBottom);

// Sends the typed message to the server and clears the input field
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

// Renders an incoming message bubble as soon as it arrives from the server
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

   scrollToBottom();
}

function toggleBookingForm() {
    const form = document.getElementById("booking-form");
    form.style.display = form.style.display === "none" ? "block" : "none";
}

// Sends a booking request for the selected course and meeting time
function sendBooking() {
    const meetingTime = document.getElementById("booking-time").value;
    const courseId = document.getElementById("booking-course").value;

    if (!meetingTime) {
        alert("Välj ett datum och tid.");
        return;
    }

    socketio.emit("send_booking", {
        receiver_id: parseInt(RECEIVER_ID),
        chat_id: parseInt(CHAT_ID),
        course_id: courseId,
        meeting_time: meetingTime
    });

    toggleBookingForm();
}

// Renders an incoming booking event: a "waiting" card for the sender, or accept/reject buttons for the receiver
socketio.on("receive_booking", function(data) {
    const msg = document.createElement("div");
    msg.classList.add("message", "booking-card");

    if (data.sender_id == CURRENT_USER_ID) {
        msg.classList.add("me");
        msg.dataset.id = data.contract_id;  
        msg.innerHTML = `
            <p>Bokningsförfrågan skickad</p>
            <p><strong>Kurs:</strong> ${data.course_name}</p>
            <p><strong>Tid:</strong> ${data.meeting_time}</p>
            <p>Väntar på svar...</p>
        `;
    } else {
        msg.classList.add("other");
        msg.innerHTML = `
        <p>Bokningsförfrågan</p>
        <p><strong>Kurs:</strong> ${data.course_name}</p>
        <p><strong>Tid:</strong> ${data.meeting_time}</p>
        <button class="respond-btn" data-id="${data.contract_id}" data-status="accepted">Acceptera</button>
        <button class="respond-btn" data-id="${data.contract_id}" data-status="rejected">Neka</button>
    `;
}

    chat.appendChild(msg);
    scrollToBottom();
});

// Sends the receiver's accept/reject decision for a booking request back to the server
function respondBooking(contractId, status) {
    socketio.emit("respond_booking", {
        contract_id: contractId,
        status: status
    });
}

// Delegates clicks on accept/reject buttons inside booking cards to respondBooking
document.addEventListener("click", function(e) {
    if (e.target.classList.contains("respond-btn")) {
        const contractId = e.target.dataset.id;
        const status = e.target.dataset.status;
        respondBooking(contractId, status);
    }
});

// Updates the booking card UI once the receiver has accepted or rejected the request
socketio.on("booking_response", function(data) {
    const status = data.status === "accepted" ? "Accepterad" : "Nekad";
    
    const buttons = document.querySelectorAll(`.respond-btn[data-id="${data.contract_id}"]`);
    if (buttons.length > 0) {
        const card = buttons[0].closest(".booking-card");
        buttons.forEach(btn => btn.remove());
        const p = document.createElement("p");
        p.textContent = status;
        card.appendChild(p);
    }

    const meCards = document.querySelectorAll(`.booking-card.me[data-id="${data.contract_id}"]`);
    meCards.forEach(card => {
        const waiting = card.querySelector("p:last-child");
        if (waiting && waiting.textContent === "Väntar på svar...") {
            waiting.textContent = status;
         }
    });

   scrollToBottom();
});



