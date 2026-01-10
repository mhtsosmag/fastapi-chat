let chatSocket = null;
let usersSocket = null;

function joinRoom() {
    const username = document.getElementById("username").value;
    const room = document.getElementById("room").value;

    // 🔴 CHAT SOCKET FIRST (IDENTITY)
    chatSocket = new WebSocket(`ws://${location.host}/ws/chat/${room}/${username}`);
    chatSocket.onmessage = e => {
        const chat = document.getElementById("chat");
        chat.innerHTML += `<div>${e.data}</div>`;
        chat.scrollTop = chat.scrollHeight;
    };

    // 🟢 USERS SOCKET SECOND (READ-ONLY)
    chatSocket.onopen = () => {
        usersSocket = new WebSocket(`ws://${location.host}/ws/users/${room}`);
        usersSocket.onmessage = e => renderUsers(JSON.parse(e.data));
    };
}

function sendMessage() {
    const input = document.getElementById("message");
    if (chatSocket && input.value.trim()) {
        chatSocket.send(input.value);
        input.value = "";
    }
}

function leaveRoom() {
    chatSocket?.close();
    usersSocket?.close();
}

function renderUsers(users) {
    const list = document.getElementById("active-users");
    list.innerHTML = "";
    users.forEach(u => {
        list.innerHTML += `
            <div class="user">
                <span class="dot"></span>${u}
            </div>
        `;
    });
}
