# 薪资阈值过滤功能实现文档

## 概述

本文档详细描述了在DecisionEngine中实现薪资匹配度阈值过滤功能的完整方案。该功能将确保只有薪资匹配度大于0.3的职位才会被推荐投递。

## 目标

- 实现薪资匹配度硬性阈值检查（≥ 0.3）
- 保持系统架构的统一性和可维护性
- 提供灵活的配置选项和详细的统计监控
- 确保向后兼容性，不影响现有功能

## 架构设计

### 1. 整体架构流程

```
职位匹配结果 → DecisionEngine → 薪资阈值预检查 → 多维度评估 → 最终决策
                                      ↓
                                 薪资不达标直接拒绝
```

### 2. 核心组件

#### 2.1 配置层
- `integration_config.yaml`: 薪资过滤配置
- 支持多层次阈值设置
- 动态调整策略配置

#### 2.2 决策引擎增强
- `DecisionEngine`: 增加薪资阈值检查逻辑
- 薪资增强处理逻辑
- 统计信息收集

#### 2.3 监控统计
- 薪资过滤效果统计
- 拒绝率分析
- 薪资分布监控

## 详细实现方案

### 第一阶段：配置文件修改

#### 1.1 修改 integration_config.yaml

在 `integration_system.decision_engine` 部分添加薪资过滤配置：

```yaml
integration_system:
  decision_engine:
    # 现有配置保持不变...
    
    # 新增：薪资阈值过滤配置
    salary_filters:
      enabled: true                    # 启用薪资过滤
      min_salary_match_score: 0.3      # 最低薪资匹配度阈值
      strict_mode: true                # 严格模式：低于阈值直接拒绝
      fallback_strategy: "reject"      # 备选策略：reject/lower_priority
      
      # 分级阈值策略（可选）
      tiered_thresholds:
        enabled: false
        senior_positions:
          min_score: 0.5
          keywords: ["高级", "资深", "专家", "架构师", "总监"]
        regular_positions:
          min_score: 0.3
          keywords: ["工程师", "开发", "分析师"]
        entry_level:
          min_score: 0.2
          keywords: ["初级", "助理", "实习"]
    
    # 增强的薪资评估配置
    salary_enhancement:
      enabled: true
      thresholds:
        excellent: 0.8    # 薪资匹配优秀
        good: 0.6         # 薪资匹配良好  
        acceptable: 0.3   # 薪资匹配可接受（最低投递线）
        poor: 0.0         # 薪资匹配较差
      
      # 薪资权重动态调整
      dynamic_weight:
        enabled: false              # 暂时禁用，保持现有权重
        base_weight: 0.2
        boost_factor: 1.5
        penalty_factor: 0.5
```

### 第二阶段：DecisionEngine 增强

#### 2.1 创建薪资过滤器类

新建文件：`src/integration/salary_filter.py`

```python
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
        salary_filters = config.get('decision_engine', {}).get('salary_filters', {})
        salary_enhancement = config.get('decision_engine', {}).get('salary_enhancement', {})
        
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
```

#### 2.2 修改 DecisionEngine

修改 `src/integration/decision_engine.py`：

```python
# 在文件顶部添加导入
from .salary_filter import SalaryFilter, SalaryFilterResult

class DecisionEngine:
    """智能决策引擎 - 基于多维度评分的投递决策"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.decision_config = config.get('decision_engine', {})
        self.learning_enabled = self.decision_config.get('enable_learning', True)
        
        # 初始化薪资过滤器
        self.salary_filter = SalaryFilter(config.get('integration_system', {}))
        
        # 现有代码保持不变...
        self.decision_history = []
        self.feedback_data = []
        self.company_cache = {}
        self.location_cache = {}
        self.stats = {
            'total_decisions_made': 0,
            'total_submissions_recommended': 0,
            'average_decision_score': 0,
            'decision_distribution': {level.value: 0 for level in DecisionLevel},
            'success_rate_by_score': {},
            'company_success_rates': {},
            'salary_filter_stats': {}  # 新增薪资过滤统计
        }
    
    async def _evaluate_single_match(self, match: Dict, criteria: DecisionCriteria) -> JobDecision:
        """增强的单个匹配评估 - 增加薪资阈值检查"""
        
        # 1. 薪资阈值预检查
        salary_result, salary_info = self.salary_filter.evaluate_salary(match)
        
        if salary_result == SalaryFilterResult.REJECT:
            return self._create_salary_rejected_decision(match, salary_info)
        
        # 2. 继续原有的多维度评估流程
        job_id = match.get('job_id', '')
        job_title = match.get('job_title', '')
        company = match.get('company', '')
        location = match.get('location', '')
        
        # 多维度评分
        dimension_scores = await self._calculate_dimension_scores(match, criteria)
        
        # 计算最终分数
        final_score = self._calculate_weighted_score(dimension_scores, criteria.weights)
        
        # 决策逻辑
        decision_level, should_submit = self._make_decision(final_score, criteria)
        
        # 确定投递优先级
        submission_priority = self._determine_priority(final_score, decision_level)
        
        # 生成决策理由
        reasoning = self._generate_decision_reasoning(dimension_scores, final_score, decision_level)
        
        # 评估成功率
        estimated_success_rate = self._estimate_success_rate(match, dimension_scores)
        
        # 识别风险因素和机会
        risk_factors = self._identify_risk_factors(match, dimension_scores)
        opportunities = self._identify_opportunities(match, dimension_scores)
        
        # 创建基础决策
        decision = JobDecision(
            job_id=job_id,
            job_title=job_title,
            company=company,
            location=location,
            final_score=final_score,
            dimension_scores=dimension_scores,
            should_submit=should_submit,
            submission_priority=submission_priority,
            decision_level=decision_level,
            decision_reasoning=reasoning,
            estimated_success_rate=estimated_success_rate,
            risk_factors=risk_factors,
            opportunities=opportunities,
            metadata={
                'match_data': match,
                'evaluation_time': datetime.now().isoformat()
            }
        )
        
        # 3. 应用薪资增强逻辑
        if salary_result == SalaryFilterResult.ENHANCE:
            decision = self._apply_salary_enhancement(decision, salary_info)
        
        return decision
    
    def _create_salary_rejected_decision(self, match: Dict, salary_info: Dict) -> JobDecision:
        """创建薪资不符合要求的拒绝决策"""
        return JobDecision(
            job_id=match.get('job_id', ''),
            job_title=match.get('job_title', ''),
            company=match.get('company', ''),
            location=match.get('location', ''),
            final_score=0.0,  # 直接设为0分
            dimension_scores={'salary_match': salary_info.get('salary_match_score', 0)},
            should_submit=False,
            submission_priority=SubmissionPriority.LOW,
            decision_level=DecisionLevel.REJECT,
            decision_reasoning=[
                f"薪资匹配度过低 ({salary_info.get('salary_match_score', 0):.2f} < {salary_info.get('required_threshold', 0.3)})",
                "不符合最低薪资要求，自动拒绝"
            ],
            estimated_success_rate=0.0,
            risk_factors=["薪资水平严重不符合期望"],
            opportunities=[],
            metadata={
                'rejection_reason': 'salary_threshold',
                'salary_filter_info': salary_info,
                'evaluation_time': datetime.now().isoformat()
            }
        )
    
    def _apply_salary_enhancement(self, decision: JobDecision, salary_info: Dict) -> JobDecision:
        """应用薪资增强逻辑"""
        enhancement_type = salary_info.get('enhancement_type')
        
        if enhancement_type == 'excellent_salary' and salary_info.get('priority_boost'):
            # 优秀薪资匹配度，提升优先级
            if decision.submission_priority != SubmissionPriority.URGENT:
                original_priority = decision.submission_priority.value
                decision.submission_priority = SubmissionPriority.HIGH
                decision.decision_reasoning.append(
                    f"薪资匹配度优秀，优先级从 {original_priority} 提升至 {decision.submission_priority.value}"
                )
        
        # 添加薪资相关的决策理由
        decision.decision_reasoning.append(salary_info.get('reasoning', ''))
        
        # 更新元数据
        decision.metadata['salary_enhancement'] = salary_info
        
        return decision
    
    def get_decision_stats(self) -> Dict[str, Any]:
        """获取决策统计信息（增强版）"""
        base_stats = {
            'stats': self.stats.copy(),
            'history_count': len(self.decision_history),
            'cache_sizes': {
                'company_cache': len(self.company_cache),
                'location_cache': len(self.location_cache)
            },
            'learning_enabled': self.learning_enabled
        }
        
        # 添加薪资过滤统计
        base_stats['salary_filter_stats'] = self.salary_filter.get_stats()
        
        return base_stats
```

### 第三阶段：数据库查询优化

#### 3.1 修改数据库操作

修改 `src/database/operations.py` 中的 `get_unprocessed_matches` 方法，添加薪资过滤支持：

```python
def get_unprocessed_matches(self, limit: int = 100, min_salary_score: float = None) -> List[Dict[str, Any]]:
    """
    获取未处理的匹配结果（支持薪资过滤）
    
    Args:
        limit: 限制数量
        min_salary_score: 最低薪资匹配度（可选）
        
    Returns:
        未处理的匹配结果列表
    """
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            base_sql = """
                SELECT * FROM resume_matches
                WHERE processed = 0 OR processed IS NULL
            """
            
            params = []
            
            # 添加薪资过滤条件
            if min_salary_score is not None:
                base_sql += " AND (salary_match_score >= ? OR salary_match_score IS NULL)"
                params.append(min_salary_score)
            
            base_sql += " ORDER BY match_score DESC, created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(base_sql, params)
            
            matches = []
            for row in cursor.fetchall():
                matches.append(dict(row))
            
            return matches
            
    except Exception as e:
        self.logger.error(f"获取未处理匹配结果失败: {e}")
        return []
```

### 第四阶段：集成测试

#### 4.1 创建测试脚本

新建文件：`test_salary_filter.py`

```python
#!/usr/bin/env python3
"""
薪资过滤功能测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integration.decision_engine import DecisionEngine
from src.integration.salary_filter import SalaryFilter
import yaml

def load_test_config():
    """加载测试配置"""
    return {
        'integration_system': {
            'decision_engine': {
                'salary_filters': {
                    'enabled': True,
                    'min_salary_match_score': 0.3,
                    'strict_mode': True,
                    'fallback_strategy': 'reject'
                },
                'salary_enhancement': {
                    'enabled': True,
                    'thresholds': {
                        'excellent': 0.8,
                        'good': 0.6,
                        'acceptable': 0.3,
                        'poor': 0.0
                    }
                }
            }
        }
    }

def create_test_matches():
    """创建测试匹配数据"""
    return [
        {
            'job_id': 'test_001',
            'job_title': '高级Python开发工程师',
            'company': '测试公司A',
            'location': '北京',
            'salary_match_score': 0.85,  # 应该通过并增强
            'overall_score': 0.75
        },
        {
            'job_id': 'test_002', 
            'job_title': 'Python开发工程师',
            'company': '测试公司B',
            'location': '上海',
            'salary_match_score': 0.45,  # 应该通过
            'overall_score': 0.70
        },
        {
            'job_id': 'test_003',
            'job_title': '初级开发工程师', 
            'company': '测试公司C',
            'location': '深圳',
            'salary_match_score': 0.25,  # 应该被拒绝
            'overall_score': 0.80
        },
        {
            'job_id': 'test_004',
            'job_title': '数据分析师',
            'company': '测试公司D', 
            'location': '杭州',
            'salary_match_score': 0.65,  # 应该通过并标记为良好
            'overall_score': 0.68
        }
    ]

async def test_salary_filter():
    """测试薪资过滤功能"""
    print("🧪 开始薪资过滤功能测试")
    
    # 加载配置
    config = load_test_config()
    
    # 创建决策引擎
    decision_engine = DecisionEngine(config)
    
    # 创建测试数据
    test_matches = create_test_matches()
    
    print(f"\n📊 测试数据: {len(test_matches)} 个职位匹配")
    
    # 模拟决策过程
    decisions = []
    for match in test_matches:
        # 这里简化测试，直接调用薪资过滤器
        salary_result, salary_info = decision_engine.salary_filter.evaluate_salary(match)
        
        print(f"\n职位: {match['job_title']}")
        print(f"薪资匹配度: {match['salary_match_score']:.2f}")
        print(f"过滤结果: {salary_result.value}")
        
        if salary_info:
            print(f"详细信息: {salary_info}")
    
    # 输出统计信息
    stats = decision_engine.salary_filter.get_stats()
    print(f"\n📈 薪资过滤统计:")
    print(f"总评估数: {stats['total_evaluated']}")
    print(f"拒绝数: {stats['salary_rejected']}")
    print(f"拒绝率: {stats['rejection_rate']:.2%}")
    print(f"薪资分布: {stats['salary_distribution']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_salary_filter())
```

## 实施计划

### 阶段1: 基础实现（第1-2天）
1. 修改配置文件
2. 实现薪资过滤器类
3. 修改DecisionEngine核心逻辑

### 阶段2: 集成测试（第3天）
1. 创建测试脚本
2. 验证过滤逻辑正确性
3. 性能测试

### 阶段3: 优化部署（第4天）
1. 数据库查询优化
2. 监控统计完善
3. 文档更新

## 预期效果

1. **精确过滤**: 薪资匹配度 < 0.3 的职位将被自动拒绝
2. **统计监控**: 提供详细的过滤效果统计
3. **灵活配置**: 支持不同职位类型的差异化阈值
4. **性能优化**: 在决策阶段早期过滤，提高整体效率

## 风险评估

1. **配置错误**: 阈值设置过高可能导致过度过滤
2. **数据质量**: 薪资匹配度计算准确性影响过滤效果
3. **性能影响**: 额外的过滤逻辑可能轻微影响处理速度

## 回滚方案

如果出现问题，可以通过以下方式快速回滚：
1. 设置 `salary_filters.enabled: false` 禁用功能
2. 恢复原始配置文件
3. 重启系统恢复原有逻辑

## 后续优化方向

1. 机器学习优化阈值
2. 动态薪资权重调整
3. 个性化薪资偏好设置
4. A/B测试不同阈值效果