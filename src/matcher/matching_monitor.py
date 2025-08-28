#!/usr/bin/env python3
"""
匹配监控和定期检查系统
用于监控匹配质量和执行定期匹配检查
"""

import asyncio
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import sqlite3
import json

from ..utils.logger import get_logger
from ..database.operations import DatabaseManager
from .generic_resume_matcher import GenericResumeJobMatcher
from .generic_resume_models import GenericResumeProfile
from ..rag.vector_manager import ChromaDBManager


@dataclass
class MatchingStats:
    """匹配统计信息"""
    total_jobs: int = 0
    total_matches: int = 0
    match_rate: float = 0.0
    avg_score: float = 0.0
    high_quality_matches: int = 0
    processing_time: float = 0.0
    timestamp: datetime = None


@dataclass
class MatchingAlert:
    """匹配告警信息"""
    alert_type: str
    severity: str  # low, medium, high, critical
    message: str
    details: Dict[str, Any]
    timestamp: datetime


class MatchingMonitor:
    """匹配监控系统"""
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 vector_manager: ChromaDBManager,
                 config: Dict = None):
        self.db_manager = db_manager
        self.vector_manager = vector_manager
        self.config = config or {}
        self.logger = get_logger(__name__)
        
        # 监控配置
        self.min_match_rate = config.get('min_match_rate', 0.15)  # 最低匹配率15%
        self.min_avg_score = config.get('min_avg_score', 0.5)    # 最低平均分数
        self.check_interval_hours = config.get('check_interval_hours', 6)  # 检查间隔6小时
        
        # 初始化匹配器
        self.matcher = GenericResumeJobMatcher(vector_manager, config)
        
        # 统计历史
        self.stats_history: List[MatchingStats] = []
        self.alerts: List[MatchingAlert] = []
    
    async def run_matching_check(self) -> MatchingStats:
        """执行匹配检查"""
        start_time = time.time()
        
        try:
            self.logger.info("🔍 开始执行定期匹配检查")
            
            # 1. 获取数据库统计
            stats = await self._collect_database_stats()
            
            # 2. 检查匹配质量
            quality_issues = await self._check_matching_quality(stats)
            
            # 3. 生成告警
            if quality_issues:
                await self._generate_alerts(quality_issues)
            
            # 4. 执行自动修复（如果配置了）
            if self.config.get('auto_fix_enabled', False):
                await self._auto_fix_issues(quality_issues)
            
            # 5. 记录统计
            stats.processing_time = time.time() - start_time
            stats.timestamp = datetime.now()
            self.stats_history.append(stats)
            
            # 保持历史记录在合理范围内
            if len(self.stats_history) > 100:
                self.stats_history = self.stats_history[-100:]
            
            self.logger.info(f"✅ 匹配检查完成，耗时 {stats.processing_time:.2f}秒")
            self.logger.info(f"📊 匹配统计: 总职位{stats.total_jobs}, 匹配{stats.total_matches}, "
                           f"匹配率{stats.match_rate:.1%}, 平均分{stats.avg_score:.3f}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"💥 匹配检查失败: {str(e)}")
            raise
    
    async def _collect_database_stats(self) -> MatchingStats:
        """收集数据库统计信息"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # 总职位数
            cursor.execute("SELECT COUNT(*) FROM jobs")
            total_jobs = cursor.fetchone()[0]
            
            # 总匹配数
            cursor.execute("SELECT COUNT(*) FROM resume_matches")
            total_matches = cursor.fetchone()[0]
            
            # 平均匹配分数
            cursor.execute("SELECT AVG(match_score) FROM resume_matches WHERE match_score > 0")
            avg_score_result = cursor.fetchone()[0]
            avg_score = avg_score_result if avg_score_result else 0.0
            
            # 高质量匹配数（分数 >= 0.7）
            cursor.execute("SELECT COUNT(*) FROM resume_matches WHERE match_score >= 0.7")
            high_quality_matches = cursor.fetchone()[0]
            
            # 计算匹配率
            match_rate = total_matches / total_jobs if total_jobs > 0 else 0.0
            
            conn.close()
            
            return MatchingStats(
                total_jobs=total_jobs,
                total_matches=total_matches,
                match_rate=match_rate,
                avg_score=avg_score,
                high_quality_matches=high_quality_matches
            )
            
        except Exception as e:
            self.logger.error(f"收集数据库统计失败: {str(e)}")
            raise
    
    async def _check_matching_quality(self, stats: MatchingStats) -> List[Dict[str, Any]]:
        """检查匹配质量问题"""
        issues = []
        
        # 1. 检查匹配率
        if stats.match_rate < self.min_match_rate:
            issues.append({
                'type': 'low_match_rate',
                'severity': 'high' if stats.match_rate < 0.1 else 'medium',
                'current_value': stats.match_rate,
                'threshold': self.min_match_rate,
                'description': f'匹配率过低: {stats.match_rate:.1%} < {self.min_match_rate:.1%}'
            })
        
        # 2. 检查平均分数
        if stats.avg_score < self.min_avg_score:
            issues.append({
                'type': 'low_avg_score',
                'severity': 'medium',
                'current_value': stats.avg_score,
                'threshold': self.min_avg_score,
                'description': f'平均匹配分数过低: {stats.avg_score:.3f} < {self.min_avg_score:.3f}'
            })
        
        # 3. 检查高质量匹配比例
        if stats.total_matches > 0:
            high_quality_ratio = stats.high_quality_matches / stats.total_matches
            if high_quality_ratio < 0.3:  # 高质量匹配应该占30%以上
                issues.append({
                    'type': 'low_quality_ratio',
                    'severity': 'medium',
                    'current_value': high_quality_ratio,
                    'threshold': 0.3,
                    'description': f'高质量匹配比例过低: {high_quality_ratio:.1%} < 30%'
                })
        
        # 4. 检查趋势（如果有历史数据）
        if len(self.stats_history) >= 3:
            recent_stats = self.stats_history[-3:]
            match_rates = [s.match_rate for s in recent_stats]
            
            # 检查匹配率是否持续下降
            if all(match_rates[i] > match_rates[i+1] for i in range(len(match_rates)-1)):
                issues.append({
                    'type': 'declining_trend',
                    'severity': 'medium',
                    'current_value': match_rates,
                    'description': '匹配率呈下降趋势'
                })
        
        return issues
    
    async def _generate_alerts(self, issues: List[Dict[str, Any]]):
        """生成告警"""
        for issue in issues:
            alert = MatchingAlert(
                alert_type=issue['type'],
                severity=issue['severity'],
                message=issue['description'],
                details=issue,
                timestamp=datetime.now()
            )
            
            self.alerts.append(alert)
            
            # 记录告警日志
            severity_emoji = {
                'low': '🟡',
                'medium': '🟠', 
                'high': '🔴',
                'critical': '💥'
            }
            
            emoji = severity_emoji.get(alert.severity, '⚠️')
            self.logger.warning(f"{emoji} 匹配质量告警 [{alert.severity.upper()}]: {alert.message}")
        
        # 保持告警历史在合理范围内
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
    
    async def _auto_fix_issues(self, issues: List[Dict[str, Any]]):
        """自动修复问题"""
        for issue in issues:
            issue_type = issue['type']
            
            try:
                if issue_type == 'low_match_rate':
                    await self._fix_low_match_rate()
                elif issue_type == 'low_avg_score':
                    await self._fix_low_avg_score()
                
                self.logger.info(f"🔧 已尝试自动修复问题: {issue_type}")
                
            except Exception as e:
                self.logger.error(f"自动修复 {issue_type} 失败: {str(e)}")
    
    async def _fix_low_match_rate(self):
        """修复低匹配率问题"""
        try:
            self.logger.info("🔧 开始修复低匹配率问题")
            
            # 1. 获取未匹配的职位
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT job_id FROM jobs 
                WHERE job_id NOT IN (SELECT DISTINCT job_id FROM resume_matches)
                AND rag_processed = 1
                LIMIT 50
            """)
            
            unmatched_jobs = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            if not unmatched_jobs:
                self.logger.info("没有找到未匹配的已处理职位")
                return
            
            self.logger.info(f"找到 {len(unmatched_jobs)} 个未匹配职位，开始重新匹配")
            
            # 2. 创建默认简历档案（这里应该从实际简历数据创建）
            resume_profile = await self._get_default_resume_profile()
            
            # 3. 重新运行匹配
            result = await self.matcher.find_matching_jobs(resume_profile, top_k=len(unmatched_jobs))
            
            # 4. 保存匹配结果
            if result.matches:
                await self._save_match_results(result.matches)
                self.logger.info(f"✅ 重新匹配完成，新增 {len(result.matches)} 个匹配")
            
        except Exception as e:
            self.logger.error(f"修复低匹配率失败: {str(e)}")
    
    async def _fix_low_avg_score(self):
        """修复低平均分数问题"""
        try:
            self.logger.info("🔧 开始修复低平均分数问题")
            
            # 这里可以实现分数重新计算逻辑
            # 例如：更新匹配权重、重新计算现有匹配的分数等
            
            self.logger.info("低平均分数修复逻辑待实现")
            
        except Exception as e:
            self.logger.error(f"修复低平均分数失败: {str(e)}")
    
    async def _get_default_resume_profile(self) -> GenericResumeProfile:
        """获取默认简历档案"""
        # 这里应该从实际的简历数据创建
        # 暂时返回一个示例档案
        from .generic_resume_models import GenericResumeProfile, SkillCategory
        
        return GenericResumeProfile(
            name="Default User",
            total_experience_years=5,
            current_position="Software Engineer",
            skill_categories=[
                SkillCategory(
                    category_name="programming_languages",
                    skills=["Python", "Java", "JavaScript"],
                    proficiency_level="advanced"
                )
            ],
            expected_salary_range={"min": 200000, "max": 500000}
        )
    
    async def _save_match_results(self, matches: List):
        """保存匹配结果到数据库"""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            for match in matches:
                cursor.execute("""
                    INSERT OR REPLACE INTO resume_matches 
                    (job_id, resume_profile_id, match_score, priority_level, 
                     semantic_score, skill_match_score, experience_match_score, 
                     location_match_score, salary_match_score, match_details, 
                     match_reasons, created_at, processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 0)
                """, (
                    match.job_id,
                    'default',
                    match.overall_score,
                    match.match_level.value if hasattr(match.match_level, 'value') else str(match.match_level),
                    match.dimension_scores.get('semantic_similarity', 0),
                    match.dimension_scores.get('skills_match', 0),
                    match.dimension_scores.get('experience_match', 0),
                    match.dimension_scores.get('industry_match', 0),
                    match.dimension_scores.get('salary_match', 0),
                    json.dumps(match.dimension_scores),
                    f"自动匹配修复: {match.job_title} at {match.company}"
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"保存匹配结果失败: {str(e)}")
    
    def start_scheduled_monitoring(self):
        """启动定时监控"""
        self.logger.info(f"🕐 启动定时匹配监控，检查间隔: {self.check_interval_hours}小时")
        
        # 设置定时任务
        schedule.every(self.check_interval_hours).hours.do(
            lambda: asyncio.create_task(self.run_matching_check())
        )
        
        # 立即执行一次检查
        asyncio.create_task(self.run_matching_check())
        
        # 运行调度器
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次调度
    
    def get_monitoring_report(self) -> Dict[str, Any]:
        """获取监控报告"""
        if not self.stats_history:
            return {"message": "暂无监控数据"}
        
        latest_stats = self.stats_history[-1]
        recent_alerts = [a for a in self.alerts if a.timestamp > datetime.now() - timedelta(hours=24)]
        
        return {
            "latest_stats": {
                "total_jobs": latest_stats.total_jobs,
                "total_matches": latest_stats.total_matches,
                "match_rate": f"{latest_stats.match_rate:.1%}",
                "avg_score": f"{latest_stats.avg_score:.3f}",
                "high_quality_matches": latest_stats.high_quality_matches,
                "timestamp": latest_stats.timestamp.isoformat() if latest_stats.timestamp else None
            },
            "recent_alerts": [
                {
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in recent_alerts
            ],
            "trend_analysis": self._analyze_trends(),
            "recommendations": self._generate_recommendations()
        }
    
    def _analyze_trends(self) -> Dict[str, Any]:
        """分析趋势"""
        if len(self.stats_history) < 2:
            return {"message": "数据不足，无法分析趋势"}
        
        recent_stats = self.stats_history[-5:]  # 最近5次检查
        
        match_rates = [s.match_rate for s in recent_stats]
        avg_scores = [s.avg_score for s in recent_stats]
        
        return {
            "match_rate_trend": "上升" if match_rates[-1] > match_rates[0] else "下降",
            "avg_score_trend": "上升" if avg_scores[-1] > avg_scores[0] else "下降",
            "match_rate_change": f"{((match_rates[-1] - match_rates[0]) / match_rates[0] * 100):.1f}%" if match_rates[0] > 0 else "N/A",
            "avg_score_change": f"{((avg_scores[-1] - avg_scores[0]) / avg_scores[0] * 100):.1f}%" if avg_scores[0] > 0 else "N/A"
        }
    
    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if not self.stats_history:
            return ["建议先运行匹配检查以获取数据"]
        
        latest_stats = self.stats_history[-1]
        
        if latest_stats.match_rate < 0.15:
            recommendations.append("匹配率过低，建议检查匹配算法参数或简历数据质量")
        
        if latest_stats.avg_score < 0.5:
            recommendations.append("平均匹配分数偏低，建议优化匹配权重配置")
        
        if latest_stats.total_matches > 0:
            high_quality_ratio = latest_stats.high_quality_matches / latest_stats.total_matches
            if high_quality_ratio < 0.3:
                recommendations.append("高质量匹配比例偏低，建议提高匹配阈值或优化技能匹配逻辑")
        
        if not recommendations:
            recommendations.append("匹配质量良好，继续保持当前配置")
        
        return recommendations


# 独立运行脚本
async def main():
    """主函数"""
    import sys
    import os
    
    # 添加项目根目录到路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    from src.database.operations import DatabaseManager
    from src.rag.vector_manager import ChromaDBManager
    
    # 初始化组件
    db_manager = DatabaseManager('data/jobs.db')
    vector_manager = ChromaDBManager()
    
    # 创建监控器
    monitor = MatchingMonitor(db_manager, vector_manager)
    
    # 运行检查
    stats = await monitor.run_matching_check()
    
    # 打印报告
    report = monitor.get_monitoring_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())