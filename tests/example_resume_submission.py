#!/usr/bin/env python3
"""
简历投递功能使用示例

展示如何使用完整的投递系统
"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.integration.master_controller import MasterController, PipelineConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_basic_submission():
    """示例1: 基本投递功能"""
    
    print("=" * 60)
    print("📋 示例1: 基本投递功能")
    print("=" * 60)
    
    # 1. 配置
    config = {
        'database_path': 'data/jobs.db',
        'browser': {
            'headless': False,  # 显示浏览器窗口，便于观察
            'window_size': (1920, 1080),
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'submission_engine': {
            'batch_size': 5,                    # 每批处理5个职位
            'daily_limit': 20,                  # 每日限制20个
            'auto_login_enabled': True,         # 启用自动登录
            'manual_login_timeout': 300,        # 手动登录超时5分钟
            'delays': {
                'min_delay': 3.0,               # 最小延迟3秒
                'max_delay': 8.0,               # 最大延迟8秒
                'batch_delay': 30.0,            # 批次间延迟30秒
                'reading_delay': 15.0           # 页面阅读延迟15秒
            }
        }
    }
    
    try:
        # 2. 初始化主控制器
        controller = MasterController(config)
        
        # 3. 创建投递配置
        pipeline_config = PipelineConfig(
            search_keywords=['Python开发工程师'],
            submission_config={
                'batch_size': 3,  # 示例只处理3个职位
                'test_mode': True
            }
        )
        
        # 4. 执行投递
        print("🚀 开始执行投递...")
        result = controller.run_stage_only('resume_submission', pipeline_config)
        
        # 5. 显示结果
        print("\n📊 投递结果:")
        print(f"- 执行状态: {'✅ 成功' if result.get('success') else '❌ 失败'}")
        print(f"- 总处理数: {result.get('total_processed', 0)}")
        print(f"- 成功投递: {result.get('successful_submissions', 0)}")
        print(f"- 失败投递: {result.get('failed_submissions', 0)}")
        print(f"- 跳过投递: {result.get('skipped_submissions', 0)}")
        print(f"- 执行时间: {result.get('processing_time', 0):.2f}秒")
        
        if result.get('error_message'):
            print(f"- 错误信息: {result['error_message']}")
        
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"基本投递示例失败: {e}")
        print(f"❌ 示例执行失败: {e}")
        return False


async def example_full_pipeline():
    """示例2: 完整流水线（包含投递）"""
    
    print("\n" + "=" * 60)
    print("📋 示例2: 完整流水线执行")
    print("=" * 60)
    
    # 配置
    config = {
        'database_path': 'data/jobs.db',
        'browser': {
            'headless': False,
            'window_size': (1920, 1080)
        },
        'submission_engine': {
            'batch_size': 5,
            'daily_limit': 30
        }
    }
    
    try:
        # 初始化控制器
        controller = MasterController(config)
        
        # 创建完整配置
        pipeline_config = PipelineConfig(
            search_keywords=['Python开发工程师', 'Java开发工程师'],
            max_jobs_per_keyword=10,  # 每个关键词最多10个职位
            max_pages=1,              # 只搜索1页
            resume_profile={
                'name': '张三',
                'experience_years': 3,
                'current_position': 'Python开发工程师',
                'skills': ['Python', 'Django', 'MySQL', 'Redis'],
                'education': '本科'
            },
            submission_config={
                'batch_size': 3,
                'auto_login_enabled': True
            }
        )
        
        print("🚀 开始执行完整流水线...")
        
        # 执行完整流水线
        report = await controller.run_full_pipeline(pipeline_config)
        
        # 显示详细结果
        print("\n📊 流水线执行报告:")
        print(f"- 流水线ID: {report.pipeline_id}")
        print(f"- 执行状态: {'✅ 成功' if report.success else '❌ 失败'}")
        print(f"- 总执行时间: {report.total_execution_time:.2f}秒")
        
        print("\n📈 各阶段结果:")
        print(f"1. 职位提取: {report.extraction_result.get('total_extracted', 0)} 个职位")
        print(f"2. RAG处理: {report.rag_result.get('processed_count', 0)} 个职位")
        print(f"3. 简历匹配: {report.matching_result.get('total_matches', 0)} 个匹配")
        print(f"4. 投递执行: 成功 {report.submission_result.get('successful_submissions', 0)}, "
              f"失败 {report.submission_result.get('failed_submissions', 0)}")
        
        if report.error_message:
            print(f"\n❌ 错误信息: {report.error_message}")
        
        return report.success
        
    except Exception as e:
        logger.error(f"完整流水线示例失败: {e}")
        print(f"❌ 流水线执行失败: {e}")
        return False


def example_submission_monitoring():
    """示例3: 投递监控和统计"""
    
    print("\n" + "=" * 60)
    print("📋 示例3: 投递监控和统计")
    print("=" * 60)
    
    try:
        from src.submission.submission_engine import ResumeSubmissionEngine
        from src.submission.data_manager import SubmissionDataManager
        
        # 基础配置
        config = {
            'database_path': 'data/jobs.db',
            'submission_engine': {
                'batch_size': 10,
                'daily_limit': 50
            }
        }
        
        # 1. 数据管理器统计
        print("📊 数据库统计:")
        data_manager = SubmissionDataManager(config['database_path'])
        
        # 获取基础统计
        stats = data_manager.get_submission_statistics()
        print(f"- 总匹配记录: {stats.get('total_matches', 0)}")
        print(f"- 待投递: {stats.get('pending_submissions', 0)}")
        print(f"- 已投递: {stats.get('completed_submissions', 0)}")
        print(f"- 成功率: {stats.get('success_rate', 0):.1%}")
        
        # 获取未处理记录
        unprocessed = data_manager.get_unprocessed_matches(limit=5)
        print(f"- 未处理记录: {len(unprocessed)} 条")
        
        if unprocessed:
            print("  前3条待投递职位:")
            for i, record in enumerate(unprocessed[:3]):
                print(f"    {i+1}. {record.job_title} @ {record.company} (匹配度: {record.match_score:.2f})")
        
        # 2. 失败记录分析
        print("\n🔍 失败记录分析:")
        failed_records = data_manager.get_failed_submissions(limit=5)
        print(f"- 失败记录数: {len(failed_records)}")
        
        if failed_records:
            print("  最近失败记录:")
            for record in failed_records[:3]:
                print(f"    - {record.get('job_title', 'N/A')}: {record.get('error_message', 'N/A')}")
        
        # 3. 投递引擎统计（如果已初始化）
        print("\n⚙️ 引擎状态:")
        try:
            engine = ResumeSubmissionEngine(config)
            engine_stats = engine.get_submission_statistics()
            print(f"- 引擎状态: {engine_stats.get('engine_status', {})}")
        except Exception as e:
            print(f"- 引擎未初始化: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"监控示例失败: {e}")
        print(f"❌ 监控示例失败: {e}")
        return False


def main():
    """主函数"""
    
    print("🎯 简历投递功能使用示例")
    print("=" * 80)
    
    # 运行示例
    examples = [
        ("投递监控和统计", example_submission_monitoring),
        ("基本投递功能", example_basic_submission),
        # ("完整流水线执行", lambda: asyncio.run(example_full_pipeline())),
    ]
    
    results = []
    
    for name, example_func in examples:
        print(f"\n🧪 运行示例: {name}")
        try:
            if asyncio.iscoroutinefunction(example_func):
                result = asyncio.run(example_func())
            else:
                result = example_func()
            results.append((name, result))
            
            if result:
                print(f"✅ {name} 执行成功")
            else:
                print(f"❌ {name} 执行失败")
                
        except Exception as e:
            logger.error(f"示例 {name} 异常: {e}")
            print(f"💥 {name} 执行异常: {e}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 示例执行汇总")
    print("=" * 80)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n📈 总体结果: {success_count}/{total_count} 示例成功")
    
    if success_count == total_count:
        print("🎉 所有示例执行成功！投递功能运行正常！")
    else:
        print("⚠️ 部分示例失败，请检查配置和环境")
    
    return success_count == total_count


if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 80)
    print("💡 使用提示:")
    print("1. 确保数据库文件存在: data/jobs.db")
    print("2. 确保Chrome浏览器已安装")
    print("3. 检查网络连接")
    print("4. 根据需要调整配置参数")
    print("5. 查看日志文件了解详细信息")
    print("=" * 80)
    
    sys.exit(0 if success else 1)