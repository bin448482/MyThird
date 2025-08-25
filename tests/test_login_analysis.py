#!/usr/bin/env python3
"""
登录状态分析测试脚本
"""

def test_login_analysis():
    """测试登录状态分析功能"""
    from src.auth.browser_manager import BrowserManager
    from src.auth.login_state_analyzer import QianchengLoginStateAnalyzer
    import yaml
    
    # 加载配置
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 创建浏览器管理器
    browser_manager = BrowserManager(config)
    driver = browser_manager.create_driver()
    
    try:
        # 导航到前程无忧登录页面
        driver.get("https://login.51job.com/")
        
        print("请在浏览器中完成登录，然后按Enter继续...")
        input()
        
        # 创建分析器
        analyzer = QianchengLoginStateAnalyzer(driver, config)
        
        # 执行分析
        results = analyzer.analyze_full_login_state()
        
        # 保存报告
        report_file = analyzer.save_analysis_report()
        
        # 显示摘要
        summary = analyzer.generate_summary_report()
        print(summary)
        
        print(f"\n详细报告已保存到: {report_file}")
        
    finally:
        browser_manager.quit_driver()

if __name__ == "__main__":
    test_login_analysis()