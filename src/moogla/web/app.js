const chatEl = document.getElementById('chat');
const inputEl = document.getElementById('message');
const loadingEl = document.getElementById('loading');
const modelSelect = document.getElementById('model');
const pluginContainer = document.getElementById('plugin-container');
const fileInput = document.getElementById('file-input');
const hintsContainer = document.getElementById('hints');
const clearBtn = document.getElementById('clear-chat');

const models = ['default', 'codellama:13b'];
const plugins = ['tests.dummy_plugin'];
const hints = ['Summarize the text', 'List key points', 'Explain it simply'];
let history = [];

function loadModels() {
    models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m;
        modelSelect.appendChild(opt);
    });
    const savedModel = localStorage.getItem('model');
    if (savedModel) modelSelect.value = savedModel;
    modelSelect.addEventListener('change', () => {
        localStorage.setItem('model', modelSelect.value);
    });
}

function loadPlugins() {
    const saved = (localStorage.getItem('plugins') || '').split(',').filter(Boolean);
    plugins.forEach(p => {
        const label = document.createElement('label');
        label.className = 'flex items-center space-x-1 text-sm';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = p;
        cb.checked = saved.includes(p);
        cb.addEventListener('change', () => {
            const selected = Array.from(pluginContainer.querySelectorAll('input:checked')).map(el => el.value);
            localStorage.setItem('plugins', selected.join(','));
        });
        label.appendChild(cb);
        label.appendChild(document.createTextNode(p));
        pluginContainer.appendChild(label);
    });
}

function loadHints() {
    hints.forEach(h => {
        const btn = document.createElement('button');
        btn.textContent = h;
        btn.className = 'text-xs bg-gray-200 px-2 py-1 rounded';
        btn.addEventListener('click', () => {
            inputEl.value = h;
            inputEl.focus();
        });
        hintsContainer.appendChild(btn);
    });
}

function loadHistory() {
    history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    history.forEach(msg => addMessage(msg.role, msg.content));
}

function addMessage(role, text) {
    const div = document.createElement('div');
    div.className = `mb-2 ${role === 'user' ? 'text-right' : 'text-left'}`;
    const span = document.createElement('span');
    span.className = `${role === 'user' ? 'bg-blue-100' : 'bg-green-100'} px-2 py-1 rounded`;
    span.textContent = text;
    div.appendChild(span);
    chatEl.appendChild(div);
    chatEl.scrollTop = chatEl.scrollHeight;
    return span;
}

async function sendMessage(textOverride) {
    const text = (textOverride ?? inputEl.value).trim();
    if (!text) return;
    const userSpan = addMessage('user', text);
    history.push({role:'user', content:text});
    localStorage.setItem('chatHistory', JSON.stringify(history));
    inputEl.value = '';
    loadingEl.classList.remove('hidden');
    try {
        const resp = await fetch('/v1/chat/completions', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({
                model: modelSelect.value,
                messages: history,
                stream: true
            })
        });
        if (resp.body && resp.headers.get('content-type')?.includes('text/event-stream')) {
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            const span = addMessage('assistant', '');
            let buffer = '';
            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, {stream:true});
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        span.textContent += data.choices[0].delta?.content || '';
                    } catch {
                        span.textContent += line;
                    }
                    chatEl.scrollTop = chatEl.scrollHeight;
                }
            }
            if (buffer.trim()) span.textContent += buffer.trim();
            history.push({role:'assistant', content: span.textContent});
        } else {
            const data = await resp.json();
            const reply = data.choices[0].message.content;
            addMessage('assistant', reply);
            history.push({role:'assistant', content:reply});
        }
    } catch (err) {
        addMessage('assistant', 'Error: '+err.message);
    } finally {
        loadingEl.classList.add('hidden');
        localStorage.setItem('chatHistory', JSON.stringify(history));
    }
}

document.getElementById('send').addEventListener('click', sendMessage);
inputEl.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (!file) return;
    const text = await file.text();
    addMessage('user', `[Uploaded: ${file.name}]`);
    await sendMessage(text);
    fileInput.value = '';
});

clearBtn.addEventListener('click', () => {
    history = [];
    localStorage.removeItem('chatHistory');
    chatEl.innerHTML = '';
});

loadModels();
loadPlugins();
loadHistory();
loadHints();
