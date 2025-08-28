#!/usr/bin/env python3
"""
LangChain Agent 测试脚本

测试智能就业市场分析Agent的功能
"""

import sys
import asyncio
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.rag.rag_system_coordinator import RAGSystemCoordinator
from src.analysis_tools.agent import create_analysis_agent

def load_test_config():
    """加载测试配置"""
    return {
        'rag_system': {
            'database': {
                'path': './data/jobs.db',
                'batch_size': 50
            },
            'llm': {
                'provider': 'zhipu',
                'model': 'glm-4-flash',
                'api_key': '0175134f27a040709d7541e14b4db353.V3KP9u8rZ0oQj9s9',
                'temperature': 0.1,
                'max_tokens': 2000
            },
            'vector_db': {
                'persist_directory': './chroma_db',
                'collection_name': 'job_positions',
                'embeddings': {
                    'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                    'device': 'cpu',
                    'normalize_embeddings': True
                }
            }
        },
        'langchain_agent': {
            'llm': {
                'provider': 'zhipu',
                'model': 'glm-4-flash',
                'api_key': '0175134f27a040709d7541e14b4db353.V3KP9u8rZ0oQj9s9',
                'temperature': 0.1,
                'max_tokens': 2000
            },
            'tools': {
                'skill_demand_analysis': {'enabled': True},
                'salary_analysis': {'enabled': True},
                'trend_analysis': {'enabled': True}
            },
            'user_experience': {
                'interaction': {
                    'welcome_message': '您好！我是就业市场分析助手，基于445个真实职位数据为您提供专业分析。',
                    'help_message': '我可以帮您分析技能需求、薪资水平和市场趋势。'
                },
                'suggested_questions': [
                    'Python工程师的市场需求如何？',
                    '前端开发的平均薪资是多少？',
                    '哪些技能最受欢迎？'
                ]
            }
        }
    }

async def test_agent_initialization():
    """测试Agent初始化"""
    print("🧪 测试1: Agent初始化")
    print("=" * 40)
    
    try:
        config = load_test_config()
        
        # 初始化RAG系统
        coordinator = RAGSystemCoordinator(config)
        if not coordinator.initialize_system():
            print("❌ RAG系统初始化失败")
            return False
        
        # 创建Agent
        agent = create_analysis_agent(coordinator, config)
        print("✅ Agent初始化成功")
        
        # 检查Agent状态
        status = agent.get_agent_status()
        print(f"📊 Agent状态:")
        print(f"   可用工具: {len(status['tools_available'])}")
        print(f"   工具列表: {', '.join(status['tools_available'])}")
        print(f"   LLM提供商: {status['llm_provider']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def test_skill_analysis():
    """测试技能需求分析"""
    print("\n🧪 测试2: 技能需求分析")
    print("=" * 40)
    
    try:
        config = load_test_config()
        coordinator = RAGSystemCoordinator(config)
        
        if not coordinator.initialize_system():
            print("❌ RAG系统初始化失败")
            return False
        
        agent = create_analysis_agent(coordinator, config)
        
        # 测试问题
        test_questions = [
            "Python工程师的市场需求如何？",
            "前端开发需要掌握哪些技能？",
            "数据科学相关的热门技能有哪些？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n📝 问题 {i}: {question}")
            
            try:
                result = agent.run(question)
                
                if result['success']:
                    print(f"✅ 分析成功")
                    print(f"📊 处理时间: {result['processing_time']:.2f}秒")
                    print(f"🔧 使用工具: {', '.join(result['tools_used']) if result['tools_used'] else '无'}")
                    print(f"📄 回答长度: {len(result['response'])} 字符")
                    
                    # 显示回答摘要
                    response_preview = result['response'][:200] + "..." if len(result['response']) > 200 else result['response']
                    print(f"💬 回答预览: {response_preview}")
                    
                else:
                    print(f"❌ 分析失败: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                print(f"❌ 问题处理失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def test_salary_analysis():
    """测试薪资分析"""
    print("\n🧪 测试3: 薪资分析")
    print("=" * 40)
    
    try:
        config = load_test_config()
        coordinator = RAGSystemCoordinator(config)
        
        if not coordinator.initialize_system():
            print("❌ RAG系统初始化失败")
            return False
        
        agent = create_analysis_agent(coordinator, config)
        
        # 测试问题
        test_questions = [
            "Java开发工程师的平均薪资是多少？",
            "北京和上海的薪资差异如何？",
            "高级工程师和初级工程师的薪资差距有多大？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n📝 问题 {i}: {question}")
            
            try:
                result = agent.run(question)
                
                if result['success']:
                    print(f"✅ 分析成功")
                    print(f"📊 处理时间: {result['processing_time']:.2f}秒")
                    print(f"🔧 使用工具: {', '.join(result['tools_used']) if result['tools_used'] else '无'}")
                    
                    # 显示回答摘要
                    response_preview = result['response'][:200] + "..." if len(result['response']) > 200 else result['response']
                    print(f"💬 回答预览: {response_preview}")
                    
                else:
                    print(f"❌ 分析失败: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                print(f"❌ 问题处理失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def test_trend_analysis():
    """测试趋势分析"""
    print("\n🧪 测试4: 趋势分析")
    print("=" * 40)
    
    try:
        config = load_test_config()
        coordinator = RAGSystemCoordinator(config)
        
        if not coordinator.initialize_system():
            print("❌ RAG系统初始化失败")
            return False
        
        agent = create_analysis_agent(coordinator, config)
        
        # 测试问题
        test_questions = [
            "AI相关职位的发展趋势如何？",
            "云计算技能的市场热度怎样？",
            "哪些新兴技术最有前景？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n📝 问题 {i}: {question}")
            
            try:
                result = agent.run(question)
                
                if result['success']:
                    print(f"✅ 分析成功")
                    print(f"📊 处理时间: {result['processing_time']:.2f}秒")
                    print(f"🔧 使用工具: {', '.join(result['tools_used']) if result['tools_used'] else '无'}")
                    
                    # 显示回答摘要
                    response_preview = result['response'][:200] + "..." if len(result['response']) > 200 else result['response']
                    print(f"💬 回答预览: {response_preview}")
                    
                else:
                    print(f"❌ 分析失败: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                print(f"❌ 问题处理失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def test_agent_memory():
    """测试Agent记忆功能"""
    print("\n🧪 测试5: Agent记忆功能")
    print("=" * 40)
    
    try:
        config = load_test_config()
        coordinator = RAGSystemCoordinator(config)
        
        if not coordinator.initialize_system():
            print("❌ RAG系统初始化失败")
            return False
        
        agent = create_analysis_agent(coordinator, config)
        
        # 第一个问题
        print("📝 问题1: Python工程师的市场需求如何？")
        result1 = agent.run("Python工程师的市场需求如何？")
        
        if result1['success']:
            print("✅ 第一个问题分析成功")
        
        # 相关的后续问题
        print("\n📝 问题2: 那么Python工程师需要掌握哪些技能？")
        result2 = agent.run("那么Python工程师需要掌握哪些技能？")
        
        if result2['success']:
            print("✅ 第二个问题分析成功")
            print("🧠 Agent能够理解上下文关联")
        
        # 检查对话历史
        history = agent.get_conversation_history()
        print(f"📚 对话历史长度: {len(history)}")
        
        # 清除记忆测试
        agent.clear_memory()
        history_after_clear = agent.get_conversation_history()
        print(f"🧹 清除后历史长度: {len(history_after_clear)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def test_agent_statistics():
    """测试Agent统计功能"""
    print("\n🧪 测试6: Agent统计功能")
    print("=" * 40)
    
    try:
        config = load_test_config()
        coordinator = RAGSystemCoordinator(config)
        
        if not coordinator.initialize_system():
            print("❌ RAG系统初始化失败")
            return False
        
        agent = create_analysis_agent(coordinator, config)
        
        # 执行几个分析
        questions = [
            "Python的市场需求如何？",
            "Java开发的薪资水平？",
            "前端技术的发展趋势？"
        ]
        
        for question in questions:
            agent.run(question)
        
        # 获取统计信息
        stats = agent.get_analysis_statistics()
        
        print("📈 分析统计:")
        print(f"   总分析次数: {stats.get('total_analyses', 0)}")
        print(f"   成功分析次数: {stats.get('successful_analyses', 0)}")
        print(f"   成功率: {stats.get('success_rate', 0):.1f}%")
        print(f"   平均处理时间: {stats.get('average_processing_time', 0):.2f}秒")
        
        tool_usage = stats.get('tool_usage', {})
        if tool_usage:
            print("🔧 工具使用统计:")
            for tool, count in tool_usage.items():
                print(f"     {tool}: {count}次")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def run_comprehensive_test():
    """运行综合测试"""
    print("🚀 LangChain Agent 综合测试")
    print("=" * 50)
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("Agent初始化", test_agent_initialization),
        ("技能需求分析", test_skill_analysis),
        ("薪资分析", test_salary_analysis),
        ("趋势分析", test_trend_analysis),
        ("记忆功能", test_agent_memory),
        ("统计功能", test_agent_statistics)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 开始测试: {test_name}")
            result = await test_func()
            test_results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
                
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            test_results.append((test_name, False))
    
    # 显示测试摘要
    print("\n" + "=" * 50)
    print("📊 测试结果摘要")
    print("=" * 50)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    print(f"总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"失败测试: {total - passed}")
    print(f"通过率: {(passed / total * 100):.1f}%")
    
    print("\n详细结果:")
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    if passed == total:
        print("\n🎉 所有测试通过！LangChain Agent系统运行正常。")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查系统配置。")
    
    return passed == total

def main():
    """主函数"""
    try:
        success = asyncio.run(run_comprehensive_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()