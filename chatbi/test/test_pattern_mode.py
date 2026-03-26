"""测试Template模式功能 - 只使用scenes.json中的配置"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbi.config import chatbi_config
from chatbi.core.template_loader import SceneTemplateLoader
from chatbi.core.intent_analyzer import IntentAnalyzer
from chatbi.core.sql_builder import PatternSQLBuilder
from chatbi.core.llm_client import LLMClient


async def test_template_loader():
    """测试模板配置加载"""
    print("\n" + "="*80)
    print("测试1: 模板配置加载")
    print("="*80)
    
    try:
        scenes_config_path = Path(chatbi_config.config_dir) / "scenes.json"
        template_loader = SceneTemplateLoader(str(scenes_config_path))
        
        # 获取所有模板
        all_templates = template_loader.get_all_templates()
        print(f"✓ 加载成功: {len(all_templates)} 个模板")
        
        # 获取某个模板
        template = template_loader.get_template("sales_point_query")
        if template:
            print(f"✓ 模板详情: {template.name} - {template.description}")
            print(f"  参数schema: {template.params_schema}")
        
        # 获取场景列表
        scenes = template_loader.get_all_scenes()
        print(f"✓ 场景数: {len(scenes)} 个")
        
        # 获取场景的模板
        scene_templates = template_loader.get_scene_templates("sales_analysis")
        print(f"✓ 销售分析场景的模板: {len(scene_templates)} 个")
        for t in scene_templates[:2]:
            print(f"  - {t.template_id}: {t.name}")
        
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_intent_analyzer():
    """测试意图分析"""
    print("\n" + "="*80)
    print("测试2: 意图分析")
    print("="*80)
    
    try:
        # 初始化组件
        scenes_config_path = Path(chatbi_config.config_dir) / "scenes.json"
        template_loader = SceneTemplateLoader(str(scenes_config_path))
        llm_client = LLMClient(
            api_base=chatbi_config.llm_api_base,
            api_key=chatbi_config.llm_api_key,
            model=chatbi_config.llm_model,
            temperature=chatbi_config.llm_temperature,
            max_tokens=chatbi_config.llm_max_tokens,
            timeout=chatbi_config.llm_timeout,
            thinking_disabled=chatbi_config.llm_thinking_disabled
        )
        intent_analyzer = IntentAnalyzer(llm_client, template_loader)
        
        # 测试查询
        test_queries = [
            "查询今天的销售额",
            "最近30天的销售趋势",
            "按地区统计销售额",
            "分析一下用户行为数据"
        ]
        
        for query in test_queries:
            print(f"\n查询: {query}")
            result = await intent_analyzer.analyze(query, "sales_analysis")
            
            print(f"  意图类型: {result.intent_type}")
            print(f"  匹配Template: {result.matched_template}")
            print(f"  置信度: {result.confidence}")
            if result.template_config:
                print(f"  Template名称: {result.template_config.name}")
            print(f"  参数: {result.params}")
            print(f"  需要澄清: {result.clarification_needed}")
        
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_sql_builder():
    """测试SQL构建"""
    print("\n" + "="*80)
    print("测试3: SQL构建")
    print("="*80)
    
    try:
        scenes_config_path = Path(chatbi_config.config_dir) / "scenes.json"
        template_loader = SceneTemplateLoader(str(scenes_config_path))
        sql_builder = PatternSQLBuilder(template_loader)
        
        # 测试用例（使用scenes.json中的模板ID）
        test_cases = [
            {
                "template_id": "sales_point_query",
                "params": {
                    "metric": "销售额",
                    "time_point": "2024-01-01"
                },
                "context": {
                    "table_name": "sales_orders",
                    "time_field": "created_at"
                }
            },
            {
                "template_id": "sales_trend_analysis",
                "params": {
                    "metric": "销售额",
                    "time_grain": "DAY"
                },
                "context": {
                    "table_name": "sales_orders",
                    "time_field": "created_at"
                }
            }
        ]
        
        for test_case in test_cases:
            print(f"\nTemplate: {test_case['template_id']}")
            sql, error = sql_builder.build(
                test_case['template_id'],
                test_case['params'],
                test_case['context']
            )
            
            if error:
                print(f"✗ 错误: {error}")
            else:
                print(f"✓ SQL: {sql}")
        
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_parameter_validation():
    """测试参数验证"""
    print("\n" + "="*80)
    print("测试4: 参数验证")
    print("="*80)
    
    try:
        scenes_config_path = Path(chatbi_config.config_dir) / "scenes.json"
        template_loader = SceneTemplateLoader(str(scenes_config_path))
        
        # 测试验证（使用scenes.json中的模板ID）
        template_id = "sales_point_query"
        
        # 有效参数
        valid_params = {
            "metric": "销售额",
            "time_point": "2024-01-01"
        }
        is_valid, errors = template_loader.validate_params(template_id, valid_params)
        print(f"\n有效参数: {is_valid}")
        if not is_valid:
            print(f"  错误: {errors}")
        
        # 无效参数(缺少必填字段)
        invalid_params = {
            "metric": "销售额"
            # 缺少 time_point
        }
        is_valid, errors = template_loader.validate_params(template_id, invalid_params)
        print(f"\n无效参数: {is_valid}")
        if not is_valid:
            print(f"  错误: {errors}")
        
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("ChatBI Template模式功能测试")
    print("="*80)
    
    results = []
    
    # 运行测试
    results.append(("模板配置加载", await test_template_loader()))
    results.append(("意图分析", await test_intent_analyzer()))
    results.append(("SQL构建", await test_sql_builder()))
    results.append(("参数验证", await test_parameter_validation()))
    
    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")


if __name__ == "__main__":
    asyncio.run(main())
