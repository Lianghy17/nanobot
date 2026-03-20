// ChatBI前端应用

// 全局状态
let currentConversation = null;
let selectedScene = null;
let scenes = [];
let conversations = [];
let eventSource = null;  // SSE连接

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

        // 建立SSE连接
        establishSSEConnection(conversation.conversation_id);

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
        // 关闭旧的SSE连接
        closeSSEConnection();

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

        // 建立SSE连接
        establishSSEConnection(conversationId);

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
        const content = msg.content || '';

        // 对于assistant的消息，渲染markdown
        if (msg.role === 'assistant') {
            console.log('[renderMessages] Assistant消息metadata:', msg.metadata);
            const markdownHtml = marked.parse(content);

            // 修复markdown中的图片路径，获取已渲染的图片列表
            const { html: fixedHtml, renderedImages } = fixMarkdownImagePaths(markdownHtml, msg.metadata?.files || []);

            // 渲染文件列表，跳过已在markdown中渲染的图片
            const filesHtml = renderFiles(msg.metadata?.files || [], renderedImages);

            return `
                <div class="message ${msg.role}">
                    <div class="bubble">
                        <div class="markdown-content">${fixedHtml}</div>
                        ${filesHtml}
                    </div>
                    <div class="time">${time}</div>
                </div>
            `;
        } else {
            // user消息不渲染markdown
            return `
                <div class="message ${msg.role}">
                    <div class="bubble">${escapeHtml(content)}</div>
                    <div class="time">${time}</div>
                </div>
            `;
        }
    }).join('');
}

// 修复markdown中的图片路径，返回 { html, renderedImages }
function fixMarkdownImagePaths(html, files) {
    // 创建临时DOM来解析HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;

    // 记录已在markdown中渲染的图片文件名
    const renderedImages = [];

    // 获取所有图片标签
    const images = tempDiv.querySelectorAll('img');

    images.forEach(img => {
        const src = img.getAttribute('src');
        if (!src) return;

        // 如果src已经是 data: URL (base64)，跳过
        if (src.startsWith('data:')) {
            return;
        }

        // 如果src已经是完整HTTP URL，跳过
        if (src.startsWith('http://') || src.startsWith('https://')) {
            return;
        }

        // 尝试匹配文件信息
        let matchedFile = null;
        
        // 从 src 中提取文件名（去掉路径前缀）
        const srcFilename = src.split('/').pop();
        
        for (const f of (files || [])) {
            // 优先匹配：有 base64 数据且文件名匹配
            if (f.base64 || f.url?.startsWith('data:')) {
                // 匹配原始文件名
                if (f.filename === src || f.filename === srcFilename) {
                    matchedFile = f;
                    break;
                }
                // 匹配 unique_filename 中的文件名部分
                if (f.unique_filename) {
                    const uniqueParts = f.unique_filename.split('_');
                    const actualName = uniqueParts.slice(3).join('_'); // 去掉 conv_id, timestamp 前缀
                    if (src === actualName || srcFilename === actualName) {
                        matchedFile = f;
                        break;
                    }
                }
            }
        }
        
        // 如果没找到 base64 匹配，尝试其他匹配方式
        if (!matchedFile) {
            matchedFile = files?.find(f => {
                if (f.filename === src || f.filename === srcFilename) return true;
                if (f.url === src) return true;
                return false;
            });
        }

        if (matchedFile) {
            // 记录已渲染的图片文件名
            renderedImages.push(matchedFile.filename);
            
            // 优先使用 base64 数据
            if (matchedFile.base64) {
                img.setAttribute('src', matchedFile.base64);
                console.log('[fixMarkdownImagePaths] 使用base64:', src, '-> base64数据');
            } else if (matchedFile.url?.startsWith('data:')) {
                img.setAttribute('src', matchedFile.url);
                console.log('[fixMarkdownImagePaths] 使用base64 URL:', src);
            } else if (matchedFile.url?.startsWith('/files/')) {
                // 静态文件URL，需要转换
                const downloadUrl = `/api/files/download/web_default_user/${currentConversation.conversation_id}/${matchedFile.filename}`;
                img.setAttribute('src', downloadUrl);
                console.log('[fixMarkdownImagePaths] 使用下载API:', src, '->', downloadUrl);
            } else if (matchedFile.url) {
                img.setAttribute('src', matchedFile.url);
                console.log('[fixMarkdownImagePaths] 使用URL:', src, '->', matchedFile.url);
            }
        } else {
            console.warn('[fixMarkdownImagePaths] 未找到文件信息:', src);
        }
    });

    return { html: tempDiv.innerHTML, renderedImages };
}

// 渲染文件列表（排除已在markdown中渲染的图片）
function renderFiles(files, skipImageFilenames = []) {
    console.log('[renderFiles] 接收到的文件数据:', files, '跳过的图片:', skipImageFilenames);

    if (!files || files.length === 0) {
        return '';
    }

    const filesHtml = files.map(file => {
        const isImage = file.type && file.type.startsWith('image/');
        const filename = file.filename || file.name;
        
        // 如果是图片且已在markdown中渲染，跳过
        if (isImage && skipImageFilenames.includes(filename)) {
            console.log('[renderFiles] 跳过已渲染的图片:', filename);
            return '';
        }

        // 优先使用 base64 数据，否则使用 URL
        let displayUrl;
        if (file.base64) {
            displayUrl = file.base64;
        } else if (file.url?.startsWith('data:')) {
            displayUrl = file.url;
        } else if (file.url) {
            displayUrl = file.url;
        } else {
            displayUrl = `/api/files/download/web_default_user/${currentConversation.conversation_id}/${filename}`;
        }

        console.log('[renderFiles] 处理文件:', { filename, type: file.type, isImage, hasBase64: !!file.base64 });

        if (isImage) {
            return `
                <div class="image-container">
                    <img src="${displayUrl}" alt="${filename}" onclick="openImage('${displayUrl}')">
                    <div class="image-caption">${filename} (${formatFileSize(file.size)})</div>
                </div>
            `;
        } else {
            const icon = getFileIcon(file.type, filename);
            const downloadUrl = `/api/files/download/web_default_user/${currentConversation.conversation_id}/${filename}`;
            return `
                <div class="file-card" onclick="downloadFile('${downloadUrl}', '${filename}')">
                    <span class="file-icon">${icon}</span>
                    <span>${filename}</span>
                    <span style="margin-left:8px;color:#95a5a6;">(${formatFileSize(file.size)})</span>
                </div>
            `;
        }
    }).filter(html => html !== '').join('');  // 过滤空字符串

    // 如果没有文件需要显示，返回空
    if (!filesHtml) {
        return '';
    }

    return `
        <div class="files-section">
            <div class="files-section-title">📎 生成的文件</div>
            ${filesHtml}
        </div>
    `;
}

// 获取文件图标
function getFileIcon(mimeType, filename) {
    // 根据MIME类型映射图标
    const mimeIcons = {
        'text/csv': '📊',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📊',
        'application/vnd.ms-excel': '📊',
        'application/json': '📋',
        'text/plain': '📄',
        'text/markdown': '📝',
        'application/pdf': '📕',
        'image/png': '🖼️',
        'image/jpeg': '🖼️',
        'image/gif': '🖼️',
        'image/svg+xml': '🖼️'
    };

    // 如果MIME类型匹配，直接返回
    if (mimeType && mimeIcons[mimeType]) {
        return mimeIcons[mimeType];
    }

    // 如果MIME类型不匹配，尝试从文件名提取扩展名
    if (filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const extIcons = {
            'csv': '📊',
            'xlsx': '📊',
            'xls': '📊',
            'json': '📋',
            'txt': '📄',
            'md': '📝',
            'pdf': '📕',
            'png': '🖼️',
            'jpg': '🖼️',
            'jpeg': '🖼️',
            'gif': '🖼️',
            'svg': '🖼️'
        };

        if (extIcons[ext]) {
            return extIcons[ext];
        }
    }

    // 默认图标
    return '📎';
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

// 打开图片（新标签页）
function openImage(url) {
    window.open(url, '_blank');
}

// 下载文件
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
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
        console.log('消息已发送:', result);

        // 等待SSE推送结果，不再使用轮询

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

// 建立SSE连接
function establishSSEConnection(conversationId) {
    // 如果已有连接，先关闭
    closeSSEConnection();

    console.log(`[SSE] 建立连接: conversation_id=${conversationId}`);

    // 创建EventSource连接
    eventSource = new EventSource(`${API_BASE}/sse/stream/${conversationId}`);

    // 连接打开
    eventSource.onopen = (event) => {
        console.log('[SSE] 连接已打开');
    };

    // 连接打开事件
    eventSource.addEventListener('connected', (event) => {
        console.log('[SSE] 连接已建立:', JSON.parse(event.data));
    });

    // 消息处理开始
    eventSource.addEventListener('processing_started', (event) => {
        console.log('[SSE] 处理开始:', JSON.parse(event.data));
    });

    // 用户消息已保存
    eventSource.addEventListener('user_message_saved', (event) => {
        console.log('[SSE] 用户消息已保存:', JSON.parse(event.data));
    });

    // 处理完成
    eventSource.addEventListener('processing_completed', (event) => {
        console.log('[SSE] 收到处理完成事件:', event.data);
        try {
            const data = JSON.parse(event.data);
            console.log('[SSE] 解析后数据:', data);

            // 移除思考中的消息
            const thinkingElements = document.querySelectorAll('.message.assistant[id^="thinking_"]');
            thinkingElements.forEach(el => el.remove());

            // 显示AI回复
            console.log('[SSE] 准备显示消息, content长度:', data.content?.length, 'files数量:', data.files?.length);
            appendMessage('assistant', data.content || '处理完成', data.files || []);

            // 启用发送按钮
            document.getElementById('sendBtn').disabled = false;

            // 只更新历史列表，不重新加载整个对话（避免覆盖刚添加的消息）
            loadHistory();
        } catch (e) {
            console.error('[SSE] 解析processing_completed事件失败:', e, event.data);
        }
    });

    // 错误事件
    eventSource.addEventListener('error', (event) => {
        console.error('[SSE] 错误:', JSON.parse(event.data));
        const data = JSON.parse(event.data);

        // 移除思考中的消息
        const thinkingElements = document.querySelectorAll('.message.assistant[id^="thinking_"]');
        thinkingElements.forEach(el => el.remove());

        // 显示错误消息
        appendMessage('assistant', data.message || '抱歉，处理请求时发生错误。');
        document.getElementById('sendBtn').disabled = false;
    });

    // 心跳事件
    eventSource.addEventListener('heartbeat', (event) => {
        console.debug('[SSE] 心跳:', JSON.parse(event.data));
    });

    // 连接错误
    eventSource.onerror = (error) => {
        console.error('[SSE] 连接错误:', error);
        closeSSEConnection();
    };
}

// 关闭SSE连接
function closeSSEConnection() {
    if (eventSource) {
        console.log('[SSE] 关闭连接');
        eventSource.close();
        eventSource = null;
    }
}

// 添加消息到列表
function appendMessage(role, content, files = []) {
    const messageList = document.getElementById('messageList');

    // 移除loading提示
    const loading = messageList.querySelector('.loading');
    if (loading) {
        loading.remove();
    }

    const time = new Date().toLocaleString('zh-CN');
    let messageHtml;

    // 对于assistant的消息，渲染markdown
    if (role === 'assistant') {
        const markdownHtml = marked.parse(content);
        // 修复markdown中的图片路径，获取已渲染的图片列表
        const { html: contentHtml, renderedImages } = fixMarkdownImagePaths(markdownHtml, files);
        // 渲染文件列表，跳过已在markdown中渲染的图片
        const filesHtml = renderFiles(files, renderedImages);

        messageHtml = `
            <div class="message ${role}">
                <div class="bubble">
                    <div class="markdown-content">${contentHtml}</div>
                    ${filesHtml}
                </div>
                <div class="time">${time}</div>
            </div>
        `;
    } else {
        // user消息不渲染markdown
        const contentHtml = escapeHtml(content);
        messageHtml = `
            <div class="message ${role}">
                <div class="bubble">${contentHtml}</div>
                <div class="time">${time}</div>
            </div>
        `;
    }

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

    if (!currentConversation) {
        alert('请先创建对话');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/conversations/${currentConversation.conversation_id}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('上传失败');
        }

        const result = await response.json();
        appendMessage('assistant', `✅ 文件上传成功：${result.filename} (${formatFileSize(result.size)})\n\n文件已准备好，可以开始分析了！`);

        // 加载文件列表
        await loadFiles();

    } catch (error) {
        console.error('上传文件失败:', error);
        alert('上传文件失败: ' + error.message);
    }

    // 清空文件选择
    fileInput.value = '';
}

// 加载文件列表（已废弃，SSE自动推送文件信息）
async function loadFiles() {
    // SSE自动推送文件信息，不再需要手动加载
    // 保留此函数以兼容现有代码
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
