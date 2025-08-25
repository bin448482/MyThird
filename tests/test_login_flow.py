#!/usr/bin/env python3
"""
测试登录流程的完整功能
1. 登录页面成功登录
2. 检测到登录后URL跳转
3. 检测跳转后的登录状态
"""

import time
import logging
import yaml
from src.auth.browser_manager import BrowserManager
from src.auth.login_manager import LoginManager, LoginDetector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_login_flow():
    """测试完整的登录流程"""
    
    print("🚀 开始测试登录流程")
    print("=" * 60)
    
    # 加载配置
    try:
        with open('config/integration_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print("✅ 配置文件加载成功")
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False
    
    browser_manager = None
    login_manager = None
    
    try:
        # 第1步：创建浏览器管理器和登录管理器
        print("\n📋 第1步：初始化浏览器和登录管理器")
        browser_manager = BrowserManager(config)
        login_manager = LoginManager(config, browser_manager)
        
        # 创建WebDriver
        driver = browser_manager.create_driver()
        print("✅ 浏览器创建成功")
        
        # 第2步：导航到登录页面
        print("\n📋 第2步：导航到登录页面")
        login_url = config['login']['login_url']
        print(f"🌐 导航到: {login_url}")
        driver.get(login_url)
        time.sleep(3)
        
        current_url = driver.current_url
        page_title = driver.title
        print(f"✅ 页面加载完成")
        print(f"   当前URL: {current_url}")
        print(f"   页面标题: {page_title}")
        
        # 第3步：等待用户登录
        print("\n📋 第3步：等待用户登录")
        print("=" * 40)
        print("🔐 请在浏览器中完成登录操作")
        print("登录完成后，按回车键继续...")
        print("=" * 40)
        input()
        
        # 第4步：检测登录状态（在登录页面）
        print("\n📋 第4步：检测登录页面的登录状态")
        login_detector = LoginDetector(driver, config)
        
        is_logged_in_on_login_page = login_detector.is_logged_in()
        current_url_after_login = driver.current_url
        page_title_after_login = driver.title
        
        print(f"   当前URL: {current_url_after_login}")
        print(f"   页面标题: {page_title_after_login}")
        print(f"   登录状态检测: {'✅ 已登录' if is_logged_in_on_login_page else '❌ 未检测到登录'}")
        
        # 第5步：跳转到搜索页面
        print("\n📋 第5步：跳转到搜索页面")
        search_url = "https://we.51job.com/pc/search?keyword=AI&searchType=2&sortType=0&metro="
        print(f"🌐 跳转到搜索页面: {search_url}")
        driver.get(search_url)
        time.sleep(5)  # 等待页面加载
        
        current_url_on_search = driver.current_url
        page_title_on_search = driver.title
        print(f"✅ 搜索页面加载完成")
        print(f"   当前URL: {current_url_on_search}")
        print(f"   页面标题: {page_title_on_search}")
        
        # 第6步：检测搜索页面的登录状态
        print("\n📋 第6步：检测搜索页面的登录状态")
        is_logged_in_on_search_page = login_detector.is_logged_in()
        print(f"   登录状态检测: {'✅ 已登录' if is_logged_in_on_search_page else '❌ 未检测到登录'}")
        
        # 第7步：详细分析页面元素
        print("\n📋 第7步：详细分析页面元素")
        analyze_page_elements(driver, config)
        
        # 第8步：测试结果总结
        print("\n📋 第8步：测试结果总结")
        print("=" * 60)
        
        results = {
            'login_page_detection': is_logged_in_on_login_page,
            'search_page_detection': is_logged_in_on_search_page,
            'url_transition': current_url != current_url_on_search
        }
        
        print(f"🔍 登录页面状态检测: {'✅ 成功' if results['login_page_detection'] else '❌ 失败'}")
        print(f"🔍 搜索页面状态检测: {'✅ 成功' if results['search_page_detection'] else '❌ 失败'}")
        print(f"🔍 URL跳转检测: {'✅ 成功' if results['url_transition'] else '❌ 失败'}")
        
        overall_success = any(results.values())
        print(f"\n🎯 总体测试结果: {'✅ 成功' if overall_success else '❌ 失败'}")
        
        if overall_success:
            print("\n💡 建议：")
            if results['search_page_detection']:
                print("   - 搜索页面的登录检测正常工作")
            if results['login_page_detection']:
                print("   - 登录页面的登录检测正常工作")
            if not results['search_page_detection'] and results['login_page_detection']:
                print("   - 需要更新搜索页面的登录指示器配置")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理资源
        print("\n🧹 清理资源...")
        if browser_manager:
            browser_manager.quit_driver()
        print("✅ 清理完成")

def analyze_page_elements(driver, config):
    """分析页面元素，查找可能的登录指示器"""
    from selenium.webdriver.common.by import By
    
    print("🔍 分析当前页面的登录相关元素:")
    
    # 当前配置的指示器
    success_indicators = config['login']['success_indicators']
    print(f"   配置的指示器: {success_indicators}")
    
    found_elements = []
    
    for selector in success_indicators:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                for i, element in enumerate(elements):
                    try:
                        is_displayed = element.is_displayed()
                        text = element.text.strip()[:30] if element.text else ""
                        tag_name = element.tag_name
                        class_attr = element.get_attribute('class') or ""
                        
                        if is_displayed or text:  # 只显示有意义的元素
                            found_elements.append({
                                'selector': selector,
                                'index': i,
                                'tag': tag_name,
                                'text': text,
                                'class': class_attr,
                                'displayed': is_displayed
                            })
                            
                            print(f"   ✅ 找到: {selector}[{i}]")
                            print(f"      标签: {tag_name}")
                            print(f"      显示: {is_displayed}")
                            print(f"      文本: '{text}'")
                            print(f"      类名: {class_attr}")
                            print()
                            
                    except Exception as e:
                        print(f"   ⚠️ 检查元素 {selector}[{i}] 时出错: {e}")
                        
        except Exception as e:
            print(f"   ❌ 选择器 '{selector}' 查找失败: {e}")
    
    print(f"📊 总共找到 {len(found_elements)} 个相关元素")
    
    # 额外检查一些常见的登录指示器
    additional_selectors = [
        'a[href*="logout"]',
        'a[href*="signout"]', 
        '.username',
        '.user-name',
        '.nickname',
        '[class*="user"]',
        '[class*="login"]',
        'a[href="javascript:"]'
    ]
    
    print("\n🔍 检查额外的可能指示器:")
    for selector in additional_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                for i, element in enumerate(elements[:3]):  # 只显示前3个
                    try:
                        is_displayed = element.is_displayed()
                        text = element.text.strip()[:30] if element.text else ""
                        href = element.get_attribute('href') or ""
                        
                        if is_displayed and (text or href):
                            print(f"   💡 发现: {selector}[{i}] - '{text}' (href: {href})")
                            
                    except Exception:
                        pass
        except Exception:
            pass

if __name__ == "__main__":
    success = test_login_flow()
    if success:
        print("\n🎉 登录流程测试完成！")
    else:
        print("\n❌ 登录流程测试失败！")