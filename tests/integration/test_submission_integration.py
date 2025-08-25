#!/usr/bin/env python3
"""
投递功能集成测试脚本

测试完整的投递流水线集成
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.integration.master_controller import MasterController, PipelineConfig
from src.integration.submission_integration import SubmissionIntegration
from src.submission.submission_engine import ResumeSubmissionEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_submission_integration.log')
    ]
)

logger = logging.getLogger(__name__)


def test_submission_integration():
    """测试投递功能集成"""
    
    print("=" * 80)
    print("🧪 投递功能集成测试")
    print("=" * 80)
    
    # 1. 配置
    config = {
        'database_path': 'data/jobs.db',
        'browser': {
            'headless': False,
            'window_size': (1920, 1080),
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'submission_engine': {
            'batch_size': 5,
            'daily_limit': 50,
            'auto_login_enabled': True,
            'manual_login_timeout': 300,
            'delays': {
                'min_delay': 3.0,
                'max_delay': 8.0,
                'batch_delay': 30.0
            }
        },
        'anti_crawler': {
            'enable_delays': True,
            'enable_risk_detection': True,
            'max_daily_submissions': 50
        }
    }
    
    try:
        # 2. 测试投递集成模块
        print("\n📋 测试 1: 投递集成模块初始化")
        submission_integration = SubmissionIntegration(config)
        print("✅ 投递集成模块初始化成功")
        
        # 3. 测试投递引擎
        print("\n📋 测试 2: 投递引擎初始化")
        submission_engine = ResumeSubmissionEngine(config)
        
        # 同步初始化测试
        init_success = submission_engine.initialize_sync()
        if init_success:
            print("✅ 投递引擎同步初始化成功")
        else:
            print("❌ 投递引擎同步初始化失败")
            return False
        
        # 4. 测试统计功能
        print("\n📋 测试 3: 获取投递统计")
        stats = submission_engine.get_submission_statistics()
        print(f"📊 统计信息: {stats}")
        
        # 5. 测试主控制器集成
        print("\n📋 测试 4: 主控制器集成")
        master_controller = MasterController(config)
        
        # 创建测试配置
        pipeline_config = PipelineConfig(
            search_keywords=['Python开发工程师'],
            submission_config={
                'batch_size': 3,
                'test_mode': True
            }
        )
        
        # 测试单独运行投递阶段
        print("🎯 测试单独运行投递阶段...")
        submission_result = master_controller.run_stage_only('resume_submission', pipeline_config)
        
        print(f"📊 投递结果: {submission_result}")
        
        if submission_result.get('success'):
            print("✅ 投递阶段测试成功")
        else:
            print(f"❌ 投递阶段测试失败: {submission_result.get('error')}")
        
        # 6. 清理资源
        print("\n🧹 清理测试资源...")
        asyncio.run(submission_engine.cleanup())
        print("✅ 资源清理完成")
        
        print("\n" + "=" * 80)
        print("🎉 投递功能集成测试完成")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"集成测试失败: {e}")
        print(f"❌ 集成测试失败: {e}")
        return False


def test_submission_data_flow():
    """测试投递数据流"""
    
    print("\n" + "=" * 60)
    print("📊 投递数据流测试")
    print("=" * 60)
    
    try:
        from src.submission.data_manager import SubmissionDataManager
        
        # 初始化数据管理器
        data_manager = SubmissionDataManager('data/jobs.db')
        
        # 1. 测试获取未处理的匹配记录
        print("\n📋 测试 1: 获取未处理的匹配记录")
        unprocessed = data_manager.get_unprocessed_matches(limit=5)
        print(f"📊 未处理记录数: {len(unprocessed)}")
        
        if unprocessed:
            print("📝 前3条记录:")
            for i, record in enumerate(unprocessed[:3]):
                print(f"  {i+1}. {record.job_title} @ {record.company}")
        
        # 2. 测试获取投递统计
        print("\n📋 测试 2: 获取投递统计")
        stats = data_manager.get_submission_statistics()
        print(f"📊 投递统计: {stats}")
        
        # 3. 测试获取失败记录
        print("\n📋 测试 3: 获取失败记录")
        failed = data_manager.get_failed_submissions(limit=5)
        print(f"📊 失败记录数: {len(failed)}")
        
        print("✅ 数据流测试完成")
        return True
        
    except Exception as e:
        logger.error(f"数据流测试失败: {e}")
        print(f"❌ 数据流测试失败: {e}")
        return False


def test_button_recognition():
    """测试按钮识别功能"""
    
    print("\n" + "=" * 60)
    print("🔍 按钮识别测试")
    print("=" * 60)
    
    try:
        from src.submission.button_recognition import ButtonRecognitionEngine
        from src.auth.browser_manager import BrowserManager
        
        # 初始化浏览器
        config = {
            'browser': {
                'headless': True,
                'window_size': (1920, 1080)
            }
        }
        
        browser_manager = BrowserManager(config)
        driver = browser_manager.create_driver()
        
        if not driver:
            print("❌ 浏览器初始化失败")
            return False
        
        # 初始化按钮识别引擎
        button_engine = ButtonRecognitionEngine(driver, config)
        
        # 测试按钮选择器
        print("\n📋 测试按钮选择器配置")
        selectors = button_engine.get_site_selectors("51job.com")
        print(f"📊 51job选择器: {len(selectors)} 个")
        
        selectors = button_engine.get_site_selectors("zhaopin.com")
        print(f"📊 智联选择器: {len(selectors)} 个")
        
        # 清理
        browser_manager.quit_driver()
        print("✅ 按钮识别测试完成")
        return True
        
    except Exception as e:
        logger.error(f"按钮识别测试失败: {e}")
        print(f"❌ 按钮识别测试失败: {e}")
        return False


def main():
    """主测试函数"""
    
    print("🚀 开始投递功能完整集成测试")
    print("=" * 80)
    
    test_results = []
    
    # 运行各项测试
    tests = [
        ("投递数据流测试", test_submission_data_flow),
        ("按钮识别测试", test_button_recognition),
        ("投递功能集成测试", test_submission_integration),
    ]
    
    for test_name, test_func in tests:
        print(f"\n🧪 开始 {test_name}...")
        try:
            result = test_func()
            test_results.append((test_name, result))
            if result:
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            logger.error(f"{test_name} 异常: {e}")
            print(f"💥 {test_name} 异常: {e}")
            test_results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！投递功能集成成功！")
        return True
    else:
        print("⚠️ 部分测试失败，请检查日志")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)