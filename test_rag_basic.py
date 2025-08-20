"""
RAG系统基础测试

测试RAG模块的基本导入和初始化功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """测试基础导入"""
    print("🔍 测试基础导入...")
    
    try:
        # 测试核心依赖
        import langchain
        print("✅ LangChain导入成功")
        
        import chromadb
        print("✅ ChromaDB导入成功")
        
        import sentence_transformers
        print("✅ Sentence Transformers导入成功")
        
        import openai
        print("✅ OpenAI导入成功")
        
        import pydantic
        print("✅ Pydantic导入成功")
        
        print("\n📦 已安装的关键版本:")
        print(f"  - LangChain: {langchain.__version__}")
        print(f"  - ChromaDB: {chromadb.__version__}")
        print(f"  - OpenAI: {openai.__version__}")
        print(f"  - Pydantic: {pydantic.__version__}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"⚠️ 其他错误: {e}")
        return False

def test_rag_modules():
    """测试RAG模块导入"""
    print("\n🧪 测试RAG模块导入...")
    
    try:
        # 测试RAG模块导入
        from src.rag import LangChainJobProcessor, ChromaDBManager, JobRAGSystem
        print("✅ RAG核心模块导入成功")
        
        from src.analyzer.rag_analyzer import RAGAnalyzer
        print("✅ RAG分析器导入成功")
        
        from src.matcher.smart_matching import SmartMatchingEngine
        print("✅ 智能匹配引擎导入成功")
        
        from src.matcher.recommendation import JobRecommendationEngine
        print("✅ 职位推荐引擎导入成功")
        
        from src.database.vector_ops import VectorDatabaseOperations
        print("✅ 向量数据库操作模块导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ RAG模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"⚠️ RAG模块错误: {e}")
        return False

def test_basic_functionality():
    """测试基础功能"""
    print("\n⚙️ 测试基础功能...")
    
    try:
        # 测试ChromaDB初始化
        import chromadb
        client = chromadb.Client()
        print("✅ ChromaDB客户端初始化成功")
        
        # 测试Pydantic模型
        from src.rag.job_processor import JobStructure
        
        # 创建测试数据
        test_job = JobStructure(
            job_title="AI工程师",
            company="测试公司",
            responsibilities=["开发AI模型", "数据分析"],
            requirements=["Python经验", "机器学习背景"],
            skills=["Python", "TensorFlow", "PyTorch"],
            education="本科及以上",
            experience="3年以上"
        )
        print("✅ JobStructure模型创建成功")
        print(f"   职位: {test_job.job_title}")
        print(f"   公司: {test_job.company}")
        print(f"   技能: {', '.join(test_job.skills)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 RAG系统基础测试开始")
    print("=" * 50)
    
    # 运行测试
    tests = [
        ("基础导入测试", test_basic_imports),
        ("RAG模块测试", test_rag_modules),
        ("基础功能测试", test_basic_functionality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"💥 {test_name} 异常: {e}")
    
    # 输出结果
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！RAG系统基础功能正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查相关配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)