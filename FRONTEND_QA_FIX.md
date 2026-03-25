# 前端QA模板显示问题诊断与修复

## 问题现象
选定场景后，前端右侧未展示问题模板列表

## 已完成的修复

### ✅ 修复1：添加config_dir属性
已在`chatbi/config.py`中为`ChatBIConfig`类添加了`config_dir`属性：

```python
@property
def config_dir(self) -> str:
    """获取配置目录路径"""
    return str(get_project_root() / "config")
```

### ✅ 修复2：服务重启
已重启服务以加载最新代码。

## 诊断结果

### ✅ 后端API正常
- API路由已正确注册：`/api/qa/templates/{scene_code}`
- API可以正常返回数据
- 测试命令：`curl http://localhost:8080/api/qa/templates/sales_analysis`

### ✅ 前端代码正确
- `loadHotQuestions()` 函数逻辑正确
- `renderQATemplates()` 渲染函数正确
- CSS样式正确（`.hot-questions-panel.active { display: flex; }`）

### ✅ 配置文件完整
- 3个场景的QA模板文件已创建
- 每个场景包含多个模板和分类
- 文件路径正确：`config/QA模板库/{scene_code}/templates.json`

## 测试工具

### 访问测试页面
```
http://localhost:8080/test_qa_frontend.html
```

这个测试页面会：
1. 测试API连接
2. 加载场景QA模板
3. 显示QA模板列表
4. 提供详细的调试日志

## 可能的原因和解决方案

### 原因1：浏览器缓存JavaScript文件
**症状：** 前端使用旧版本代码

**解决方案：**
```bash
# 方法1：强制刷新浏览器
# Mac: Cmd + Shift + R
# Windows/Linux: Ctrl + Shift + R

# 方法2：清除浏览器缓存
# Chrome设置 > 隐私和安全 > 清除浏览数据

# 方法3：使用无痕模式测试
```

### 原因2：JavaScript执行错误
**症状：** 代码执行到某处停止

**解决方案：**
1. 打开浏览器开发者工具（F12）
2. 切换到Console标签
3. 选择一个场景
4. 查看是否有红色错误信息

### 原因3：API请求失败
**症状：** Network标签显示请求失败

**解决方案：**
1. 打开浏览器开发者工具（F12）
2. 切换到Network标签
3. 选择一个场景
4. 查找`/api/qa/templates/{scene_code}`请求
5. 检查：
   - 状态码是否为200
   - 响应是否包含数据
   - Response Headers是否正确

## 手动测试步骤

### 步骤1：测试API
```bash
curl http://localhost:8080/api/qa/templates/sales_analysis | python3 -m json.tool | head -20
```

预期输出：
```json
{
    "status": "success",
    "scene_code": "sales_analysis",
    "templates": [...],
    "categories": {...}
}
```

### 步骤2：检查前端HTML结构
在浏览器中：
1. 右键点击页面 > 检查
2. 查找`id="hotQuestionsPanel"`
3. 确认该元素存在且在选中场景后添加了`active`类

### 步骤3：检查JavaScript执行
在浏览器Console中执行：
```javascript
// 检查全局变量
console.log('selectedScene:', selectedScene);
console.log('qaTemplates:', qaTemplates);

// 手动调用函数
loadHotQuestions('sales_analysis');
```

## 常见问题

### Q1: 点击按钮后无反应
**A:** 检查Console是否有JavaScript错误，可能是某个函数定义错误。

### Q2: API返回404
**A:** 确认服务已重启，且路由已正确注册。

### Q3: 面板显示了但内容为空
**A:** 检查API返回的数据格式是否正确，确认`templates`数组不为空。

### Q4: 模板可以加载但点击无反应
**A:** 检查`useTemplate()`函数是否正确实现。

## 调试技巧

### 1. 添加console.log
在关键位置添加日志：
```javascript
async function loadHotQuestions(sceneCode) {
    console.log('开始加载QA模板:', sceneCode);
    try {
        const response = await fetch(`${API_BASE}/qa/templates/${sceneCode}`);
        console.log('响应状态:', response.status);
        const data = await response.json();
        console.log('响应数据:', data);
        // ...
    }
}
```

### 2. 使用断点调试
在Chrome DevTools中：
1. 切换到Sources标签
2. 找到app.js文件
3. 在关键行号左侧点击设置断点
4. 执行操作，代码会在断点处暂停

### 3. 网络请求检查
在Network标签中：
1. 选择XHR过滤器
2. 查看所有AJAX请求
3. 点击请求查看详情
4. 查看Request和Response

## 最终验证清单

- [ ] 服务正在运行（`lsof -i :8080`）
- [ ] API路由已注册（访问`/docs`查看）
- [ ] API可以返回数据（使用curl测试）
- [ ] 前端HTML结构正确（检查hotQuestionsPanel元素）
- [ ] JavaScript文件已加载（Sources标签）
- [ ] 无JavaScript错误（Console标签）
- [ ] API请求成功（Network标签）
- [ ] 面板已添加active类（检查DOM）
- [ ] 模板数据已加载（检查qaTemplates变量）

## 联系支持
如果以上步骤都无法解决问题，请提供：
1. 浏览器Console的完整错误信息
2. Network标签中API请求的详细信息
3. 当前使用的浏览器版本
4. 重现问题的详细步骤
