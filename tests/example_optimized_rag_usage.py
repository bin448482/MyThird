#!/usr/bin/env python3
"""
RAG系统性能优化和错误处理使用示例

展示如何使用增强的RAG系统，包括性能优化和错误处理功能
"""

import asyncio
import logging
import yaml
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.rag.rag_system_coordinator import RAGSystemCoordinator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/rag_example.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def load_optimized_config():
    """加载优化配置"""
    config_path = Path('./config/rag_optimization_config.yaml')
    
    if not config_path.exists():
        logger.warning(f"优化配置文件不存在: {config_path}")
        # 返回默认配置
        return {
            'rag_system': {
                'database': {
                    'path': './data/jobs.db',
                    'batch_size': 50
                },
                'llm': {
                    'provider': 'zhipu',
                    'model': 'glm-4-flash',
                    'api_key': 'test-key',
                    'temperature': 0.1,
                    'max_tokens': 1500
                },
                'vector_db': {
                    'persist_directory': './data/chroma_db',
                    'collection_name': 'job_documents',
                    'embeddings': {
                        'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                        'device': 'cpu',
                        'normalize_embeddings': True
                    }
                },
                'documents': {
                    'types': ['overview', 'responsibility', 'requirement', 'skills', 'basic_requirements']
                },
                'processing': {
                    'skip_processed': True,
                    'batch_size': 20
                },
                'performance_optimization': {
                    'cache': {
                        'max_size': 1000,
                        'ttl_seconds': 3600
                    },
                    'batch_processing': {
                        'batch_size': 10,
                        'max_workers': 4
                    },
                    'memory_management': {
                        'threshold_mb': 1000
                    },
                    'enable_caching': True,
                    'enable_batch_processing': True,
                    'enable_memory_monitoring': True
                },
                'error_handling': {
                    'retry': {
                        'max_attempts': 3,
                        'base_delay': 1.0,
                        'max_delay': 60.0,
                        'exponential_base': 2.0,
                        'jitter': True
                    },
                    'enable_error_reporting': True,
                    'error_report_file': './logs/rag_error_report.json'
                }
            }
        }
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"成功加载优化配置: {config_path}")
        return config
    except Exception as e:
        logger.error(f"加载优化配置失败: {e}")
        raise

async def demonstrate_basic_usage():
    """演示基本使用方法"""
    print("\n" + "="*60)
    print("🚀 RAG系统基本使用演示")
    print("="*60)
    
    # 加载配置
    config = load_optimized_config()
    
    # 创建RAG系统协调器
    coordinator = RAGSystemCoordinator(config)
    
    try:
        # 1. 初始化系统
        print("\n1️⃣ 初始化RAG系统...")
        success = coordinator.initialize_system()
        if success:
            print("✅ 系统初始化成功")
        else:
            print("❌ 系统初始化失败")
            return
        
        # 2. 获取系统状态
        print("\n2️⃣ 获取系统状态...")
        status = coordinator.get_system_status()
        print(f"📊 系统状态:")
        print(f"   - 已初始化: {status.get('is_initialized', False)}")
        print(f"   - 组件状态: {status.get('components', {})}")
        
        # 3. 获取处理进度
        print("\n3️⃣ 获取处理进度...")
        progress = coordinator.get_processing_progress()
        db_stats = progress.get('database_stats', {})
        print(f"📈 处理进度:")
        print(f"   - 总职位数: {db_stats.get('total', 0)}")
        print(f"   - 已处理: {db_stats.get('processed', 0)}")
        print(f"   - 进度: {progress.get('progress_percentage', 0):.1f}%")
        
        # 4. 演示批量导入（少量数据）
        print("\n4️⃣ 演示批量导入...")
        import_result = await coordinator.import_database_jobs(
            batch_size=5,
            max_jobs=10,
            force_reprocess=False
        )
        
        print(f"📥 导入结果:")
        print(f"   - 导入: {import_result.get('total_imported', 0)}")
        print(f"   - 跳过: {import_result.get('total_skipped', 0)}")
        print(f"   - 错误: {import_result.get('total_errors', 0)}")
        print(f"   - 处理时间: {import_result.get('processing_time', 0):.2f}秒")
        print(f"   - 处理速度: {import_result.get('processing_rate', 0):.2f} 职位/秒")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        logger.error(f"演示失败: {e}")
    
    finally:
        # 清理资源
        coordinator.cleanup_system()
        print("\n🧹 系统资源已清理")

async def demonstrate_performance_features():
    """演示性能优化功能"""
    print("\n" + "="*60)
    print("⚡ RAG系统性能优化功能演示")
    print("="*60)
    
    config = load_optimized_config()
    coordinator = RAGSystemCoordinator(config)
    
    try:
        coordinator.initialize_system()
        
        # 1. 获取性能指标
        print("\n1️⃣ 获取性能指标...")
        performance_metrics = coordinator.get_performance_metrics()
        
        if 'error' not in performance_metrics:
            print("📊 性能指标:")
            perf_metrics = performance_metrics.get('performance_metrics', {})
            print(f"   - 总操作数: {perf_metrics.get('total_operations', 0)}")
            print(f"   - 成功操作数: {perf_metrics.get('successful_operations', 0)}")
            print(f"   - 平均耗时: {perf_metrics.get('avg_duration', 0):.3f}秒")
            
            cache_stats = performance_metrics.get('cache_stats', {})
            print(f"   - 缓存条目数: {cache_stats.get('total_entries', 0)}")
            print(f"   - 缓存使用率: {cache_stats.get('usage_ratio', 0):.2%}")
        else:
            print(f"⚠️ 获取性能指标失败: {performance_metrics['error']}")
        
        # 2. 系统性能优化
        print("\n2️⃣ 执行系统性能优化...")
        optimization_result = coordinator.optimize_system_performance()
        
        if 'error' not in optimization_result:
            print("🔧 优化结果:")
            actions = optimization_result.get('actions_taken', [])
            for action in actions:
                action_name = action.get('action', 'unknown')
                print(f"   - {action_name}: 已执行")
        else:
            print(f"⚠️ 性能优化失败: {optimization_result['error']}")
        
        # 3. 内存使用情况
        print("\n3️⃣ 检查内存使用情况...")
        if hasattr(coordinator, 'performance_optimizer'):
            memory_info = coordinator.performance_optimizer.memory_manager.get_memory_usage()
            print("💾 内存使用:")
            print(f"   - 系统总内存: {memory_info.get('system_total_gb', 0):.2f} GB")
            print(f"   - 系统已用内存: {memory_info.get('system_used_gb', 0):.2f} GB")
            print(f"   - 系统内存使用率: {memory_info.get('system_percent', 0):.1f}%")
            print(f"   - 进程内存使用: {memory_info.get('process_memory_mb', 0):.1f} MB")
        
    except Exception as e:
        print(f"❌ 性能演示过程中发生错误: {e}")
        logger.error(f"性能演示失败: {e}")
    
    finally:
        coordinator.cleanup_system()

async def demonstrate_error_handling():
    """演示错误处理功能"""
    print("\n" + "="*60)
    print("🛡️ RAG系统错误处理功能演示")
    print("="*60)
    
    config = load_optimized_config()
    coordinator = RAGSystemCoordinator(config)
    
    try:
        coordinator.initialize_system()
        
        # 1. 获取错误报告
        print("\n1️⃣ 获取错误报告...")
        error_report = coordinator.get_error_report()
        
        if 'error' not in error_report:
            print("📋 错误报告:")
            print(f"   - 总错误数: {error_report.get('total_errors', 0)}")
            print(f"   - 已解决错误数: {error_report.get('resolved_errors', 0)}")
            print(f"   - 解决率: {error_report.get('resolution_rate', 0):.1f}%")
            
            # 显示错误分布
            severity_dist = error_report.get('severity_distribution', {})
            if severity_dist:
                print("   - 错误严重程度分布:")
                for severity, count in severity_dist.items():
                    if count > 0:
                        print(f"     * {severity}: {count}")
            
            category_dist = error_report.get('category_distribution', {})
            if category_dist:
                print("   - 错误类别分布:")
                for category, count in category_dist.items():
                    if count > 0:
                        print(f"     * {category}: {count}")
        else:
            print(f"⚠️ 获取错误报告失败: {error_report['error']}")
        
        # 2. 模拟错误处理
        print("\n2️⃣ 模拟错误处理...")
        try:
            # 故意触发一个错误来演示错误处理
            await coordinator.process_single_job({})  # 空数据应该会被正确处理
            print("✅ 错误处理正常工作")
        except Exception as e:
            print(f"⚠️ 捕获到预期错误: {type(e).__name__}")
        
        # 3. 再次获取错误报告查看变化
        print("\n3️⃣ 检查错误报告更新...")
        updated_error_report = coordinator.get_error_report()
        if 'error' not in updated_error_report:
            new_total = updated_error_report.get('total_errors', 0)
            print(f"📊 更新后总错误数: {new_total}")
        
    except Exception as e:
        print(f"❌ 错误处理演示过程中发生错误: {e}")
        logger.error(f"错误处理演示失败: {e}")
    
    finally:
        coordinator.cleanup_system()

async def demonstrate_advanced_features():
    """演示高级功能"""
    print("\n" + "="*60)
    print("🔬 RAG系统高级功能演示")
    print("="*60)
    
    config = load_optimized_config()
    coordinator = RAGSystemCoordinator(config)
    
    try:
        coordinator.initialize_system()
        
        # 1. 获取完整系统状态
        print("\n1️⃣ 获取完整系统状态...")
        full_status = coordinator.get_system_status()
        
        print("🔍 完整系统状态:")
        print(f"   - 初始化状态: {full_status.get('is_initialized', False)}")
        
        components = full_status.get('components', {})
        print("   - 组件状态:")
        for component, status in components.items():
            status_icon = "✅" if status else "❌"
            print(f"     * {component}: {status_icon}")
        
        # 2. 处理统计信息
        processing_stats = full_status.get('processing_stats', {})
        if processing_stats:
            print("   - 处理统计:")
            print(f"     * 总处理数: {processing_stats.get('total_processed', 0)}")
            print(f"     * 总错误数: {processing_stats.get('total_errors', 0)}")
            print(f"     * 处理速率: {processing_stats.get('processing_rate', 0):.2f} 职位/秒")
        
        # 3. 配置信息
        config_info = full_status.get('config', {})
        if config_info:
            print("   - 配置信息:")
            print(f"     * 批处理大小: {config_info.get('batch_size', 'N/A')}")
            print(f"     * 向量数据库路径: {config_info.get('vector_db_path', 'N/A')}")
            print(f"     * LLM提供商: {config_info.get('llm_provider', 'N/A')}")
        
        # 4. 性能报告（如果可用）
        perf_report = full_status.get('performance_report')
        if perf_report and 'error' not in perf_report:
            print("   - 性能报告: ✅ 可用")
        
        # 5. 错误摘要（如果可用）
        error_summary = full_status.get('error_summary')
        if error_summary and 'error' not in error_summary:
            print("   - 错误摘要: ✅ 可用")
        
        print("\n2️⃣ 系统健康检查...")
        
        # 检查各个组件的健康状态
        health_checks = {
            '数据库连接': coordinator.db_reader is not None,
            '职位处理器': coordinator.job_processor is not None,
            '向量管理器': coordinator.vector_manager is not None,
            '文档创建器': coordinator.document_creator is not None,
            '性能优化器': hasattr(coordinator, 'performance_optimizer') and coordinator.performance_optimizer is not None,
            '错误处理器': hasattr(coordinator, 'error_handler') and coordinator.error_handler is not None
        }
        
        print("🏥 健康检查结果:")
        all_healthy = True
        for component, is_healthy in health_checks.items():
            status_icon = "✅" if is_healthy else "❌"
            print(f"   - {component}: {status_icon}")
            if not is_healthy:
                all_healthy = False
        
        overall_health = "🟢 健康" if all_healthy else "🟡 部分问题"
        print(f"\n🎯 系统整体状态: {overall_health}")
        
    except Exception as e:
        print(f"❌ 高级功能演示过程中发生错误: {e}")
        logger.error(f"高级功能演示失败: {e}")
    
    finally:
        coordinator.cleanup_system()

async def main():
    """主函数"""
    print("🎉 RAG系统性能优化和错误处理功能演示")
    print("本演示将展示RAG系统的各种增强功能")
    
    # 确保日志目录存在
    Path('./logs').mkdir(exist_ok=True)
    
    try:
        # 1. 基本使用演示
        await demonstrate_basic_usage()
        
        # 2. 性能优化功能演示
        await demonstrate_performance_features()
        
        # 3. 错误处理功能演示
        await demonstrate_error_handling()
        
        # 4. 高级功能演示
        await demonstrate_advanced_features()
        
        print("\n" + "="*60)
        print("🎊 所有演示完成！")
        print("="*60)
        print("\n📝 演示总结:")
        print("✅ 基本功能：系统初始化、状态查询、批量导入")
        print("⚡ 性能优化：缓存管理、内存监控、批处理优化")
        print("🛡️ 错误处理：错误分类、自动重试、恢复机制")
        print("🔬 高级功能：完整状态报告、健康检查、系统监控")
        print("\n💡 提示：查看 ./logs/ 目录下的日志文件获取详细信息")
        
    except Exception as e:
        print(f"❌ 演示过程中发生严重错误: {e}")
        logger.error(f"主演示失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)