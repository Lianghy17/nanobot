#!/bin/bash

echo "=========================================="
echo "  QA模板系统诊断工具"
echo "=========================================="
echo ""

# 检查服务状态
echo "1. 检查服务状态..."
if lsof -i :8080 > /dev/null 2>&1; then
    echo "   ✅ 主服务运行中 (端口8080)"
else
    echo "   ❌ 主服务未运行 (端口8080)"
    exit 1
fi

if lsof -i :8081 > /dev/null 2>&1; then
    echo "   ✅ 图片服务运行中 (端口8081)"
else
    echo "   ⚠️  图片服务未运行 (端口8081)"
fi

echo ""

# 检查API路由
echo "2. 检查API路由..."
RESPONSE=$(curl -s http://localhost:8080/docs 2>/dev/null | grep -o "qa" | head -1)
if [ -n "$RESPONSE" ]; then
    echo "   ✅ QA API路由已注册"
else
    echo "   ❌ QA API路由未注册"
fi

echo ""

# 测试QA模板API
echo "3. 测试QA模板API..."
for scene in "sales_analysis" "user_behavior" "general_bi"; do
    echo "   测试场景: $scene"
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/qa/templates/$scene 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        echo "      ✅ API正常 ($scene)"
    else
        echo "      ❌ API失败 ($scene) - HTTP $STATUS"
    fi
done

echo ""

# 检查配置文件
echo "4. 检查配置文件..."
CONFIG_DIR="/Users/lianghaoyun/project/nanobot/config"
for scene in "sales_analysis" "user_behavior" "general_bi"; do
    TEMPLATE_FILE="$CONFIG_DIR/QA模板库/$scene/templates.json"
    if [ -f "$TEMPLATE_FILE" ]; then
        COUNT=$(python3 -c "import json; data=json.load(open('$TEMPLATE_FILE')); print(len(data.get('templates', [])))" 2>/dev/null)
        echo "   ✅ $scene: $COUNT 个模板"
    else
        echo "   ❌ $scene: 文件不存在"
    fi
done

echo ""

# 检查前端文件
echo "5. 检查前端文件..."
HTML_FILE="/Users/lianghaoyun/project/nanobot/frontend/index.html"
JS_FILE="/Users/lianghaoyun/project/nanobot/frontend/js/app.js"

if [ -f "$HTML_FILE" ]; then
    echo "   ✅ index.html 存在"
else
    echo "   ❌ index.html 不存在"
fi

if [ -f "$JS_FILE" ]; then
    echo "   ✅ app.js 存在"
else
    echo "   ❌ app.js 不存在"
fi

echo ""

# 检查关键函数
echo "6. 检查JavaScript函数..."
if grep -q "function loadHotQuestions" "$JS_FILE"; then
    echo "   ✅ loadHotQuestions 函数已定义"
else
    echo "   ❌ loadHotQuestions 函数未定义"
fi

if grep -q "function renderQATemplates" "$JS_FILE"; then
    echo "   ✅ renderQATemplates 函数已定义"
else
    echo "   ❌ renderQATemplates 函数未定义"
fi

if grep -q "function switchMode" "$JS_FILE"; then
    echo "   ✅ switchMode 函数已定义"
else
    echo "   ❌ switchMode 函数未定义"
fi

if grep -q "function useTemplate" "$JS_FILE"; then
    echo "   ✅ useTemplate 函数已定义"
else
    echo "   ❌ useTemplate 函数未定义"
fi

echo ""

# 测试API响应内容
echo "7. 测试API响应内容..."
RESPONSE=$(curl -s http://localhost:8080/api/qa/templates/sales_analysis 2>/dev/null)
if echo "$RESPONSE" | grep -q '"status": *"success"'; then
    echo "   ✅ API响应格式正确"
else
    echo "   ❌ API响应格式错误"
    echo "   响应内容: $(echo "$RESPONSE" | head -c 100)"
fi

if echo "$RESPONSE" | grep -q '"templates"'; then
    echo "   ✅ 包含templates字段"
else
    echo "   ❌ 缺少templates字段"
fi

if echo "$RESPONSE" | grep -q '"categories"'; then
    echo "   ✅ 包含categories字段"
else
    echo "   ❌ 缺少categories字段"
fi

echo ""
echo "=========================================="
echo "  诊断完成"
echo "=========================================="
echo ""
echo "建议操作："
echo "1. 访问 http://localhost:8080/test_qa_frontend.html 进行前端测试"
echo "2. 打开浏览器开发者工具（F12）查看Console和Network"
echo "3. 如果所有检查都通过，尝试清除浏览器缓存或使用无痕模式"
echo ""
