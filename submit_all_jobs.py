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
        
        # 4. 检查薪资过滤配置
        print("\n💰 检查薪资过滤配置...")
        salary_filter_config = config.get('integration_system', {}).get('decision_engine', {}).get('salary_filters', {})
        salary_filter_enabled = salary_filter_config.get('enabled', False)
        salary_threshold = salary_filter_config.get('min_salary_match_score', 0.3)
        
        print(f"  薪资过滤状态: {'✅ 启用' if salary_filter_enabled else '❌ 禁用'}")
        if salary_filter_enabled:
            print(f"  薪资匹配阈值: {salary_threshold} ({salary_threshold*100:.0f}%)")
            print(f"  严格模式: {'✅ 是' if salary_filter_config.get('strict_mode', True) else '❌ 否'}")
        
        # 5. 获取待投递职位总数（不应用薪资过滤）
        print("\n📊 检查待投递职位...")
        all_pending_jobs_raw = engine.data_manager.get_unprocessed_matches(limit=10000, apply_salary_filter=False)
        total_jobs_raw = len(all_pending_jobs_raw)
        
        # 获取薪资过滤后的职位
        all_pending_jobs_filtered = engine.data_manager.get_unprocessed_matches(limit=10000, apply_salary_filter=True)
        total_jobs_filtered = len(all_pending_jobs_filtered)
        
        print(f"📋 原始待投递职位总数: {total_jobs_raw}")
        if salary_filter_enabled:
            filtered_count = total_jobs_raw - total_jobs_filtered
            filter_rate = (filtered_count / total_jobs_raw * 100) if total_jobs_raw > 0 else 0
            print(f"💰 薪资过滤拒绝职位: {filtered_count} 个 ({filter_rate:.1f}%)")
            print(f"📋 薪资过滤后职位: {total_jobs_filtered}")
        
        # 使用过滤后的职位数量
        all_pending_jobs = all_pending_jobs_filtered
        total_jobs = total_jobs_filtered
        
        if total_jobs == 0:
            if salary_filter_enabled and total_jobs_raw > 0:
                print("⚠️ 所有职位都被薪资过滤拒绝了")
                print("💡 建议: 降低薪资匹配阈值或检查薪资匹配度计算")
            else:
                print("✅ 没有待投递的职位")
            return
        
        # 6. 显示薪资过滤统计
        if salary_filter_enabled and engine.data_manager.salary_filter:
            print("\n💰 薪资过滤统计:")
            filter_stats = engine.data_manager.salary_filter.get_stats()
            print(f"  总评估数: {filter_stats['total_evaluated']}")
            print(f"  拒绝数: {filter_stats['salary_rejected']}")
            print(f"  拒绝率: {filter_stats['rejection_rate']:.2%}")
            print(f"  增强数: {filter_stats['salary_enhanced']}")
            
            # 显示薪资分布
            distribution = filter_stats['salary_distribution']
            print(f"  薪资分布:")
            print(f"    优秀 (≥0.8): {distribution['excellent']} 个")
            print(f"    良好 (0.6-0.8): {distribution['good']} 个")
            print(f"    可接受 (0.3-0.6): {distribution['acceptable']} 个")
            print(f"    较差 (<0.3): {distribution['poor']} 个")
        
        # 7. 显示前几个职位信息
        print("\n📋 前5个待投递职位:")
        for i, job in enumerate(all_pending_jobs[:5], 1):
            print(f"  {i}. {job.job_title} @ {job.company} (匹配度: {job.match_score:.2f})")
        
        if total_jobs > 5:
            print(f"  ... 还有 {total_jobs - 5} 个职位")
        
        # 8. 确认执行
        print(f"\n⚠️ 即将投递 {total_jobs} 个职位")
        if salary_filter_enabled:
            print(f"💰 薪资过滤已启用，阈值: {salary_threshold}")
            print(f"💰 已过滤掉 {total_jobs_raw - total_jobs} 个低薪职位")
        
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
        
        # 9. 显示薪资过滤最终统计
        if salary_filter_enabled and engine.data_manager.salary_filter:
            print(f"\n💰 薪资过滤最终统计:")
            final_filter_stats = engine.data_manager.salary_filter.get_stats()
            print(f"  📊 过滤效果:")
            print(f"    原始职位数: {total_jobs_raw}")
            print(f"    过滤拒绝数: {final_filter_stats['salary_rejected']}")
            print(f"    实际投递数: {total_jobs}")
            print(f"    过滤率: {final_filter_stats['rejection_rate']:.2%}")
            
            print(f"  📈 薪资质量分布:")
            distribution = final_filter_stats['salary_distribution']
            total_evaluated = final_filter_stats['total_evaluated']
            if total_evaluated > 0:
                print(f"    优秀薪资 (≥80%): {distribution['excellent']} ({distribution['excellent']/total_evaluated*100:.1f}%)")
                print(f"    良好薪资 (60-80%): {distribution['good']} ({distribution['good']/total_evaluated*100:.1f}%)")
                print(f"    可接受薪资 (30-60%): {distribution['acceptable']} ({distribution['acceptable']/total_evaluated*100:.1f}%)")
                print(f"    较差薪资 (<30%): {distribution['poor']} ({distribution['poor']/total_evaluated*100:.1f}%)")
            
            if final_filter_stats['salary_enhanced'] > 0:
                print(f"  ⭐ 薪资增强处理: {final_filter_stats['salary_enhanced']} 个职位")
            
            # 计算薪资过滤的价值
            if final_filter_stats['salary_rejected'] > 0:
                avg_time = total_time / total_successful if total_successful > 0 else 30
                time_saved = final_filter_stats['salary_rejected'] * avg_time
                print(f"  ⏰ 预估节省时间: {time_saved:.1f}秒 ({time_saved/60:.1f}分钟)")
                print(f"  💡 薪资过滤避免了 {final_filter_stats['salary_rejected']} 次低价值投递")
        
        # 10. 检查失败记录
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
        
        # 11. 薪资过滤建议
        if salary_filter_enabled and engine.data_manager.salary_filter:
            final_stats = engine.data_manager.salary_filter.get_stats()
            rejection_rate = final_stats['rejection_rate']
            
            print(f"\n💡 薪资过滤建议:")
            if rejection_rate > 0.7:
                print("  ⚠️ 过滤率过高 (>70%)，建议降低薪资阈值")
                print(f"  💡 当前阈值: {salary_threshold} → 建议: {max(0.1, salary_threshold - 0.1)}")
            elif rejection_rate < 0.1:
                print("  📈 过滤率较低 (<10%)，可以考虑提高薪资阈值")
                print(f"  💡 当前阈值: {salary_threshold} → 建议: {min(0.8, salary_threshold + 0.1)}")
            else:
                print("  ✅ 薪资过滤率适中，配置合理")
            
            if final_stats['salary_enhanced'] > 0:
                enhancement_rate = final_stats['salary_enhanced'] / total_jobs * 100
                print(f"  ⭐ {enhancement_rate:.1f}% 的职位获得薪资增强，优先级得到提升")
        
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
    print("快速投递所有剩余职位 (增强版 + 薪资过滤)")
    print("="*60)
    print("🆕 新功能: 智能状态检测")
    print("  • 自动识别暂停招聘职位并删除")
    print("  • 自动识别已申请职位并标记")
    print("  • 高效页面检测，避免重复DOM查找")
    print("  • 详细日志记录到 logs/ 目录")
    print("💰 薪资过滤功能:")
    print("  • 自动过滤薪资匹配度低于阈值的职位")
    print("  • 支持灵活的阈值配置 (默认0.3)")
    print("  • 提供详细的过滤统计和建议")
    print("  • 节省时间，避免低价值投递")
    print("="*60)
    print("⚠️ 注意: 这将投递数据库中所有未处理的职位")
    print("⚠️ 薪资过滤功能会自动排除低薪职位")
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