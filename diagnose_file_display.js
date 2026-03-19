// 复制这个脚本到浏览器控制台中运行，用于诊断文件显示问题

(async function diagnoseFileDisplay() {
    console.log('='.repeat(80));
    console.log('开始诊断文件显示问题');
    console.log('='.repeat(80));

    const convId = 'conv_1773809745_a5e1017a';
    const API_BASE = '/api';

    try {
        // 1. 测试API连接
        console.log('\n[1] 测试API连接...');
        const testResponse = await fetch(`${API_BASE}/conversations`);
        console.log(`   状态: ${testResponse.status} ${testResponse.statusText}`);
        console.log(`   ✅ API连接正常`);

        // 2. 加载会话
        console.log('\n[2] 加载会话...');
        const convResponse = await fetch(`${API_BASE}/conversations/${convId}`);
        const conversation = await convResponse.json();
        console.log(`   会话ID: ${conversation.conversation_id}`);
        console.log(`   消息数量: ${conversation.messages.length}`);
        console.log(`   ✅ 会话加载成功`);

        // 3. 分析每条消息
        console.log('\n[3] 分析消息metadata...');
        conversation.messages.forEach((msg, idx) => {
            if (msg.role === 'assistant') {
                console.log(`\n   Assistant消息 ${idx + 1}:`);
                console.log(`   - 内容长度: ${msg.content?.length || 0} 字符`);

                // 检查metadata
                const hasMetadata = msg.metadata != null && typeof msg.metadata === 'object';
                const hasFiles = hasMetadata && 'files' in msg.metadata;
                const filesArray = hasFiles ? msg.metadata.files : null;
                const filesCount = Array.isArray(filesArray) ? filesArray.length : 0;

                console.log(`   - 有metadata: ${hasMetadata ? '✅' : '❌'}`);
                console.log(`   - 有files字段: ${hasFiles ? '✅' : '❌'}`);
                console.log(`   - files是数组: ${Array.isArray(filesArray) ? '✅' : '❌'}`);
                console.log(`   - files数组长度: ${filesCount}`);

                if (filesCount > 0) {
                    console.log(`   - ✅ 找到${filesCount}个文件:`);
                    filesArray.forEach((file, fileIdx) => {
                        const isImage = file.type && file.type.startsWith('image/');
                        console.log(`     文件${fileIdx + 1}: ${file.filename}`);
                        console.log(`       类型: ${file.type}`);
                        console.log(`       大小: ${file.size} 字节`);
                        console.log(`       是图片: ${isImage ? '✅' : '❌'}`);
                        console.log(`       路径: ${file.path}`);

                        // 检查下载URL
                        const downloadUrl = `${API_BASE}/files/download/web_default_user/${convId}/${file.path}`;
                        console.log(`       下载URL: ${downloadUrl}`);

                        // 测试图片是否可以加载
                        if (isImage) {
                            console.log(`       测试图片加载...`);
                            const img = new Image();
                            img.onload = () => {
                                console.log(`       ✅ 图片加载成功 (${img.width}x${img.height})`);
                            };
                            img.onerror = () => {
                                console.log(`       ❌ 图片加载失败`);
                            };
                            img.src = downloadUrl;
                        }
                    });
                } else {
                    console.log(`   - ⚠️ 没有文件数据`);
                }
            }
        });

        // 4. 检查前端渲染
        console.log('\n[4] 检查前端渲染...');
        const messageBubbles = document.querySelectorAll('.message.assistant .bubble');
        console.log(`   找到 ${messageBubbles.length} 个assistant消息气泡`);

        if (messageBubbles.length > 0) {
            messageBubbles.forEach((bubble, idx) => {
                const hasFilesSection = bubble.querySelector('.files-section') !== null;
                const hasImageContainer = bubble.querySelector('.image-container') !== null;
                const hasImages = bubble.querySelectorAll('img').length;

                console.log(`   消息气泡 ${idx + 1}:`);
                console.log(`   - 有files-section: ${hasFilesSection ? '✅' : '❌'}`);
                console.log(`   - 有image-container: ${hasImageContainer ? '✅' : '❌'}`);
                console.log(`   - 图片数量: ${hasImages}`);
            });
        }

        // 5. 检查文件列表API
        console.log('\n[5] 检查文件列表API...');
        const filesResponse = await fetch(`${API_BASE}/files/list/web_default_user/${convId}`);
        const filesData = await filesResponse.json();
        console.log(`   成功: ${filesData.success ? '✅' : '❌'}`);
        console.log(`   文件数量: ${filesData.count || 0}`);
        if (filesData.files && filesData.files.length > 0) {
            console.log(`   文件列表:`);
            filesData.files.forEach((file, idx) => {
                console.log(`     ${idx + 1}. ${file.filename} (${file.size} 字节)`);
            });
        }

        console.log('\n' + '='.repeat(80));
        console.log('诊断完成！');
        console.log('='.repeat(80));
        console.log('\n下一步建议:');
        console.log('1. 如果"有files"显示❌，说明API返回数据有问题');
        console.log('2. 如果"前端渲染"显示❌，说明前端渲染代码有问题');
        console.log('3. 如果"图片加载失败"，说明文件下载API有问题');
        console.log('4. 将完整的控制台输出截图，以便进一步诊断');

    } catch (error) {
        console.error('\n❌ 诊断失败:', error);
        console.error('错误详情:', error.message);
        console.error('错误堆栈:', error.stack);
    }
})();
