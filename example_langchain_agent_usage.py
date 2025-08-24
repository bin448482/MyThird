#!/usr/bin/env python3
"""
LangChain Agent 智能数据分析系统使用示例

这个脚本演示了如何使用LangChain Agent系统进行职位市场数据分析
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.analysis_tools.agent import JobMarketAnalysisAgent
from src.rag.rag_system_coordinator import RAGSystemCoordinator

def main():
    """主函数 - 演示LangChain Agent的使用"""
    
    print("🤖 LangChain Agent 智能数据分析系统演示")
    print("=" * 50)
    
    try:
        # 1. 初始化RAG系统
        print("\n📊 初始化RAG系统...")
        rag_coordinator = RAGSystemCoordinator()
        rag_coordinator.initialize_system()
        print("✅ RAG系统初始化完成")
        
        # 2. 创建LangChain Agent
        print("\n🤖 创建LangChain Agent...")
        agent = JobMarketAnalysisAgent(
            rag_coordinator=rag_coordinator,
            config_path="config/agent_config.yaml"
        )
        print("✅ Agent创建完成")
        
        # 3. 显示Agent状态
        print(f"\n📋 Agent状态:")
        print(f"   可用工具: {len(agent.tools)}")
        print(f"   工具列表: {', '.join([tool.name for tool in agent.tools])}")
        
        # 4. 演示分析功能
        print("\n🔍 开始智能分析演示...")
        
        # 示例问题列表
        demo_questions = [
            "Python工程师的市场需求如何？",
            "前端开发工程师的平均薪资是多少？",
            "AI和机器学习相关职位的发展趋势怎样？",
            "数据分析师需要掌握哪些核心技能？"
        ]
        
        for i, question in enumerate(demo_questions, 1):
            print(f"\n💬 问题 {i}: {question}")
            print("-" * 40)
            
            try:
                # 执行分析
                response = agent.analyze(question)
                print(f"🤖 Agent回答: {response[:200]}...")
                
            except Exception as e:
                print(f"❌ 分析失败: {e}")
        
        # 5. 显示统计信息
        print("\n📊 分析统计信息:")
        stats = agent.get_analysis_stats()
        print(f"   总分析次数: {stats.get('total_analyses', 0)}")
        print(f"   成功率: {stats.get('success_rate', 0):.1%}")
        print(f"   平均处理时间: {stats.get('average_processing_time', 0):.2f}秒")
        
        # 6. 交互式演示（可选）
        print("\n🎯 交互式演示 (输入 'quit' 退出):")
        while True:
            try:
                user_input = input("\n💬 请输入您的问题: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出']:
                    break
                
                if not user_input:
                    continue
                
                print("🤖 分析中...")
                response = agent.analyze(user_input)
                print(f"\n🤖 Agent回答: {response}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ 分析失败: {e}")
        
        print("\n✅ 演示完成！")
        
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return 1
    
    return 0

def show_system_info():
    """显示系统信息"""
    print("\n📋 系统信息:")
    print(f"   Python版本: {sys.version}")
    print(f"   项目路径: {project_root}")
    print(f"   配置文件: config/agent_config.yaml")
    print(f"   数据库: data/jobs.db")
    print(f"   向量数据库: chroma_db/")

if __name__ == "__main__":
    # 显示系统信息
    show_system_info()
    
    # 运行主程序
    exit_code = main()
    sys.exit(exit_code)