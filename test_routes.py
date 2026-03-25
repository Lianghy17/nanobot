#!/usr/bin/env python3
"""测试FastAPI路由注册"""
import sys
sys.path.insert(0, '/Users/lianghaoyun/project/nanobot')

from chatbi.main import app

def test_routes():
    """测试路由注册"""
    print("=" * 80)
    print("测试FastAPI路由注册")
    print("=" * 80)
    
    # 获取所有路由
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
    
    print(f"\n✓ 总共有 {len(routes)} 个路由")
    
    # 查找patterns相关的路由
    patterns_routes = [r for r in routes if '/patterns' in r]
    print(f"✓ patterns相关的路由有 {len(patterns_routes)} 个:")
    for route in sorted(patterns_routes):
        print(f"  - {route}")
    
    # 查找hot-questions路由
    hot_questions_routes = [r for r in routes if 'hot-questions' in r]
    print(f"\n✓ hot-questions路由有 {len(hot_questions_routes)} 个:")
    for route in hot_questions_routes:
        print(f"  - {route}")
    
    print("\n" + "=" * 80)
    return len(hot_questions_routes) > 0

if __name__ == "__main__":
    success = test_routes()
    print("✓ hot-questions路由已注册" if success else "✗ hot-questions路由未注册")
    print("=" * 80)
    sys.exit(0 if success else 1)
