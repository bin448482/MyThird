"""
薪资过滤器模块
处理薪资匹配度阈值检查和增强逻辑
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SalaryFilterResult(Enum):
    """薪资过滤结果"""
    PASS = "pass"           # 通过过滤
    REJECT = "reject"       # 拒绝
    ENHANCE = "enhance"     # 需要增强处理

@dataclass
class SalaryFilterConfig:
    """薪资过滤配置"""
    enabled: bool = True
    min_salary_match_score: float = 0.3
    strict_mode: bool = True
    fallback_strategy: str = "reject"
    
    # 薪资等级阈值
    excellent_threshold: float = 0.8
    good_threshold: float = 0.6
    acceptable_threshold: float = 0.3
    
    # 分级阈值
    tiered_enabled: bool = False
    senior_min_score: float = 0.5
    regular_min_score: float = 0.3
    entry_min_score: float = 0.2

@dataclass
class SalaryFilterStats:
    """薪资过滤统计"""
    total_evaluated: int = 0
    salary_rejected: int = 0
    salary_enhanced: int = 0
    salary_distribution: Dict[str, int] = None
    
    def __post_init__(self):
        if self.salary_distribution is None:
            self.salary_distribution = {
                'excellent': 0,    # >= 0.8
                'good': 0,         # 0.6-0.8
                'acceptable': 0,   # 0.3-0.6
                'poor': 0          # < 0.3
            }
    
    def get_rejection_rate(self) -> float:
        return self.salary_rejected / self.total_evaluated if self.total_evaluated > 0 else 0
    
    def update_distribution(self, salary_score: float):
        """更新薪资分布统计"""
        if salary_score >= 0.8:
            self.salary_distribution['excellent'] += 1
        elif salary_score >= 0.6:
            self.salary_distribution['good'] += 1
        elif salary_score >= 0.3:
            self.salary_distribution['acceptable'] += 1
        else:
            self.salary_distribution['poor'] += 1

class SalaryFilter:
    """薪资过滤器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = self._parse_config(config)
        self.stats = SalaryFilterStats()
        self.logger = logging.getLogger(__name__)
    
    def _parse_config(self, config: Dict[str, Any]) -> SalaryFilterConfig:
        """解析配置"""
        # 从integration_system.decision_engine中读取配置
        decision_engine_config = config.get('integration_system', {}).get('decision_engine', {})
        salary_filters = decision_engine_config.get('salary_filters', {})
        salary_enhancement = decision_engine_config.get('salary_enhancement', {})
        
        return SalaryFilterConfig(
            enabled=salary_filters.get('enabled', True),
            min_salary_match_score=salary_filters.get('min_salary_match_score', 0.3),
            strict_mode=salary_filters.get('strict_mode', True),
            fallback_strategy=salary_filters.get('fallback_strategy', 'reject'),
            
            # 薪资等级阈值
            excellent_threshold=salary_enhancement.get('thresholds', {}).get('excellent', 0.8),
            good_threshold=salary_enhancement.get('thresholds', {}).get('good', 0.6),
            acceptable_threshold=salary_enhancement.get('thresholds', {}).get('acceptable', 0.3),
            
            # 分级阈值
            tiered_enabled=salary_filters.get('tiered_thresholds', {}).get('enabled', False),
            senior_min_score=salary_filters.get('tiered_thresholds', {}).get('senior_positions', {}).get('min_score', 0.5),
            regular_min_score=salary_filters.get('tiered_thresholds', {}).get('regular_positions', {}).get('min_score', 0.3),
            entry_min_score=salary_filters.get('tiered_thresholds', {}).get('entry_level', {}).get('min_score', 0.2)
        )
    
    def evaluate_salary(self, match: Dict[str, Any]) -> tuple[SalaryFilterResult, Dict[str, Any]]:
        """评估薪资匹配度"""
        if not self.config.enabled:
            return SalaryFilterResult.PASS, {}
        
        salary_match_score = match.get('salary_match_score', 0.0)
        job_title = match.get('job_title', '')
        
        # 更新统计
        self.stats.total_evaluated += 1
        self.stats.update_distribution(salary_match_score)
        
        # 确定适用的阈值
        applicable_threshold = self._get_applicable_threshold(job_title)
        
        # 薪资阈值检查
        if salary_match_score < applicable_threshold:
            self.stats.salary_rejected += 1
            self.logger.debug(f"薪资过滤拒绝: {match.get('job_id')} - 分数 {salary_match_score:.3f} < 阈值 {applicable_threshold}")
            
            return SalaryFilterResult.REJECT, {
                'rejection_reason': 'salary_threshold',
                'salary_match_score': salary_match_score,
                'required_threshold': applicable_threshold,
                'job_title': job_title
            }
        
        # 薪资增强检查
        enhancement_info = self._get_enhancement_info(salary_match_score)
        if enhancement_info:
            self.stats.salary_enhanced += 1
            return SalaryFilterResult.ENHANCE, enhancement_info
        
        return SalaryFilterResult.PASS, {}
    
    def _get_applicable_threshold(self, job_title: str) -> float:
        """获取适用的薪资阈值"""
        if not self.config.tiered_enabled:
            return self.config.min_salary_match_score
        
        job_title_lower = job_title.lower()
        
        # 高级职位
        senior_keywords = ["高级", "资深", "专家", "架构师", "总监", "senior", "lead", "principal", "architect"]
        if any(keyword in job_title_lower for keyword in senior_keywords):
            return self.config.senior_min_score
        
        # 入门级职位
        entry_keywords = ["初级", "助理", "实习", "junior", "intern", "assistant"]
        if any(keyword in job_title_lower for keyword in entry_keywords):
            return self.config.entry_min_score
        
        # 普通职位
        return self.config.regular_min_score
    
    def _get_enhancement_info(self, salary_score: float) -> Optional[Dict[str, Any]]:
        """获取薪资增强信息"""
        if salary_score >= self.config.excellent_threshold:
            return {
                'enhancement_type': 'excellent_salary',
                'priority_boost': True,
                'reasoning': f"薪资匹配度优秀 ({salary_score:.2f})"
            }
        elif salary_score >= self.config.good_threshold:
            return {
                'enhancement_type': 'good_salary',
                'priority_boost': False,
                'reasoning': f"薪资匹配度良好 ({salary_score:.2f})"
            }
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_evaluated': self.stats.total_evaluated,
            'salary_rejected': self.stats.salary_rejected,
            'salary_enhanced': self.stats.salary_enhanced,
            'rejection_rate': self.stats.get_rejection_rate(),
            'salary_distribution': self.stats.salary_distribution.copy(),
            'filter_enabled': self.config.enabled,
            'current_threshold': self.config.min_salary_match_score
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = SalaryFilterStats()