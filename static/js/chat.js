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

function toggleBookingForm() {
    const form = document.getElementById("booking-form");
    form.style.display = form.style.display === "none" ? "block" : "none";
}

function sendBooking() {
    const courseId = document.getElementById("booking-course").value;
    const meetingTime = document.getElementById("booking-time").value;

    if (!meetingTime) {
        alert("Välj ett datum och tid.");
        return;
    }

    socketio.emit("send_booking", {
        receiver_id: RECEIVER_ID,
        chat_id: CHAT_ID,
        course_id: courseId,
        meeting_time: meetingTime
    });

    toggleBookingForm();
}

socketio.on("receive_booking", function(data) {
    const msg = document.createElement("div");
    msg.classList.add("message", "booking-card");

    if (data.sender_id == CURRENT_USER_ID) {
        msg.classList.add("me");
        msg.innerHTML = `
            <p>📅 Bokningsförfrågan skickad</p>
            <p><strong>Kurs:</strong> ${data.course_name}</p>
            <p><strong>Tid:</strong> ${data.meeting_time}</p>
            <p>Väntar på svar...</p>
        `;
    } else {
        msg.classList.add("other");
        msg.innerHTML = `
            <p>📅 Bokningsförfrågan</p>
            <p><strong>Kurs:</strong> ${data.course_name}</p>
            <p><strong>Tid:</strong> ${data.meeting_time}</p>
            <button onclick="respondBooking(${data.contract_id}, 'accepted')">✅ Acceptera</button>
            <button onclick="respondBooking(${data.contract_id}, 'rejected')">❌ Neka</button>
        `;
    }

    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
});

function respondBooking(contractId, status) {
    socketio.emit("respond_booking", {
        contract_id: contractId,
        status: status
    });
}

socketio.on("booking_response", function(data) {
    alert(`Bokning ${data.status === "accepted" ? "accepterad ✅" : "nekad ❌"}`);
});

