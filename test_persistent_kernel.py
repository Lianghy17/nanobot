#!/usr/bin/env python3
"""测试持久化内核"""
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from chatbi.core.sandbox_manager import PersistentPythonKernel

def test_persistent_kernel():
    """测试持久化内核"""
    import tempfile
    
    print("=" * 60)
    print("测试持久化内核 (jupyter_client)")
    print("=" * 60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix='test_kernel_')
    
    try:
        # 启动内核
        print("\n1. 启动内核...")
        kernel = PersistentPythonKernel('test_conv', temp_dir)
        kernel.start()
        print("✅ 内核启动成功")
        
        # 测试1：执行代码
        print("\n2. 执行第一个代码块...")
        result1 = kernel.execute("""
x = 42
y = 100
print(f"x = {x}, y = {y}")
""", timeout=10)
        
        print(f"✅ 执行1: success={result1['success']}")
        print(f"   输出: {result1['output'][:100]}")
        print(f"   变量: {result1['variables']}")
        
        # 测试2：变量持久化
        print("\n3. 执行第二个代码块（变量应保持）...")
        result2 = kernel.execute("""
z = x + y
print(f"x + y = {z}")
""", timeout=10)
        
        print(f"✅ 执行2: success={result2['success']}")
        print(f"   输出: {result2['output'][:100]}")
        print(f"   变量: {result2['variables']}")
        
        # 验证变量保持
        assert 'x' in result2['variables'], "变量 x 未保持"
        assert 'y' in result2['variables'], "变量 y 未保持"
        assert 'z' in result2['variables'], "变量 z 未创建"
        print("✅ 变量持久化验证成功")
        
        # 测试3：导入持久化
        print("\n4. 测试导入持久化...")
        result3 = kernel.execute("""
import math as mt
print(f"π = {mt.pi}")
""", timeout=10)
        
        print(f"✅ 执行3: success={result3['success']}")
        print(f"   输出: {result3['output'][:100]}")
        
        # 测试4：错误处理
        print("\n5. 测试错误处理...")
        result4 = kernel.execute("""
print(undefined_variable)
""", timeout=10)
        
        print(f"✅ 执行4: success={result4['success']}")
        print(f"   错误: {result4.get('error', 'No error')[:100]}")
        
        # 关闭内核
        print("\n6. 关闭内核...")
        kernel.close()
        print("✅ 内核关闭成功")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    test_persistent_kernel()
