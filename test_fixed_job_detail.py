#!/usr/bin/env python3
"""
测试修复后的职位详情页解析功能
"""

import sys
import os
import logging
import json
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
            logging.FileHandler('test_fixed_job_detail.log', encoding='utf-8')
        ]
    )

def test_fixed_detail_parsing():
    """测试修复后的详情页解析"""
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
        
        # 6. 使用修复后的解析方法
        logger.info("🔧 使用修复后的详情页解析方法...")
        detail_data = page_parser.parse_job_detail(driver, test_url)
        
        if detail_data:
            logger.info("✅ 详情页解析成功！")
            logger.info("=" * 80)
            logger.info(f"URL: {detail_data.get('url', '')}")
            logger.info(f"页面标题: {detail_data.get('page_title', '')}")
            logger.info(f"职位描述长度: {len(detail_data.get('description', ''))} 字符")
            logger.info(f"职位要求长度: {len(detail_data.get('requirements', ''))} 字符")
            logger.info(f"公司信息: {detail_data.get('company_info', '未提取到')}")
            logger.info(f"福利待遇: {detail_data.get('benefits', '未提取到')}")
            logger.info("=" * 80)
            
            # 显示部分职位描述
            description = detail_data.get('description', '')
            if description:
                logger.info("📝 职位描述片段:")
                logger.info(description[:200] + "..." if len(description) > 200 else description)
            
            # 保存完整结果
            result_file = 'fixed_job_detail_result.json'
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(detail_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 详细结果已保存到 {result_file}")
            return True
            
        else:
            logger.error("❌ 详情页解析失败！")
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
    print("🧪 开始测试修复后的职位详情页解析...")
    
    # 设置日志
    setup_logging()
    
    try:
        # 运行测试
        success = test_fixed_detail_parsing()
        
        if success:
            print("✅ 修复后的详情页解析测试成功！")
            print("📁 查看 fixed_job_detail_result.json 获取详细结果")
            print("📄 查看 test_fixed_job_detail.log 获取日志")
        else:
            print("❌ 修复后的详情页解析测试失败！")
            print("📄 查看 test_fixed_job_detail.log 获取错误详情")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(0)

if __name__ == "__main__":
    main()