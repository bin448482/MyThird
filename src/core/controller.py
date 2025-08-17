"""
核心控制器

协调各个模块，控制整体流程
"""

import time
import logging
from typing import Dict, Any

from .exceptions import ResumeSubmitterError
from ..database.operations import DatabaseManager
from ..crawler.engine import CrawlerEngine
from ..analyzer.job_analyzer import JobAnalyzer
from ..matcher.matching_engine import MatchingEngine
from ..submitter.submission_engine import SubmissionEngine
from ..adapters.base import AdapterFactory


class ResumeSubmitterController:
    """简历投递控制器"""
    
    def __init__(self, config: Dict[str, Any], website: str, dry_run: bool = False):
        """
        初始化控制器
        
        Args:
            config: 配置字典
            website: 目标网站
            dry_run: 是否为试运行模式
        """
        self.config = config
        self.website = website
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)
        
        # 初始化各个组件
        self._init_components()
    
    def _init_components(self):
        """初始化各个组件"""
        try:
            # 数据库管理器
            self.db_manager = DatabaseManager(self.config['database']['path'])
            
            # 网站适配器
            self.adapter = AdapterFactory.create_adapter(self.website, self.config)
            
            # 爬虫引擎
            self.crawler = CrawlerEngine(self.config, self.adapter)
            
            # 职位分析器
            self.analyzer = JobAnalyzer(self.config)
            
            # 匹配引擎
            self.matcher = MatchingEngine(self.config)
            
            # 投递引擎
            self.submitter = SubmissionEngine(self.config, self.adapter)
            
            self.logger.info("所有组件初始化完成")
            
        except Exception as e:
            self.logger.error(f"组件初始化失败: {e}")
            raise ResumeSubmitterError(f"组件初始化失败: {e}")
    
    def run(self):
        """运行主流程"""
        try:
            self.logger.info("开始执行自动投递流程")
            
            # 1. 初始化数据库
            self._init_database()
            
            # 2. 启动浏览器并等待登录
            self._start_browser_and_login()
            
            # 3. 开始爬取和处理职位
            self._process_jobs()
            
            # 4. 生成报告
            self._generate_report()
            
        except KeyboardInterrupt:
            self.logger.info("用户中断程序执行")
            raise
        except Exception as e:
            self.logger.error(f"程序执行出错: {e}")
            raise
        finally:
            # 清理资源
            self._cleanup()
    
    def _init_database(self):
        """初始化数据库"""
        self.logger.info("初始化数据库...")
        self.db_manager.init_database()
        self.logger.info("数据库初始化完成")
    
    def _start_browser_and_login(self):
        """启动浏览器并等待用户登录"""
        self.logger.info("启动浏览器...")
        self.crawler.start_browser()
        
        self.logger.info("等待用户登录...")
        print("\n" + "="*50)
        print("请在浏览器中完成登录操作")
        print("登录完成后，程序将自动检测并继续执行")
        print("="*50 + "\n")
        
        # 等待登录完成
        self.crawler.wait_for_login()
        self.logger.info("登录检测完成，开始自动化流程")
    
    def _process_jobs(self):
        """处理职位信息"""
        self.logger.info("开始处理职位信息...")
        
        page_num = 1
        total_processed = 0
        total_submitted = 0
        
        while True:
            self.logger.info(f"处理第 {page_num} 页...")
            
            # 获取当前页的职位列表
            job_links = self.crawler.get_job_links()
            
            if not job_links:
                self.logger.info("没有找到更多职位，结束处理")
                break
            
            # 处理每个职位
            for i, job_link in enumerate(job_links, 1):
                try:
                    self.logger.info(f"处理第 {page_num} 页第 {i} 个职位...")
                    
                    # 检查是否已经处理过
                    job_id = self.adapter.extract_job_id(job_link)
                    if self.db_manager.job_exists(job_id):
                        self.logger.info(f"职位 {job_id} 已存在，跳过")
                        continue
                    
                    # 点击进入职位详情页
                    job_info = self.crawler.get_job_details(job_link)
                    
                    if not job_info:
                        self.logger.warning("无法获取职位信息，跳过")
                        continue
                    
                    # AI分析职位
                    analyzed_job = self.analyzer.analyze_job(job_info)
                    
                    # 计算匹配度
                    match_result = self.matcher.calculate_match(analyzed_job)
                    
                    # 决定是否投递
                    should_submit = self._should_submit(match_result['overall_score'])
                    
                    # 保存职位信息
                    job_record = {
                        'job_id': job_id,
                        'title': job_info.get('title', ''),
                        'company': job_info.get('company', ''),
                        'url': job_link,
                        'match_score': match_result['overall_score'],
                        'website': self.website,
                        'application_status': 'pending'
                    }
                    
                    if should_submit and not self.dry_run:
                        # 执行投递
                        success = self.submitter.submit_application()
                        if success:
                            job_record['application_status'] = 'submitted'
                            job_record['submitted_at'] = time.time()
                            total_submitted += 1
                            self.logger.info(f"投递成功: {job_info.get('title', '')}")
                        else:
                            job_record['application_status'] = 'failed'
                            self.logger.warning(f"投递失败: {job_info.get('title', '')}")
                    elif should_submit and self.dry_run:
                        job_record['application_status'] = 'would_submit'
                        self.logger.info(f"试运行模式，将会投递: {job_info.get('title', '')}")
                    else:
                        job_record['application_status'] = 'skipped'
                        self.logger.info(f"匹配度不足，跳过: {job_info.get('title', '')}")
                    
                    # 保存到数据库
                    self.db_manager.save_job(job_record)
                    total_processed += 1
                    
                    # 随机延迟
                    self.crawler.random_delay()
                    
                except Exception as e:
                    self.logger.error(f"处理职位时出错: {e}")
                    continue
            
            # 尝试翻页
            if not self.crawler.go_to_next_page():
                self.logger.info("没有下一页，处理完成")
                break
            
            page_num += 1
        
        self.logger.info(f"处理完成，共处理 {total_processed} 个职位，投递 {total_submitted} 个")
    
    def _should_submit(self, match_score: float) -> bool:
        """
        判断是否应该投递
        
        Args:
            match_score: 匹配度分数
            
        Returns:
            是否应该投递
        """
        thresholds = self.config.get('matching', {}).get('thresholds', {})
        auto_submit_threshold = thresholds.get('auto_submit', 0.8)
        
        return match_score >= auto_submit_threshold
    
    def _generate_report(self):
        """生成执行报告"""
        self.logger.info("生成执行报告...")
        
        stats = self.db_manager.get_statistics()
        
        print("\n" + "="*50)
        print("执行报告")
        print("="*50)
        print(f"总处理职位数: {stats.get('total', 0)}")
        print(f"已投递: {stats.get('submitted', 0)}")
        print(f"跳过: {stats.get('skipped', 0)}")
        print(f"失败: {stats.get('failed', 0)}")
        print(f"平均匹配度: {stats.get('avg_match_score', 0):.2f}")
        print("="*50 + "\n")
    
    def _cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'crawler'):
                self.crawler.close()
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")