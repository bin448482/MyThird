"""
LangChain分析工具模块

提供基于真实职位数据的智能分析工具，支持技能需求、薪资分析、趋势分析等功能
"""

from .base_tool import BaseAnalysisTool
from .skill_demand_tool import SkillDemandAnalysisTool
from .salary_analysis_tool import SalaryAnalysisTool
from .trend_analysis_tool import TrendAnalysisTool
# from .competitiveness_tool import CompetitivenessAnalysisTool  # TODO: Implement
# from .location_analysis_tool import LocationAnalysisTool  # TODO: Implement

__all__ = [
    'BaseAnalysisTool',
    'SkillDemandAnalysisTool',
    'SalaryAnalysisTool',
    'TrendAnalysisTool',
    # 'CompetitivenessAnalysisTool',  # TODO: Implement
    # 'LocationAnalysisTool',  # TODO: Implement
    'create_analysis_agent'
]

def create_analysis_agent(coordinator, config):
    """
    创建分析Agent实例
    
    Args:
        coordinator: RAG系统协调器
        config: 配置字典
        
    Returns:
        JobMarketAnalysisAgent实例
    """
    from .agent import JobMarketAnalysisAgent
    return JobMarketAnalysisAgent(coordinator, config)