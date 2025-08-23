"""
page_parser.parse_job_list 调试测试
用于调试数据丢失问题
"""

import asyncio
import logging
import yaml
from src.extraction.page_parser import PageParser
from src.auth.browser_manager import BrowserManager
from src.search.url_builder import SearchURLBuilder

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_integration_config():
    """加载integration_config.yaml配置"""
    try:
        with open('config/integration_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}

def test_parse_job_list():
    """测试parse_job_list方法"""
    logger.info("🚀 开始测试 page_parser.parse_job_list")
    
    # 加载配置
    config = load_integration_config()
    logger.info(f"✅ 配置加载成功")
    
    # 从配置中获取测试参数
    search_config = config.get('search', {})
    keywords = search_config.get('keywords', {}).get('priority_1', ['Python开发'])
    test_keyword = keywords[0] if keywords else 'Python开发'
    
    logger.info(f"🔍 使用测试关键词: {test_keyword}")
    
    # 初始化组件
    browser_manager = BrowserManager(config)
    page_parser = PageParser(config)
    url_builder = SearchURLBuilder(config)
    
    try:
        # 创建浏览器
        driver = browser_manager.create_driver()
        logger.info("✅ 浏览器创建成功")
        
        # 构建搜索URL
        search_url = url_builder.build_search_url(test_keyword)
        logger.info(f"🌐 搜索URL: {search_url}")
        
        # 导航到搜索页面
        driver.get(search_url)
        logger.info("✅ 页面导航成功")
        
        # 等待页面加载
        import time
        time.sleep(3)
        
        # 调用parse_job_list进行测试
        logger.info("📊 开始调用 parse_job_list...")
        
        # 测试不同的max_results参数
        test_cases = [
            {'max_results': None, 'description': '无限制'},
            {'max_results': 10, 'description': '限制10个'},
            {'max_results': 20, 'description': '限制20个'},
            {'max_results': 40, 'description': '限制40个'},
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n{'='*50}")
            logger.info(f"🧪 测试用例 {i}: {test_case['description']}")
            logger.info(f"{'='*50}")
            
            try:
                # 刷新页面确保状态一致
                if i > 1:
                    driver.refresh()
                    time.sleep(2)
                
                # 调用parse_job_list
                jobs = page_parser.parse_job_list(driver, test_case['max_results'])
                
                logger.info(f"📋 解析结果:")
                logger.info(f"   - 返回职位数量: {len(jobs)}")
                logger.info(f"   - 期望最大数量: {test_case['max_results']}")
                
                # 分析前5个职位的详细信息
                logger.info(f"📝 前5个职位详情:")
                for j, job in enumerate(jobs[:5], 1):
                    logger.info(f"   {j}. 标题: {job.get('title', 'N/A')}")
                    logger.info(f"      公司: {job.get('company', 'N/A')}")
                    logger.info(f"      地点: {job.get('location', 'N/A')}")
                    logger.info(f"      薪资: {job.get('salary', 'N/A')}")
                    logger.info(f"      指纹: {job.get('job_fingerprint', 'N/A')}")
                
                # 检查数据完整性
                complete_jobs = 0
                incomplete_jobs = 0
                
                for job in jobs:
                    if job.get('title') and job.get('company'):
                        complete_jobs += 1
                    else:
                        incomplete_jobs += 1
                
                logger.info(f"📊 数据完整性分析:")
                logger.info(f"   - 完整职位: {complete_jobs}")
                logger.info(f"   - 不完整职位: {incomplete_jobs}")
                logger.info(f"   - 完整率: {complete_jobs/len(jobs)*100:.1f}%" if jobs else "0%")
                
                # 如果有数据丢失，分析原因
                if test_case['max_results'] and len(jobs) < test_case['max_results']:
                    logger.warning(f"⚠️ 数据丢失检测:")
                    logger.warning(f"   - 期望: {test_case['max_results']} 个职位")
                    logger.warning(f"   - 实际: {len(jobs)} 个职位")
                    logger.warning(f"   - 丢失: {test_case['max_results'] - len(jobs)} 个职位")
                    
                    # 检查页面元素
                    from selenium.webdriver.common.by import By
                    job_elements = driver.find_elements(By.CSS_SELECTOR, ".joblist-item")
                    logger.warning(f"   - 页面实际元素数量: {len(job_elements)}")
                    
                    if len(job_elements) > len(jobs):
                        logger.warning(f"   - 可能原因: 解析过程中有元素被跳过")
                    elif len(job_elements) < test_case['max_results']:
                        logger.warning(f"   - 可能原因: 页面实际职位数量不足")
                
            except Exception as e:
                logger.error(f"❌ 测试用例 {i} 执行失败: {e}")
                import traceback
                logger.error(f"错误详情: {traceback.format_exc()}")
        
        logger.info(f"\n{'='*50}")
        logger.info("🎉 所有测试用例执行完成")
        logger.info(f"{'='*50}")
        
    except Exception as e:
        logger.error(f"❌ 测试执行失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
    
    finally:
        # 清理资源
        try:
            browser_manager.quit_driver()
            logger.info("✅ 浏览器已关闭")
        except:
            pass

if __name__ == "__main__":
    test_parse_job_list()