#!/usr/bin/env python3
"""
快速调试 ContentExtractor.extract_from_keyword 方法
简化版本，专注于核心功能测试
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def quick_test():
    """快速测试 extract_from_keyword 方法"""
    
    # 设置简单日志
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # 最小配置
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
    
    print("🚀 开始快速调试测试...")
    print(f"⏰ 开始时间: {time.strftime('%H:%M:%S')}")
    
    try:
        from src.extraction.content_extractor import ContentExtractor
        
        # 创建提取器
        extractor = ContentExtractor(config)
        
        # 测试参数
        keyword = "Python开发"
        max_results = 5  # 只测试5个职位
        max_pages = 1    # 只测试1页
        extract_details = False  # 先不提取详情，测试基础功能
        
        print(f"📊 测试参数: 关键词='{keyword}', 最大结果={max_results}, 页数={max_pages}")
        
        # 执行测试
        start_time = time.time()
        
        results = extractor.extract_from_keyword(
            keyword=keyword,
            max_results=max_results,
            save_results=True,
            extract_details=extract_details,
            max_pages=max_pages
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 输出结果
        print(f"\n✅ 测试完成!")
        print(f"⏰ 结束时间: {time.strftime('%H:%M:%S')}")
        print(f"⏱️ 执行时间: {execution_time:.2f} 秒")
        print(f"📊 提取结果: {len(results)} 个职位")
        
        if results:
            print(f"📊 平均每个职位: {execution_time/len(results):.2f} 秒")
            
            print(f"\n📋 前3个结果:")
            for i, job in enumerate(results[:3], 1):
                print(f"  {i}. {job.get('title', 'N/A')} - {job.get('company', 'N/A')} - {job.get('salary', 'N/A')}")
        else:
            print("⚠️ 没有提取到任何职位")
        
        # 清理
        extractor.close()
        
        return results
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_with_details():
    """测试包含详情提取的版本"""
    print("\n" + "="*50)
    print("🔍 测试详情提取功能...")
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
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
            },
            'job_detail': {
                'job_description': '.bmsg.job_msg.inbox',
                'requirements': '.job-requirements',
                'company_info': '.company-info',
                'benefits': '.job-benefits'
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
        
        # 测试参数 - 减少数量以便观察详情提取
        keyword = "Python开发"
        max_results = 40  # 只测试2个职位的详情
        max_pages = 2
        extract_details = True  # 提取详情
        
        print(f"📊 详情测试参数: 关键词='{keyword}', 最大结果={max_results}, 提取详情={extract_details}")
        
        start_time = time.time()
        
        results = extractor.extract_from_keyword(
            keyword=keyword,
            max_results=max_results,
            save_results=True,
            extract_details=extract_details,
            max_pages=max_pages
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n✅ 详情测试完成!")
        print(f"⏱️ 执行时间: {execution_time:.2f} 秒")
        print(f"📊 提取结果: {len(results)} 个职位")
        
        if results:
            print(f"📊 平均每个职位: {execution_time/len(results):.2f} 秒")
            
            for i, job in enumerate(results, 1):
                print(f"\n📋 职位 {i}:")
                print(f"  标题: {job.get('title', 'N/A')}")
                print(f"  公司: {job.get('company', 'N/A')}")
                print(f"  URL: {job.get('url', 'N/A')}")
                desc_len = len(job.get('description', ''))
                print(f"  描述长度: {desc_len} 字符")
                if desc_len > 0:
                    print(f"  描述预览: {job.get('description', '')[:100]}...")
        
        extractor.close()
        return results
        
    except Exception as e:
        print(f"❌ 详情测试失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_performance_comparison():
    """性能对比测试（基于实际PageParser优化）"""
    print("\n" + "="*50)
    print("⚡ 测试PageParser性能优化...")
    
    try:
        from src.extraction.page_parser import PageParser
        
        # 模拟配置
        config = {
            'selectors': {
                'search_page': {
                    'company_name': '.cname',
                    'salary': '.sal',
                    'location': '.area',
                    'experience': '.experience',
                    'education': '.education',
                    'job_title': '.jname a'
                }
            }
        }
        
        parser = PageParser(config)
        
        # 创建模拟职位元素
        class MockElement:
            def __init__(self, data):
                self.data = data
            
            def find_element(self, by, selector):
                time.sleep(0.005)  # 模拟DOM查询延迟
                mock_elem = type('MockElem', (), {})()
                selector_map = {
                    '.cname': 'company',
                    '.sal': 'salary',
                    '.area': 'location',
                    '.experience': 'experience',
                    '.education': 'education',
                    '.jname a': 'title'
                }
                field = selector_map.get(selector, 'unknown')
                mock_elem.text = self.data.get(field, f"默认{field}")
                return mock_elem
        
        # 创建测试数据
        test_jobs = []
        for i in range(10):
            job_data = {
                'title': f'Python开发工程师{i+1}',
                'company': f'科技公司{i+1}',
                'salary': f'{15+i*2}-{25+i*2}K',
                'location': f'广州市{i+1}区',
                'experience': f'{1+i%5}年经验',
                'education': '本科'
            }
            test_jobs.append(MockElement(job_data))
        
        print(f"📊 测试数据: {len(test_jobs)} 个模拟职位")
        
        # 测试原始串行版本（模拟）
        print("\n🐌 测试串行字段提取...")
        serial_start = time.time()
        serial_results = []
        
        for i, job_element in enumerate(test_jobs):
            # 模拟原始的串行提取
            job_data = {'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S')}
            
            # 串行提取每个字段
            job_data['company'] = parser._extract_text_by_selector(job_element, '.cname', '未知公司')
            job_data['salary'] = parser._extract_text_by_selector(job_element, '.sal', '薪资面议')
            job_data['location'] = parser._extract_text_by_selector(job_element, '.area', '未知地点')
            job_data['experience'] = parser._extract_text_by_selector(job_element, '.experience', '经验不限')
            job_data['education'] = parser._extract_text_by_selector(job_element, '.education', '学历不限')
            
            serial_results.append(job_data)
        
        serial_time = time.time() - serial_start
        
        # 测试批量优化版本
        print("🚀 测试批量字段提取...")
        batch_start = time.time()
        batch_results = []
        
        for job_element in test_jobs:
            # 使用优化的批量提取方法
            job_data = {'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S')}
            field_data = parser._extract_multiple_fields_batch(job_element)
            job_data.update(field_data)
            batch_results.append(job_data)
        
        batch_time = time.time() - batch_start
        
        # 性能对比
        print(f"\n🏁 PageParser性能对比:")
        print(f"   串行提取: {serial_time:.3f}s ({serial_time/len(test_jobs):.3f}s/职位)")
        print(f"   批量提取: {batch_time:.3f}s ({batch_time/len(test_jobs):.3f}s/职位)")
        
        if serial_time > batch_time:
            improvement = ((serial_time - batch_time) / serial_time) * 100
            print(f"   性能提升: {improvement:.1f}%")
        else:
            print("   批量提取性能相当")
        
        print(f"✅ 测试完成: 串行={len(serial_results)}个, 批量={len(batch_results)}个")
        
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 ContentExtractor 快速调试工具")
    print("=" * 50)
    
    # 选择测试类型
    print("选择测试类型:")
    print("1. 基础功能测试 (不提取详情)")
    print("2. 详情提取测试")
    print("3. PageParser性能对比测试")
    
    choice = input("请输入 1-3: ").strip()
    
    if choice == "1":
        results = quick_test()
    elif choice == "2":
        results = test_with_details()
    elif choice == "3":
        test_performance_comparison()
        results = []
    else:
        print("❌ 无效选择，执行基础测试...")
        results = quick_test()
    
    print(f"\n🎉 调试完成! 共提取 {len(results)} 个职位")