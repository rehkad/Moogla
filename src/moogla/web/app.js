async function sendMessage() {
    const input = document.getElementById('message');
    const text = input.value.trim();
    if (!text) return;
    const chat = document.getElementById('chat');
    chat.innerHTML += `<div class="text-right mb-2"><span class="bg-blue-100 px-2 py-1 rounded">${text}</span></div>`;
    input.value = '';
    const resp = await fetch('/v1/chat/completions', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({messages: [{role: 'user', content: text}]})
    });
    const data = await resp.json();
    const reply = data.choices[0].message.content;
    chat.innerHTML += `<div class="text-left mb-2"><span class="bg-green-100 px-2 py-1 rounded">${reply}</span></div>`;
    chat.scrollTop = chat.scrollHeight;
}

document.getElementById('send').addEventListener('click', sendMessage);
document.getElementById('message').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});
