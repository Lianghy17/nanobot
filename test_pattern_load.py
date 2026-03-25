#!/usr/bin/env python3
"""测试Pattern配置加载"""
import sys
sys.path.insert(0, '/Users/lianghaoyun/project/nanobot')

from chatbi.core.pattern_loader import PatternLoader
from chatbi.config import chatbi_config

def test_pattern_loading():
    """测试Pattern配置加载"""
    print("=" * 80)
    print("测试Pattern配置加载")
    print("=" * 80)
    
    try:
        # 初始化PatternLoader
        pattern_loader = PatternLoader(chatbi_config.pattern_config_path)
        
        print(f"✓ PatternLoader初始化成功")
        print(f"✓ 配置路径: {chatbi_config.pattern_config_path}")
        
        # 获取所有patterns
        all_patterns = pattern_loader.get_all_patterns()
        print(f"✓ 加载了 {len(all_patterns)} 个Pattern")
        
        # 测试funnel pattern（因为它有step_time_limit字段）
        funnel_pattern = pattern_loader.get_pattern("funnel")
        if funnel_pattern:
            print(f"✓ 找到funnel pattern: {funnel_pattern.name}")
            print(f"  - description: {funnel_pattern.description}")
            print(f"  - step_time_limit: {funnel_pattern.step_time_limit}")
            print(f"  - complexity: {funnel_pattern.complexity}")
        else:
            print(f"✗ 未找到funnel pattern")
        
        # 测试hot_templates
        hot_templates = pattern_loader.get_hot_templates("funnel")
        print(f"✓ funnel pattern有 {len(hot_templates)} 个热门模板")
        
        # 测试目录
        catalog = pattern_loader.get_pattern_catalog()
        print(f"✓ Pattern目录有 {len(catalog)} 个类别")
        
        print("\n" + "=" * 80)
        print("✓ Pattern配置加载测试通过！")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n✗ Pattern配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pattern_loading()
    sys.exit(0 if success else 1)
