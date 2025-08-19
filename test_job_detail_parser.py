#!/usr/bin/env python3
"""
专门测试职位详情页解析的脚本
用于调试和修复职位详情页解析问题
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('test_job_detail_parser.log', encoding='utf-8')
        ]
    )

def test_job_detail_parsing():
    """测试职位详情页解析"""
    logger = logging.getLogger(__name__)
    
    try:
        # 导入必要的模块
        from src.core.config import ConfigManager
        from src.extraction.page_parser import PageParser
        from src.auth.browser_manager import BrowserManager
        
        # 1. 加载配置
        logger.info("🔧 加载配置文件...")
        config_manager = ConfigManager("config/config.yaml")
        config = config_manager.load_config()
        
        # 设置为开发模式
        config['mode']['skip_login'] = True
        config['mode']['development'] = True
        
        # 2. 创建组件
        logger.info("🚀 创建解析器组件...")
        browser_manager = BrowserManager(config)
        page_parser = PageParser(config)
        
        # 3. 测试URL
        test_url = "https://jobs.51job.com/shanghai/167134875.html"
        logger.info(f"🔍 测试URL: {test_url}")
        
        # 4. 创建浏览器
        logger.info("🌐 创建浏览器实例...")
        driver = browser_manager.create_driver()
        
        # 5. 导航到页面
        logger.info(f"📄 导航到职位详情页: {test_url}")
        driver.get(test_url)
        
        # 等待页面加载
        import time
        time.sleep(3)
        
        # 6. 检查页面基本信息
        page_title = driver.title
        current_url = driver.current_url
        logger.info(f"📋 页面标题: {page_title}")
        logger.info(f"🔗 当前URL: {current_url}")
        
        # 7. 尝试找到职位描述容器
        logger.info("🔍 开始查找职位描述容器...")
        
        # 根据你提供的HTML结构，尝试这些选择器
        job_msg_selectors = [
            '.bmsg.job_msg.inbox',
            '.bmsg.job_msg',
            '.job_msg.inbox',
            '.bmsg',
            '.job_msg'
        ]
        
        job_description = None
        used_selector = None
        
        for selector in job_msg_selectors:
            try:
                from selenium.webdriver.common.by import By
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element:
                    job_description = element.text.strip()
                    if job_description:
                        used_selector = selector
                        logger.info(f"✅ 找到职位描述容器: {selector}")
                        logger.info(f"📝 描述长度: {len(job_description)} 字符")
                        break
            except Exception as e:
                logger.debug(f"选择器 '{selector}' 未找到: {e}")
                continue
        
        if job_description:
            # 8. 输出职位描述
            logger.info("🎯 成功提取职位描述:")
            logger.info("=" * 80)
            logger.info(job_description)
            logger.info("=" * 80)
            
            # 9. 尝试提取职能类别和关键字
            try:
                # 职能类别
                category_element = driver.find_element(By.CSS_SELECTOR, '.fp .label')
                if category_element and category_element.text.strip() == "职能类别：":
                    category_link = driver.find_element(By.CSS_SELECTOR, '.fp .el.tdn')
                    category = category_link.text.strip()
                    logger.info(f"🏷️ 职能类别: {category}")
                
                # 关键字
                keywords_elements = driver.find_elements(By.CSS_SELECTOR, '.fp .el.tdn')
                if len(keywords_elements) > 1:
                    keywords = [elem.text.strip() for elem in keywords_elements[1:]]
                    logger.info(f"🔑 关键字: {', '.join(keywords)}")
                    
            except Exception as e:
                logger.warning(f"提取职能类别和关键字时出错: {e}")
            
            # 10. 保存结果
            result_data = {
                'url': test_url,
                'title': page_title,
                'used_selector': used_selector,
                'description': job_description,
                'description_length': len(job_description),
                'extract_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            import json
            with open('job_detail_parse_result.json', 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            logger.info("💾 解析结果已保存到 job_detail_parse_result.json")
            return True
            
        else:
            logger.error("❌ 未找到职位描述内容")
            
            # 调试：输出页面结构
            logger.info("🔍 调试页面结构...")
            page_source = driver.page_source
            
            # 查找可能的容器
            possible_containers = [
                'div[class*="msg"]',
                'div[class*="job"]',
                'div[class*="desc"]',
                'div[class*="detail"]',
                'div[class*="content"]'
            ]
            
            for container in possible_containers:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, container)
                    if elements:
                        logger.info(f"找到可能的容器: {container} (数量: {len(elements)})")
                        for i, elem in enumerate(elements[:3]):  # 只显示前3个
                            text = elem.text.strip()[:100]
                            logger.info(f"  容器 {i+1}: {text}...")
                except:
                    continue
            
            return False
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    finally:
        # 清理资源
        try:
            if 'browser_manager' in locals():
                browser_manager.quit_driver()
        except:
            pass

def main():
    """主函数"""
    print("🧪 开始职位详情页解析测试...")
    
    # 设置日志
    setup_logging()
    
    try:
        # 运行测试
        success = test_job_detail_parsing()
        
        if success:
            print("✅ 职位详情页解析测试成功！")
            print("📁 查看 job_detail_parse_result.json 获取解析结果")
            print("📄 查看 test_job_detail_parser.log 获取详细日志")
        else:
            print("❌ 职位详情页解析测试失败！")
            print("📄 查看 test_job_detail_parser.log 获取错误详情")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(0)

if __name__ == "__main__":
    main()