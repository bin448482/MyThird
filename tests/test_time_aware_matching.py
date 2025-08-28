#!/usr/bin/env python3
"""
时间感知匹配功能测试脚本
验证新数据不被老数据掩盖的解决方案
"""

import asyncio
import logging
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open('config/integration_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info("✅ 配置文件加载成功")
        return config
    except Exception as e:
        logger.error(f"❌ 配置文件加载失败: {e}")
        return {}

def test_time_aware_config(config: Dict[str, Any]):
    """测试时间感知配置"""
    logger.info("🔧 测试时间感知配置...")
    
    # 检查向量数据库时间感知配置
    vector_config = config.get('rag_system', {}).get('vector_db', {}).get('time_aware_search', {})
    if vector_config.get('enable_time_boost'):
        logger.info(f"✅ 向量数据库时间感知已启用")
        logger.info(f"   - 新数据加分: {vector_config.get('fresh_data_boost', 0.2)}")
        logger.info(f"   - 新数据天数: {vector_config.get('fresh_data_days', 7)}")
        logger.info(f"   - 时间衰减因子: {vector_config.get('time_decay_factor', 0.1)}")
    else:
        logger.warning("⚠️ 向量数据库时间感知未启用")
    
    # 检查简历匹配时间感知配置
    matching_config = config.get('resume_matching_advanced', {}).get('time_aware_matching', {})
    if matching_config.get('enable_time_aware'):
        logger.info(f"✅ 简历匹配时间感知已启用")
        logger.info(f"   - 搜索策略: {matching_config.get('search_strategy', 'hybrid')}")
        logger.info(f"   - 新数据优先: {matching_config.get('fresh_data_priority', {}).get('enable', False)}")
    else:
        logger.warning("⚠️ 简历匹配时间感知未启用")

async def test_vector_manager():
    """测试向量管理器的时间感知功能"""
    logger.info("🧪 测试向量管理器时间感知功能...")
    
    try:
        from src.rag.vector_manager import ChromaDBManager
        
        # 加载配置
        config = load_config()
        vector_config = config.get('rag_system', {}).get('vector_db', {})
        
        # 初始化向量管理器
        vector_manager = ChromaDBManager(vector_config)
        
        # 检查时间感知功能是否可用
        if hasattr(vector_manager, 'time_aware_similarity_search'):
            logger.info("✅ 时间感知搜索方法已实现")
            
            # 测试基础搜索功能
            try:
                results = vector_manager.time_aware_similarity_search(
                    query="Python开发工程师",
                    k=5,
                    strategy='hybrid'
                )
                logger.info(f"✅ 时间感知搜索测试成功，返回 {len(results)} 个结果")
                
                # 分析时间分布
                if results:
                    current_time = datetime.now()
                    fresh_count = 0
                    old_count = 0
                    
                    for doc, score in results:
                        created_at_str = doc.metadata.get('created_at')
                        if created_at_str:
                            try:
                                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                time_diff = (current_time - created_at).total_seconds() / (24 * 3600)
                                if time_diff <= 7:
                                    fresh_count += 1
                                else:
                                    old_count += 1
                            except:
                                old_count += 1
                        else:
                            old_count += 1
                    
                    logger.info(f"📊 时间分布: 新数据 {fresh_count} 个, 老数据 {old_count} 个")
                
            except Exception as e:
                logger.error(f"❌ 时间感知搜索测试失败: {e}")
        else:
            logger.error("❌ 时间感知搜索方法未实现")
            
        # 测试时间权重计算
        if hasattr(vector_manager, '_calculate_time_weight'):
            logger.info("✅ 时间权重计算方法已实现")
        else:
            logger.error("❌ 时间权重计算方法未实现")
            
        # 关闭连接
        vector_manager.close()
        
    except ImportError as e:
        logger.error(f"❌ 导入向量管理器失败: {e}")
    except Exception as e:
        logger.error(f"❌ 向量管理器测试失败: {e}")

async def test_resume_matcher():
    """测试简历匹配器的时间感知功能"""
    logger.info("🧪 测试简历匹配器时间感知功能...")
    
    try:
        from src.matcher.generic_resume_matcher import GenericResumeJobMatcher
        from src.rag.vector_manager import ChromaDBManager
        
        # 加载配置
        config = load_config()
        
        # 初始化组件
        vector_manager = ChromaDBManager(config.get('rag_system', {}).get('vector_db', {}))
        matcher = GenericResumeJobMatcher(vector_manager, config)
        
        # 检查时间感知配置是否正确加载
        time_aware_config = config.get('resume_matching_advanced', {}).get('time_aware_matching', {})
        if time_aware_config.get('enable_time_aware'):
            logger.info("✅ 简历匹配器时间感知配置已加载")
        else:
            logger.warning("⚠️ 简历匹配器时间感知配置未启用")
        
        # 测试语义搜索是否使用时间感知
        try:
            search_results = await matcher._execute_semantic_search(
                query="Python开发工程师 机器学习",
                k=10
            )
            logger.info(f"✅ 时间感知语义搜索测试成功，返回 {len(search_results)} 个结果")
        except Exception as e:
            logger.error(f"❌ 时间感知语义搜索测试失败: {e}")
        
        # 关闭连接
        vector_manager.close()
        
    except ImportError as e:
        logger.error(f"❌ 导入简历匹配器失败: {e}")
    except Exception as e:
        logger.error(f"❌ 简历匹配器测试失败: {e}")

def test_time_weight_calculation():
    """测试时间权重计算逻辑"""
    logger.info("🧪 测试时间权重计算逻辑...")
    
    try:
        from src.rag.vector_manager import ChromaDBManager
        from langchain.schema import Document
        
        # 创建测试文档
        current_time = datetime.now()
        
        # 新数据 (3天前)
        fresh_doc = Document(
            page_content="Python开发工程师职位",
            metadata={
                'created_at': (current_time - timedelta(days=3)).isoformat(),
                'job_id': 'fresh_job_001'
            }
        )
        
        # 老数据 (60天前)
        old_doc = Document(
            page_content="Python开发工程师职位",
            metadata={
                'created_at': (current_time - timedelta(days=60)).isoformat(),
                'job_id': 'old_job_001'
            }
        )
        
        # 无时间戳数据
        no_time_doc = Document(
            page_content="Python开发工程师职位",
            metadata={'job_id': 'no_time_job_001'}
        )
        
        # 初始化向量管理器
        config = load_config()
        vector_config = config.get('rag_system', {}).get('vector_db', {})
        vector_manager = ChromaDBManager(vector_config)
        
        # 测试时间权重计算
        if hasattr(vector_manager, '_calculate_time_weight'):
            fresh_weight = vector_manager._calculate_time_weight(fresh_doc, current_time)
            old_weight = vector_manager._calculate_time_weight(old_doc, current_time)
            no_time_weight = vector_manager._calculate_time_weight(no_time_doc, current_time)
            
            logger.info(f"📊 时间权重计算结果:")
            logger.info(f"   - 新数据 (3天前): {fresh_weight:.3f}")
            logger.info(f"   - 老数据 (60天前): {old_weight:.3f}")
            logger.info(f"   - 无时间戳: {no_time_weight:.3f}")
            
            # 验证权重合理性
            if fresh_weight > old_weight:
                logger.info("✅ 新数据权重高于老数据，计算逻辑正确")
            else:
                logger.error("❌ 新数据权重不高于老数据，计算逻辑有误")
                
            if 0.0 <= fresh_weight <= 1.0 and 0.0 <= old_weight <= 1.0:
                logger.info("✅ 权重值在合理范围内 [0.0, 1.0]")
            else:
                logger.error("❌ 权重值超出合理范围")
        else:
            logger.error("❌ 时间权重计算方法未实现")
        
        # 关闭连接
        vector_manager.close()
        
    except Exception as e:
        logger.error(f"❌ 时间权重计算测试失败: {e}")

async def run_comprehensive_test():
    """运行综合测试"""
    logger.info("🚀 开始时间感知匹配功能综合测试")
    logger.info("=" * 60)
    
    # 加载配置
    config = load_config()
    
    # 1. 测试配置
    test_time_aware_config(config)
    logger.info("-" * 40)
    
    # 2. 测试向量管理器
    await test_vector_manager()
    logger.info("-" * 40)
    
    # 3. 测试简历匹配器
    await test_resume_matcher()
    logger.info("-" * 40)
    
    # 4. 测试时间权重计算
    test_time_weight_calculation()
    logger.info("-" * 40)
    
    logger.info("🎉 时间感知匹配功能测试完成")
    logger.info("=" * 60)

def print_solution_summary():
    """打印解决方案总结"""
    logger.info("📋 时间感知匹配解决方案总结:")
    logger.info("=" * 60)
    logger.info("🎯 问题: 向量数据库中新数据被老数据的高相似度掩盖")
    logger.info("")
    logger.info("💡 解决方案:")
    logger.info("1. 时间权重计算: 根据文档创建时间计算时间权重")
    logger.info("2. 混合评分策略: 结合相似度分数和时间权重")
    logger.info("3. 新数据加分机制: 为新数据提供额外加分")
    logger.info("4. 多种搜索策略: hybrid/fresh_first/balanced")
    logger.info("5. 配置化管理: 通过配置文件灵活调整参数")
    logger.info("")
    logger.info("🔧 核心特性:")
    logger.info("- 时间感知向量搜索 (ChromaDBManager.time_aware_similarity_search)")
    logger.info("- 智能时间权重计算 (基于文档创建时间)")
    logger.info("- 新数据优先级提升 (fresh_data_boost)")
    logger.info("- 老数据时间衰减 (time_decay_factor)")
    logger.info("- 灵活的搜索策略选择")
    logger.info("")
    logger.info("📊 预期效果:")
    logger.info("- 新职位数据获得更高的匹配优先级")
    logger.info("- 保持语义相似度的准确性")
    logger.info("- 平衡新旧数据的展示机会")
    logger.info("- 提高用户匹配体验")
    logger.info("=" * 60)

if __name__ == "__main__":
    # 打印解决方案总结
    print_solution_summary()
    
    # 运行测试
    asyncio.run(run_comprehensive_test())