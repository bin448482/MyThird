"""
投递引擎测试脚本

用于测试投递简历功能的基本流程
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


async def test_submission_engine():
    """测试投递引擎"""
    
    # 加载配置
    config_path = Path("config/submission_config.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            submission_config = yaml.safe_load(f)
    else:
        submission_config = {}
    
    # 加载主配置
    main_config_path = Path("config/integration_config.yaml")
    if main_config_path.exists():
        with open(main_config_path, 'r', encoding='utf-8') as f:
            main_config = yaml.safe_load(f)
    else:
        main_config = {}
    
    # 合并配置
    config = {**main_config, **submission_config}
    config['database_path'] = 'data/jobs.db'
    
    print("🚀 开始测试投递引擎")
    print("="*60)
    
    # 创建投递引擎
    engine = ResumeSubmissionEngine(config)
    
    try:
        # 1. 测试初始化
        print("1. 测试引擎初始化...")
        init_success = await engine.initialize()
        
        if not init_success:
            print("❌ 引擎初始化失败")
            return
        
        print("✅ 引擎初始化成功")
        
        # 2. 获取统计信息
        print("\n2. 获取当前统计信息...")
        stats = engine.get_submission_statistics()
        print(f"数据库统计: {stats.get('database_stats', {})}")
        
        # 3. 获取待投递职位数量
        print("\n3. 检查待投递职位...")
        pending_jobs = engine.data_manager.get_unprocessed_matches(limit=5)
        print(f"待投递职位数量: {len(pending_jobs)}")
        
        if pending_jobs:
            print("前5个待投递职位:")
            for i, job in enumerate(pending_jobs[:5], 1):
                print(f"  {i}. {job.job_title} @ {job.company} (匹配度: {job.match_score:.2f})")
        
        # 4. 测试批量投递（小批次）
        if pending_jobs:
            print(f"\n4. 测试批量投递（最多3个职位）...")
            
            # 询问用户是否继续
            user_input = input("是否继续执行实际投递测试？(y/N): ").strip().lower()
            
            if user_input == 'y':
                print("开始执行投递测试...")
                report = await engine.run_submission_batch(batch_size=3)
                
                print("\n投递报告:")
                print(f"  总处理数: {report.total_processed}")
                print(f"  成功数: {report.successful_count}")
                print(f"  失败数: {report.failed_count}")
                print(f"  跳过数: {report.skipped_count}")
                print(f"  成功率: {report.success_rate:.2%}")
                print(f"  总耗时: {report.total_execution_time:.2f}秒")
                
                if report.results:
                    print("\n详细结果:")
                    for result in report.results:
                        status_emoji = "✅" if result.status.value == "success" else "❌"
                        print(f"  {status_emoji} {result.job_title} - {result.status.value}: {result.message}")
            else:
                print("跳过实际投递测试")
        else:
            print("没有待投递的职位，跳过投递测试")
        
        # 5. 获取失败记录
        print("\n5. 检查失败记录...")
        failed_records = engine.get_failed_submissions(limit=5)
        if failed_records:
            print(f"最近失败记录数量: {len(failed_records)}")
            for record in failed_records[:3]:
                print(f"  - {record.get('title', 'N/A')} @ {record.get('company', 'N/A')}: {record.get('submission_status', 'N/A')}")
        else:
            print("没有失败记录")
        
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        print("\n🧹 清理资源...")
        await engine.cleanup()
        print("✅ 资源清理完成")


def test_data_manager():
    """测试数据管理器"""
    print("\n" + "="*60)
    print("🔍 测试数据管理器")
    print("="*60)
    
    from src.submission.data_manager import SubmissionDataManager
    
    # 创建数据管理器
    data_manager = SubmissionDataManager('data/jobs.db')
    
    try:
        # 1. 获取未处理匹配记录
        print("1. 获取未处理匹配记录...")
        unprocessed = data_manager.get_unprocessed_matches(limit=10)
        print(f"未处理记录数量: {len(unprocessed)}")
        
        # 2. 获取统计信息
        print("\n2. 获取统计信息...")
        stats = data_manager.get_submission_statistics()
        print(f"统计信息: {stats}")
        
        # 3. 获取每日投递数量
        print("\n3. 获取每日投递数量...")
        daily_count = data_manager.get_daily_submission_count()
        print(f"今日投递数量: {daily_count}")
        
        print("✅ 数据管理器测试完成")
        
    except Exception as e:
        print(f"❌ 数据管理器测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_button_recognition():
    """测试按钮识别（不需要浏览器）"""
    print("\n" + "="*60)
    print("🔍 测试按钮识别配置")
    print("="*60)
    
    from src.submission.button_recognition import ButtonRecognitionEngine
    
    # 模拟配置
    config = {
        'button_recognition': {
            'timeout': 10,
            'retry_attempts': 3,
            'selectors': {
                'qiancheng': [
                    "a.but_sq#app_ck",
                    "a[onclick*='delivery']"
                ]
            }
        }
    }
    
    try:
        # 测试网站类型检测
        print("1. 测试网站类型检测...")
        
        # 创建一个模拟的按钮识别引擎（不需要真实的driver）
        class MockDriver:
            def __init__(self):
                self.current_url = "https://jobs.51job.com/test"
        
        mock_driver = MockDriver()
        engine = ButtonRecognitionEngine(mock_driver, config)
        
        # 测试网站检测
        website_type = engine.detect_website("https://jobs.51job.com/test")
        print(f"检测到网站类型: {website_type}")
        
        website_type = engine.detect_website("https://www.zhaopin.com/test")
        print(f"检测到网站类型: {website_type}")
        
        # 测试选择器加载
        print("\n2. 测试选择器配置...")
        selectors = engine.button_selectors
        for site, site_selectors in selectors.items():
            print(f"{site}: {len(site_selectors)} 个选择器")
        
        print("✅ 按钮识别配置测试完成")
        
    except Exception as e:
        print(f"❌ 按钮识别测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("投递引擎测试脚本")
    print("="*60)
    
    # 选择测试类型
    print("请选择测试类型:")
    print("1. 完整投递引擎测试（需要浏览器）")
    print("2. 数据管理器测试")
    print("3. 按钮识别配置测试")
    print("4. 全部测试")
    
    choice = input("请输入选择 (1-4): ").strip()
    
    if choice == "1":
        asyncio.run(test_submission_engine())
    elif choice == "2":
        test_data_manager()
    elif choice == "3":
        test_button_recognition()
    elif choice == "4":
        test_data_manager()
        test_button_recognition()
        print("\n是否继续完整引擎测试？")
        if input("(y/N): ").strip().lower() == 'y':
            asyncio.run(test_submission_engine())
    else:
        print("无效选择")