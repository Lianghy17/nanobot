#!/usr/bin/env python3
"""ChatBI API测试脚本"""

import requests
import json
from datetime import datetime

# API基础URL
API_BASE = "http://localhost:8000/api"


def test_health():
    """测试健康检查"""
    print("\n=== 测试健康检查 ===")
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_get_scenes():
    """测试获取场景列表"""
    print("\n=== 测试获取场景列表 ===")
    try:
        response = requests.get(f"{API_BASE}/scenes")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            scenes = data.get("scenes", [])
            print(f"场景数量: {len(scenes)}")
            for scene in scenes:
                print(f"  - {scene['scene_code']}: {scene['scene_name']}")
            return scenes
        else:
            print(f"错误: {response.text}")
            return []
    except Exception as e:
        print(f"错误: {e}")
        return []


def test_create_conversation():
    """测试创建对话"""
    print("\n=== 测试创建对话 ===")
    try:
        response = requests.post(
            f"{API_BASE}/conversations",
            json={"scene_code": "sales_analysis"}
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"对话ID: {data['conversation_id']}")
            print(f"场景: {data['scene_name']}")
            return data['conversation_id']
        else:
            print(f"错误: {response.text}")
            return None
    except Exception as e:
        print(f"错误: {e}")
        return None


def test_send_message(conversation_id):
    """测试发送消息"""
    print("\n=== 测试发送消息 ===")
    try:
        response = requests.post(
            f"{API_BASE}/messages",
            json={
                "conversation_id": conversation_id,
                "content": "查询上个月的销售额"
            }
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"消息ID: {data['message_id']}")
            print(f"状态: {data['status']}")
            return True
        else:
            print(f"错误: {response.text}")
            return False
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_get_conversation(conversation_id):
    """测试获取对话详情"""
    print("\n=== 测试获取对话详情 ===")
    try:
        response = requests.get(f"{API_BASE}/conversations/{conversation_id}")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"场景: {data['scene_name']}")
            print(f"消息数: {len(data['messages'])}")
            if data['messages']:
                print("最新消息:")
                msg = data['messages'][-1]
                print(f"  [{msg['role']}]: {msg['content'][:100]}")
            return True
        else:
            print(f"错误: {response.text}")
            return False
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_list_conversations():
    """测试获取对话列表"""
    print("\n=== 测试获取对话列表 ===")
    try:
        response = requests.get(f"{API_BASE}/conversations")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"对话数量: {len(data)}")
            for conv in data:
                print(f"  - {conv['conversation_id']}: {conv['scene_name']} ({conv['message_count']}条消息)")
            return True
        else:
            print(f"错误: {response.text}")
            return False
    except Exception as e:
        print(f"错误: {e}")
        return False


def main():
    """主测试流程"""
    print("=" * 50)
    print("ChatBI API 测试")
    print("=" * 50)
    
    # 1. 健康检查
    if not test_health():
        print("\n❌ 健康检查失败，请确保服务已启动")
        return
    
    print("\n✅ 服务正常运行")
    
    # 2. 获取场景列表
    scenes = test_get_scenes()
    if not scenes:
        print("\n⚠️ 无法获取场景列表")
        return
    
    print("\n✅ 场景列表获取成功")
    
    # 3. 创建对话
    conversation_id = test_create_conversation()
    if not conversation_id:
        print("\n⚠️ 创建对话失败")
        return
    
    print("\n✅ 对话创建成功")
    
    # 4. 等待消息处理
    print("\n等待消息处理...")
    import time
    time.sleep(3)
    
    # 5. 发送消息
    if not test_send_message(conversation_id):
        print("\n⚠️ 发送消息失败")
        return
    
    print("\n✅ 消息发送成功")
    
    # 6. 等待AI回复
    print("\n等待AI回复...")
    time.sleep(5)
    
    # 7. 获取对话详情
    if not test_get_conversation(conversation_id):
        print("\n⚠️ 获取对话详情失败")
        return
    
    print("\n✅ 对话详情获取成功")
    
    # 8. 获取对话列表
    if not test_list_conversations():
        print("\n⚠️ 获取对话列表失败")
        return
    
    print("\n✅ 对话列表获取成功")
    
    print("\n" + "=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)


if __name__ == "__main__":
    main()
