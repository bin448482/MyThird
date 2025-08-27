"""
快速投递所有剩余职位脚本
基于 test_submission_engine.py 的逻辑，简化版本用于快速投递所有数据库中的剩余职位

新增功能:
- 智能职位状态检测：自动识别暂停招聘、已申请等状态
- 高效DOM查找：一次性获取页面信息，避免重复查找
- 自动数据清理：删除暂停职位，标记已申请职位
- 详细日志记录：记录所有状态检测结果到logs目录

使用方法:
python submit_all_jobs.py
"""

import asyncio
import logging
import yaml
import time
from pathlib import Path
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.submission.submission_engine import ResumeSubmissionEngine


async def submit_all_remaining_jobs():
    """投递所有剩余职位"""
    
    print("🚀 开始投递所有剩余职位")
    print("="*60)
    
    # 1. 加载配置
    config = {}
    
    # 尝试加载配置文件
    config_files = [
        "config/submission_config.yaml",
        "config/integration_config.yaml"
    ]
    
    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config.update(file_config)
                        print(f"✅ 加载配置: {config_file}")
            except Exception as e:
                print(f"⚠️ 加载配置失败 {config_file}: {e}")
    
    # 设置默认配置
    config.setdefault('database_path', 'data/jobs.db')
    
    print(f"📁 数据库路径: {config['database_path']}")
    
    # 2. 创建投递引擎
    engine = ResumeSubmissionEngine(config)
    
    try:
        # 3. 初始化引擎
        print("\n🔧 初始化投递引擎...")
        init_success = await engine.initialize()
        
        if not init_success:
            print("❌ 引擎初始化失败")
            return
        
        print("✅ 引擎初始化成功")
        
        # 4. 获取待投递职位总数
        print("\n📊 检查待投递职位...")
        all_pending_jobs = engine.data_manager.get_unprocessed_matches(limit=10000)
        total_jobs = len(all_pending_jobs)
        
        print(f"📋 待投递职位总数: {total_jobs}")
        
        if total_jobs == 0:
            print("✅ 没有待投递的职位")
            return
        
        # 5. 显示前几个职位信息
        print("\n📋 前5个待投递职位:")
        for i, job in enumerate(all_pending_jobs[:5], 1):
            print(f"  {i}. {job.job_title} @ {job.company} (匹配度: {job.match_score:.2f})")
        
        if total_jobs > 5:
            print(f"  ... 还有 {total_jobs - 5} 个职位")
        
        # 6. 确认执行
        print(f"\n⚠️ 即将投递 {total_jobs} 个职位")
        user_input = input("确认继续执行批量投递？(y/N): ").strip().lower()
        
        if user_input != 'y':
            print("❌ 用户取消执行")
            return
        
        # 7. 开始批量投递
        print(f"\n🎯 开始批量投递 {total_jobs} 个职位...")
        print("="*60)
        
        start_time = time.time()
        total_successful = 0
        total_failed = 0
        total_skipped = 0
        batch_size = 20  # 每批处理20个
        
        # 分批处理
        for batch_start in range(0, total_jobs, batch_size):
            batch_end = min(batch_start + batch_size, total_jobs)
            current_batch_size = batch_end - batch_start
            batch_number = (batch_start // batch_size) + 1
            
            print(f"\n🔄 执行第 {batch_number} 批次 ({batch_start + 1}-{batch_end}/{total_jobs})")
            print("-" * 40)
            
            # 执行当前批次
            report = await engine.run_submission_batch(current_batch_size)
            
            # 更新统计
            total_successful += report.successful_count
            total_failed += report.failed_count
            total_skipped += report.skipped_count
            
            # 显示批次结果（包含新的状态类型）
            print(f"  ✅ 成功: {report.successful_count}")
            print(f"  ❌ 失败: {report.failed_count}")
            print(f"  ⏭️ 跳过: {report.skipped_count}")
            print(f"  🔄 已申请: {report.already_applied_count}")
            
            # 显示新增的状态统计
            if hasattr(report, 'job_suspended_count') and report.job_suspended_count > 0:
                print(f"  🗑️ 暂停删除: {report.job_suspended_count}")
            if hasattr(report, 'job_expired_count') and report.job_expired_count > 0:
                print(f"  ⏰ 职位过期: {report.job_expired_count}")
            if hasattr(report, 'page_error_count') and report.page_error_count > 0:
                print(f"  🚫 页面错误: {report.page_error_count}")
            
            print(f"  📈 成功率: {report.success_rate:.2%}")
            print(f"  ⏱️ 耗时: {report.total_execution_time:.2f}秒")
            
            # 显示当前总体进度
            processed_so_far = batch_end
            overall_progress = (processed_so_far / total_jobs) * 100
            print(f"  📊 总体进度: {processed_so_far}/{total_jobs} ({overall_progress:.1f}%)")
            
            # 批次间延迟（除了最后一批）
            if batch_end < total_jobs:
                delay_time = 30  # 30秒延迟
                print(f"  ⏳ 批次间延迟 {delay_time} 秒...")
                await asyncio.sleep(delay_time)
        
        # 8. 显示最终结果
        total_time = time.time() - start_time
        
        print("\n" + "="*60)
        print("🎉 批量投递完成!")
        print("="*60)
        print(f"📊 最终统计:")
        print(f"  📋 总职位数: {total_jobs}")
        print(f"  ✅ 成功投递: {total_successful}")
        print(f"  ❌ 投递失败: {total_failed}")
        print(f"  ⏭️ 跳过职位: {total_skipped}")
        
        if total_jobs > 0:
            success_rate = (total_successful / total_jobs) * 100
            print(f"  📈 总成功率: {success_rate:.2f}%")
        
        print(f"  ⏱️ 总耗时: {total_time:.2f}秒")
        
        if total_successful > 0:
            avg_time = total_time / total_successful
            print(f"  ⚡ 平均每个成功投递耗时: {avg_time:.2f}秒")
        
        # 9. 检查失败记录
        print(f"\n🔍 检查失败记录...")
        failed_records = engine.get_failed_submissions(limit=10)
        if failed_records:
            print(f"📋 最近失败记录 (前10个):")
            for i, record in enumerate(failed_records[:10], 1):
                print(f"  {i}. {record.get('title', 'N/A')} @ {record.get('company', 'N/A')}")
                print(f"     状态: {record.get('submission_status', 'N/A')}")
                print(f"     原因: {record.get('message', 'N/A')}")
        else:
            print("✅ 没有失败记录")
        
        print(f"\n✅ 所有剩余职位投递完成!")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        print("\n🧹 清理资源...")
        await engine.cleanup()
        print("✅ 资源清理完成")


def main():
    """主函数"""
    print("快速投递所有剩余职位 (增强版)")
    print("="*60)
    print("🆕 新功能: 智能状态检测")
    print("  • 自动识别暂停招聘职位并删除")
    print("  • 自动识别已申请职位并标记")
    print("  • 高效页面检测，避免重复DOM查找")
    print("  • 详细日志记录到 logs/ 目录")
    print("="*60)
    print("⚠️ 注意: 这将投递数据库中所有未处理的职位")
    print("⚠️ 请确保您已经准备好进行大量投递操作")
    print("="*60)
    
    try:
        asyncio.run(submit_all_remaining_jobs())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")


if __name__ == "__main__":
    main()