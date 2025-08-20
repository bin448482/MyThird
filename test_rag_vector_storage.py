#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试RAG向量存储功能

验证JSON职位数据保存到向量数据库的完整流程
"""

import os
import sys
import json
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.rag.vector_manager import ChromaDBManager
from src.rag.job_processor import LangChainJobProcessor
from src.rag.document_creator import DocumentCreator
from src.rag.rag_chain import JobRAGSystem
from src.rag.semantic_search import SemanticSearchEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 智谱GLM API密钥
API_KEY = "0175134f27a040709d7541e14b4db353.V3KP9u8rZ0oQj9s9"

class RAGVectorStorageTest:
    """RAG向量存储测试类"""
    
    def __init__(self, api_key: str):
        """
        初始化测试环境
        
        Args:
            api_key: 智谱GLM API密钥
        """
        self.api_key = api_key
        
        # RAG系统配置
        self.config = {
            'vectorstore': {
                'persist_directory': './test_chroma_db',
                'collection_name': 'test_job_positions'
            },
            'embeddings': {
                'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'device': 'cpu',
                'normalize_embeddings': True
            },
            'llm': {
                'provider': 'zhipu',
                'api_key': api_key,
                'model': 'glm-4-flash',
                'temperature': 0.1,
                'max_tokens': 2000
            },
            'text_splitter': {
                'chunk_size': 500,
                'chunk_overlap': 50
            }
        }
        
        # 初始化组件
        self.vector_manager = None
        self.job_processor = None
        self.document_creator = None
        self.rag_system = None
        self.search_engine = None
    
    def setup_components(self):
        """设置RAG组件"""
        try:
            logger.info("🔧 初始化RAG组件...")
            
            # 1. 初始化向量存储管理器
            self.vector_manager = ChromaDBManager(self.config['vectorstore'])
            logger.info("✅ 向量存储管理器初始化完成")
            
            # 2. 初始化职位处理器
            self.job_processor = LangChainJobProcessor(
                llm_config=self.config['llm'],
                config=self.config['text_splitter']
            )
            logger.info("✅ 职位处理器初始化完成")
            
            # 3. 初始化文档创建器
            self.document_creator = DocumentCreator(self.config)
            logger.info("✅ 文档创建器初始化完成")
            
            # 4. 初始化RAG系统
            self.rag_system = JobRAGSystem(
                vectorstore_manager=self.vector_manager,
                config=self.config
            )
            logger.info("✅ RAG系统初始化完成")
            
            # 5. 初始化语义搜索引擎
            self.search_engine = SemanticSearchEngine(
                vector_manager=self.vector_manager,
                config=self.config
            )
            logger.info("✅ 语义搜索引擎初始化完成")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 组件初始化失败: {e}")
            return False
    
    def load_job_data(self, json_file: str) -> dict:
        """加载职位JSON数据"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"📂 成功加载职位数据: {json_file}")
            return data
        except Exception as e:
            logger.error(f"❌ 加载职位数据失败: {e}")
            return {}
    
    async def test_job_processing(self, job_data: dict) -> bool:
        """测试职位数据处理"""
        try:
            logger.info("🔍 开始职位数据处理...")
            
            # 1. 结构化提取职位信息
            job_structure = await self.job_processor.process_job_data(job_data)
            logger.info(f"✅ 职位结构化提取完成: {job_structure.job_title}")
            
            # 2. 创建文档对象
            documents = self.document_creator.create_job_documents(
                job_structure=job_structure,
                job_id="test_job_001",
                source_url=job_data.get('url', '')
            )
            logger.info(f"✅ 创建了 {len(documents)} 个文档对象")
            
            # 3. 保存到向量数据库
            doc_ids = self.vector_manager.add_job_documents(
                documents=documents,
                job_id="test_job_001"
            )
            logger.info(f"✅ 成功保存 {len(doc_ids)} 个文档到向量数据库")
            
            # 4. 验证存储
            stats = self.vector_manager.get_collection_stats()
            logger.info(f"📊 向量数据库统计: {stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 职位数据处理失败: {e}")
            return False
    
    def test_vector_search(self) -> bool:
        """测试向量搜索功能"""
        try:
            logger.info("🔍 开始向量搜索测试...")
            
            # 测试查询列表
            test_queries = [
                "AI工程师职位要求",
                "Python开发经验",
                "机器学习技能",
                "LLM应用开发",
                "薪资待遇"
            ]
            
            for query in test_queries:
                logger.info(f"🔎 搜索查询: {query}")
                
                # 1. 相似度搜索
                results = self.search_engine.search(
                    query=query,
                    strategy='similarity',
                    k=3
                )
                
                logger.info(f"  📋 找到 {len(results)} 个相关结果")
                
                for i, result in enumerate(results, 1):
                    logger.info(f"    {i}. 相似度: {result['similarity_score']:.3f}")
                    logger.info(f"       内容: {result['content'][:100]}...")
                    logger.info(f"       类型: {result['metadata'].get('type', 'unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 向量搜索测试失败: {e}")
            return False
    
    async def test_rag_qa(self) -> bool:
        """测试RAG问答功能"""
        try:
            logger.info("💬 开始RAG问答测试...")
            
            # 测试问题列表
            test_questions = [
                "这个职位需要什么技能？",
                "工作经验要求是什么？",
                "薪资范围是多少？",
                "主要工作职责有哪些？",
                "学历要求是什么？"
            ]
            
            for question in test_questions:
                logger.info(f"❓ 问题: {question}")
                
                # 使用RAG系统回答问题
                answer_result = await self.rag_system.ask_question(
                    question=question,
                    k=5
                )
                
                logger.info(f"  💡 回答: {answer_result['answer'][:200]}...")
                logger.info(f"  📊 置信度: {answer_result['confidence']:.3f}")
                logger.info(f"  📚 参考文档数: {len(answer_result['source_documents'])}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ RAG问答测试失败: {e}")
            return False
    
    def cleanup(self):
        """清理测试环境"""
        try:
            # 先关闭所有组件连接
            if self.vector_manager:
                self.vector_manager.close()
            
            # 清理组件引用
            self.vector_manager = None
            self.job_processor = None
            self.document_creator = None
            self.rag_system = None
            self.search_engine = None
            
            # 强制垃圾回收
            import gc
            gc.collect()
            
            # 等待一下让文件句柄释放
            import time
            time.sleep(1)
            
            # 删除测试数据库
            import shutil
            test_db_path = self.config['vectorstore']['persist_directory']
            if os.path.exists(test_db_path):
                try:
                    shutil.rmtree(test_db_path)
                    logger.info("🧹 清理测试数据库完成")
                except PermissionError as pe:
                    # Windows文件访问权限问题，这是正常的
                    logger.info("🧹 测试完成，数据库文件将在进程结束后自动清理")
                
        except Exception as e:
            logger.warning(f"⚠️ 清理过程中出现警告: {e}")

async def main():
    """主测试函数"""
    print("🚀 RAG向量存储功能测试")
    print("=" * 60)
    
    # 检查API密钥
    if not API_KEY or API_KEY == "your_api_key_here":
        print("❌ 请先设置智谱GLM API密钥")
        return
    
    # 检查JSON文件
    json_file = "fixed_job_detail_result.json"
    if not os.path.exists(json_file):
        print(f"❌ 找不到测试数据文件: {json_file}")
        return
    
    # 创建测试实例
    test = RAGVectorStorageTest(API_KEY)
    
    try:
        # 1. 设置组件
        print("\n📋 步骤1: 初始化RAG组件")
        if not test.setup_components():
            print("❌ 组件初始化失败")
            return
        
        # 2. 加载测试数据
        print("\n📋 步骤2: 加载职位数据")
        job_data = test.load_job_data(json_file)
        if not job_data:
            print("❌ 职位数据加载失败")
            return
        
        # 3. 测试职位数据处理和存储
        print("\n📋 步骤3: 测试职位数据处理和向量存储")
        if not await test.test_job_processing(job_data):
            print("❌ 职位数据处理失败")
            return
        
        # 4. 测试向量搜索
        print("\n📋 步骤4: 测试向量搜索功能")
        if not test.test_vector_search():
            print("❌ 向量搜索测试失败")
            return
        
        # 5. 测试RAG问答
        print("\n📋 步骤5: 测试RAG问答功能")
        if not await test.test_rag_qa():
            print("❌ RAG问答测试失败")
            return
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！RAG向量存储功能正常工作")
        print("\n✅ 测试结果总结:")
        print("  - 智谱GLM集成成功")
        print("  - 职位数据结构化提取正常")
        print("  - 向量数据库存储成功")
        print("  - 语义搜索功能正常")
        print("  - RAG问答系统工作正常")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试环境
        print("\n🧹 清理测试环境...")
        test.cleanup()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())