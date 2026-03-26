# QA模板系统问题排查与解决方案

## 问题描述
选定场景后，前端右侧未展示问题模板列表。

## ✅ 已完成的修复

### 1. 后端配置修复
- **文件**: `chatbi/config.py`
- **修改**: 为`ChatBIConfig`类添加了`config_dir`属性
- **代码**:
```python
@property
def config_dir(self) -> str:
    """获取配置目录路径"""
    return str(get_project_root() / "config")
```

### 2. 服务重启
- 已停止旧服务进程
- 已重新启动ChatBI服务和图片服务
- 服务正常运行在端口8080（主服务）和8081（图片服务）

### 3. API路由注册
- QA模板API路由已正确注册：`/api/qa/templates/{scene_code}`
- 路由已在`chatbi/main.py`中注册

## ✅ 系统状态验证

### API状态
```bash
# 测试API
curl http://localhost:8080/api/qa/templates/sales_analysis | python3 -m json.tool
```

**结果**: ✅ 正常
- 返回状态：`success`
- 模板数量：8个
- 分类数量：5个（销售趋势、产品分析、渠道分析、客户分析、区域分析）

### 配置文件状态
- ✅ `config/QA模板库/sales_analysis/templates.json` - 8个模板
- ✅ `config/QA模板库/user_behavior/templates.json` - 7个模板
- ✅ `config/QA模板库/general_bi/templates.json` - 8个模板

### 前端代码状态
- ✅ `loadHotQuestions()` 函数已定义（第26行）
- ✅ `renderQATemplates()` 函数已定义（第44行）
- ✅ `switchMode()` 函数已定义（第102行）
- ✅ `useTemplate()` 函数已定义（第167行）
- ✅ HTML结构正确（包含`hotQuestionsPanel`元素）
- ✅ CSS样式正确（`.hot-questions-panel.active { display: flex; }`）

## 🔍 问题排查步骤

### 步骤1：运行诊断脚本
```bash
cd /Users/lianghaoyun/project/nanobot
./diagnose_qa_system.sh
```

预期输出：
```
✅ 主服务运行中 (端口8080)
✅ 图片服务运行中 (端口8081)
✅ QA API路由已注册
✅ API正常 (sales_analysis)
✅ API正常 (user_behavior)
✅ API正常 (general_bi)
✅ sales_analysis: 8 个模板
✅ user_behavior: 7 个模板
✅ general_bi: 8 个模板
✅ index.html 存在
✅ app.js 存在
✅ loadHotQuestions 函数已定义
✅ renderQATemplates 函数已定义
✅ switchMode 函数已定义
✅ useTemplate 函数已定义
✅ API响应格式正确
✅ 包含templates字段
✅ 包含categories字段
```

### 步骤2：使用测试页面
访问：`http://localhost:8080/test_qa_frontend.html`

这个测试页面会：
1. 测试API连接
2. 加载场景QA模板
3. 显示QA模板列表
4. 提供详细的调试日志

### 步骤3：检查浏览器控制台
1. 打开浏览器开发者工具（F12）
2. 切换到**Console**标签
3. 选择一个场景
4. 查看是否有错误信息

正常情况下应该看到：
```
开始加载场景: sales_analysis
请求URL: /api/qa/templates/sales_analysis
响应状态: 200 OK
✅ 场景 sales_analysis 加载成功: 8 个模板, 5 个分类
开始渲染 8 个模板
渲染分类 "销售趋势": 2 个模板
渲染分类 "产品分析": 2 个模板
渲染分类 "渠道分析": 1 个模板
渲染分类 "客户分析": 1 个模板
渲染分类 "区域分析": 2 个模板
模板渲染完成
```

### 步骤4：检查网络请求
1. 打开浏览器开发者工具（F12）
2. 切换到**Network**标签
3. 选择**XHR**过滤器
4. 选择一个场景
5. 查找`/api/qa/templates/{scene_code}`请求
6. 点击请求查看详情

正常情况下应该看到：
- **Status**: 200 OK
- **Response**: 包含`status: "success"`, `templates: [...]`, `categories: {...}`

## 🛠️ 常见问题与解决方案

### 问题1：浏览器缓存导致使用旧代码
**症状**：修改代码后仍然显示旧行为

**解决方案**：
```bash
# 方法1：强制刷新
Mac: Cmd + Shift + R
Windows/Linux: Ctrl + Shift + R

# 方法2：清除缓存
Chrome设置 > 隐私和安全 > 清除浏览数据 > 缓存的图片和文件

# 方法3：使用无痕模式测试
Chrome: Cmd + Shift + N (Mac) / Ctrl + Shift + N (Windows)
```

### 问题2：JavaScript执行错误
**症状**：Console中有红色错误信息

**常见错误**：
- `ReferenceError: xxx is not defined` - 函数或变量未定义
- `TypeError: Cannot read property 'xxx' of undefined` - 访问undefined对象的属性
- `NetworkError` - API请求失败

**解决方案**：
1. 查看错误堆栈信息
2. 检查相关代码
3. 使用`console.log()`调试

### 问题3：API请求失败
**症状**：Network标签显示请求失败（非200状态码）

**可能原因**：
- 服务未启动
- 端口被占用
- 路由未注册

**解决方案**：
```bash
# 检查服务状态
lsof -i :8080

# 重启服务
cd /Users/lianghaoyun/project/nanobot
./chatbi/start_with_image_server.sh
```

### 问题4：面板已显示但内容为空
**症状**：右侧面板出现，但显示"暂无QA模板"

**可能原因**：
- API返回的`templates`数组为空
- 渲染函数逻辑错误

**解决方案**：
1. 检查API响应
2. 在Console中执行：`console.log(qaTemplates)`
3. 检查模板文件内容

## 📝 手动测试清单

在浏览器中执行以下操作，逐一确认：

- [ ] 访问 `http://localhost:8080`
- [ ] 点击"新建对话"按钮
- [ ] 选择一个场景（如"销售分析"）
- [ ] 右侧面板自动展开
- [ ] 显示"📋 QA模板库"标题
- [ ] 显示3个模式选择按钮
- [ ] 显示分类列表（如"销售趋势"、"产品分析"等）
- [ ] 点击分类可以展开/收起
- [ ] 每个分类下显示对应的模板
- [ ] 点击模板会触发`useTemplate()`函数
- [ ] Console中无错误信息

## 🎯 快速修复命令

如果所有配置都正确但前端仍不显示，尝试：

```bash
# 1. 完全停止所有服务
lsof -i :8080 -i :8081 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null

# 2. 清除Python缓存
find /Users/lianghaoyun/project/nanobot -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find /Users/lianghaoyun/project/nanobot -type f -name "*.pyc" -delete 2>/dev/null

# 3. 重新启动服务
cd /Users/lianghaoyun/project/nanobot
nohup /bin/bash chatbi/start_with_image_server.sh > logs/server.log 2>&1 &

# 4. 等待服务启动
sleep 5

# 5. 验证服务状态
lsof -i :8080 -i :8081 | grep LISTEN
```

## 📚 相关文档

- `QA_TEMPLATE_SYSTEM.md` - QA模板系统完整实现文档
- `README_QA_TEMPLATE_IMPLEMENTATION.md` - 实现总结
- `FRONTEND_QA_FIX.md` - 前端修复详细说明
- `diagnose_qa_system.sh` - 诊断脚本

## 💡 调试技巧

### 1. 在浏览器Console中调试
```javascript
// 检查全局状态
console.log('selectedScene:', selectedScene);
console.log('qaTemplates:', qaTemplates);
console.log('currentMode:', currentMode);

// 手动调用函数
loadHotQuestions('sales_analysis');

// 检查DOM元素
const panel = document.getElementById('hotQuestionsPanel');
console.log('Panel exists:', !!panel);
console.log('Panel classes:', panel.className);
console.log('Panel display:', window.getComputedStyle(panel).display);
```

### 2. 在Network中查看详细请求
1. 点击请求
2. 查看**Headers**标签 - 请求URL、方法
3. 查看**Response**标签 - 响应内容
4. 查看**Timing**标签 - 请求耗时

### 3. 使用Chrome DevTools断点调试
1. 打开**Sources**标签
2. 找到`app.js`文件
3. 在关键行号左侧点击设置断点
4. 执行操作，代码会在断点处暂停
5. 查看变量值、调用栈

## 🆘 如果问题仍未解决

请提供以下信息：

1. **浏览器Console完整错误信息**
   - 截图或复制所有红色错误

2. **Network请求详情**
   - API请求的完整URL
   - 请求状态码
   - 响应内容（至少前20行）

3. **浏览器版本信息**
   - Chrome/Edge/Firefox版本号
   - 操作系统版本

4. **重现问题的详细步骤**
   - 从打开页面开始
   - 每一步的操作
   - 预期结果 vs 实际结果

5. **诊断脚本输出**
   ```bash
   ./diagnose_qa_system.sh > diagnosis.txt
   ```
   - 提供`diagnosis.txt`内容

## ✨ 成功标志

当问题解决时，你应该看到：

1. ✅ 右侧面板自动展开
2. ✅ 显示"📋 QA模板库"标题
3. ✅ 显示3个模式按钮（模板模式/React模式/QA模式）
4. ✅ 显示分类列表（如销售趋势、产品分析等）
5. ✅ 每个分类下显示对应的模板卡片
6. ✅ 模板卡片显示名称和描述
7. ✅ 点击分类可以展开/收起
8. ✅ 点击模板会填充输入框
9. ✅ Console中无错误信息
10. ✅ 所有功能正常工作
