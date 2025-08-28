"""
职位状态检测功能测试脚本
用于测试新实现的职位状态检测功能
"""

import asyncio
import logging
import yaml
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.submission.submission_engine import ResumeSubmissionEngine
from src.submission.models import SubmissionStatus


async def test_job_status_detection():
    """测试职位状态检测功能"""
    
    print("🧪 测试职位状态检测功能")
    print("="*60)
    
    # 1. 加载配置
    config = {}
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
    
    config.setdefault('database_path', 'data/jobs.db')
    
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
        
        # 4. 测试状态检测器
        print("\n🔍 测试职位状态检测器...")
        
        if not engine.status_detector:
            print("❌ 状态检测器未初始化")
            return
        
        print("✅ 状态检测器已初始化")
        
        # 5. 获取几个测试职位
        print("\n📋 获取测试职位...")
        test_jobs = engine.data_manager.get_unprocessed_matches(limit=3)
        
        if not test_jobs:
            print("⚠️ 没有可测试的职位")
            return
        
        print(f"📋 找到 {len(test_jobs)} 个测试职位")
        
        # 6. 测试每个职位的状态检测
        print("\n🧪 开始测试状态检测...")
        
        for i, job in enumerate(test_jobs, 1):
            print(f"\n--- 测试职位 {i}: {job.job_title} @ {job.company} ---")
            
            try:
                # 导航到职位页面
                print(f"🌐 导航到职位页面: {job.job_url}")
                navigation_success = engine.anti_crawler.safe_navigate_to_job(job.job_url)
                
                if not navigation_success:
                    print("❌ 页面导航失败")
                    continue
                
                # 模拟页面阅读
                engine.anti_crawler.simulate_job_page_reading(min_time=1.0, max_time=2.0)
                
                # 执行状态检测
                print("🔍 执行状态检测...")
                status_result = engine.status_detector.detect_job_status()
                
                # 显示检测结果
                print(f"📊 检测结果:")
                print(f"  状态: {status_result.status.value}")
                print(f"  原因: {status_result.reason}")
                print(f"  检测耗时: {status_result.detection_time:.3f}秒")
                
                if status_result.page_title:
                    print(f"  页面标题: {status_result.page_title}")
                
                if status_result.button_text:
                    print(f"  按钮文本: {status_result.button_text}")
                
                if status_result.button_class:
                    print(f"  按钮样式: {status_result.button_class}")
                
                if status_result.page_content_snippet:
                    print(f"  页面内容: {status_result.page_content_snippet}")
                
                # 测试状态处理逻辑
                print(f"🔧 状态处理建议:")
                if engine.status_detector.should_delete_job(status_result):
                    print("  建议: 删除暂停职位记录")
                elif engine.status_detector.should_mark_as_applied(status_result):
                    print("  建议: 标记为已申请")
                elif engine.status_detector.is_job_available_for_submission(status_result):
                    print("  建议: 可以继续投递")
                else:
                    print("  建议: 标记为已处理")
                
                # 记录检测结果
                engine.data_manager.log_job_status_detection(job, status_result, "测试检测")
                
                print("✅ 检测完成")
                
            except Exception as e:
                print(f"❌ 检测失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 7. 测试数据管理器方法
        print(f"\n🗃️ 测试数据管理器方法...")
        
        # 测试统计功能
        stats = engine.data_manager.get_submission_statistics()
        print(f"📊 投递统计: {stats.get('overall', {})}")
        
        # 测试失败记录获取
        failed_records = engine.data_manager.get_failed_submissions(limit=3)
        print(f"📋 失败记录数量: {len(failed_records)}")
        
        print(f"\n✅ 职位状态检测功能测试完成!")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        print("\n🧹 清理资源...")
        await engine.cleanup()
        print("✅ 资源清理完成")


def main():
    """主函数"""
    print("职位状态检测功能测试")
    print("="*60)
    print("🧪 这个脚本将测试新实现的职位状态检测功能")
    print("="*60)
    
    try:
        asyncio.run(test_job_status_detection())
    except KeyboardInterrupt:
        print("\n👋 测试已退出")
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")


if __name__ == "__main__":
    main()