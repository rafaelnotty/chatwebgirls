let token = localStorage.getItem('token');
let currentUser = localStorage.getItem('username');
let userType = localStorage.getItem('type_user');
let ws = null;

// Inicialización
if (token) {
    showChat();
    connectWebSocket();
    loadMessages();
}

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
    });

    if (response.ok) {
        const data = await response.json();
        token = data.access_token;
        currentUser = username;
        userType = data.type_user;
        
        localStorage.setItem('token', token);
        localStorage.setItem('username', currentUser);
        localStorage.setItem('type_user', userType);
        
        document.getElementById('login-error').innerText = '';
        showChat();
        connectWebSocket();
        loadMessages();
    } else {
        document.getElementById('login-error').innerText = 'Credenciales inválidas';
    }
}

function logout() {
    localStorage.clear();
    if (ws) ws.close();
    window.location.reload();
}

function showChat() {
    document.getElementById('login-container').style.display = 'none';
    document.getElementById('chat-container').style.display = 'block';
    document.getElementById('current-user-display').innerText = currentUser;
    if (userType === 'admin') {
        document.getElementById('admin-panel').style.display = 'block';
    }
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws?token=${token}`);
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
            appendMessage(data);
        } else if (data.type === 'delete') {
            loadMessages(); // Recargar historial si alguien borra un mensaje
        }
    };
}

async function loadMessages() {
    const response = await fetch('/messages/', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (response.ok) {
        const messages = await response.json();
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML = '';
        messages.forEach(msg => appendMessage(msg));
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

function appendMessage(msg) {
    const messagesDiv = document.getElementById('messages');
    const div = document.createElement('div');
    const isAdmin = userType === 'admin';
    div.className = `message ${msg.user_id === currentUser ? 'own' : ''} ${msg.is_deleted ? 'deleted' : ''}`;

    let contentHtml = `<strong>${msg.user_id}:</strong> `;

    if (msg.is_deleted && !isAdmin) {
        // Usuarios normales: el mensaje desaparece del API, nunca llegan aquí en práctica
        // pero si se recibe vía WS antes del reload, mostramos placeholder
        contentHtml += `<em class="deleted-text">[Mensaje eliminado]</em>`;
    } else {
        // Admin ve todo el contenido real; usuarios normales ven sus mensajes vigentes
        if (msg.message_type === 'audio') {
            contentHtml += `<audio controls src="${msg.content}" preload="none"></audio>`;
            if (msg.is_deleted && isAdmin) {
                contentHtml += ` <span class="deleted-badge">eliminado</span>`;
            }
        } else {
            contentHtml += msg.content;
            if (msg.is_deleted && isAdmin) {
                contentHtml += ` <span class="deleted-badge">eliminado</span>`;
            }
        }
    }

    contentHtml += `<small>${new Date(msg.timestamp).toLocaleTimeString()}</small>`;

    if (!msg.is_deleted && (msg.user_id === currentUser || isAdmin)) {
        contentHtml += `<button class="delete-btn" onclick="deleteMessage(${msg.id})">X</button>`;
    }

    div.innerHTML = contentHtml;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById('message-input');
    if (input.value.trim() !== '' && ws) {
        ws.send(input.value);
        input.value = '';
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') sendMessage();
}

async function deleteMessage(id) {
    await fetch(`/messages/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
}

// --- Funciones de Administrador ---
async function createUser() {
    const username = document.getElementById('new-user').value;
    const password = document.getElementById('new-pass').value;
    const type_user = document.getElementById('new-type').value;

    const response = await fetch('/users/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ username, password, type_user })
    });
    const data = await response.json();
    alert(data.detail || data.msg);
}

async function deleteUser() {
    const username = document.getElementById('del-user').value;
    const response = await fetch(`/users/${username}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    alert(data.detail || data.msg);
}
// --- Emojis ---

window.addEventListener('DOMContentLoaded', () => {
    const emojiBtn = document.getElementById('emoji-btn');
    const messageInput = document.getElementById('message-input');
    const pickerContainer = document.getElementById('emoji-picker-container');
    const pickerEl = pickerContainer.querySelector('emoji-picker');

    emojiBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        pickerContainer.style.display = pickerContainer.style.display === 'none' ? 'block' : 'none';
    });

    pickerEl.addEventListener('emoji-click', (e) => {
        messageInput.value += e.detail.unicode;
        pickerContainer.style.display = 'none';
        messageInput.focus();
    });

    document.addEventListener('click', (e) => {
        if (!pickerContainer.contains(e.target) && e.target !== emojiBtn) {
            pickerContainer.style.display = 'none';
        }
    });

    // --- Grabación de audio ---

    const recordBtn = document.getElementById('record-btn');
    let mediaRecorder = null;
    let audioChunks = [];
    let recordingStream = null;

    recordBtn.addEventListener('click', async () => {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            // Detener grabación
            mediaRecorder.stop();
        } else {
            // Iniciar grabación
            try {
                recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(recordingStream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) audioChunks.push(e.data);
                };

                mediaRecorder.onstop = async () => {
                    recordBtn.textContent = '🎤';
                    recordBtn.classList.remove('recording');
                    recordingStream.getTracks().forEach(t => t.stop());

                    const blob = new Blob(audioChunks, { type: 'audio/webm' });
                    const formData = new FormData();
                    formData.append('audio', blob, 'audio.webm');

                    await fetch('/messages/audio', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` },
                        body: formData
                    });
                };

                mediaRecorder.start();
                recordBtn.textContent = '⏹';
                recordBtn.classList.add('recording');
            } catch (err) {
                alert('No se pudo acceder al micrófono: ' + err.message);
            }
        }
    });
});