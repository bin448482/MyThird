"""
分析工具基类

提供所有分析工具的通用功能和接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


class BaseAnalysisTool(BaseTool, ABC):
    """分析工具基类"""
    
    # 使用类变量存储管理器实例
    _db_manager = None
    _vector_manager = None
    
    def __init__(self, db_manager, vector_manager=None, **kwargs):
        """
        初始化分析工具
        
        Args:
            db_manager: 数据库管理器实例
            vector_manager: 向量数据库管理器实例（可选）
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        # 使用类变量存储管理器
        BaseAnalysisTool._db_manager = db_manager
        BaseAnalysisTool._vector_manager = vector_manager
    
    @property
    def db_manager(self):
        """获取数据库管理器"""
        return BaseAnalysisTool._db_manager
    
    @property
    def vector_manager(self):
        """获取向量数据库管理器"""
        return BaseAnalysisTool._vector_manager
    
    @property
    def logger(self):
        """获取日志记录器"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger
    
    @abstractmethod
    def _run(self, **kwargs) -> str:
        """
        执行分析逻辑
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            分析结果的文本描述
        """
        pass
    
    def _format_result(self, result: Dict[str, Any]) -> str:
        """
        格式化结果为LLM可理解的文本
        
        Args:
            result: 分析结果字典
            
        Returns:
            格式化后的文本
        """
        if not result:
            return "未找到相关数据"
        
        # 基础格式化逻辑
        formatted_lines = []
        
        # 添加标题
        if 'title' in result:
            formatted_lines.append(f"**{result['title']}**\n")
        
        # 添加摘要
        if 'summary' in result:
            # 检查摘要中是否包含占位符
            summary = result['summary']
            if 'XX' in summary or '[' in summary and ']' in summary:
                formatted_lines.append(f"📊 **分析摘要**: 数据处理异常，包含占位符，请联系技术人员修复\n")
            else:
                formatted_lines.append(f"📊 **分析摘要**: {summary}\n")
        
        # 添加主要数据
        if 'data' in result and isinstance(result['data'], list):
            formatted_lines.append("📈 **详细数据**:")
            for i, item in enumerate(result['data'][:10], 1):  # 限制显示前10项
                if isinstance(item, dict):
                    # 格式化字典项
                    if 'name' in item and 'value' in item:
                        # 检查值中是否包含占位符
                        value = str(item['value'])
                        if 'XX' in value or '[' in value and ']' in value:
                            formatted_lines.append(f"  {i}. **{item['name']}**: 数据异常（包含占位符）")
                        else:
                            formatted_lines.append(f"  {i}. **{item['name']}**: {value}")
                        if 'percentage' in item:
                            formatted_lines.append(f" ({item['percentage']:.1f}%)")
                        if 'description' in item:
                            desc = item['description']
                            if 'XX' in desc or '[' in desc and ']' in desc:
                                formatted_lines.append(f" - 描述数据异常（包含占位符）")
                            else:
                                formatted_lines.append(f" - {desc}")
                else:
                    formatted_lines.append(f"  {i}. {item}")
            formatted_lines.append("")
        
        # 添加统计信息
        if 'statistics' in result:
            stats = result['statistics']
            formatted_lines.append("📊 **统计信息**:")
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    if isinstance(value, float):
                        formatted_lines.append(f"  • {key}: {value:.2f}")
                    else:
                        formatted_lines.append(f"  • {key}: {value:,}")
                else:
                    formatted_lines.append(f"  • {key}: {value}")
            formatted_lines.append("")
        
        # 添加洞察和建议
        if 'insights' in result and result['insights']:
            formatted_lines.append("💡 **关键洞察**:")
            for insight in result['insights']:
                formatted_lines.append(f"  • {insight}")
            formatted_lines.append("")
        
        if 'recommendations' in result and result['recommendations']:
            formatted_lines.append("🎯 **建议**:")
            for recommendation in result['recommendations']:
                formatted_lines.append(f"  • {recommendation}")
            formatted_lines.append("")
        
        # 添加数据来源说明
        if 'data_source' in result:
            formatted_lines.append(f"📋 **数据来源**: {result['data_source']}")
        
        return "\n".join(formatted_lines)
    
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行数据库查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        try:
            # 检查db_manager是否是DatabaseJobReader类型
            if hasattr(self.db_manager, 'db_manager'):
                # 如果是DatabaseJobReader，使用其内部的db_manager
                db_manager = self.db_manager.db_manager
            else:
                # 否则直接使用db_manager
                db_manager = self.db_manager
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # 获取列名
                columns = [description[0] for description in cursor.description]
                
                # 转换为字典列表
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
                
        except Exception as e:
            self.logger.error(f"数据库查询失败: {e}")
            return []
    
    def _get_job_count(self) -> int:
        """获取总职位数量"""
        try:
            # 检查db_manager是否是DatabaseJobReader类型
            if hasattr(self.db_manager, 'db_manager'):
                # 如果是DatabaseJobReader，使用其内部的db_manager
                db_manager = self.db_manager.db_manager
            else:
                # 否则直接使用db_manager
                db_manager = self.db_manager
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM jobs")
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            self.logger.error(f"获取职位总数失败: {e}")
            return 0
    
    def _standardize_skill_name(self, skill: str) -> str:
        """
        标准化技能名称
        
        Args:
            skill: 原始技能名称
            
        Returns:
            标准化后的技能名称
        """
        if not skill:
            return ""
        
        # 转换为小写并去除空格
        skill = skill.lower().strip()
        
        # 技能名称映射表
        skill_mappings = {
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'golang': 'go',
            'nodejs': 'node.js',
            'reactjs': 'react',
            'vuejs': 'vue.js',
            'angularjs': 'angular',
            'mysql': 'mysql',
            'postgresql': 'postgresql',
            'mongodb': 'mongodb',
            'redis': 'redis',
            'elasticsearch': 'elasticsearch',
            'docker': 'docker',
            'kubernetes': 'kubernetes',
            'k8s': 'kubernetes',
            'aws': 'aws',
            'azure': 'azure',
            'gcp': 'google cloud',
            'ml': 'machine learning',
            'ai': 'artificial intelligence',
            'dl': 'deep learning'
        }
        
        return skill_mappings.get(skill, skill)
    
    def _parse_salary_range(self, salary_text: str) -> Dict[str, int]:
        """
        解析薪资范围文本
        
        Args:
            salary_text: 薪资文本，如"15-25k"、"20万-30万"等
            
        Returns:
            包含min、max、avg的字典
        """
        if not salary_text:
            return {'min': 0, 'max': 0, 'avg': 0}
        
        import re
        
        # 薪资解析模式
        patterns = [
            r'(\d+)-(\d+)k',           # 15-25k
            r'(\d+)k-(\d+)k',          # 15k-25k  
            r'(\d+)-(\d+)万',          # 15-25万
            r'(\d+)万-(\d+)万',        # 15万-25万
            r'(\d+)-(\d+)',            # 15000-25000
            r'(\d+)k',                 # 25k (单个值)
            r'(\d+)万',                # 25万 (单个值)
        ]
        
        salary_lower = salary_text.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, salary_lower)
            if match:
                if len(match.groups()) == 2:
                    # 范围值
                    min_val, max_val = match.groups()
                    min_val, max_val = int(min_val), int(max_val)
                    
                    # 根据模式调整单位
                    if 'k' in pattern:
                        min_val *= 1000
                        max_val *= 1000
                    elif '万' in pattern:
                        min_val *= 10000
                        max_val *= 10000
                    
                    avg_val = (min_val + max_val) // 2
                    return {'min': min_val, 'max': max_val, 'avg': avg_val}
                else:
                    # 单个值
                    val = int(match.groups()[0])
                    if 'k' in pattern:
                        val *= 1000
                    elif '万' in pattern:
                        val *= 10000
                    
                    return {'min': val, 'max': val, 'avg': val}
        
        # 如果无法解析，返回0
        return {'min': 0, 'max': 0, 'avg': 0}
    
    def _format_number(self, number: int) -> str:
        """格式化数字显示"""
        if number >= 10000:
            return f"{number:,}"
        return str(number)
    
    def _format_percentage(self, value: float, total: float) -> float:
        """计算并格式化百分比"""
        if total == 0:
            return 0.0
        return round((value / total) * 100, 1)