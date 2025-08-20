#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM工厂模式测试脚本

展示如何使用统一的LLM工厂来切换不同的语言模型
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.rag.llm_factory import (
    LLMFactory, 
    create_llm, 
    create_llm_from_config,
    LLM_CONFIGS
)
from src.rag.vector_manager import ChromaDBManager
from src.rag.job_processor import LangChainJobProcessor
from src.rag.document_creator import DocumentCreator
from src.rag.rag_chain import JobRAGSystem

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API密钥配置
API_KEYS = {
    "zhipu": "0175134f27a040709d7541e14b4db353.V3KP9u8rZ0oQj9s9",
    "openai": "your_openai_api_key",  # 替换为你的OpenAI API密钥
    "claude": "your_claude_api_key",  # 替换为你的Claude API密钥
}

class LLMFactoryTest:
    """LLM工厂模式测试类"""
    
    def __init__(self):
        self.test_prompt = "请简要介绍一下人工智能的发展历史，不超过100字。"
    
    def test_basic_llm_creation(self):
        """测试基础LLM创建"""
        print("🔧 测试基础LLM创建")
        print("-" * 50)
        
        # 测试支持的提供商
        providers = LLMFactory.get_supported_providers()
        print(f"支持的LLM提供商: {providers}")
        
        # 测试智谱GLM
        if API_KEYS["zhipu"]:
            try:
                zhipu_llm = create_llm(
                    provider="zhipu",
                    api_key=API_KEYS["zhipu"],
                    model="glm-4-flash",
                    temperature=0.1
                )
                print(f"✅ 智谱GLM创建成功: {zhipu_llm._llm_type}")
                
                # 测试调用
                response = zhipu_llm(self.test_prompt)
                print(f"📝 智谱GLM回复: {response[:100]}...")
                
            except Exception as e:
                print(f"❌ 智谱GLM测试失败: {e}")
        
        # 测试Ollama（如果本地运行）
        try:
            ollama_llm = create_llm(
                provider="ollama",
                model="llama2",
                base_url="http://localhost:11434",
                temperature=0.1
            )
            print(f"✅ Ollama创建成功: {ollama_llm._llm_type}")
            
            # 测试调用（可能会失败如果Ollama未运行）
            try:
                response = ollama_llm(self.test_prompt)
                print(f"📝 Ollama回复: {response[:100]}...")
            except Exception as e:
                print(f"⚠️ Ollama调用失败（可能未运行）: {e}")
                
        except Exception as e:
            print(f"❌ Ollama创建失败: {e}")
        
        print()
    
    def test_config_based_creation(self):
        """测试基于配置的LLM创建"""
        print("⚙️ 测试基于配置的LLM创建")
        print("-" * 50)
        
        # 显示可用配置
        print(f"可用配置: {list(LLM_CONFIGS.keys())}")
        
        # 测试智谱GLM配置
        try:
            zhipu_llm = create_llm_from_config(
                "zhipu_default",
                api_key=API_KEYS["zhipu"]
            )
            print(f"✅ 从配置创建智谱GLM成功: {zhipu_llm._identifying_params}")
            
        except Exception as e:
            print(f"❌ 配置创建失败: {e}")
        
        # 测试Ollama配置
        try:
            ollama_llm = create_llm_from_config("ollama_llama2")
            print(f"✅ 从配置创建Ollama成功: {ollama_llm._identifying_params}")
            
        except Exception as e:
            print(f"❌ Ollama配置创建失败: {e}")
        
        print()
    
    async def test_rag_with_different_llms(self):
        """测试RAG系统使用不同的LLM"""
        print("🤖 测试RAG系统使用不同LLM")
        print("-" * 50)
        
        # 加载测试数据
        json_file = "fixed_job_detail_result.json"
        if not os.path.exists(json_file):
            print(f"❌ 找不到测试数据文件: {json_file}")
            return
        
        with open(json_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # 测试不同LLM配置
        llm_configs = [
            {
                "name": "智谱GLM",
                "config": {
                    "provider": "zhipu",
                    "api_key": API_KEYS["zhipu"],
                    "model": "glm-4-flash",
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            },
            {
                "name": "Ollama Llama2",
                "config": {
                    "provider": "ollama",
                    "model": "llama2",
                    "base_url": "http://localhost:11434",
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            }
        ]
        
        for llm_config in llm_configs:
            print(f"\n🔍 测试 {llm_config['name']}")
            print("-" * 30)
            
            try:
                # 创建RAG系统配置
                rag_config = {
                    'vectorstore': {
                        'persist_directory': f'./test_chroma_db_{llm_config["name"].lower().replace(" ", "_")}',
                        'collection_name': 'test_job_positions'
                    },
                    'llm': llm_config['config']
                }
                
                # 初始化组件
                vector_manager = ChromaDBManager(rag_config['vectorstore'])
                job_processor = LangChainJobProcessor(
                    llm_config=llm_config['config']
                )
                document_creator = DocumentCreator()
                rag_system = JobRAGSystem(
                    vectorstore_manager=vector_manager,
                    config=rag_config
                )
                
                # 处理职位数据
                job_structure = await job_processor.process_job_data(job_data)
                print(f"  ✅ 职位结构化提取完成: {job_structure.job_title}")
                
                # 创建文档并存储
                documents = document_creator.create_job_documents(job_structure)
                doc_ids = vector_manager.add_job_documents(documents)
                print(f"  ✅ 保存了 {len(doc_ids)} 个文档到向量数据库")
                
                # 测试问答
                question = "这个职位需要什么技能？"
                answer_result = await rag_system.ask_question(question)
                print(f"  💬 问题: {question}")
                print(f"  💡 回答: {answer_result['answer'][:150]}...")
                
                # 清理
                vector_manager.close()
                
            except Exception as e:
                print(f"  ❌ {llm_config['name']} 测试失败: {e}")
        
        print()
    
    def test_custom_adapter_registration(self):
        """测试自定义适配器注册"""
        print("🔌 测试自定义适配器注册")
        print("-" * 50)
        
        # 创建一个简单的自定义适配器
        from src.rag.llm_factory import BaseLLMAdapter
        from typing import Optional, List, Any
        from langchain.callbacks.manager import CallbackManagerForLLMRun
        
        class MockLLMAdapter(BaseLLMAdapter):
            """模拟LLM适配器"""
            
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
            
            @property
            def _llm_type(self) -> str:
                return "mock_llm"
            
            def _call(
                self,
                prompt: str,
                stop: Optional[List[str]] = None,
                run_manager: Optional[CallbackManagerForLLMRun] = None,
                **kwargs: Any,
            ) -> str:
                return f"这是模拟回复：{prompt[:50]}..."
            
            @property
            def _identifying_params(self):
                return {"type": "mock"}
        
        # 注册自定义适配器
        try:
            LLMFactory.register_adapter("mock", MockLLMAdapter)
            print("✅ 自定义适配器注册成功")
            
            # 测试使用自定义适配器
            mock_llm = create_llm(provider="mock")
            response = mock_llm("测试提示")
            print(f"📝 自定义适配器回复: {response}")
            
            # 检查提供商列表
            providers = LLMFactory.get_supported_providers()
            print(f"更新后的提供商列表: {providers}")
            
        except Exception as e:
            print(f"❌ 自定义适配器测试失败: {e}")
        
        print()

async def main():
    """主测试函数"""
    print("🚀 LLM工厂模式测试")
    print("=" * 60)
    
    test = LLMFactoryTest()
    
    # 1. 测试基础LLM创建
    test.test_basic_llm_creation()
    
    # 2. 测试基于配置的创建
    test.test_config_based_creation()
    
    # 3. 测试RAG系统使用不同LLM
    await test.test_rag_with_different_llms()
    
    # 4. 测试自定义适配器注册
    test.test_custom_adapter_registration()
    
    print("=" * 60)
    print("🎉 LLM工厂模式测试完成！")
    print("\n💡 使用说明:")
    print("1. 通过配置文件轻松切换不同的LLM提供商")
    print("2. 支持智谱GLM、Ollama、OpenAI、Claude等多种模型")
    print("3. 可以注册自定义的LLM适配器")
    print("4. 统一的接口，便于维护和扩展")
    
    print("\n🔧 配置示例:")
    print("""
# 使用智谱GLM
config = {
    'llm': {
        'provider': 'zhipu',
        'api_key': 'your_api_key',
        'model': 'glm-4-flash'
    }
}

# 使用Ollama
config = {
    'llm': {
        'provider': 'ollama',
        'model': 'llama2',
        'base_url': 'http://localhost:11434'
    }
}

# 使用OpenAI
config = {
    'llm': {
        'provider': 'openai',
        'api_key': 'your_api_key',
        'model': 'gpt-3.5-turbo'
    }
}
""")

if __name__ == "__main__":
    asyncio.run(main())