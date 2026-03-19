// 调试辅助函数
function debugMessageRendering(messages) {
    console.log('=== 调试消息渲染 ===');
    console.log('消息总数:', messages.length);

    messages.forEach((msg, idx) => {
        console.log(`\n消息 ${idx}:`);
        console.log('  role:', msg.role);
        console.log('  content长度:', msg.content?.length || 0);

        // 详细检查metadata
        console.log('  metadata:', msg.metadata);
        console.log('  metadata类型:', typeof msg.metadata);
        console.log('  metadata是否为null:', msg.metadata === null);
        console.log('  metadata是否为undefined:', msg.metadata === undefined);

        if (msg.metadata) {
            console.log('  metadata.keys:', Object.keys(msg.metadata));
            console.log('  metadata.files:', msg.metadata.files);
            console.log('  metadata.files类型:', typeof msg.metadata.files);
            console.log('  metadata.files是否为数组:', Array.isArray(msg.metadata.files));

            if (Array.isArray(msg.metadata.files) && msg.metadata.files.length > 0) {
                console.log('  ✅ 发现文件:', msg.metadata.files);
                msg.metadata.files.forEach((file, fileIdx) => {
                    console.log(`    文件${fileIdx}:`, {
                        filename: file.filename,
                        type: file.type,
                        size: file.size,
                        path: file.path,
                        isImage: file.type?.startsWith('image/')
                    });
                });
            } else {
                console.log('  ⚠️ 没有文件或文件数组为空');
            }
        } else {
            console.log('  ❌ metadata为空或未定义');
        }
    });
    console.log('=== 调试结束 ===\n');
}

// 调试renderFiles函数
function debugRenderFiles(files) {
    console.log('=== 调试renderFiles ===');
    console.log('输入的files参数:', files);
    console.log('files类型:', typeof files);
    console.log('files是否为数组:', Array.isArray(files));
    console.log('files长度:', files?.length || 0);

    if (!files || files.length === 0) {
        console.log('❌ files为空或未定义，返回空字符串');
        return '';
    }

    console.log('✅ 开始渲染文件...');

    const result = files.map((file, idx) => {
        console.log(`\n处理文件 ${idx}:`, file);
        const isImage = file.type && file.type.startsWith('image/');
        console.log('  isImage:', isImage);
        console.log('  file.type:', file.type);
        console.log('  file.filename:', file.filename);

        return {
            file: file,
            isImage: isImage,
            willDisplay: true
        };
    });

    console.log(`\n✅ 将渲染 ${result.length} 个文件`);
    console.log('=== 调试结束 ===\n');

    return '';
}

// 在浏览器控制台运行这些函数进行调试
console.log('调试函数已加载。使用方法:');
console.log('1. 在当前页面加载消息后，运行 debugMessageRendering(messages)');
console.log('2. 运行 debugRenderFiles(files)');
