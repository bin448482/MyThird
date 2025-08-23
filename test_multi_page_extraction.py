"""
测试多页职位提取功能
验证数据丢失问题是否已修复
"""

import asyncio
import logging
import yaml
from src.extraction.content_extractor import ContentExtractor

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

def test_multi_page_extraction():
    """测试多页职位提取"""
    logger.info("🚀 开始测试多页职位提取功能")
    
    # 加载配置
    config = load_integration_config()
    logger.info(f"✅ 配置加载成功")
    
    # 从配置中获取测试参数
    search_config = config.get('search', {})
    keywords = search_config.get('keywords', {}).get('priority_1', ['Python开发'])
    test_keyword = keywords[0] if keywords else 'Python开发'
    
    logger.info(f"🔍 使用测试关键词: {test_keyword}")
    
    # 初始化ContentExtractor
    content_extractor = ContentExtractor(config)
    
    try:
        # 测试不同的参数组合
        test_cases = [
            {
                'max_results': 40,
                'max_pages': 2,
                'description': '40个职位，2页'
            },
            {
                'max_results': 30,
                'max_pages': 2,
                'description': '30个职位，2页'
            },
            {
                'max_results': 25,
                'max_pages': 2,
                'description': '25个职位，2页'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 测试用例 {i}: {test_case['description']}")
            logger.info(f"{'='*60}")
            
            try:
                # 调用extract_from_keyword进行多页提取
                extracted_jobs = content_extractor.extract_from_keyword(
                    keyword=test_keyword,
                    max_results=test_case['max_results'],
                    save_results=False,  # 测试时不保存
                    extract_details=False,  # 测试时不提取详情，加快速度
                    max_pages=test_case['max_pages']
                )
                
                logger.info(f"📊 提取结果分析:")
                logger.info(f"   - 期望职位数量: {test_case['max_results']}")
                logger.info(f"   - 实际提取数量: {len(extracted_jobs)}")
                logger.info(f"   - 最大页数: {test_case['max_pages']}")
                
                # 检查是否达到期望数量
                if len(extracted_jobs) >= test_case['max_results']:
                    logger.info(f"✅ 测试通过: 成功提取到足够的职位数量")
                elif len(extracted_jobs) >= test_case['max_results'] * 0.8:  # 80%以上认为基本成功
                    logger.warning(f"⚠️ 部分成功: 提取数量接近期望值")
                else:
                    logger.error(f"❌ 测试失败: 提取数量远低于期望值")
                
                # 分析前5个职位
                logger.info(f"📝 前5个职位详情:")
                for j, job in enumerate(extracted_jobs[:5], 1):
                    logger.info(f"   {j}. 标题: {job.get('title', 'N/A')}")
                    logger.info(f"      公司: {job.get('company', 'N/A')}")
                    logger.info(f"      页码: {job.get('page_number', 'N/A')}")
                
                # 分析页面分布
                page_distribution = {}
                for job in extracted_jobs:
                    page_num = job.get('page_number', 1)
                    page_distribution[page_num] = page_distribution.get(page_num, 0) + 1
                
                logger.info(f"📄 页面分布:")
                for page_num, count in sorted(page_distribution.items()):
                    logger.info(f"   - 第{page_num}页: {count}个职位")
                
                # 检查是否有多页数据
                if len(page_distribution) > 1:
                    logger.info(f"✅ 多页提取成功: 共处理了 {len(page_distribution)} 页")
                else:
                    logger.warning(f"⚠️ 只处理了1页，可能存在翻页问题")
                
            except Exception as e:
                logger.error(f"❌ 测试用例 {i} 执行失败: {e}")
                import traceback
                logger.error(f"错误详情: {traceback.format_exc()}")
        
        logger.info(f"\n{'='*60}")
        logger.info("🎉 多页提取测试完成")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"❌ 测试执行失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
    
    finally:
        # 清理资源
        try:
            content_extractor.close()
            logger.info("✅ 资源清理完成")
        except:
            pass

if __name__ == "__main__":
    test_multi_page_extraction()