# QA模板系统快速开始指南

## 🎯 系统已就绪

QA模板系统已经完全实现并正常运行！

## 🚀 快速测试

### 方法1：使用测试页面（推荐）
```
访问：http://localhost:8080/test_qa_frontend.html
```
这个页面会自动测试所有功能并显示详细的调试信息。

### 方法2：使用主界面
```
访问：http://localhost:8080
```
1. 点击"新建对话"
2. 选择一个场景（如"销售分析"）
3. 右侧会自动显示QA模板库

### 方法3：运行诊断脚本
```bash
cd /Users/lianghaoyun/project/nanobot
./diagnose_qa_system.sh
```

## ✅ 系统状态

### 服务状态
- ✅ ChatBI主服务：http://localhost:8080
- ✅ 图片服务：http://localhost:8081

### API端点
- `GET /api/qa/templates/{scene_code}` - 获取场景QA模板
- `GET /api/qa/templates/{scene_code}/{template_id}` - 获取模板详情
- `GET /api/qa/schema/{scene_code}` - 获取场景表结构
- `GET /api/qa/knowledge/{scene_code}` - 获取场景知识库

### 可用场景
1. **销售分析** (sales_analysis) - 8个模板
2. **用户行为** (user_behavior) - 7个模板
3. **通用BI** (general_bi) - 8个模板

## 🎨 三种问答模式

### 1. 🎯 模板模式
- 用户直接提问
- 系统自动匹配模板
- 引导用户完善查询条件
- 生成SQL

### 2. 🤖 React模式
- 问题未命中模板时自动切换
- 使用大模型理解意图
- 通过多轮对话明确需求
- 灵活支持复杂查询

### 3. 📝 QA模式
- 直接点击右侧QA模板
- 系统引导填写参数
- 生成SQL并执行

## 📁 配置文件结构

```
config/
├── QA模板库/
│   ├── sales_analysis/
│   │   └── templates.json    # 8个模板
│   ├── user_behavior/
│   │   └── templates.json    # 7个模板
│   └── general_bi/
│       └── templates.json    # 8个模板
├── 表schema/
│   ├── sales_analysis/
│   │   └── sales_schema.json
│   ├── user_behavior/
│   │   └── user_behavior_schema.json
│   └── general_bi/
│       └── general_schema.json
└── 知识库/
    ├── sales_analysis/
    │   ├── 业务知识.md
    │   └── 指标说明.md
    ├── user_behavior/
    │   ├── 业务知识.md
    │   └── 指标说明.md
    └── general_bi/
        └── 业务知识.md
```

## 🔧 如果遇到问题

### 快速修复
```bash
# 1. 重启服务
cd /Users/lianghaoyun/project/nanobot
lsof -i :8080 -i :8081 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null
nohup /bin/bash chatbi/start_with_image_server.sh > logs/server.log 2>&1 &

# 2. 清除浏览器缓存
# Mac: Cmd + Shift + R
# Windows: Ctrl + Shift + R

# 3. 使用无痕模式测试
# Chrome: Cmd + Shift + N (Mac) / Ctrl + Shift + N (Windows)
```

### 详细排查
查看完整排查指南：`QA_TEMPLATE_TROUBLESHOOTING.md`

## 📚 相关文档

- `QA_TEMPLATE_TROUBLESHOOTING.md` - 完整问题排查指南
- `QA_TEMPLATE_SYSTEM.md` - 系统实现文档
- `README_QA_TEMPLATE_IMPLEMENTATION.md` - 实现总结
- `diagnose_qa_system.sh` - 诊断脚本

## ✨ 使用示例

### 示例1：使用模板模式
1. 选择"销售分析"场景
2. 在输入框中输入："查看最近30天的销售趋势"
3. 系统自动匹配"日销售趋势"模板
4. 引导填写时间范围等参数
5. 生成SQL并执行

### 示例2：使用QA模式
1. 选择"销售分析"场景
2. 在右侧面板找到"销售趋势"分类
3. 点击"日销售趋势"模板
4. 系统引导填写参数
5. 自动生成查询

### 示例3：使用React模式
1. 选择"销售分析"场景
2. 点击"React模式"按钮
3. 输入复杂问题："对比北京和上海各个渠道的销售额"
4. 系统通过多轮对话理解需求
5. 生成灵活的SQL查询

## 🎉 系统特性

- ✅ 3个预定义场景，23个QA模板
- ✅ 3种问答模式，灵活切换
- ✅ 模板分类管理，易于扩展
- ✅ 参数引导填写，降低使用门槛
- ✅ 实时SQL生成和执行
- ✅ 完整的调试和诊断工具

## 📞 获取帮助

如果遇到问题：
1. 查看浏览器Console（F12）
2. 运行诊断脚本：`./diagnose_qa_system.sh`
3. 参考排查文档：`QA_TEMPLATE_TROUBLESHOOTING.md`
4. 使用测试页面：`http://localhost:8080/test_qa_frontend.html`

---

**祝您使用愉快！🚀**
