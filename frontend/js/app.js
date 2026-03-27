// ChatBI前端应用

// 全局状态
let currentConversation = null;
let selectedScene = null;
let scenes = [];
let conversations = [];
let eventSource = null;  // SSE连接
let currentMessageId = null;  // 当前正在处理的消息ID（用于取消）
let isProcessing = false;  // 是否正在处理
let currentMode = 'template';  // 当前问答模式: template/react/qa
let qaTemplates = {};  // QA模板数据
let currentTemplate = null;  // 当前选中的模板
let inTemplateMode = false;  // 是否在模板模式中
let forceReactMode = false;  // 是否强制使用React模式（退出模板模式后）

// API基础URL
const API_BASE = '/api';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadScenes();
    loadHistory();
    setupInputListener();
});

// 加载热门问题（改为加载QA模板）
async function loadHotQuestions(sceneCode) {
    try {
        const response = await fetch(`${API_BASE}/qa/templates/${sceneCode}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            qaTemplates = data;
            renderQATemplates(data);
            document.getElementById('hotQuestionsPanel').classList.add('active');
        }
    } catch (error) {
        console.error('加载QA模板失败:', error);
        // 显示默认消息
        document.getElementById('hotQuestionsList').innerHTML = '<div class="loading"><p>QA模板加载失败</p></div>';
    }
}

// 渲染QA模板（只显示模板模式的模板）
function renderQATemplates(qaData) {
    const hotQuestionsList = document.getElementById('hotQuestionsList');

    if (!qaData.templates || qaData.templates.length === 0) {
        hotQuestionsList.innerHTML = '<div class="loading"><p>暂无QA模板</p></div>';
        return;
    }

    // 只显示模板模式的模板（mode='template'或没有mode字段的模板）
    const allTemplates = qaData.templates || [];
    const templateModeTemplates = allTemplates.filter(t => !t.mode || t.mode === 'template');

    if (templateModeTemplates.length === 0) {
        hotQuestionsList.innerHTML = '<div class="loading"><p>暂无模板模式的QA模板</p></div>';
        return;
    }

    // 按类别分组
    const categories = qaData.categories || {};

    // 如果有分类，按分类渲染
    if (Object.keys(categories).length > 0) {
        let html = '';
        for (const [categoryKey, categoryInfo] of Object.entries(categories)) {
            const categoryTemplates = templateModeTemplates.filter(t => categoryInfo.templates.includes(t.id));

            if (categoryTemplates.length > 0) {
                html += `
                    <div class="qa-category">
                        <div class="qa-category-header" onclick="toggleCategory('${categoryKey}')">
                            <span class="category-icon">${categoryInfo.icon || '📁'}</span>
                            <span class="category-name">${categoryKey}</span>
                            <span class="category-desc">${categoryTemplates.length}个模板</span>
                        </div>
                        <div class="qa-category-content" id="category-${categoryKey}">
                            ${categoryTemplates.map(t => renderTemplateItem(t)).join('')}
                        </div>
                    </div>
                `;
            }
        }
        hotQuestionsList.innerHTML = html || '<div class="loading"><p>暂无模板模式的QA模板</p></div>';
    } else {
        // 没有分类，直接渲染所有模板
        hotQuestionsList.innerHTML = templateModeTemplates.map(t => renderTemplateItem(t)).join('');
    }
}

// 渲染单个模板项
function renderTemplateItem(template) {
    return `
        <div class="hot-question-item" onclick="useTemplate('${template.id}')">
            <div class="pattern-tag">${template.category || '默认'}</div>
            <div class="question-text">${template.name || template.question_template}</div>
            <div class="template-hint">${template.description || ''}</div>
        </div>
    `;
}

// 切换分类展开/收起
function toggleCategory(categoryKey) {
    const content = document.getElementById(`category-${categoryKey}`);
    content.classList.toggle('expanded');
}

// 更新模式指示器（在输入框右上角）
function updateModeIndicator(mode) {
    const indicator = document.getElementById('modeIndicator');
    const modeText = document.getElementById('modeText');

    if (!indicator || !modeText) {
        return;
    }

    // 移除所有模式类
    indicator.classList.remove('template-mode', 'react-mode');

    if (mode === 'template') {
        indicator.classList.add('template-mode');
        indicator.querySelector('.mode-icon').textContent = '🎯';
        modeText.textContent = '模板模式';
    } else if (mode === 'react') {
        indicator.classList.add('react-mode');
        indicator.querySelector('.mode-icon').textContent = '🤖';
        modeText.textContent = 'React模式';
    }
}

// 切换问答模式
function switchMode(mode) {
    currentMode = mode;

    // 更新模式指示器（在输入框右上角）
    updateModeIndicator(mode);

    // 更新UI状态（如果还存在mode-btn的话）
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // 不再在消息列表中显示模式提示
}

// 使用QA模板
function useTemplate(templateId) {
    if (!currentConversation) {
        alert('请先创建对话');
        return;
    }
    
    const templates = qaTemplates.templates || [];
    const template = templates.find(t => t.id === templateId);
    
    if (!template) {
        alert('模板不存在');
        return;
    }
    
    currentTemplate = template;
    inTemplateMode = true;
    
    // 切换到模板模式
    switchMode('template');
    
    // 构建模板提示
    const prompt = `我想使用"${template.name}"模板：${template.description}\n\n请引导我填写参数。`;
    
    // 发送消息，带上模板元数据
    sendMessage(prompt, {
        template_mode: true,
        template_id: templateId,
        template_name: template.name,
        template_data: template  // 传递完整模板数据
    });
}

// 显示场景欢迎提示
function showSceneWelcome(scene) {
    if (!scene) return;
    
    // 构建欢迎消息
    let welcomeContent = `## 🎉 欢迎使用${scene.scene_name}\n\n`;
    
    // 添加场景描述
    if (scene.description) {
        welcomeContent += `**场景说明**：${scene.description}\n\n`;
    }
    
    // 添加 user_prompt
    if (scene.user_prompt) {
        welcomeContent += `${scene.user_prompt}\n\n`;
    }
    
    // 添加 important_notes
    if (scene.important_notes && scene.important_notes.length > 0) {
        welcomeContent += `**注意事项**：\n`;
        scene.important_notes.forEach(note => {
            welcomeContent += `- ${note}\n`;
        });
        welcomeContent += `\n`;
    }
    
    // 添加模板提示
    welcomeContent += `---\n\n`;
    welcomeContent += `💡 **提示**：您可以点击右侧的「📋 QA模板库」选择预设问题模板，快速生成数据分析查询。\n\n`;
    welcomeContent += `也可以直接输入您的问题，系统将自动选择最合适的分析模式。`;
    
    // 显示欢迎消息（作为 assistant 消息）
    appendMessage('assistant', welcomeContent, [], { mode: 'react', is_welcome: true });
}

// 显示模式提示（已废弃，使用switchMode）
function showModeTip() {
    // 使用默认模板模式
    switchMode('template');
}

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
        document.getElementById('messageList').innerHTML = '';
        document.getElementById('sendBtn').disabled = false;

        hideSceneDialog();
        loadHistory();

        // 默认显示React模式（未选择模板时）
        switchMode('react');

        // 显示场景欢迎提示
        showSceneWelcome(selectedScene);

        // 加载QA模板
        loadHotQuestions(selectedScene.scene_code);

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

        // 加载QA模板
        loadHotQuestions(conversation.scene_code);

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

            // 检查是否在模板模式中
            const isPatternMode = msg.metadata?.pattern_mode || msg.metadata?.template_mode;
            const showExitButton = isPatternMode && inTemplateMode;

            // 构建操作按钮
            let actionButtonsHtml = '';
            if (showExitButton) {
                actionButtonsHtml = `
                    <div class="message-actions">
                        <button class="btn-exit-template" onclick="exitTemplateMode()">
                            退出模板模式
                        </button>
                    </div>
                `;
            }

            // 如果是React模式，显示提示
            let modeTipHtml = '';
            if (msg.metadata?.mode === 'react' && !isPatternMode) {
                modeTipHtml = `
                    <div class="mode-indicator">
                        <span class="mode-icon">🤖</span>
                        <span>当前为React模式 - 灵活分析</span>
                    </div>
                `;
            }

            return `
                <div class="message ${msg.role}">
                    <div class="bubble">
                        ${modeTipHtml}
                        <div class="markdown-content">${fixedHtml}</div>
                        ${filesHtml}
                        ${actionButtonsHtml}
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
async function sendMessage(messageContent = null, customMetadata = {}) {
    const input = document.getElementById('messageInput');
    const content = messageContent || input.value.trim();

    if (!content) {
        alert('请输入内容');
        return;
    }

    if (!currentConversation) {
        alert('请先创建对话');
        return;
    }

    // 清空输入框（如果不是使用预定义内容）
    if (!messageContent) {
        input.value = '';
    }

    // 构建元数据
    let metadata = { ...customMetadata };
    
    // 如果强制React模式（退出模板模式后），通知后端不走模板续接
    if (forceReactMode) {
        metadata.fallback_to_react = true;
        forceReactMode = false;  // 只触发一次
    }
    
    // 如果在模板模式中，添加模板状态信息
    if (inTemplateMode && currentTemplate && !metadata.template_mode) {
        metadata.template_mode = true;
        metadata.template_id = currentTemplate.id;
        metadata.template_name = currentTemplate.name;
        metadata.continuing_pattern = true;  // 标记为继续Pattern模式
    }

    // 标记为正在处理
    isProcessing = true;
    updateSendButton();

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
                content: content,
                metadata: metadata  // 添加元数据
            })
        });

        if (!response.ok) {
            throw new Error('发送消息失败');
        }

        const result = await response.json();
        currentMessageId = result.message_id; // 保存消息ID用于取消
        console.log('消息已发送:', result);

        // 等待SSE推送结果，不再使用轮询

    } catch (error) {
        console.error('发送消息失败:', error);
        removeThinkingMessage(thinkingMessageId);
        appendMessage('assistant', '抱歉，发送消息失败，请稍后重试。');
        isProcessing = false;
        updateSendButton();
    }
}

// 取消消息
async function cancelMessage() {
    if (!currentMessageId) {
        return;
    }

    if (!confirm('确定要取消当前任务吗？')) {
        return;
    }

    try {
        // 发送取消请求到后端
        const response = await fetch(`${API_BASE}/messages/${currentMessageId}/cancel`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('取消请求失败');
        }

        const result = await response.json();
        console.log('取消请求已发送到后端:', result);

        // 注意：不要立即重置状态，等待 SSE 的 processing_cancelled 事件
        // 这样可以确保后端真正停止了任务

    } catch (error) {
        console.error('取消任务失败:', error);
        alert('取消任务失败: ' + error.message);
    }
}

// 更新发送按钮状态
function updateSendButton() {
    const sendBtn = document.getElementById('sendBtn');

    if (isProcessing) {
        sendBtn.textContent = '取消';
        sendBtn.classList.add('canceling');
        sendBtn.disabled = false;  // 取消按钮应该可用
    } else {
        sendBtn.textContent = '发送';
        sendBtn.classList.remove('canceling');
    }
}

// 处理发送/取消按钮点击
function handleSendOrCancel() {
    if (isProcessing) {
        cancelMessage();
    } else {
        sendMessage();
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

    // 意图分析完成
    eventSource.addEventListener('intent_analyzed', (event) => {
        console.log('[SSE] 意图分析完成:', JSON.parse(event.data));
        try {
            const data = JSON.parse(event.data);
            console.log('[SSE] 意图类型:', data.intent_type, '匹配Pattern:', data.matched_pattern, '模式:', data.mode);

            // 根据意图分析结果更新模式指示器
            if (data.mode) {
                switchMode(data.mode);
            }
        } catch (e) {
            console.error('[SSE] 解析intent_analyzed事件失败:', e, event.data);
        }
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
            console.log('[SSE] 准备显示消息, content长度:', data.content?.length, 'files数量:', data.files?.length, 'metadata:', data.metadata);
            appendMessage('assistant', data.content || '处理完成', data.files || [], data.metadata || {});

            // 重置状态
            isProcessing = false;
            currentMessageId = null;
            updateSendButton();

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

        // 重置状态
        isProcessing = false;
        currentMessageId = null;
        updateSendButton();
    });

    // 取消事件
    eventSource.addEventListener('processing_cancelled', (event) => {
        console.log('[SSE] 收到处理取消事件:', event.data);
        try {
            const data = JSON.parse(event.data);
            console.log('[SSE] 解析后数据:', data);

            // 移除思考中的消息
            const thinkingElements = document.querySelectorAll('.message.assistant[id^="thinking_"]');
            thinkingElements.forEach(el => el.remove());

            // 显示取消消息
            appendMessage('assistant', '⚠️ 任务已被取消');

            // 重置状态
            isProcessing = false;
            currentMessageId = null;
            updateSendButton();

            // 更新历史列表
            loadHistory();
        } catch (e) {
            console.error('[SSE] 解析processing_cancelled事件失败:', e, event.data);
        }
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
function appendMessage(role, content, files = [], metadata = {}) {
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
        // 根据metadata.mode更新模式指示器
        if (metadata.mode) {
            switchMode(metadata.mode);
        }

        const markdownHtml = marked.parse(content);
        // 修复markdown中的图片路径，获取已渲染的图片列表
        const { html: contentHtml, renderedImages } = fixMarkdownImagePaths(markdownHtml, files);
        // 渲染文件列表，跳过已在markdown中渲染的图片
        const filesHtml = renderFiles(files, renderedImages);

        // 检查是否在模板模式中
        const isPatternMode = metadata.pattern_mode || metadata.template_mode;
        const showExitButton = isPatternMode && inTemplateMode;

        // 构建操作按钮
        let actionButtonsHtml = '';
        if (showExitButton) {
            actionButtonsHtml = `
                <div class="message-actions">
                    <button class="btn-exit-template" onclick="exitTemplateMode()">
                        退出模板模式
                    </button>
                </div>
            `;
        }

        // 如果是React模式且不是欢迎消息，显示提示（可选，可以根据需要显示或隐藏）
        let modeTipHtml = '';
        if (metadata.mode === 'react' && !isPatternMode && !metadata.is_welcome) {
            modeTipHtml = `
                <div class="message-mode-indicator">
                    <span class="mode-icon">🤖</span>
                    <span>当前为React模式 - 灵活分析</span>
                </div>
            `;
        }

        messageHtml = `
            <div class="message ${role}">
                <div class="bubble">
                    ${modeTipHtml}
                    <div class="markdown-content">${contentHtml}</div>
                    ${filesHtml}
                    ${actionButtonsHtml}
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

// 退出模板模式
function exitTemplateMode() {
    if (!confirm('确定要退出模板模式吗？')) {
        return;
    }

    inTemplateMode = false;
    currentTemplate = null;
    forceReactMode = true;  // 标记后续消息强制走React模式

    // 切换到React模式
    switchMode('react');

    // 提示用户
    appendMessage('assistant', '✅ 已退出模板模式，请输入您的问题。', [], { mode: 'react' });
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
        // 如果正在处理，不改变按钮状态（保持取消按钮可用）
        if (isProcessing) {
            return;
        }
        // 如果没有正在处理，根据输入内容启用/禁用按钮
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
