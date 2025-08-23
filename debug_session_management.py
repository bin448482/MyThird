#!/usr/bin/env python3
"""
WebDriver 会话管理调试脚本
专门测试和调试浏览器会话超时问题
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_session_timeout():
    """测试会话超时问题"""
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    # 基础配置
    config = {
        'selenium': {
            'headless': False,
            'window_size': '1920,1080',
            'page_load_timeout': 30,
            'element_wait_timeout': 10,
            'implicit_wait': 5
        },
        'mode': {
            'development': True,
            'debug': True
        }
    }
    
    print("🔍 开始会话管理调试...")
    
    try:
        from src.auth.browser_manager import BrowserManager
        
        browser_manager = BrowserManager(config)
        
        # 创建浏览器
        print("🚀 创建浏览器实例...")
        driver = browser_manager.create_driver()
        print("✅ 浏览器创建成功")
        
        # 导航到测试页面
        test_url = "https://we.51job.com/pc/search?jobArea=020000&keyword=Python%E5%BC%80%E5%8F%91&searchType=2&keywordType="
        print(f"🌐 导航到测试页面: {test_url}")
        driver.get(test_url)
        print("✅ 页面加载完成")
        
        # 模拟长时间处理 - 测试会话保持
        test_duration = 300  # 5分钟测试
        check_interval = 30   # 每30秒检查一次
        
        print(f"⏰ 开始 {test_duration} 秒的会话保持测试...")
        print(f"🔍 每 {check_interval} 秒检查一次会话状态")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < test_duration:
            check_count += 1
            elapsed = time.time() - start_time
            
            print(f"\n🔍 检查 {check_count} (已运行 {elapsed:.0f}s):")
            
            # 检查会话状态
            is_alive = browser_manager.is_driver_alive()
            print(f"  会话状态: {'✅ 活跃' if is_alive else '❌ 失效'}")
            
            if is_alive:
                try:
                    # 测试基本操作
                    current_url = driver.current_url
                    page_title = driver.title
                    print(f"  当前URL: {current_url[:50]}...")
                    print(f"  页面标题: {page_title[:30]}...")
                    
                    # 测试页面交互
                    job_elements = driver.find_elements("css selector", ".joblist-item")
                    print(f"  找到职位元素: {len(job_elements)} 个")
                    
                    # 模拟滚动
                    driver.execute_script("window.scrollTo(0, 500);")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, 0);")
                    
                    print("  ✅ 页面交互正常")
                    
                except Exception as e:
                    print(f"  ❌ 页面交互失败: {e}")
                    print("  🔄 尝试刷新会话...")
                    
                    try:
                        driver = browser_manager.restart_driver()
                        driver.get(test_url)
                        print("  ✅ 会话刷新成功")
                    except Exception as refresh_error:
                        print(f"  ❌ 会话刷新失败: {refresh_error}")
                        break
            else:
                print("  🔄 会话失效，尝试重启...")
                try:
                    driver = browser_manager.restart_driver()
                    driver.get(test_url)
                    print("  ✅ 会话重启成功")
                except Exception as restart_error:
                    print(f"  ❌ 会话重启失败: {restart_error}")
                    break
            
            # 等待下次检查
            print(f"  ⏳ 等待 {check_interval} 秒...")
            time.sleep(check_interval)
        
        total_time = time.time() - start_time
        print(f"\n🎉 会话测试完成!")
        print(f"📊 总运行时间: {total_time:.0f} 秒")
        print(f"📊 检查次数: {check_count}")
        print(f"📊 平均检查间隔: {total_time/check_count:.1f} 秒")
        
        # 清理
        browser_manager.quit_driver()
        print("🧹 浏览器已关闭")
        
    except Exception as e:
        print(f"❌ 会话测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_long_running_extraction():
    """测试长时间运行的提取过程"""
    
    print("\n" + "="*50)
    print("⏰ 测试长时间运行的提取过程...")
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
    
    config = {
        'search': {
            'base_url': 'https://we.51job.com/pc/search',
            'job_area': '020000',
            'search_type': '2',
            'keyword_type': '',
            'strategy': {'max_pages': 1, 'page_delay': 1}
        },
        'selectors': {
            'search_page': {
                'job_list': '.joblist',
                'job_title': '.jname a',
                'company_name': '.cname',
                'salary': '.sal',
                'location': '.area',
                'next_page': '.btn-next'
            }
        },
        'selenium': {
            'headless': False,
            'window_size': '1920,1080',
            'page_load_timeout': 30,
            'element_wait_timeout': 10,
            'implicit_wait': 5
        },
        'mode': {
            'development': True,
            'debug': True,
            'skip_login': True,
            'close_on_complete': True
        },
        'database': {'enabled': True, 'path': './data/debug_jobs.db'}
    }
    
    try:
        from src.extraction.content_extractor import ContentExtractor
        
        extractor = ContentExtractor(config)
        
        # 模拟长时间处理
        keyword = "Python开发"
        max_results = 20  # 更多职位
        
        print(f"🚀 开始长时间提取测试...")
        print(f"📊 参数: 关键词='{keyword}', 最大结果={max_results}")
        
        start_time = time.time()
        
        # 分阶段执行，每阶段检查会话
        print("🔍 阶段1: 准备浏览器...")
        driver = extractor._prepare_browser()
        
        # 检查会话
        if not extractor.browser_manager.is_driver_alive():
            print("❌ 浏览器会话在准备阶段就失效了")
            return
        
        print("🔍 阶段2: 导航到搜索页面...")
        search_url = extractor.url_builder.build_search_url(keyword)
        extractor._navigate_to_page(driver, search_url)
        
        # 再次检查会话
        if not extractor.browser_manager.is_driver_alive():
            print("❌ 浏览器会话在导航阶段失效")
            return
        
        print("🔍 阶段3: 解析职位列表...")
        jobs = extractor.page_parser.parse_job_list(driver, max_results=max_results)
        
        elapsed = time.time() - start_time
        print(f"📊 阶段3完成: 找到 {len(jobs)} 个职位，耗时 {elapsed:.1f} 秒")
        
        # 检查会话状态
        if not extractor.browser_manager.is_driver_alive():
            print("❌ 浏览器会话在解析阶段失效")
            return
        
        print("🔍 阶段4: 模拟详情提取...")
        # 模拟详情提取的时间消耗
        for i, job in enumerate(jobs[:5], 1):  # 只处理前5个
            print(f"  处理职位 {i}/5: {job.get('title', 'N/A')}")
            
            # 模拟详情提取的时间延迟
            time.sleep(2)  # 每个职位2秒
            
            # 每处理一个职位检查一次会话
            if not extractor.browser_manager.is_driver_alive():
                print(f"❌ 浏览器会话在处理第 {i} 个职位时失效")
                break
            
            elapsed = time.time() - start_time
            print(f"    会话状态: ✅ 活跃 (已运行 {elapsed:.1f}s)")
        
        total_time = time.time() - start_time
        print(f"\n✅ 长时间提取测试完成!")
        print(f"📊 总耗时: {total_time:.1f} 秒")
        print(f"📊 处理职位: {len(jobs)} 个")
        print(f"📊 会话状态: {'✅ 正常' if extractor.browser_manager.is_driver_alive() else '❌ 失效'}")
        
        extractor.close()
        
    except Exception as e:
        print(f"❌ 长时间提取测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 WebDriver 会话管理调试工具")
    print("=" * 50)
    
    choice = input("选择测试类型:\n1. 会话超时测试 (5分钟)\n2. 长时间提取过程测试\n请输入 1 或 2: ").strip()
    
    if choice == "1":
        test_session_timeout()
    elif choice == "2":
        test_long_running_extraction()
    else:
        print("❌ 无效选择，执行会话超时测试...")
        test_session_timeout()
    
    print("\n🎉 调试完成!")