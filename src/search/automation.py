"""
前程无忧自动化搜索控制器

实现人工登录后自动导航到搜索页面的功能
"""

import time
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from .url_builder import SearchURLBuilder
from .login_detector import LoginDetector
from ..core.config import ConfigManager
from ..core.exceptions import WebDriverError, LoginTimeoutError
from ..utils.logger import setup_logger


class JobSearchAutomation:
    """前程无忧自动化搜索控制器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化自动化搜索控制器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.driver = None
        self.url_builder = SearchURLBuilder(self.config)
        self.login_detector = None
        self.logger = self._setup_logger()
        
        # 搜索结果存储
        self.search_results = []
        self.current_keyword = None
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            config_manager = ConfigManager(self.config_path)
            return config_manager.load_config()
        except Exception as e:
            raise Exception(f"配置文件加载失败: {e}")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        return setup_logger(self.config)
    
    def start_search_session(self, keyword: Optional[str] = None) -> None:
        """
        开始搜索会话
        
        Args:
            keyword: 搜索关键词，如果为None则使用配置中的默认关键词
        """
        try:
            self.logger.info("🚀 开始前程无忧自动化搜索会话")
            
            # 1. 设置搜索关键词
            if keyword:
                self.current_keyword = keyword
                self.url_builder.set_current_keyword(keyword)
            else:
                self.current_keyword = self.url_builder.get_current_keyword()
            
            self.logger.info(f"🔍 搜索关键词: {self.current_keyword}")
            
            # 2. 启动浏览器
            self._setup_driver()
            
            # 3. 导航到登录页面
            self._navigate_to_login()
            
            # 4. 等待用户登录
            self.login_detector = LoginDetector(self.driver, self.config)
            self.login_detector.wait_for_login()
            
            # 5. 登录成功后自动导航到搜索页面
            search_url = self.url_builder.build_search_url(self.current_keyword)
            self._navigate_to_search(search_url)
            
            # 6. 开始搜索流程
            self._execute_search()
            
            self.logger.info("✅ 搜索会话完成")
            
        except KeyboardInterrupt:
            self.logger.info("⚠️ 用户中断搜索会话")
            raise
        except Exception as e:
            self.logger.error(f"❌ 搜索会话失败: {e}")
            raise
        finally:
            self._cleanup()
    
    def _setup_driver(self) -> None:
        """设置WebDriver"""
        try:
            self.logger.info("🔧 设置Chrome WebDriver...")
            
            # Chrome选项
            chrome_options = Options()
            selenium_config = self.config.get('selenium', {})
            
            if selenium_config.get('headless', False):
                chrome_options.add_argument('--headless')
            
            # 反爬虫设置
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 窗口大小
            window_size = selenium_config.get('window_size', '1920,1080')
            chrome_options.add_argument(f'--window-size={window_size}')
            
            # 用户代理
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 禁用日志输出
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            # 自动下载并设置ChromeDriver
            service = Service(ChromeDriverManager().install())
            
            # 创建WebDriver实例
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置超时
            page_load_timeout = selenium_config.get('page_load_timeout', 30)
            element_wait_timeout = selenium_config.get('element_wait_timeout', 10)
            implicit_wait = selenium_config.get('implicit_wait', 5)
            
            self.driver.implicitly_wait(implicit_wait)
            self.driver.set_page_load_timeout(page_load_timeout)
            
            # 执行反检测脚本
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("✅ WebDriver设置成功")
            
        except Exception as e:
            self.logger.error(f"❌ WebDriver设置失败: {e}")
            raise WebDriverError(f"WebDriver设置失败: {e}")
    
    def _navigate_to_login(self) -> None:
        """导航到登录页面"""
        login_url = self.config['login']['login_url']
        self.logger.info(f"🌐 导航到登录页面: {login_url}")
        
        try:
            self.driver.get(login_url)
            
            # 等待页面加载
            WebDriverWait(self.driver, 15).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            self.logger.info("✅ 登录页面加载完成")
            
        except TimeoutException:
            self.logger.error("❌ 登录页面加载超时")
            raise
        except Exception as e:
            self.logger.error(f"❌ 导航到登录页面失败: {e}")
            raise
    
    def _navigate_to_search(self, search_url: str) -> None:
        """
        导航到搜索页面
        
        Args:
            search_url: 搜索页面URL
        """
        self.logger.info(f"🔍 导航到搜索页面: {search_url}")
        
        try:
            self.driver.get(search_url)
            
            # 等待搜索页面加载
            selectors = self.config['selectors']['search_page']
            job_list_selector = selectors['job_list']
            
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, job_list_selector))
            )
            
            self.logger.info("✅ 搜索页面加载完成")
            
        except TimeoutException:
            self.logger.warning("⚠️ 搜索页面加载超时，可能需要手动刷新")
            # 尝试刷新页面
            self.driver.refresh()
            time.sleep(5)
        except Exception as e:
            self.logger.error(f"❌ 导航到搜索页面失败: {e}")
            raise
    
    def _execute_search(self) -> None:
        """执行搜索和数据收集"""
        self.logger.info(f"📊 开始收集搜索结果 - 关键词: {self.current_keyword}")
        
        selectors = self.config['selectors']['search_page']
        strategy = self.config['search']['strategy']
        
        try:
            # 等待页面稳定
            time.sleep(3)
            
            # 获取职位列表
            job_elements = self.driver.find_elements(By.CSS_SELECTOR, selectors['job_list'])
            
            if not job_elements:
                self.logger.warning("⚠️ 未找到职位列表，可能页面结构发生变化")
                self.logger.warning("💡 提示: 建议人工检查页面结构，可能需要更新选择器")
                return
            
            self.logger.info(f"📋 找到 {len(job_elements)} 个职位")
            
            # 处理每个职位
            max_results = strategy.get('max_results_per_keyword', 50)
            processed_count = 0
            
            for i, job_element in enumerate(job_elements, 1):
                if processed_count >= max_results:
                    self.logger.info(f"📊 已达到最大结果数量限制: {max_results}")
                    break
                
                try:
                    job_data = self._extract_job_data(job_element, selectors)
                    if job_data:
                        self.search_results.append(job_data)
                        processed_count += 1
                        
                        self.logger.info(
                            f"📝 职位 {processed_count}: {job_data.get('title', '未知')} - "
                            f"{job_data.get('company', '未知')} - {job_data.get('salary', '面议')}"
                        )
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ 处理职位 {i} 时出错: {e}")
                    continue
            
            # 保存搜索结果
            if strategy.get('save_job_details', True):
                self._save_search_results()
            
            self.logger.info(f"✅ 搜索完成，共收集 {processed_count} 个职位信息")
            
        except Exception as e:
            self.logger.error(f"❌ 执行搜索失败: {e}")
            raise
    
    def _extract_job_data(self, job_element, selectors: Dict) -> Optional[Dict]:
        """
        提取职位数据
        
        Args:
            job_element: 职位元素
            selectors: 选择器配置
            
        Returns:
            职位数据字典
        """
        job_data = {
            'keyword': self.current_keyword,
            'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            # 职位标题
            try:
                title_element = job_element.find_element(By.CSS_SELECTOR, selectors['job_title'])
                job_data['title'] = title_element.text.strip()
                job_data['url'] = title_element.get_attribute('href')
            except:
                job_data['title'] = "未知职位"
                job_data['url'] = ""
            
            # 公司名称
            try:
                company_element = job_element.find_element(By.CSS_SELECTOR, selectors['company_name'])
                job_data['company'] = company_element.text.strip()
            except:
                job_data['company'] = "未知公司"
            
            # 薪资
            try:
                salary_element = job_element.find_element(By.CSS_SELECTOR, selectors['salary'])
                job_data['salary'] = salary_element.text.strip()
            except:
                job_data['salary'] = "薪资面议"
            
            # 地点
            try:
                location_element = job_element.find_element(By.CSS_SELECTOR, selectors['location'])
                job_data['location'] = location_element.text.strip()
            except:
                job_data['location'] = "未知地点"
            
            # 经验要求
            try:
                experience_element = job_element.find_element(By.CSS_SELECTOR, selectors['experience'])
                job_data['experience'] = experience_element.text.strip()
            except:
                job_data['experience'] = "经验不限"
            
            # 学历要求
            try:
                education_element = job_element.find_element(By.CSS_SELECTOR, selectors['education'])
                job_data['education'] = education_element.text.strip()
            except:
                job_data['education'] = "学历不限"
            
            return job_data
            
        except Exception as e:
            self.logger.warning(f"⚠️ 提取职位数据失败: {e}")
            return None
    
    def _save_search_results(self) -> None:
        """保存搜索结果到文件"""
        if not self.search_results:
            return
        
        try:
            # 创建数据目录
            data_dir = Path("data/search_results")
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"search_{self.current_keyword}_{timestamp}.json"
            filepath = data_dir / filename
            
            # 保存数据
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.search_results, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 搜索结果已保存到: {filepath}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存搜索结果失败: {e}")
    
    def _debug_page_structure(self) -> None:
        """调试页面结构（当找不到预期元素时）"""
        self.logger.info("🔍 调试页面结构...")
        
        try:
            # 获取页面基本信息
            self.logger.info(f"当前URL: {self.driver.current_url}")
            self.logger.info(f"页面标题: {self.driver.title}")
            
            # 查找可能的职位列表元素
            possible_selectors = [
                ".job-list",
                ".job-item",
                ".position-list",
                ".search-result",
                "[data-testid*='job']",
                ".list-item"
            ]
            
            for selector in possible_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.logger.info(f"找到可能的职位列表: {selector} (数量: {len(elements)})")
                except:
                    continue
            
        except Exception as e:
            self.logger.error(f"调试页面结构失败: {e}")
    
    def get_search_results(self) -> List[Dict]:
        """
        获取搜索结果
        
        Returns:
            搜索结果列表
        """
        return self.search_results.copy()
    
    def get_search_summary(self) -> Dict:
        """
        获取搜索摘要
        
        Returns:
            搜索摘要信息
        """
        return {
            'keyword': self.current_keyword,
            'total_results': len(self.search_results),
            'search_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'config_file': self.config_path
        }
    
    def _cleanup(self) -> None:
        """清理资源"""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("🧹 WebDriver已关闭")
        except Exception as e:
            self.logger.error(f"❌ 清理资源时出错: {e}")


def main():
    """主函数 - 使用示例"""
    import argparse
    
    parser = argparse.ArgumentParser(description="前程无忧自动化搜索")
    parser.add_argument("--keyword", help="搜索关键词")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径")
    args = parser.parse_args()
    
    try:
        # 创建搜索自动化实例
        automation = JobSearchAutomation(args.config)
        
        # 开始搜索会话
        automation.start_search_session(keyword=args.keyword)
        
        # 显示搜索摘要
        summary = automation.get_search_summary()
        print("\n" + "="*50)
        print("搜索摘要")
        print("="*50)
        print(f"关键词: {summary['keyword']}")
        print(f"结果数量: {summary['total_results']}")
        print(f"搜索时间: {summary['search_time']}")
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n搜索被用户中断")
    except Exception as e:
        print(f"\n搜索失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())