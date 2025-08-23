"""
智能决策引擎 (DecisionEngine)
基于多维度评分的智能投递决策
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

class DecisionLevel(Enum):
    """决策级别"""
    REJECT = "reject"
    CONSIDER = "consider"
    RECOMMEND = "recommend"
    PRIORITY = "priority"
    URGENT = "urgent"

class SubmissionPriority(Enum):
    """投递优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class DecisionCriteria:
    """决策标准"""
    submission_threshold: float = 0.7
    priority_threshold: float = 0.8
    urgent_threshold: float = 0.9
    max_daily_submissions: int = 50
    max_submissions_per_company: int = 3
    min_salary_requirement: Optional[int] = None
    preferred_locations: List[str] = field(default_factory=list)
    blacklisted_companies: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=lambda: {
        'match_score': 0.3,
        'company_reputation': 0.2,
        'salary_attractiveness': 0.2,
        'location_preference': 0.1,
        'career_growth_potential': 0.1,
        'application_competition': 0.1
    })

@dataclass
class JobDecision:
    """职位决策结果"""
    job_id: str
    job_title: str
    company: str
    location: str
    final_score: float
    dimension_scores: Dict[str, float]
    should_submit: bool
    submission_priority: SubmissionPriority
    decision_level: DecisionLevel
    decision_reasoning: List[str]
    estimated_success_rate: float
    risk_factors: List[str]
    opportunities: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DecisionResult:
    """决策结果"""
    total_evaluated: int
    recommended_submissions: int
    decisions: List[JobDecision]
    decision_summary: Dict[str, Any]
    global_constraints_applied: List[str]
    decision_time: str
    success: bool = True
    error_message: Optional[str] = None

class DecisionEngine:
    """智能决策引擎 - 基于多维度评分的投递决策"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.decision_config = config.get('decision_engine', {})
        self.learning_enabled = self.decision_config.get('enable_learning', True)
        
        # 决策历史
        self.decision_history = []
        self.feedback_data = []
        
        # 公司信息缓存
        self.company_cache = {}
        self.location_cache = {}
        
        # 统计信息
        self.stats = {
            'total_decisions_made': 0,
            'total_submissions_recommended': 0,
            'average_decision_score': 0,
            'decision_distribution': {level.value: 0 for level in DecisionLevel},
            'success_rate_by_score': {},
            'company_success_rates': {}
        }
    
    async def make_submission_decisions(self, matching_result: Dict, decision_criteria: Dict[str, Any] = None) -> DecisionResult:
        """制定投递决策"""
        try:
            start_time = datetime.now()
            
            # 解析决策标准
            criteria = self._parse_decision_criteria(decision_criteria or {})
            
            # 获取匹配结果
            matches = matching_result.get('matches', [])
            if not matches:
                return DecisionResult(
                    total_evaluated=0,
                    recommended_submissions=0,
                    decisions=[],
                    decision_summary={},
                    global_constraints_applied=[],
                    decision_time=start_time.isoformat(),
                    success=False,
                    error_message="No matches to evaluate"
                )
            
            logger.info(f"开始评估 {len(matches)} 个职位匹配")
            
            # 评估每个匹配
            decisions = []
            for match in matches:
                decision = await self._evaluate_single_match(match, criteria)
                decisions.append(decision)
            
            # 应用全局约束
            final_decisions, constraints_applied = self._apply_global_constraints(decisions, criteria)
            
            # 生成决策摘要
            decision_summary = self._generate_decision_summary(final_decisions)
            
            # 更新统计信息
            self._update_stats(final_decisions)
            
            # 保存决策历史
            if self.learning_enabled:
                self._save_decision_history(final_decisions, criteria)
            
            result = DecisionResult(
                total_evaluated=len(matches),
                recommended_submissions=len([d for d in final_decisions if d.should_submit]),
                decisions=final_decisions,
                decision_summary=decision_summary,
                global_constraints_applied=constraints_applied,
                decision_time=start_time.isoformat(),
                success=True
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"决策完成，耗时 {execution_time:.2f} 秒，推荐投递 {result.recommended_submissions} 个职位")
            
            return result
            
        except Exception as e:
            logger.error(f"决策制定失败: {e}")
            return DecisionResult(
                total_evaluated=0,
                recommended_submissions=0,
                decisions=[],
                decision_summary={},
                global_constraints_applied=[],
                decision_time=datetime.now().isoformat(),
                success=False,
                error_message=str(e)
            )
    
    async def _evaluate_single_match(self, match: Dict, criteria: DecisionCriteria) -> JobDecision:
        """评估单个匹配结果"""
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
        
        return JobDecision(
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
    
    async def _calculate_dimension_scores(self, match: Dict, criteria: DecisionCriteria) -> Dict[str, float]:
        """计算各维度分数"""
        scores = {}
        
        # 1. 匹配分数 (基础分数)
        scores['match_score'] = match.get('overall_score', 0)
        
        # 2. 公司声誉评分
        scores['company_reputation'] = await self._evaluate_company_reputation(match.get('company', ''))
        
        # 3. 薪资吸引力评分
        scores['salary_attractiveness'] = self._evaluate_salary_attractiveness(
            match.get('salary_range', {}), criteria.min_salary_requirement
        )
        
        # 4. 地理位置偏好评分
        scores['location_preference'] = self._evaluate_location_preference(
            match.get('location', ''), criteria.preferred_locations
        )
        
        # 5. 职业发展潜力评分
        scores['career_growth_potential'] = self._evaluate_career_growth(match)
        
        # 6. 申请竞争程度评分 (越低越好，所以取反)
        competition_level = await self._evaluate_competition_level(match)
        scores['application_competition'] = 1.0 - competition_level
        
        return scores
    
    async def _evaluate_company_reputation(self, company: str) -> float:
        """评估公司声誉"""
        if not company:
            return 0.5
        
        # 检查缓存
        if company in self.company_cache:
            return self.company_cache[company]
        
        # 基于公司名称的简单评分逻辑
        score = 0.5  # 默认分数
        
        # 知名大公司
        famous_companies = ['腾讯', '阿里巴巴', '百度', '字节跳动', '美团', '京东', '华为', '小米']
        if any(famous in company for famous in famous_companies):
            score = 0.9
        
        # 外企
        foreign_indicators = ['有限公司', 'Ltd', 'Inc', 'Corp', 'GmbH']
        if any(indicator in company for indicator in foreign_indicators):
            score = max(score, 0.7)
        
        # 创业公司指标
        startup_indicators = ['科技', '信息', '网络', '软件', '数据']
        if any(indicator in company for indicator in startup_indicators):
            score = max(score, 0.6)
        
        # 缓存结果
        self.company_cache[company] = score
        return score
    
    def _evaluate_salary_attractiveness(self, salary_range: Dict, min_requirement: Optional[int]) -> float:
        """评估薪资吸引力"""
        if not salary_range:
            return 0.5
        
        min_salary = salary_range.get('min', 0)
        max_salary = salary_range.get('max', 0)
        
        if min_salary == 0 and max_salary == 0:
            return 0.5
        
        # 计算平均薪资
        avg_salary = (min_salary + max_salary) / 2 if max_salary > 0 else min_salary
        
        # 基于最低要求评分
        if min_requirement:
            if avg_salary >= min_requirement * 1.5:
                return 1.0
            elif avg_salary >= min_requirement * 1.2:
                return 0.8
            elif avg_salary >= min_requirement:
                return 0.6
            else:
                return 0.3
        
        # 基于薪资范围评分
        if avg_salary >= 50000:  # 50K+
            return 1.0
        elif avg_salary >= 30000:  # 30K+
            return 0.8
        elif avg_salary >= 20000:  # 20K+
            return 0.6
        elif avg_salary >= 10000:  # 10K+
            return 0.4
        else:
            return 0.2
    
    def _evaluate_location_preference(self, location: str, preferred_locations: List[str]) -> float:
        """评估地理位置偏好"""
        if not location:
            return 0.5
        
        if not preferred_locations:
            return 0.7  # 没有偏好时给中等分数
        
        # 检查是否在偏好列表中
        for preferred in preferred_locations:
            if preferred in location:
                return 1.0
        
        # 一线城市加分
        tier1_cities = ['北京', '上海', '广州', '深圳']
        if any(city in location for city in tier1_cities):
            return 0.8
        
        # 新一线城市
        new_tier1_cities = ['杭州', '成都', '武汉', '重庆', '南京', '天津', '苏州', '西安']
        if any(city in location for city in new_tier1_cities):
            return 0.6
        
        return 0.4
    
    def _evaluate_career_growth(self, match: Dict) -> float:
        """评估职业发展潜力"""
        score = 0.5
        
        job_title = match.get('job_title', '').lower()
        job_description = match.get('job_description', '').lower()
        
        # 高级职位加分
        senior_keywords = ['高级', '资深', '专家', '架构师', '技术总监', 'senior', 'lead', 'principal']
        if any(keyword in job_title for keyword in senior_keywords):
            score += 0.3
        
        # 管理职位加分
        management_keywords = ['经理', '总监', '主管', 'manager', 'director', 'head']
        if any(keyword in job_title for keyword in management_keywords):
            score += 0.2
        
        # 新技术相关加分
        tech_keywords = ['ai', '人工智能', '机器学习', '深度学习', '大数据', '云计算', '区块链']
        if any(keyword in job_description for keyword in tech_keywords):
            score += 0.2
        
        return min(score, 1.0)
    
    async def _evaluate_competition_level(self, match: Dict) -> float:
        """评估申请竞争程度"""
        # 基于职位热度的简单评估
        score = 0.5
        
        job_title = match.get('job_title', '').lower()
        company = match.get('company', '')
        
        # 热门职位竞争激烈
        popular_positions = ['产品经理', '数据分析', '算法工程师', 'ai工程师']
        if any(pos in job_title for pos in popular_positions):
            score += 0.3
        
        # 知名公司竞争激烈
        if await self._evaluate_company_reputation(company) > 0.8:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_weighted_score(self, dimension_scores: Dict[str, float], weights: Dict[str, float]) -> float:
        """计算加权总分"""
        total_score = 0
        total_weight = 0
        
        for dimension, score in dimension_scores.items():
            weight = weights.get(dimension, 0.1)
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def _make_decision(self, final_score: float, criteria: DecisionCriteria) -> Tuple[DecisionLevel, bool]:
        """做出决策"""
        if final_score >= criteria.urgent_threshold:
            return DecisionLevel.URGENT, True
        elif final_score >= criteria.priority_threshold:
            return DecisionLevel.PRIORITY, True
        elif final_score >= criteria.submission_threshold:
            return DecisionLevel.RECOMMEND, True
        elif final_score >= 0.5:
            return DecisionLevel.CONSIDER, False
        else:
            return DecisionLevel.REJECT, False
    
    def _determine_priority(self, final_score: float, decision_level: DecisionLevel) -> SubmissionPriority:
        """确定投递优先级"""
        if decision_level == DecisionLevel.URGENT:
            return SubmissionPriority.URGENT
        elif decision_level == DecisionLevel.PRIORITY:
            return SubmissionPriority.HIGH
        elif decision_level == DecisionLevel.RECOMMEND:
            return SubmissionPriority.MEDIUM
        else:
            return SubmissionPriority.LOW
    
    def _generate_decision_reasoning(self, dimension_scores: Dict[str, float], 
                                   final_score: float, decision_level: DecisionLevel) -> List[str]:
        """生成决策理由"""
        reasoning = []
        
        # 基于最终分数
        if final_score >= 0.8:
            reasoning.append(f"综合评分优秀 ({final_score:.2f})")
        elif final_score >= 0.6:
            reasoning.append(f"综合评分良好 ({final_score:.2f})")
        else:
            reasoning.append(f"综合评分一般 ({final_score:.2f})")
        
        # 基于各维度分数
        for dimension, score in dimension_scores.items():
            if score >= 0.8:
                reasoning.append(f"{dimension} 表现优秀 ({score:.2f})")
            elif score <= 0.3:
                reasoning.append(f"{dimension} 需要关注 ({score:.2f})")
        
        # 基于决策级别
        if decision_level == DecisionLevel.URGENT:
            reasoning.append("强烈推荐立即申请")
        elif decision_level == DecisionLevel.PRIORITY:
            reasoning.append("优先考虑申请")
        elif decision_level == DecisionLevel.RECOMMEND:
            reasoning.append("建议申请")
        elif decision_level == DecisionLevel.CONSIDER:
            reasoning.append("可以考虑，但不是优先选择")
        else:
            reasoning.append("不建议申请")
        
        return reasoning
    
    def _estimate_success_rate(self, match: Dict, dimension_scores: Dict[str, float]) -> float:
        """估算申请成功率"""
        # 基于历史数据和当前评分估算
        base_rate = 0.3  # 基础成功率
        
        # 匹配分数影响
        match_score = dimension_scores.get('match_score', 0)
        base_rate += match_score * 0.4
        
        # 公司声誉影响（知名公司成功率可能更低）
        company_score = dimension_scores.get('company_reputation', 0)
        if company_score > 0.8:
            base_rate -= 0.1  # 知名公司竞争激烈
        
        # 竞争程度影响
        competition_score = dimension_scores.get('application_competition', 0)
        base_rate += competition_score * 0.2
        
        return max(0.1, min(0.9, base_rate))
    
    def _identify_risk_factors(self, match: Dict, dimension_scores: Dict[str, float]) -> List[str]:
        """识别风险因素"""
        risks = []
        
        if dimension_scores.get('salary_attractiveness', 0) < 0.4:
            risks.append("薪资水平可能不符合期望")
        
        if dimension_scores.get('location_preference', 0) < 0.4:
            risks.append("工作地点不在偏好范围内")
        
        if dimension_scores.get('application_competition', 0) < 0.3:
            risks.append("申请竞争可能较为激烈")
        
        if dimension_scores.get('company_reputation', 0) < 0.4:
            risks.append("公司知名度相对较低")
        
        return risks
    
    def _identify_opportunities(self, match: Dict, dimension_scores: Dict[str, float]) -> List[str]:
        """识别机会点"""
        opportunities = []
        
        if dimension_scores.get('career_growth_potential', 0) > 0.7:
            opportunities.append("职业发展前景良好")
        
        if dimension_scores.get('company_reputation', 0) > 0.8:
            opportunities.append("知名公司，品牌价值高")
        
        if dimension_scores.get('match_score', 0) > 0.8:
            opportunities.append("技能匹配度很高")
        
        if dimension_scores.get('salary_attractiveness', 0) > 0.8:
            opportunities.append("薪资待遇具有吸引力")
        
        return opportunities
    
    def _apply_global_constraints(self, decisions: List[JobDecision], 
                                criteria: DecisionCriteria) -> Tuple[List[JobDecision], List[str]]:
        """应用全局约束"""
        constraints_applied = []
        final_decisions = decisions.copy()
        
        # 1. 每日投递限制
        submission_candidates = [d for d in final_decisions if d.should_submit]
        if len(submission_candidates) > criteria.max_daily_submissions:
            # 按分数排序，保留前N个
            submission_candidates.sort(key=lambda x: x.final_score, reverse=True)
            
            for i, decision in enumerate(final_decisions):
                if decision.should_submit and decision not in submission_candidates[:criteria.max_daily_submissions]:
                    decision.should_submit = False
                    decision.decision_reasoning.append("受每日投递限制影响")
            
            constraints_applied.append(f"应用每日投递限制: {criteria.max_daily_submissions}")
        
        # 2. 每家公司投递限制
        company_counts = {}
        for decision in final_decisions:
            if decision.should_submit:
                company = decision.company
                company_counts[company] = company_counts.get(company, 0) + 1
                
                if company_counts[company] > criteria.max_submissions_per_company:
                    decision.should_submit = False
                    decision.decision_reasoning.append("受单公司投递限制影响")
        
        if any(count > criteria.max_submissions_per_company for count in company_counts.values()):
            constraints_applied.append(f"应用单公司投递限制: {criteria.max_submissions_per_company}")
        
        # 3. 黑名单公司过滤
        blacklisted_count = 0
        for decision in final_decisions:
            if any(blacklisted in decision.company for blacklisted in criteria.blacklisted_companies):
                if decision.should_submit:
                    blacklisted_count += 1
                decision.should_submit = False
                decision.decision_reasoning.append("公司在黑名单中")
        
        if blacklisted_count > 0:
            constraints_applied.append(f"过滤黑名单公司: {blacklisted_count} 个")
        
        return final_decisions, constraints_applied
    
    def _generate_decision_summary(self, decisions: List[JobDecision]) -> Dict[str, Any]:
        """生成决策摘要"""
        total_decisions = len(decisions)
        submissions = [d for d in decisions if d.should_submit]
        
        # 按优先级统计
        priority_counts = {priority.value: 0 for priority in SubmissionPriority}
        for decision in submissions:
            priority_counts[decision.submission_priority.value] += 1
        
        # 按决策级别统计
        level_counts = {level.value: 0 for level in DecisionLevel}
        for decision in decisions:
            level_counts[decision.decision_level.value] += 1
        
        # 分数分布
        scores = [d.final_score for d in decisions]
        avg_score = sum(scores) / len(scores) if scores else 0
        max_score = max(scores) if scores else 0
        min_score = min(scores) if scores else 0
        
        return {
            'total_evaluated': total_decisions,
            'total_submissions': len(submissions),
            'submission_rate': len(submissions) / total_decisions if total_decisions > 0 else 0,
            'priority_distribution': priority_counts,
            'decision_level_distribution': level_counts,
            'score_statistics': {
                'average': avg_score,
                'maximum': max_score,
                'minimum': min_score
            },
            'top_companies': self._get_top_companies(submissions),
            'top_locations': self._get_top_locations(submissions)
        }
    
    def _get_top_companies(self, submissions: List[JobDecision], top_n: int = 5) -> List[Dict[str, Any]]:
        """获取推荐投递的顶级公司"""
        company_stats = {}
        for decision in submissions:
            company = decision.company
            if company not in company_stats:
                company_stats[company] = {
                    'company': company,
                    'count': 0,
                    'avg_score': 0,
                    'scores': []
                }
            company_stats[company]['count'] += 1
            company_stats[company]['scores'].append(decision.final_score)
        
        # 计算平均分数
        for stats in company_stats.values():
            stats['avg_score'] = sum(stats['scores']) / len(stats['scores'])
            del stats['scores']  # 删除原始分数列表
        
        # 按平均分数排序
        sorted_companies = sorted(company_stats.values(), key=lambda x: x['avg_score'], reverse=True)
        return sorted_companies[:top_n]
    
    def _get_top_locations(self, submissions: List[JobDecision], top_n: int = 5) -> List[Dict[str, Any]]:
        """获取推荐投递的顶级地点"""
        location_stats = {}
        for decision in submissions:
            location = decision.location
            if location not in location_stats:
                location_stats[location] = {
                    'location': location,
                    'count': 0,
                    'avg_score': 0,
                    'scores': []
                }
            location_stats[location]['count'] += 1
            location_stats[location]['scores'].append(decision.final_score)
        
        # 计算平均分数
        for stats in location_stats.values():
            stats['avg_score'] = sum(stats['scores']) / len(stats['scores'])
            del stats['scores']
        
        # 按数量和平均分数排序
        sorted_locations = sorted(
            location_stats.values(), 
            key=lambda x: (x['count'], x['avg_score']), 
            reverse=True
        )
        return sorted_locations[:top_n]
    
    def _parse_decision_criteria(self, criteria_dict: Dict[str, Any]) -> DecisionCriteria:
        """解析决策标准"""
        return DecisionCriteria(
            submission_threshold=criteria_dict.get('submission_threshold', 0.7),
            priority_threshold=criteria_dict.get('priority_threshold', 0.8),
            urgent_threshold=criteria_dict.get('urgent_threshold', 0.9),
            max_daily_submissions=criteria_dict.get('max_daily_submissions', 50),
            max_submissions_per_company=criteria_dict.get('max_submissions_per_company', 3),
            min_salary_requirement=criteria_dict.get('min_salary_requirement'),
            preferred_locations=criteria_dict.get('preferred_locations', []),
            blacklisted_companies=criteria_dict.get('blacklisted_companies', []),
            required_skills=criteria_dict.get('required_skills', []),
            weights=criteria_dict.get('weights', {
                'match_score': 0.3,
                'company_reputation': 0.2,
                'salary_attractiveness': 0.2,
                'location_preference': 0.1,
                'career_growth_potential': 0.1,
                'application_competition': 0.1
            })
        )
    
    def _update_stats(self, decisions: List[JobDecision]):
        """更新统计信息"""
        self.stats['total_decisions_made'] += len(decisions)
        submissions = [d for d in decisions if d.should_submit]
        self.stats['total_submissions_recommended'] += len(submissions)
        
        # 更新平均分数
        if decisions:
            total_score = sum(d.final_score for d in decisions)
            self.stats['average_decision_score'] = total_score / len(decisions)
        
        # 更新决策级别分布
        for decision in decisions:
            self.stats['decision_distribution'][decision.decision_level.value] += 1
    
    def _save_decision_history(self, decisions: List[JobDecision], criteria: DecisionCriteria):
        """保存决策历史"""
        if self.learning_enabled:
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'decisions_count': len(decisions),
                'submissions_count': len([d for d in decisions if d.should_submit]),
                'criteria': criteria.__dict__,
                'average_score': sum(d.final_score for d in decisions) / len(decisions) if decisions else 0
            }
            self.decision_history.append(history_entry)
            
            # 保留最近1000条记录
            if len(self.decision_history) > 1000:
                self.decision_history = self.decision_history[-1000:]
    
    def get_decision_stats(self) -> Dict[str, Any]:
        """获取决策统计信息"""
        return {
            'stats': self.stats.copy(),
            'history_count': len(self.decision_history),
            'cache_sizes': {
                'company_cache': len(self.company_cache),
                'location_cache': len(self.location_cache)
            },
            'learning_enabled': self.learning_enabled
        }
    
    async def learn_from_feedback(self, feedback_data: List[Dict[str, Any]]):
        """从反馈中学习"""
        if not self.learning_enabled:
            return
        
        self.feedback_data.extend(feedback_data)
        
        # 分析反馈数据，调整决策参数
        # 