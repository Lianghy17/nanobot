// ChatBI前端应用

// 全局状态
let currentConversation = null;
let selectedScene = null;
let scenes = [];
let conversations = [];
let pollingInterval = null;  // 轮询定时器

// API基础URL
const API_BASE = '/api';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadScenes();
    loadHistory();
    setupInputListener();
});

// 加载场景列表
async function loadScenes() {
    try {
        const response = await fetch(`${API_BASE}/scenes`);
        const data = await response.json();
        scenes = data.scenes || [];
        renderScenes();
    } catch (error) {
        console.error('加载场景失败:', error);
        alert('加载场景列表失败');
    }
}

// 渲染场景列表
function renderScenes() {
    const sceneList = document.getElementById('sceneList');
    sceneList.innerHTML = scenes.map(scene => `
        <div class="scene-card" onclick="selectScene('${scene.scene_code}')">
            <h3>${scene.scene_name}</h3>
            <p>${scene.description}</p>
            <p><small>支持技能: ${scene.supported_skills.join(', ')}</small></p>
        </div>
    `).join('');
}

// 显示场景选择弹窗
function showSceneDialog() {
    selectedScene = null;
    document.getElementById('sceneModal').classList.add('active');
    document.getElementById('createBtn').disabled = true;
    
    // 清除选中状态
    document.querySelectorAll('.scene-card').forEach(card => {
        card.classList.remove('selected');
    });
}

// 隐藏场景选择弹窗
function hideSceneDialog() {
    document.getElementById('sceneModal').classList.remove('active');
}

// 选择场景
function selectScene(sceneCode) {
    selectedScene = scenes.find(s => s.scene_code === sceneCode);
    
    // 更新UI
    document.querySelectorAll('.scene-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    event.currentTarget.classList.add('selected');
    document.getElementById('createBtn').disabled = false;
}

// 创建对话
async function createConversation() {
    if (!selectedScene) {
        alert('请选择场景');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/conversations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scene_code: selectedScene.scene_code
            })
        });
        
        if (!response.ok) {
            throw new Error('创建对话失败');
        }
        
        const conversation = await response.json();
        currentConversation = conversation;
        
        // 更新UI
        document.getElementById('convTitle').textContent = conversation.scene_name;
        document.getElementById('messageList').innerHTML = '<div class="loading"><p>新对话已创建，开始提问吧！</p></div>';
        document.getElementById('sendBtn').disabled = false;
        
        hideSceneDialog();
        loadHistory();
        
        // 聚焦输入框
        document.getElementById('messageInput').focus();
        
    } catch (error) {
        console.error('创建对话失败:', error);
        alert('创建对话失败');
    }
}

// 加载历史对话
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/conversations`);
        const data = await response.json();
        conversations = data || [];
        renderHistory();
    } catch (error) {
        console.error('加载历史对话失败:', error);
    }
}

// 渲染历史对话
function renderHistory() {
    const historyList = document.getElementById('historyList');
    
    if (conversations.length === 0) {
        historyList.innerHTML = '<p style="text-align:center;color:#95a5a6;padding:20px;">暂无历史对话</p>';
        return;
    }
    
    historyList.innerHTML = conversations.map(conv => {
        const isActive = currentConversation && currentConversation.conversation_id === conv.conversation_id;
        const date = new Date(conv.created_at).toLocaleString('zh-CN');
        
        return `
            <div class="history-item ${isActive ? 'active' : ''}" onclick="loadConversation('${conv.conversation_id}')">
                <div class="history-title">${conv.title || '新对话'}</div>
                <div class="history-time">${date} • ${conv.message_count}条消息</div>
            </div>
        `;
    }).join('');
}

// 加载指定对话
async function loadConversation(conversationId) {
    try {
        const response = await fetch(`${API_BASE}/conversations/${conversationId}`);
        
        if (!response.ok) {
            throw new Error('加载对话失败');
        }
        
        const conversation = await response.json();
        currentConversation = conversation;
        
        // 更新UI
        document.getElementById('convTitle').textContent = conversation.scene_name;
        renderMessages(conversation.messages);
        document.getElementById('sendBtn').disabled = false;
        
        renderHistory();
        scrollToBottom();
        
    } catch (error) {
        console.error('加载对话失败:', error);
        alert('加载对话失败');
    }
}

// 渲染消息
function renderMessages(messages) {
    const messageList = document.getElementById('messageList');
    
    if (messages.length === 0) {
        messageList.innerHTML = '<div class="loading"><p>暂无消息，开始提问吧！</p></div>';
        return;
    }
    
    messageList.innerHTML = messages.map(msg => {
        const time = new Date(msg.timestamp).toLocaleString('zh-CN');
        
        return `
            <div class="message ${msg.role}">
                <div class="bubble">${escapeHtml(msg.content)}</div>
                <div class="time">${time}</div>
            </div>
        `;
    }).join('');
}

// 发送消息
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();

    if (!content) {
        alert('请输入内容');
        return;
    }

    if (!currentConversation) {
        alert('请先创建对话');
        return;
    }

    // 清空输入框
    input.value = '';
    document.getElementById('sendBtn').disabled = true;

    // 显示用户消息
    appendMessage('user', content);

    // 显示AI正在思考
    const thinkingMessageId = appendThinkingMessage();

    try {
        const response = await fetch(`${API_BASE}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation_id: currentConversation.conversation_id,
                content: content
            })
        });

        if (!response.ok) {
            throw new Error('发送消息失败');
        }

        const result = await response.json();

        // 开始轮询获取AI回复
        startPolling(thinkingMessageId);

    } catch (error) {
        console.error('发送消息失败:', error);
        removeThinkingMessage(thinkingMessageId);
        appendMessage('assistant', '抱歉，发送消息失败，请稍后重试。');
        document.getElementById('sendBtn').disabled = false;
    }
}

// 添加思考中的消息占位符
function appendThinkingMessage() {
    const messageList = document.getElementById('messageList');

    // 移除loading提示
    const loading = messageList.querySelector('.loading');
    if (loading) {
        loading.remove();
    }

    const thinkingId = 'thinking_' + Date.now();
    const thinkingHtml = `
        <div class="message assistant" id="${thinkingId}">
            <div class="bubble thinking">
                <span class="thinking-dot"></span>
                <span class="thinking-dot"></span>
                <span class="thinking-dot"></span>
            </div>
        </div>
    `;

    messageList.insertAdjacentHTML('beforeend', thinkingHtml);
    scrollToBottom();

    return thinkingId;
}

// 移除思考中的消息
function removeThinkingMessage(thinkingId) {
    const thinkingElement = document.getElementById(thinkingId);
    if (thinkingElement) {
        thinkingElement.remove();
    }
}

// 开始轮询获取AI回复
function startPolling(thinkingMessageId) {
    // 清除之前的轮询
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    let pollCount = 0;
    const maxPolls = 30;  // 最多轮询30次（30秒）

    pollingInterval = setInterval(async () => {
        pollCount++;

        if (pollCount > maxPolls) {
            clearInterval(pollingInterval);
            removeThinkingMessage(thinkingMessageId);
            appendMessage('assistant', '抱歉，处理时间过长，请稍后刷新查看结果。');
            document.getElementById('sendBtn').disabled = false;
            return;
        }

        try {
            // 获取对话的最新消息
            const response = await fetch(`${API_BASE}/conversations/${currentConversation.conversation_id}/messages`);

            if (!response.ok) {
                return;
            }

            const data = await response.json();

            // 检查是否有新的AI回复
            const messages = data.messages || [];
            const lastMessage = messages[messages.length - 1];

            // 如果最后一条消息是assistant，说明AI已回复
            if (lastMessage && lastMessage.role === 'assistant') {
                clearInterval(pollingInterval);
                removeThinkingMessage(thinkingMessageId);

                // 重新加载对话以显示完整内容
                await loadConversation(currentConversation.conversation_id);

                document.getElementById('sendBtn').disabled = false;
            }

        } catch (error) {
            console.error('轮询失败:', error);
        }
    }, 1000);  // 每秒轮询一次
}

// 停止轮询
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// 添加消息到列表
function appendMessage(role, content) {
    const messageList = document.getElementById('messageList');
    
    // 移除loading提示
    const loading = messageList.querySelector('.loading');
    if (loading) {
        loading.remove();
    }
    
    const time = new Date().toLocaleString('zh-CN');
    
    const messageHtml = `
        <div class="message ${role}">
            <div class="bubble">${escapeHtml(content)}</div>
            <div class="time">${time}</div>
        </div>
    `;
    
    messageList.insertAdjacentHTML('beforeend', messageHtml);
    scrollToBottom();
}

// 滚动到底部
function scrollToBottom() {
    const messageList = document.getElementById('messageList');
    messageList.scrollTop = messageList.scrollHeight;
}

// 键盘事件处理
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// 输入框监听
function setupInputListener() {
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    
    input.addEventListener('input', () => {
        sendBtn.disabled = !input.value.trim() || !currentConversation;
    });
}

// 上传文件
async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/files/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('上传失败');
        }
        
        const result = await response.json();
        alert(`文件上传成功：${result.file_path}`);
        
    } catch (error) {
        console.error('上传文件失败:', error);
        alert('上传文件失败');
    }
    
    // 清空文件选择
    fileInput.value = '';
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 页面加载完成后初始化
window.addEventListener('load', () => {
    console.log('ChatBI应用已加载');
});
