const API_BASE = 'http://localhost:8000/api/v1';
let currentScene = null;
let sessionId = null;

async function loadScenes() {
    try {
        const response = await fetch(`${API_BASE}/scenes`);
        const scenes = await response.json();
        const grid = document.getElementById('sceneGrid');
        grid.innerHTML = scenes.map(scene => `
            <div class="scene-card" onclick="selectScene('${scene.scene_code}')">
                <h3>${scene.scene_name}</h3>
                <p>${scene.description}</p>
                <span class="code">${scene.scene_code}</span>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load scenes:', error);
        alert('加载场景失败，请检查后端服务是否启动');
    }
}

function selectScene(sceneCode) {
    currentScene = sceneCode;
    sessionId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    fetch(`${API_BASE}/scenes`)
        .then(r => r.json())
        .then(scenes => {
            const scene = scenes.find(s => s.scene_code === sceneCode);
            if (scene) {
                document.getElementById('currentSceneName').textContent = scene.scene_name;
                document.getElementById('currentSceneCode').textContent = scene.scene_code;
                document.getElementById('sceneSelection').style.display = 'none';
                document.getElementById('chatContainer').style.display = 'flex';
            }
        });
}

function goBack() {
    document.getElementById('sceneSelection').style.display = 'flex';
    document.getElementById('chatContainer').style.display = 'none';
    document.getElementById('chatMessages').innerHTML = '';
    currentScene = null;
    sessionId = null;
}

function addMessage(role, content) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `<div class="message-content">${content}</div>`;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addToolCall(name, params) {
    const messagesDiv = document.getElementById('chatMessages');
    const toolDiv = document.createElement('div');
    toolDiv.className = 'tool-call';
    toolDiv.innerHTML = `<strong>🔧 调用工具:</strong> ${name}<br><small>${JSON.stringify(params)}</small>`;
    messagesDiv.appendChild(toolDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addToolResult(result) {
    const messagesDiv = document.getElementById('chatMessages');
    const resultDiv = document.createElement('div');
    resultDiv.className = 'tool-result';
    resultDiv.innerHTML = `<strong>📊 工具结果:</strong><br><pre>${escapeHtml(result)}</pre>`;
    messagesDiv.appendChild(resultDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    addMessage('user', message);

    const messagesDiv = document.getElementById('chatMessages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = '<div class="message-content"><div class="loading"></div> 思考中...</div>';
    messagesDiv.appendChild(loadingDiv);

    try {
        const response = await fetch(`${API_BASE}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                scene_code: currentScene,
                session_id: sessionId,
                user_id: 'web-user',
                stream: true
            })
        });

        messagesDiv.removeChild(loadingDiv);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantMessage = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        if (data.type === 'thinking') {
                            if (!assistantMessage) {
                                addMessage('assistant', data.content);
                            }
                        } else if (data.type === 'tool_call') {
                            addToolCall(data.name, data.params);
                        } else if (data.type === 'tool_result') {
                            addToolResult(data.result);
                        } else if (data.type === 'content') {
                            if (assistantMessage) {
                                const lastMessage = messagesDiv.querySelector('.message.assistant:last-child .message-content');
                                if (lastMessage) {
                                    lastMessage.innerHTML += escapeHtml(data.content);
                                }
                            } else {
                                addMessage('assistant', data.content);
                                assistantMessage = data.content;
                            }
                        }
                    } catch (e) {
                        console.error('Error parsing SSE:', e);
                    }
                }
            }
        }
    } catch (error) {
        messagesDiv.removeChild(loadingDiv);
        addMessage('assistant', `错误: ${error.message}`);
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

document.addEventListener('DOMContentLoaded', loadScenes);
