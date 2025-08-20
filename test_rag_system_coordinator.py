#!/usr/bin/env python3
"""
测试RAGSystemCoordinator功能
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.rag.rag_system_coordinator import RAGSystemCoordinator

def test_rag_system_coordinator():
    """测试RAG系统协调器"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 测试RAGSystemCoordinator功能")
    print("=" * 50)
    
    async def run_tests():
        try:
            # 配置RAG系统
            config = {
                'rag_system': {
                    'database': {
                        'path': './data/jobs.db',
                        'batch_size': 10
                    },
                    'llm': {
                        'provider': 'zhipu',
                        'model': 'glm-4-flash',
                        'api_key': 'test-key',  # 测试用
                        'temperature': 0.1,
                        'max_tokens': 1500
                    },
                    'vector_db': {
                        'persist_directory': './test_chroma_db',
                        'collection_name': 'test_job_positions',
                        'embeddings': {
                            'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                            'device': 'cpu',
                            'normalize_embeddings': True
                        }
                    },
                    'documents': {
                        'types': ['overview', 'responsibility', 'requirement', 'skills', 'basic_requirements'],
                        'create_comprehensive_doc': False
                    },
                    'processing': {
                        'skip_processed': True,
                        'force_reprocess': False,
                        'batch_size': 5
                    }
                }
            }
            
            # 初始化协调器
            coordinator = RAGSystemCoordinator(config)
            print("✅ RAGSystemCoordinator初始化成功")
            
            # 测试1: 系统初始化
            print("\n🚀 测试1: 系统初始化")
            init_success = coordinator.initialize_system()
            print(f"   初始化结果: {'✅ 成功' if init_success else '❌ 失败'}")
            
            # 测试2: 获取系统状态
            print("\n📊 测试2: 系统状态检查")
            system_status = coordinator.get_system_status()
            print(f"   系统初始化状态: {system_status.get('is_initialized', False)}")
            print(f"   组件状态:")
            components = system_status.get('components', {})
            for comp_name, comp_status in components.items():
                status_icon = "✅" if comp_status else "❌"
                print(f"      {comp_name}: {status_icon}")
            
            # 测试3: 获取处理进度
            print("\n📈 测试3: 处理进度检查")
            progress = coordinator.get_processing_progress()
            db_stats = progress.get('database_stats', {})
            print(f"   数据库统计:")
            print(f"      总职位数: {db_stats.get('total', 0)}")
            print(f"      已处理: {db_stats.get('processed', 0)}")
            print(f"      未处理: {db_stats.get('unprocessed', 0)}")
            print(f"      处理进度: {progress.get('progress_percentage', 0):.1f}%")
            
            vector_stats = progress.get('vector_stats', {})
            print(f"   向量数据库统计:")
            print(f"      文档数量: {vector_stats.get('document_count', 0)}")
            print(f"      集合名称: {vector_stats.get('collection_name', 'N/A')}")
            
            # 测试4: 模拟单个职位处理（不实际调用LLM）
            print("\n🔄 测试4: 单个职位处理测试（模拟模式）")
            
            # 获取一个测试职位
            test_jobs = coordinator.db_reader.get_jobs_for_rag_processing(limit=1)
            if test_jobs:
                test_job = test_jobs[0]
                print(f"   测试职位: {test_job.get('title', '无标题')} - {test_job.get('company', '无公司')}")
                print(f"   职位ID: {test_job.get('job_id', 'N/A')}")
                print(f"   描述长度: {len(test_job.get('description', '') or '')}")
                
                # 模拟处理（不实际调用LLM）
                print("   ⚠️ 跳过实际LLM处理（避免API调用）")
                
                # 验证数据完整性
                has_required_data = all([
                    test_job.get('job_id'),
                    test_job.get('title'),
                    test_job.get('company')
                ])
                print(f"   数据完整性: {'✅ 完整' if has_required_data else '❌ 不完整'}")
                
            else:
                print("   ⚠️ 没有可测试的职位数据")
            
            # 测试5: 配置验证
            print("\n⚙️ 测试5: 配置验证")
            config_info = system_status.get('config', {})
            print(f"   批处理大小: {config_info.get('batch_size', 'N/A')}")
            print(f"   向量数据库路径: {config_info.get('vector_db_path', 'N/A')}")
            print(f"   LLM提供商: {config_info.get('llm_provider', 'N/A')}")
            
            # 测试6: 处理统计
            print("\n📊 测试6: 处理统计")
            processing_stats = system_status.get('processing_stats', {})
            print(f"   总处理数: {processing_stats.get('total_processed', 0)}")
            print(f"   总错误数: {processing_stats.get('total_errors', 0)}")
            print(f"   处理速率: {processing_stats.get('processing_rate', 0):.2f} 职位/秒")
            print(f"   最后处理时间: {processing_stats.get('last_processing_time', 'N/A')}")
            
            print("\n🎉 所有测试完成!")
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 清理资源
            try:
                coordinator.cleanup_system()
                print("✅ 系统资源清理完成")
            except:
                pass
    
    # 运行异步测试
    return asyncio.run(run_tests())

if __name__ == "__main__":
    success = test_rag_system_coordinator()
    sys.exit(0 if success else 1)