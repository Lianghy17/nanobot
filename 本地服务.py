"""使用 requests 请求大模型 API 的示例"""

import requests
import json

# 示例 1: 请求 Moonshot/Kimi (基于 config_backup.json 配置)
def request_moonshot():
    """请求 Moonshot/Kimi API"""
    url = "https://api.moonshot.cn/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-HSOmrqHUbXiysyRHD5TkkAJKTy6UbNQieW42A2IE4aYIG7ht"
    }
    
    data = {
        "model": "moonshot-v1-8k",
        "messages": [
            {"role": "user", "content": "你好，请用一句话介绍一下你自己"}
        ],
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    else:
        return f"请求失败: {response.status_code} - {response.text}"


# 示例 2: 请求 OpenAI 兼容接口
def request_openai_compatible(api_key, base_url, model, messages):
    """请求 OpenAI 兼容的 API"""
    url = f"{base_url}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    else:
        return f"请求失败: {response.status_code} - {response.text}"


# 示例 3: 带 Stream 流式响应
def request_with_stream():
    """带流式响应的请求"""
    url = "https://api.moonshot.cn/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-HSOmrqHUbXiysyRHD5TkkAJKTy6UbNQieW42A2IE4aYIG7ht"
    }
    
    data = {
        "model": "moonshot-v1-8k",
        "messages": [
            {"role": "user", "content": "用三个词描述Python"}
        ],
        "stream": True  # 开启流式响应
    }
    
    response = requests.post(url, headers=headers, json=data, stream=True, timeout=30)
    
    full_content = ""
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                if data_str == '[DONE]':
                    break
                try:
                    json_data = json.loads(data_str)
                    delta = json_data.get('choices', [{}])[0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        full_content += content
                        print(content, end='', flush=True)
                except json.JSONDecodeError:
                    continue
    
    return full_content


# 示例 4: 请求本地服务 (nanobot server)
def request_nanobot_local():
    """请求本地 nanobot 服务"""
    url = "http://localhost:5088/api/agent/chat"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "message": "画一个简单的折线图",
        "session_id": "web:123456"
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=120)
    
    if response.status_code == 200:
        result = response.json()
        return result.get("response", "无响应")
    else:
        return f"请求失败: {response.status_code} - {response.text}"


# 示例 5: OpenAI 兼容接口 + 工具调用
def request_with_tools():
    """OpenAI 兼容接口带工具调用"""
    url = "https://api.moonshot.cn/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-HSOmrqHUbXiysyRHD5TkkAJKTy6UbNQieW42A2IE4aYIG7ht"
    }
    
    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取指定城市的天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称，例如：北京"
                        }
                    },
                    "required": ["city"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "执行数学计算",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，例如：2 + 3 * 4"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    ]
    
    data = {
        "model": "moonshot-v1-8k",
        "messages": [
            {"role": "system", "content": "你是一个有用的助手，可以使用工具来帮助用户。"},
            {"role": "user", "content": "帮我计算 123 + 456"}
        ],
        "tools": tools,
        "tool_choice": "auto",  # 自动选择工具
        "temperature": 0
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        choice = result["choices"][0]
        
        if choice.get("finish_reason") == "tool_calls":
            # 模型决定调用工具
            tool_calls = choice["message"].get("tool_calls", [])
            print(f"模型决定调用 {len(tool_calls)} 个工具:")
            
            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                print(f"\n工具名称: {function_name}")
                print(f"参数: {function_args}")
                
                # 执行工具
                if function_name == "calculate":
                    result = eval(function_args["expression"])
                    print(f"执行结果: {result}")
        
        return choice["message"].get("content", "")
    else:
        return f"请求失败: {response.status_code} - {response.text}"


# 示例 6: 多轮对话 + 工具调用
def request_multi_turn_with_tools():
    """多轮对话中的工具调用"""
    url = "https://api.moonshot.cn/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-HSOmrqHUbXiysyRHD5TkkAJKTy6UbNQieW42A2IE4aYIG7ht"
    }
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取当前时间",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]
    
    messages = [
        {"role": "system", "content": "你是一个有用的助手。"},
        {"role": "user", "content": "现在几点了？"}
    ]
    
    # 第一轮请求
    print("第一轮请求...")
    data = {
        "model": "moonshot-v1-8k",
        "messages": messages,
        "tools": tools,
        "temperature": 0
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    result = response.json()
    choice = result["choices"][0]
    
    # 将助手响应添加到历史
    messages.append(choice["message"])
    
    # 检查是否需要调用工具
    if choice.get("finish_reason") == "tool_calls":
        tool_calls = choice["message"].get("tool_calls", [])
        
        # 执行工具并添加工具响应
        for tool_call in tool_calls:
            from datetime import datetime
            tool_response = {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False)
            }
            messages.append(tool_response)
        
        # 第二轮请求（提供工具结果）
        print("\n第二轮请求（包含工具结果）...")
        data["messages"] = messages
        
        response2 = requests.post(url, headers=headers, json=data, timeout=30)
        result2 = response2.json()
        return result2["choices"][0]["message"]["content"]
    
    return choice["message"].get("content", "")


if __name__ == "__main__":
    # 测试工具调用
    print("=" * 50)
    print("测试 1: 工具调用（非流式）")
    print("=" * 50)
    result = request_with_tools()
    print("\n最终回复:", result)
    print()
    
    # 测试多轮对话 + 工具调用
    print("=" * 50)
    print("测试 2: 多轮对话 + 工具调用")
    print("=" * 50)
    result = request_multi_turn_with_tools()
    print("回复:", result)
