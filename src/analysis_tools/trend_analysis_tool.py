
"""
趋势分析工具

基于RAG系统和向量数据库，分析职位市场的趋势变化
结合时间序列分析和语义搜索，识别新兴技能和市场趋势
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from .base_tool import BaseAnalysisTool


class TrendAnalysisInput(BaseModel):
    """趋势分析输入参数"""
    skill: Optional[str] = Field(None, description="特定技能名称，如'Python'、'AI'等")
    time_period: Optional[int] = Field(30, description="分析时间段（天数），默认30天")
    trend_type: Optional[str] = Field("skill", description="趋势类型：skill(技能)、salary(薪资)、location(地区)、overall(整体)")
    compare_periods: Optional[bool] = Field(False, description="是否进行时期对比分析")
    include_predictions: Optional[bool] = Field(False, description="是否包含趋势预测")


class TrendAnalysisTool(BaseAnalysisTool):
    """趋势分析工具 - 基于RAG和向量搜索"""
    
    name: str = "trend_analysis"
    description: str = """
    基于RAG系统分析职位市场的趋势变化。结合向量搜索和时间序列分析：
    1. 分析特定技能的需求趋势变化
    2. 识别新兴技能和衰落技能
    3. 分析薪资水平的时间变化
    4. 通过语义搜索发现市场趋势
    5. 提供趋势预测和建议
    
    输入参数：
    - skill: 特定技能名称（可选）
    - time_period: 分析时间段天数（默认30天）
    - trend_type: 趋势类型（skill/salary/location/overall）
    - compare_periods: 是否进行时期对比分析（默认false）
    - include_predictions: 是否包含趋势预测（默认false）
    """
    args_schema: type = TrendAnalysisInput
    
    def _run(self, skill: Optional[str] = None, time_period: int = 30,
             trend_type: str = "skill", compare_periods: bool = False,
             include_predictions: bool = False) -> str:
        """
        执行趋势分析
        
        Args:
            skill: 特定技能名称
            time_period: 分析时间段（天数）
            trend_type: 趋势类型
            compare_periods: 是否进行时期对比
            include_predictions: 是否包含预测
            
        Returns:
            分析结果文本
        """
        try:
            if trend_type == "skill":
                if skill:
                    result = self._analyze_skill_trend(skill, time_period, compare_periods, include_predictions)
                else:
                    result = self._analyze_overall_skill_trends(time_period, compare_periods)
            elif trend_type == "salary":
                result = self._analyze_salary_trends(skill, time_period, compare_periods)
            elif trend_type == "location":
                result = self._analyze_location_trends(time_period, compare_periods)
            else:
                result = self._analyze_overall_market_trends(time_period, compare_periods, include_predictions)
            
            return self._format_result(result)
            
        except Exception as e:
            self.logger.error(f"趋势分析失败: {e}")
            return f"分析失败: {str(e)}"
    
    def _analyze_skill_trend(self, skill: str, time_period: int = 30,
                           compare_periods: bool = False, include_predictions: bool = False) -> dict:
        """
        分析特定技能的趋势变化
        
        Args:
            skill: 技能名称
            time_period: 时间段
            compare_periods: 是否对比时期
            include_predictions: 是否包含预测
            
        Returns:
            技能趋势分析结果
        """
        # 1. 使用向量搜索获取技能相关职位的时间序列数据
        skill_timeline_data = self._get_skill_timeline_data_vector(skill, time_period)
        
        if not skill_timeline_data:
            return {
                'title': f'{skill}技能趋势分析',
                'summary': f'未找到{skill}技能在过去{time_period}天的趋势数据',
                'data': [],
                'statistics': {},
                'insights': [f'{skill}技能数据不足，无法进行趋势分析'],
                'recommendations': ['建议扩大时间范围或关注相关技能'],
                'data_source': '基于RAG向量搜索和时间序列分析'
            }
        
        # 2. 计算趋势指标
        trend_metrics = self._calculate_trend_metrics(skill_timeline_data)
        
        # 3. 时期对比分析
        period_comparison = {}
        if compare_periods:
            period_comparison = self._compare_time_periods(skill, time_period)
        
        # 4. 趋势预测
        predictions = {}
        if include_predictions:
            predictions = self._predict_skill_trend(skill_timeline_data, skill)
        
        # 5. 相关技能趋势对比
        related_skills_trends = self._get_related_skills_trends_vector(skill, time_period)
        
        result = {
            'title': f'{skill}技能市场趋势分析（{time_period}天）',
            'summary': f'{skill}技能在过去{time_period}天呈现{trend_metrics["trend_direction"]}趋势，变化率{trend_metrics["change_rate"]:.1f}%',
            'data': [
                {
                    'name': '趋势方向',
                    'value': trend_metrics['trend_direction'],
                    'description': f'基于{len(skill_timeline_data)}个数据点的趋势分析'
                },
                {
                    'name': '变化率',
                    'value': f'{trend_metrics["change_rate"]:.1f}%',
                    'description': f'相比{time_period}天前的变化幅度'
                },
                {
                    'name': '平均日增长',
                    'value': f'{trend_metrics["daily_growth"]:.2f}',
                    'description': '每日平均职位数量变化'
                },
                {
                    'name': '波动性',
                    'value': trend_metrics['volatility_level'],
                    'description': '趋势稳定性评估'
                }
            ],
            'statistics': trend_metrics,
            'insights': self._generate_skill_trend_insights(skill, trend_metrics, related_skills_trends),
            'recommendations': self._generate_skill_trend_recommendations(skill, trend_metrics, predictions),
            'related_data': {
                'timeline_data': skill_timeline_data,
                'period_comparison': period_comparison,
                'predictions': predictions,
                'related_skills_trends': related_skills_trends,
                'trend_analysis': self._analyze_trend_patterns(skill_timeline_data)
            },
            'data_source': f'基于RAG向量搜索和{len(skill_timeline_data)}个时间点的趋势分析'
        }
        
        return result
    
    def _analyze_overall_skill_trends(self, time_period: int = 30, compare_periods: bool = False) -> dict:
        """
        分析整体技能市场趋势
        
        Args:
            time_period: 时间段
            compare_periods: 是否对比时期
            
        Returns:
            整体技能趋势分析结果
        """
        # 1. 获取热门技能的趋势数据
        top_skills = self._get_top_skills_with_trends(time_period)
        
        if not top_skills:
            return {
                'title': '整体技能市场趋势分析',
                'summary': '暂无足够的技能趋势数据',
                'data': [],
                'statistics': {},
                'insights': ['当前时间段内技能数据不足'],
                'recommendations': ['建议扩大分析时间范围'],
                'data_source': '基于技能市场趋势分析'
            }
        
        # 2. 识别新兴技能和衰落技能
        emerging_skills = [skill for skill in top_skills if skill['trend_direction'] == '上升' and skill['change_rate'] > 20]
        declining_skills = [skill for skill in top_skills if skill['trend_direction'] == '下降' and skill['change_rate'] < -10]
        
        # 3. 计算市场整体趋势
        overall_metrics = self._calculate_overall_market_metrics(top_skills)
        
        # 4. 技能分类趋势分析
        category_trends = self._analyze_skill_category_trends(top_skills)
        
        result = {
            'title': f'整体技能市场趋势分析（{time_period}天）',
            'summary': f'分析了{len(top_skills)}个主要技能，发现{len(emerging_skills)}个新兴技能，{len(declining_skills)}个需求下降技能',
            'data': [
                {
                    'rank': i + 1,
                    'name': skill['skill'],
                    'value': skill['current_demand'],
                    'percentage': skill['change_rate'],
                    'description': f'{skill["trend_direction"]}趋势，变化率{skill["change_rate"]:.1f}%'
                }
                for i, skill in enumerate(top_skills[:10])
            ],
            'statistics': overall_metrics,
            'insights': self._generate_overall_trend_insights(top_skills, emerging_skills, declining_skills, overall_metrics),
            'recommendations': self._generate_overall_trend_recommendations(emerging_skills, declining_skills),
            'related_data': {
                'emerging_skills': emerging_skills,
                'declining_skills': declining_skills,
                'category_trends': category_trends,
                'market_momentum': overall_metrics.get('market_momentum', 'stable')
            },
            'data_source': f'基于{len(top_skills)}个技能的市场趋势综合分析'
        }
        
        return result
    
    def _analyze_salary_trends(self, skill: Optional[str] = None, time_period: int = 30,
                             compare_periods: bool = False) -> dict:
        """
        分析薪资趋势变化
        
        Args:
            skill: 特定技能（可选）
            time_period: 时间段
            compare_periods: 是否对比时期
            
        Returns:
            薪资趋势分析结果
        """
        # 1. 获取薪资时间序列数据
        salary_timeline = self._get_salary_timeline_data(skill, time_period)
        
        if not salary_timeline:
            title = f'{skill}技能薪资趋势分析' if skill else '整体薪资趋势分析'
            return {
                'title': title,
                'summary': '暂无足够的薪资趋势数据',
                'data': [],
                'statistics': {},
                'insights': ['当前时间段内薪资数据不足'],
                'recommendations': ['建议扩大分析时间范围或关注主要技能'],
                'data_source': '基于薪资趋势分析'
            }
        
        # 2. 计算薪资趋势指标
        salary_metrics = self._calculate_salary_trend_metrics(salary_timeline)
        
        # 3. 薪资区间变化分析
        salary_range_changes = self._analyze_salary_range_changes(salary_timeline)
        
        title = f'{skill}技能薪资趋势分析（{time_period}天）' if skill else f'整体薪资趋势分析（{time_period}天）'
        
        result = {
            'title': title,
            'summary': f'薪资呈现{salary_metrics["trend_direction"]}趋势，平均薪资变化{salary_metrics["avg_change"]:.1f}%',
            'data': [
                {
                    'name': '薪资趋势',
                    'value': salary_metrics['trend_direction'],
                    'description': f'基于{len(salary_timeline)}个时间点的薪资变化'
                },
                {
                    'name': '平均薪资变化',
                    'value': f'{salary_metrics["avg_change"]:.1f}%',
                    'description': f'相比{time_period}天前的薪资变化'
                },
                {
                    'name': '当前平均月薪',
                    'value': f'{salary_metrics["current_avg"]//1000}k',
                    'description': f'最近时期的平均月薪水平，年薪约{salary_metrics["current_avg"]*12//10000}万元'
                },
                {
                    'name': '薪资波动性',
                    'value': salary_metrics['volatility'],
                    'description': '薪资变化的稳定性'
                }
            ],
            'statistics': salary_metrics,
            'insights': self._generate_salary_trend_insights(salary_metrics, skill),
            'recommendations': self._generate_salary_trend_recommendations(salary_metrics, skill),
            'related_data': {
                'timeline_data': salary_timeline,
                'range_changes': salary_range_changes,
                'trend_analysis': self._analyze_salary_trend_patterns(salary_timeline)
            },
            'data_source': f'基于{len(salary_timeline)}个时间点的薪资趋势分析'
        }
        
        return result
    
    def _analyze_location_trends(self, time_period: int = 30, compare_periods: bool = False) -> dict:
        """
        分析地区就业趋势
        
        Args:
            time_period: 时间段
            compare_periods: 是否对比时期
            
        Returns:
            地区趋势分析结果
        """
        # 1. 获取主要城市的职位趋势数据
        location_trends = self._get_location_trends_data(time_period)
        
        if not location_trends:
            return {
                'title': f'地区就业趋势分析（{time_period}天）',
                'summary': '暂无足够的地区趋势数据',
                'data': [],
                'statistics': {},
                'insights': ['当前时间段内地区数据不足'],
                'recommendations': ['建议扩大分析时间范围'],
                'data_source': '基于地区就业趋势分析'
            }
        
        # 2. 识别热门和冷门地区
        hot_locations = [loc for loc in location_trends if loc['change_rate'] > 10]
        cold_locations = [loc for loc in location_trends if loc['change_rate'] < -5]
        
        # 3. 计算地区趋势指标
        location_metrics = self._calculate_location_trend_metrics(location_trends)
        
        result = {
            'title': f'地区就业趋势分析（{time_period}天）',
            'summary': f'分析了{len(location_trends)}个主要城市，{len(hot_locations)}个城市需求上升，{len(cold_locations)}个城市需求下降',
            'data': [
                {
                    'rank': i + 1,
                    'name': loc['location'],
                    'value': str(loc['current_jobs']),
                    'percentage': loc['change_rate'],
                    'description': f'{loc["trend_direction"]}趋势，变化率{loc["change_rate"]:.1f}%'
                }
                for i, loc in enumerate(location_trends)
            ],
            'statistics': location_metrics,
            'insights': self._generate_location_trend_insights(location_trends, hot_locations, cold_locations),
            'recommendations': self._generate_location_trend_recommendations(hot_locations, cold_locations),
            'related_data': {
                'hot_locations': hot_locations,
                'cold_locations': cold_locations,
                'regional_analysis': self._analyze_regional_patterns(location_trends)
            },
            'data_source': f'基于{len(location_trends)}个城市的就业趋势分析'
        }
        
        return result
    
    def _analyze_overall_market_trends(self, time_period: int = 30, compare_periods: bool = False,
                                     include_predictions: bool = False) -> dict:
        """
        分析整体市场趋势
        
        Args:
            time_period: 时间段
            compare_periods: 是否对比时期
            include_predictions: 是否包含预测
            
        Returns:
            整体市场趋势分析结果
        """
        # 1. 获取整体市场数据
        market_data = self._get_overall_market_timeline(time_period)
        
        if not market_data:
            return {
                'title': f'整体市场趋势分析（{time_period}天）',
                'summary': '暂无足够的市场趋势数据',
                'data': [],
                'statistics': {},
                'insights': ['当前时间段内市场数据不足'],
                'recommendations': ['建议扩大分析时间范围'],
                'data_source': '基于整体市场趋势分析'
            }
        
        # 2. 计算市场趋势指标
        market_metrics = self._calculate_market_trend_metrics(market_data)
        
        # 3. 行业趋势分析
        industry_trends = self._analyze_industry_trends(time_period)
        
        # 4. 市场预测
        predictions = {}
        if include_predictions:
            predictions = self._predict_market_trends(market_data)
        
        result = {
            'title': f'整体就业市场趋势分析（{time_period}天）',
            'summary': f'市场呈现{market_metrics["overall_trend"]}趋势，职位总量变化{market_metrics["job_change_rate"]:.1f}%',
            'data': [
                {
                    'name': '市场趋势',
                    'value': market_metrics['overall_trend'],
                    'description': f'基于{len(market_data)}个时间点的市场分析'
                },
                {
                    'name': '职位总量变化',
                    'value': f'{market_metrics["job_change_rate"]:.1f}%',
                    'description': f'相比{time_period}天前的职位数量变化'
                },
                {
                    'name': '市场活跃度',
                    'value': market_metrics['market_activity'],
                    'description': '基于职位发布频率的活跃度评估'
                },
                {
                    'name': '竞争激烈程度',
                    'value': market_metrics['competition_level'],
                    'description': '基于职位供需比的竞争程度'
                }
            ],
            'statistics': market_metrics,
            'insights': self._generate_market_trend_insights(market_metrics, industry_trends),
            'recommendations': self._generate_market_trend_recommendations(market_metrics, predictions),
            'related_data': {
                'timeline_data': market_data,
                'industry_trends': industry_trends,
                'predictions': predictions,
                'market_indicators': self._calculate_market_indicators(market_data)
            },
            'data_source': f'基于{len(market_data)}个时间点的整体市场趋势分析'
        }
        
        return result
    
    def _get_skill_timeline_data_vector(self, skill: str, time_period: int) -> list:
        """使用向量搜索获取技能的时间序列数据"""
        if not self.vector_manager:
            return self._get_skill_timeline_data_traditional(skill, time_period)
        
        try:
            # 构建时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period)
            
            # 使用向量搜索获取技能相关职位
            skill_queries = [
                f"{skill}开发工程师",
                f"{skill}技能要求",
                f"熟悉{skill}",
                f"{skill}经验"
            ]
            
            all_job_ids = set()
            for query in skill_queries:
                docs = self.vector_manager.search_similar_jobs(query, k=100)
                for doc in docs:
                    job_id = doc.metadata.get('job_id')
                    if job_id:
                        all_job_ids.add(job_id)
            
            if not all_job_ids:
                return []
            
            # 查询这些职位的时间分布
            placeholders = ','.join('?' * len(all_job_ids))
            query = f"""
            SELECT 
                DATE(j.created_at) as date,
                COUNT(*) as job_count
            FROM jobs j
            WHERE j.job_id IN ({placeholders})
            AND j.created_at >= ? AND j.created_at <= ?
            GROUP BY DATE(j.created_at)
            ORDER BY date
            """
            
            params = list(all_job_ids) + [start_date.isoformat(), end_date.isoformat()]
            timeline_data = self._execute_query(query, tuple(params))
            
            return timeline_data
            
        except Exception as e:
            self.logger.warning(f"向量搜索时间序列数据失败: {e}")
            return self._get_skill_timeline_data_traditional(skill, time_period)
    
    def _get_skill_timeline_data_traditional(self, skill: str, time_period: int) -> list:
        """传统方式获取技能时间序列数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period)
            
            skill_pattern = f"%{self._standardize_skill_name(skill)}%"
            
            query = """
            SELECT 
                DATE(j.created_at) as date,
                COUNT(*) as job_count
            FROM jobs j
            JOIN job_details jd ON j.job_id = jd.job_id
            WHERE (LOWER(jd.keyword) LIKE ? OR LOWER(jd.description) LIKE ? OR LOWER(jd.requirements) LIKE ?)
            AND j.created_at >= ? AND j.created_at <= ?
            GROUP BY DATE(j.created_at)
            ORDER BY date
            """
            
            params = (skill_pattern, skill_pattern, skill_pattern, start_date.isoformat(), end_date.isoformat())
            return self._execute_query(query, params)
            
        except Exception as e:
            self.logger.error(f"获取技能时间序列数据失败: {e}")
            return []
    
    def _calculate_trend_metrics(self, timeline_data: list) -> dict:
        """计算趋势指标"""
        if len(timeline_data) < 2:
            return {
                'trend_direction': '数据不足',
                'change_rate': 0,
                'daily_growth': 0,
                'volatility_level': '未知'
            }
        
        # 计算总体变化率
        first_value = timeline_data[0]['job_count']
        last_value = timeline_data[-1]['job_count']
        
        if first_value == 0:
            change_rate = 100 if last_value > 0 else 0
        else:
            change_rate = ((last_value - first_value) / first_value) * 100
        
        # 确定趋势方向
        if change_rate > 5:
            trend_direction = '上升'
        elif change_rate < -5:
            trend_direction = '下降'
        else:
            trend_direction = '稳定'
        
        # 计算日均增长
        days = len(timeline_data)
        daily_growth = (last_value - first_value) / days if days > 0 else 0
        
        # 计算波动性
        values = [item['job_count'] for item in timeline_data]
        if len(values) > 1:
            mean_val = sum(values) / len(values)
            variance = sum((x - mean_val) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            volatility_ratio = std_dev / mean_val if mean_val > 0 else 0
            
            if volatility_ratio > 0.3:
                volatility_level = '高波动'
            elif volatility_ratio > 0.15:
                volatility_level = '中等波动'
            else:
                volatility_level = '低波动'
        else:
            volatility_level = '未知'
        
        return {
            'trend_direction': trend_direction,
            'change_rate': change_rate,
            'daily_growth': daily_growth,
            'volatility_level': volatility_level,
            'data_points': len(timeline_data),
            'first_value': first_value,
            'last_value': last_value,
            'max_value': max(values) if values else 0,
            'min_value': min(values) if values else 0
        }
    
    def _get_related_skills_trends_vector(self, skill: str, time_period: int) -> list:
        """获取相关技能的趋势对比"""
        if not self.vector_manager:
            return []
        
        try:
            # 使用向量搜索找到相关技能
            docs = self.vector_manager.search_similar_jobs(f"{skill}相关技能", k=20)
            
            # 提取相关技能关键词
            related_skills = set()
            common_skills = ['python', 'java', 'javascript', 'react', 'vue', 'node.js', 'mysql', 'redis']
            
            for doc in docs:
                content = doc.page_content.lower()
                for common_skill in common_skills:
                    if common_skill != skill.lower() and common_skill in content:
                        related_skills.add(common_skill)
            
            # 获取相关技能的趋势数据
            related_trends = []
            for related_skill in list(related_skills)[:5]:  # 限制为前5个
                skill_timeline = self._get_skill_timeline_data_vector(related_skill, time_period)
                if skill_timeline:
                    metrics = self._calculate_trend_metrics(skill_timeline)
                    related_trends.append({
                        'skill': related_skill,
                        'trend_direction': metrics['trend_direction'],
                        'change_rate': metrics['change_rate']
                    })
            
            return related_trends
            
        except Exception as e:
            self.logger.warning(f"获取相关技能趋势失败: {e}")
            return []
    
    def _get_top_skills_with_trends(self, time_period: int) -> list:
        """获取热门技能及其趋势"""
        try:
            # 获取热门技能列表
            query = """
            SELECT 
                LOWER(TRIM(jd.keyword)) as skill,
                COUNT(*) as total_count
            FROM job_details jd
            JOIN jobs j ON jd.job_id = j.job_id
            WHERE jd.keyword IS NOT NULL AND jd.keyword != ''
            GROUP BY LOWER(TRIM(jd.keyword))
            HAVING total_count >= 5
            ORDER BY total_count DESC
            LIMIT 20
            """
            
            skills_data = self._execute_query(query)
            
            # 为每个技能计算趋势
            skills_with_trends = []
            for skill_info in skills_data:
                skill = skill_info['skill']
                timeline_data = self._get_skill_timeline_data_vector(skill, time_period)
                
                if timeline_data:
                    metrics = self._calculate_trend_metrics(timeline_data)
                    skills_with_trends.append({
                        'skill': skill,
                        'current_demand': skill_info['total_count'],
                        'trend_direction': metrics['trend_direction'],
                        'change_rate': metrics['change_rate'],
                        'daily_growth': metrics['daily_growth']
                    })
            
            return skills_with_trends
            
        except Exception as e:
            self.logger.error(f"获取技能趋势数据失败: {e}")
            return []
    
    def _generate_skill_trend_insights(self, skill: str, metrics: dict, related_trends: list) -> list:
        """生成技能趋势洞察"""
        insights = []
        
        # 趋势方向洞察
        trend_direction = metrics['trend_direction']
        change_rate = metrics['change_rate']
        
        if trend_direction == '上升':
            if change_rate > 50:
                insights.append(f"{skill}技能需求激增，是当前最热门的技能之一")
            elif change_rate > 20:
                insights.append(f"{skill}技能需求稳步上升，市场前景良好")
            else:
                insights.append(f"{skill}技能需求温和上升，保持稳定增长")
        elif trend_direction == '下降':
            if change_rate < -30:
                insights.append(f"{skill}技能需求大幅下降，可能面临技术更新换代")
            else:
                insights.append(f"{skill}技能需求有所下降，建议关注相关新技术")
        else:
            insights.append(f"{skill}技能需求保持稳定，是成熟的技术选择")
        
        # 波动性洞察
        volatility = metrics['volatility_level']
        if volatility == '高波动':
            insights.append(f"{skill}技能市场波动较大，需要密切关注市场变化")
        elif volatility == '低波动':
            insights.append(f"{skill}技能市场相对稳定，适合长期规划")
        
        # 相关技能对比洞察
        if related_trends:
            rising_related = [t for t in related_trends if t['trend_direction'] == '上升']
            if rising_related:
                related_names = [t['skill'] for t in rising_related[:2]]
                insights.append(f"相关技能{', '.join(related_names)}也呈上升趋势，形成技能生态")
        
        return insights
    
    def _generate_skill_trend_recommendations(self, skill: str, metrics: dict, predictions: dict) -> list:
        """生成技能趋势建议"""
        recommendations = []
        
        trend_direction = metrics['trend_direction']
        change_rate = metrics['change_rate']
        
        if trend_direction == '上升':
            if change_rate > 30:
                recommendations.append(f"强烈建议立即学习{skill}技能，市场需求激增")
            else:
                recommendations.append(f"建议优先学习{skill}技能，市场前景良好")
        elif trend_direction == '下降':
            recommendations.append(f"建议关注{skill}的替代技术，准备技能转型")
        else:
            recommendations.append(f"{skill}技能稳定，可以作为基础技能持续维护")
        
        # 基于预测的建议
        if predictions and predictions.get('future_trend'):
            future_trend = predictions['future_trend']
            if future_trend == '继续上升':
                recommendations.append("预测显示未来需求将继续增长，建议深入学习")
            elif future_trend == '可能下降':
                recommendations.append("预测显示未来需求可能下降，建议谨慎投入")
        
        recommendations.append(f"持续关注{skill}技能的市场动态和技术发展")
        
        return recommendations
    
    def _calculate_overall_market_metrics(self, skills_data: list) -> dict:
        """计算整体市场指标"""
        if not skills_data:
            return {}
        
        # 计算平均变化率
        change_rates = [skill['change_rate'] for skill in skills_data]
        avg_change_rate = sum(change_rates) / len(change_rates)
        
        # 统计趋势方向
        rising_count = len([s for s in skills_data if s['trend_direction'] == '上升'])
        declining_count = len([s for s in skills_data if s['trend_direction'] == '下降'])
        stable_count = len(skills_data) - rising_count - declining_count
        
        # 确定市场整体趋势
        if rising_count > declining_count * 1.5:
            market_trend = '积极'
        elif declining_count > rising_count * 1.5:
            market_trend = '消极'
        else:
            market_trend = '稳定'
        
        return {
            'total_skills_analyzed': len(skills_data),
            'average_change_rate': avg_change_rate,
            'rising_skills_count': rising_count,
            'declining_skills_count': declining_count,
            'stable_skills_count': stable_count,
            'market_trend': market_trend,
            'market_momentum': 'strong' if abs(avg_change_rate) > 15 else 'moderate' if abs(avg_change_rate) > 5 else 'weak'
        }
    
    def _analyze_skill_category_trends(self, skills_data: list) -> dict:
        """分析技能分类趋势"""
        # 简化的技能分类
        categories = {
            '编程语言': ['python', 'java', 'javascript', 'go', 'rust', 'typescript'],
            '前端框架': ['react', 'vue', 'angular', 'svelte'],
            '后端框架': ['spring', 'django', 'flask', 'express'],
            '数据库': ['mysql', 'postgresql', 'mongodb', 'redis'],
            '云平台': ['aws', 'azure', 'gcp', 'docker', 'kubernetes'],
            '人工智能': ['tensorflow', 'pytorch', 'scikit-learn', 'opencv']
        }
        
        category_trends = {}
        
        for category, category_skills in categories.items():
            category_data = []
            for skill_info in skills_data:
                skill = skill_info['skill'].lower()
                if any(cat_skill in skill for cat_skill in category_skills):
                    category_data.append(skill_info)
            
            if category_data:
                avg_change = sum(s['change_rate'] for s in category_data) / len(category_data)
                rising_count = len([s for s in category_data if s['trend_direction'] == '上升'])
                
                category_trends[category] = {
                    'skills_count': len(category_data),
                    'average_change_rate': avg_change,
                    'rising_skills_count': rising_count,
                    'trend_direction': '上升' if avg_change > 5 else '下降' if avg_change < -5 else '稳定'
                }
        
        return category_trends
    
    def _generate_overall_trend_insights(self, skills_data: list, emerging_skills: list,
                                       declining_skills: list, metrics: dict) -> list:
        """生成整体趋势洞察"""
        insights = []
        
        market_trend = metrics.get('market_trend', '稳定')
        avg_change = metrics.get('average_change_rate', 0)
        
        # 市场整体趋势洞察
        if market_trend == '积极':
            insights.append(f"技能市场整体呈积极趋势，平均增长率{avg_change:.1f}%")
        elif market_trend == '消极':
            insights.append(f"技能市场整体趋势偏消极，平均变化率{avg_change:.1f}%")
        else:
            insights.append("技能市场整体保持稳定，各技能需求相对均衡")
        
        # 新兴技能洞察
        if emerging_skills:
            top_emerging = emerging_skills[0]
            insights.append(f"最热门的新兴技能是{top_emerging['skill']}，增长率{top_emerging['change_rate']:.1f}%")
        
        # 衰落技能洞察
        if declining_skills:
            insights.append(f"有{len(declining_skills)}个技能需求下降，可能面临技术更新")
        
        # 市场动力洞察
        momentum = metrics.get('market_momentum', 'moderate')
        if momentum == 'strong':
            insights.append("市场变化动力强劲，技能更新换代较快")
        elif momentum == 'weak':
            insights.append("市场变化相对缓慢，技能需求较为稳定")
        
        return insights
    
    def _generate_overall_trend_recommendations(self, emerging_skills: list, declining_skills: list) -> list:
        """生成整体趋势建议"""
        recommendations = []
        
        # 新兴技能建议
        if emerging_skills:
            top_3_emerging = [skill['skill'] for skill in emerging_skills[:3]]
            recommendations.append(f"重点关注新兴技能：{', '.join(top_3_emerging)}")
        
        # 技能组合建议
        if len(emerging_skills) >= 2:
            recommendations.append("建议学习多个新兴技能，形成技能组合优势")
        
        # 风险规避建议
        if declining_skills:
            recommendations.append("及时更新技能栈，避免依赖需求下降的技能")
        
        recommendations.append("持续关注技能市场趋势，保持学习敏感度")
        recommendations.append("结合个人兴趣和市场趋势，制定技能发展规划")
        
        return recommendations
    
    def _get_salary_timeline_data(self, skill: Optional[str], time_period: int) -> list:
        """获取薪资时间序列数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period)
            
            conditions = ["jd.salary IS NOT NULL AND jd.salary != ''"]
            params = []
            
            if skill:
                skill_pattern = f"%{self._standardize_skill_name(skill)}%"
                conditions.append("(LOWER(jd.keyword) LIKE ? OR LOWER(jd.description) LIKE ? OR LOWER(jd.requirements) LIKE ?)")
                params.extend([skill_pattern, skill_pattern, skill_pattern])
            
            conditions.append("j.created_at >= ? AND j.created_at <= ?")
            params.extend([start_date.isoformat(), end_date.isoformat()])
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
            SELECT
                DATE(j.created_at) as date,
                AVG(CASE
                    WHEN jd.salary LIKE '%k%' THEN CAST(SUBSTR(jd.salary, 1, INSTR(jd.salary, 'k')-1) AS REAL) * 1000
                    WHEN jd.salary LIKE '%万%' THEN CAST(SUBSTR(jd.salary, 1, INSTR(jd.salary, '万')-1) AS REAL) * 10000
                    ELSE 0
                END) as avg_salary,
                COUNT(*) as job_count
            FROM jobs j
            JOIN job_details jd ON j.job_id = jd.job_id
            WHERE {where_clause}
            GROUP BY DATE(j.created_at)
            HAVING avg_salary > 0
            ORDER BY date
            """
            
            return self._execute_query(query, tuple(params))
            
        except Exception as e:
            self.logger.error(f"获取薪资时间序列数据失败: {e}")
            return []
    
    def _calculate_salary_trend_metrics(self, timeline_data: list) -> dict:
        """计算薪资趋势指标"""
        if len(timeline_data) < 2:
            return {
                'trend_direction': '数据不足',
                'avg_change': 0,
                'current_avg': 0,
                'volatility': '未知'
            }
        
        # 计算薪资变化
        first_salary = timeline_data[0]['avg_salary']
        last_salary = timeline_data[-1]['avg_salary']
        
        if first_salary == 0:
            avg_change = 0
        else:
            avg_change = ((last_salary - first_salary) / first_salary) * 100
        
        # 确定趋势方向
        if avg_change > 3:
            trend_direction = '上升'
        elif avg_change < -3:
            trend_direction = '下降'
        else:
            trend_direction = '稳定'
        
        # 计算波动性
        salaries = [item['avg_salary'] for item in timeline_data]
        mean_salary = sum(salaries) / len(salaries)
        variance = sum((x - mean_salary) ** 2 for x in salaries) / len(salaries)
        std_dev = variance ** 0.5
        volatility_ratio = std_dev / mean_salary if mean_salary > 0 else 0
        
        if volatility_ratio > 0.1:
            volatility = '高'
        elif volatility_ratio > 0.05:
            volatility = '中'
        else:
            volatility = '低'
        
        return {
            'trend_direction': trend_direction,
            'avg_change': avg_change,
            'current_avg': int(last_salary),
            'volatility': volatility,
            'data_points': len(timeline_data),
            'salary_range': {
                'min': int(min(salaries)),
                'max': int(max(salaries))
            }
        }
    
    def _generate_salary_trend_insights(self, metrics: dict, skill: Optional[str] = None) -> list:
        """生成薪资趋势洞察"""
        insights = []
        
        trend_direction = metrics['trend_direction']
        avg_change = metrics['avg_change']
        current_avg = metrics['current_avg']
        
        # 薪资趋势洞察
        if trend_direction == '上升':
            if avg_change > 10:
                insights.append(f"薪资大幅上升{avg_change:.1f}%，市场对该技能需求强劲")
            else:
                insights.append(f"薪资温和上升{avg_change:.1f}%，保持良好增长势头")
        elif trend_direction == '下降':
            insights.append(f"薪资下降{abs(avg_change):.1f}%，可能受市场供需影响")
        else:
            insights.append("薪资保持稳定，市场相对成熟")
        
        # 薪资水平洞察
        current_annual = current_avg * 12
        if current_avg > 300000:
            insights.append(f"当前平均月薪{current_avg//1000}k（年薪约{current_annual//10000}万元），属于高薪技能")
        elif current_avg > 200000:
            insights.append(f"当前平均月薪{current_avg//1000}k（年薪约{current_annual//10000}万元），薪资水平良好")
        else:
            insights.append(f"当前平均月薪{current_avg//1000}k（年薪约{current_annual//10000}万元），有提升空间")
        
        # 波动性洞察
        volatility = metrics['volatility']
        if volatility == '高':
            insights.append("薪资波动较大，建议关注市场变化")
        elif volatility == '低':
            insights.append("薪资相对稳定，适合长期职业规划")
        
        return insights
    
    def _generate_salary_trend_recommendations(self, metrics: dict, skill: Optional[str] = None) -> list:
        """生成薪资趋势建议"""
        recommendations = []
        
        trend_direction = metrics['trend_direction']
        current_avg = metrics['current_avg']
        
        if trend_direction == '上升':
            recommendations.append("薪资上升趋势良好，建议抓住机会提升技能深度")
        elif trend_direction == '下降':
            recommendations.append("薪资下降需要关注，建议考虑技能转型或升级")
        
        # 基于薪资水平的建议
        if current_avg < 200000:
            recommendations.append("当前薪资水平有提升空间，建议关注高薪技能方向")
        
        if skill:
            recommendations.append(f"持续关注{skill}技能的薪资变化和市场动态")
        
        recommendations.append("结合薪资趋势和个人能力，制定合理的薪资期望")
        
        return recommendations
    
    def _compare_time_periods(self, skill: str, time_period: int) -> dict:
        """对比不同时期的数据"""
        # 获取当前时期和前一时期的数据进行对比
        current_data = self._get_skill_timeline_data_vector(skill, time_period)
        previous_data = self._get_skill_timeline_data_vector(skill, time_period, offset=time_period)
        
        if not current_data or not previous_data:
            return {}
        
        current_total = sum(item['job_count'] for item in current_data)
        previous_total = sum(item['job_count'] for item in previous_data)
        
        if previous_total == 0:
            change_rate = 100 if current_total > 0 else 0
        else:
            change_rate = ((current_total - previous_total) / previous_total) * 100
        
        return {
            'current_period_total': current_total,
            'previous_period_total': previous_total,
            'period_change_rate': change_rate,
            'comparison_result': '增长' if change_rate > 0 else '下降' if change_rate < 0 else '持平'
        }
    
    def _predict_skill_trend(self, timeline_data: list, skill: str) -> dict:
        """预测技能趋势"""
        if len(timeline_data) < 5:
            return {'prediction': '数据不足，无法预测'}
        
        # 简单的线性趋势预测
        values = [item['job_count'] for item in timeline_data]
        n = len(values)
        
        # 计算线性回归斜率
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # 预测未来趋势
        if slope > 1:
            future_trend = '继续上升'
            confidence = 'high' if slope > 2 else 'medium'
        elif slope < -1:
            future_trend = '可能下降'
            confidence = 'high' if slope < -2 else 'medium'
        else:
            future_trend = '保持稳定'
            confidence = 'medium'
        
        return {
            'future_trend': future_trend,
            'confidence_level': confidence,
            'predicted_change': slope * 7,  # 预测未来7天的变化
            'prediction_basis': f'基于{n}个数据点的线性趋势分析'
        }
    
    def _analyze_trend_patterns(self, timeline_data: list) -> dict:
        """分析趋势模式"""
        if len(timeline_data) < 7:
            return {'pattern': '数据不足'}
        
        values = [item['job_count'] for item in timeline_data]
        
        # 检测周期性模式（简化版）
        # 检查是否有周期性波动
        weekly_pattern = []
        for i in range(0, len(values) - 6, 7):
            week_values = values[i:i+7]
            if len(week_values) == 7:
                weekly_pattern.append(sum(week_values))
        
        if len(weekly_pattern) >= 2:
            week_variance = sum((x - sum(weekly_pattern)/len(weekly_pattern))**2 for x in weekly_pattern) / len(weekly_pattern)
            if week_variance < (sum(weekly_pattern)/len(weekly_pattern)) * 0.1:
                pattern_type = '周期性稳定'
            else:
                pattern_type = '不规则波动'
        else:
            pattern_type = '线性趋势'
        
        return {
            'pattern': pattern_type,
            'weekly_analysis': weekly_pattern,
            'volatility_assessment': '高' if len(weekly_pattern) > 0 and week_variance > sum(weekly_pattern)/len(weekly_pattern) * 0.2 else '低'
        }
    
    def _get_location_trends_data(self, time_period: int) -> list:
        """获取地区趋势数据"""
        try:
            major_cities = ['北京', '上海', '深圳', '杭州', '广州', '成都', '南京', '武汉', '西安', '苏州']
            location_trends = []
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period)
            mid_date = start_date + timedelta(days=time_period//2)
            
            for city in major_cities:
                # 获取前半期和后半期的职位数量
                city_pattern = f"%{city}%"
                
                # 前半期数据
                early_query = """
                SELECT COUNT(*) as job_count
                FROM jobs j
                JOIN job_details jd ON j.job_id = jd.job_id
                WHERE LOWER(jd.location) LIKE ?
                AND j.created_at >= ? AND j.created_at < ?
                """
                early_result = self._execute_query(early_query, (city_pattern, start_date.isoformat(), mid_date.isoformat()))
                early_count = early_result[0]['job_count'] if early_result else 0
                
                # 后半期数据
                late_query = """
                SELECT COUNT(*) as job_count
                FROM jobs j
                JOIN job_details jd ON j.job_id = jd.job_id
                WHERE LOWER(jd.location) LIKE ?
                AND j.created_at >= ? AND j.created_at <= ?
                """
                late_result = self._execute_query(late_query, (city_pattern, mid_date.isoformat(), end_date.isoformat()))
                late_count = late_result[0]['job_count'] if late_result else 0
                
                # 计算变化率
                if early_count == 0:
                    change_rate = 100 if late_count > 0 else 0
                else:
                    change_rate = ((late_count - early_count) / early_count) * 100
                
                # 确定趋势方向
                if change_rate > 5:
                    trend_direction = '上升'
                elif change_rate < -5:
                    trend_direction = '下降'
                else:
                    trend_direction = '稳定'
                
                location_trends.append({
                    'location': city,
                    'current_jobs': late_count,
                    'previous_jobs': early_count,
                    'change_rate': change_rate,
                    'trend_direction': trend_direction
                })
            
            # 按当前职位数量排序
            location_trends.sort(key=lambda x: x['current_jobs'], reverse=True)
            return location_trends
            
        except Exception as e:
            self.logger.error(f"获取地区趋势数据失败: {e}")
            return []
    
    def _calculate_location_trend_metrics(self, location_trends: list) -> dict:
        """计算地区趋势指标"""
        if not location_trends:
            return {}
        
        total_current = sum(loc['current_jobs'] for loc in location_trends)
        total_previous = sum(loc['previous_jobs'] for loc in location_trends)
        
        overall_change = ((total_current - total_previous) / total_previous * 100) if total_previous > 0 else 0
        
        rising_cities = len([loc for loc in location_trends if loc['trend_direction'] == '上升'])
        declining_cities = len([loc for loc in location_trends if loc['trend_direction'] == '下降'])
        
        return {
            'total_cities_analyzed': len(location_trends),
            'total_current_jobs': total_current,
            'total_previous_jobs': total_previous,
            'overall_change_rate': overall_change,
            'rising_cities_count': rising_cities,
            'declining_cities_count': declining_cities,
            'market_concentration': location_trends[0]['current_jobs'] / total_current * 100 if total_current > 0 else 0
        }
    
    def _generate_location_trend_insights(self, location_trends: list, hot_locations: list, cold_locations: list) -> list:
        """生成地区趋势洞察"""
        insights = []
        
        if location_trends:
            top_city = location_trends[0]
            insights.append(f"{top_city['location']}是当前最活跃的就业市场，职位数量{top_city['current_jobs']}个")
        
        if hot_locations:
            hot_names = [loc['location'] for loc in hot_locations[:3]]
            insights.append(f"就业热点城市：{', '.join(hot_names)}，需求增长明显")
        
        if cold_locations:
            insights.append(f"有{len(cold_locations)}个城市就业需求下降，可能受经济环境影响")
        
        # 地区集中度分析
        if len(location_trends) >= 3:
            top3_jobs = sum(loc['current_jobs'] for loc in location_trends[:3])
            total_jobs = sum(loc['current_jobs'] for loc in location_trends)
            concentration = top3_jobs / total_jobs * 100 if total_jobs > 0 else 0
            
            if concentration > 70:
                insights.append("就业机会高度集中在少数城市，地区差异明显")
            else:
                insights.append("就业机会在各城市间分布相对均衡")
        
        return insights
    
    def _generate_location_trend_recommendations(self, hot_locations: list, cold_locations: list) -> list:
        """生成地区趋势建议"""
        recommendations = []
        
        if hot_locations:
            top_hot = hot_locations[0]
            recommendations.append(f"建议关注{top_hot['location']}的就业机会，市场需求增长{top_hot['change_rate']:.1f}%")
        
        if len(hot_locations) >= 2:
            recommendations.append("可以考虑在多个热点城市同时寻找机会，增加成功率")
        
        if cold_locations:
            recommendations.append("谨慎考虑需求下降城市的机会，关注当地经济发展趋势")
        
        recommendations.append("选择城市时要综合考虑就业趋势、薪资水平和生活成本")
        recommendations.append("关注新兴城市的发展机会，可能存在蓝海市场")
        
        return recommendations
    
    def _get_overall_market_timeline(self, time_period: int) -> list:
        """获取整体市场时间序列数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period)
            
            query = """
            SELECT
                DATE(created_at) as date,
                COUNT(*) as job_count
            FROM jobs
            WHERE created_at >= ? AND created_at <= ?
            GROUP BY DATE(created_at)
            ORDER BY date
            """
            
            return self._execute_query(query, (start_date.isoformat(), end_date.isoformat()))
            
        except Exception as e:
            self.logger.error(f"获取整体市场时间序列数据失败: {e}")
            return []
    
    def _calculate_market_trend_metrics(self, market_data: list) -> dict:
        """计算市场趋势指标"""
        if len(market_data) < 2:
            return {
                'overall_trend': '数据不足',
                'job_change_rate': 0,
                'market_activity': '未知',
                'competition_level': '未知'
            }
        
        # 计算整体变化率
        first_count = market_data[0]['job_count']
        last_count = market_data[-1]['job_count']
        
        if first_count == 0:
            job_change_rate = 100 if last_count > 0 else 0
        else:
            job_change_rate = ((last_count - first_count) / first_count) * 100
        
        # 确定整体趋势
        if job_change_rate > 10:
            overall_trend = '强劲增长'
        elif job_change_rate > 3:
            overall_trend = '温和增长'
        elif job_change_rate < -10:
            overall_trend = '明显下降'
        elif job_change_rate < -3:
            overall_trend = '轻微下降'
        else:
            overall_trend = '基本稳定'
        
        # 计算市场活跃度
        total_jobs = sum(item['job_count'] for item in market_data)
        avg_daily_jobs = total_jobs / len(market_data)
        
        if avg_daily_jobs > 50:
            market_activity = '高'
        elif avg_daily_jobs > 20:
            market_activity = '中'
        else:
            market_activity = '低'
        
        # 简化的竞争程度评估
        job_counts = [item['job_count'] for item in market_data]
        max_jobs = max(job_counts)
        min_jobs = min(job_counts)
        
        if max_jobs > min_jobs * 2:
            competition_level = '波动较大'
        else:
            competition_level = '相对稳定'
        
        return {
            'overall_trend': overall_trend,
            'job_change_rate': job_change_rate,
            'market_activity': market_activity,
            'competition_level': competition_level,
            'total_jobs_period': total_jobs,
            'avg_daily_jobs': avg_daily_jobs,
            'data_points': len(market_data)
        }
    
    def _analyze_industry_trends(self, time_period: int) -> dict:
        """分析行业趋势"""
        try:
            # 简化的行业分类（基于公司名称和职位描述）
            industries = {
                '互联网': ['科技', '网络', '互联网', '电商', '平台'],
                '金融': ['银行', '金融', '保险', '证券', '投资'],
                '制造业': ['制造', '工厂', '生产', '机械', '汽车'],
                '教育': ['教育', '培训', '学校', '大学', '学院'],
                '医疗': ['医院', '医疗', '健康', '药品', '生物']
            }
            
            industry_trends = {}
            
            for industry, keywords in industries.items():
                # 构建查询条件
                keyword_conditions = []
                params = []
                
                for keyword in keywords:
                    keyword_conditions.append("(LOWER(j.company) LIKE ? OR LOWER(j.title) LIKE ?)")
                    params.extend([f"%{keyword}%", f"%{keyword}%"])
                
                where_clause = " OR ".join(keyword_conditions)
                
                # 获取该行业的职位趋势
                end_date = datetime.now()
                start_date = end_date - timedelta(days=time_period)
                
                query = f"""
                SELECT COUNT(*) as job_count
                FROM jobs j
                WHERE ({where_clause})
                AND j.created_at >= ? AND j.created_at <= ?
                """
                
                params.extend([start_date.isoformat(), end_date.isoformat()])
                result = self._execute_query(query, tuple(params))
                
                if result:
                    industry_trends[industry] = result[0]['job_count']
            
            return industry_trends
            
        except Exception as e:
            self.logger.error(f"分析行业趋势失败: {e}")
            return {}
    
    def _predict_market_trends(self, market_data: list) -> dict:
        """预测市场趋势"""
        if len(market_data) < 7:
            return {'prediction': '数据不足，无法预测'}
        
        # 使用简单的移动平均预测
        recent_values = [item['job_count'] for item in market_data[-7:]]
        moving_avg = sum(recent_values) / len(recent_values)
        
        # 计算趋势斜率
        values = [item['job_count'] for item in market_data]
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # 预测未来趋势
        predicted_change = slope * 7  # 预测未来7天
        
        if predicted_change > 5:
            future_trend = '继续增长'
            confidence = 'medium'
        elif predicted_change < -5:
            future_trend = '可能下降'
            confidence = 'medium'
        else:
            future_trend = '保持稳定'
            confidence = 'high'
        
        return {
            'future_trend': future_trend,
            'confidence_level': confidence,
            'predicted_weekly_change': predicted_change,
            'moving_average': moving_avg,
            'prediction_basis': f'基于{n}个数据点的趋势分析'
        }
    
    def _calculate_market_indicators(self, market_data: list) -> dict:
        """计算市场指标"""
        if not market_data:
            return {}
        
        job_counts = [item['job_count'] for item in market_data]
        
        # 基本统计指标
        total_jobs = sum(job_counts)
        avg_jobs = total_jobs / len(job_counts)
        max_jobs = max(job_counts)
        min_jobs = min(job_counts)
        
        # 波动性指标
        variance = sum((x - avg_jobs) ** 2 for x in job_counts) / len(job_counts)
        volatility = (variance ** 0.5) / avg_jobs if avg_jobs > 0 else 0
        
        # 增长动量指标
        if len(job_counts) >= 7:
            recent_avg = sum(job_counts[-7:]) / 7
            early_avg = sum(job_counts[:7]) / 7
            momentum = (recent_avg - early_avg) / early_avg * 100 if early_avg > 0 else 0
        else:
            momentum = 0
        
        return {
            'total_jobs': total_jobs,
            'average_daily_jobs': avg_jobs,
            'max_daily_jobs': max_jobs,
            'min_daily_jobs': min_jobs,
            'volatility_index': volatility,
            'growth_momentum': momentum,
            'market_stability': 'stable' if volatility < 0.2 else 'volatile'
        }
    
    def _generate_market_trend_insights(self, metrics: dict, industry_trends: dict) -> list:
        """生成市场趋势洞察"""
        insights = []
        
        overall_trend = metrics.get('overall_trend', '未知')
        job_change_rate = metrics.get('job_change_rate', 0)
        market_activity = metrics.get('market_activity', '未知')
        
        # 整体趋势洞察
        if overall_trend == '强劲增长':
            insights.append(f"就业市场呈现强劲增长态势，职位增长{job_change_rate:.1f}%")
        elif overall_trend == '明显下降':
            insights.append(f"就业市场面临挑战，职位减少{abs(job_change_rate):.1f}%")
        else:
            insights.append(f"就业市场{overall_trend}，变化率{job_change_rate:.1f}%")
        
        # 市场活跃度洞察
        if market_activity == '高':
            insights.append("市场活跃度高，职位发布频繁，求职机会较多")
        elif market_activity == '低':
            insights.append("市场活跃度较低，职位发布相对稀少")
        
        # 行业趋势洞察
        if industry_trends:
            top_industry = max(industry_trends.items(), key=lambda x: x[1])
            insights.append(f"{top_industry[0]}行业职位最多，共{top_industry[1]}个职位")
        
        return insights
    
    def _generate_market_trend_recommendations(self, metrics: dict, predictions: dict) -> list:
        """生成市场趋势建议"""
        recommendations = []
        
        overall_trend = metrics.get('overall_trend', '未知')
        market_activity = metrics.get('market_activity', '未知')
        
        # 基于整体趋势的建议
        if overall_trend in ['强劲增长', '温和增长']:
            recommendations.append("市场趋势积极，建议积极寻找机会，提升技能竞争力")
        elif overall_trend in ['明显下降', '轻微下降']:
            recommendations.append("市场趋势偏弱，建议谨慎选择，关注稳定性较好的职位")
        else:
            recommendations.append("市场相对稳定，可以按计划进行职业发展")
        
        # 基于市场活跃度的建议
        if market_activity == '高':
            recommendations.append("市场活跃度高，建议快速响应，抓住机会窗口")
        elif market_activity == '低':
            recommendations.append("市场活跃度低，建议耐心等待，提升自身能力")
        
        # 基于预测的建议
        if predictions and predictions.get('future_trend'):
            future_trend = predictions['future_trend']
            if future_trend == '继续增长':
                recommendations.append("预测市场将继续增长，建议提前准备，抢占先机")
            elif future_trend == '可能下降':
                recommendations.append("预测市场可能下降，建议做好风险准备")
        
        recommendations.append("持续关注市场动态，灵活调整求职策略")
        
        return recommendations
    
    def _analyze_salary_range_changes(self, timeline_data: list) -> dict:
        """分析薪资区间变化"""
        if not timeline_data:
            return {}
        
        # 简化的薪资区间分析
        ranges = {'low': [], 'medium': [], 'high': []}
        
        for item in timeline_data:
            avg_salary = item['avg_salary']
            if avg_salary < 200000:
                ranges['low'].append(avg_salary)
            elif avg_salary < 400000:
                ranges['medium'].append(avg_salary)
            else:
                ranges['high'].append(avg_salary)
        
        range_changes = {}
        for range_name, salaries in ranges.items():
            if salaries:
                range_changes[f'{range_name}_range'] = {
                    'count': len(salaries),
                    'avg_salary': sum(salaries) / len(salaries),
                    'trend': '上升' if len(salaries) > len(timeline_data) / 4 else '稳定'
                }
        
        return range_changes
    
    def _analyze_salary_trend_patterns(self, timeline_data: list) -> dict:
        """分析薪资趋势模式"""
        if len(timeline_data) < 5:
            return {'pattern': '数据不足'}
        
        salaries = [item['avg_salary'] for item in timeline_data]
        
        # 检测趋势模式
        increases = sum(1 for i in range(1, len(salaries)) if salaries[i] > salaries[i-1])
        decreases = sum(1 for i in range(1, len(salaries)) if salaries[i] < salaries[i-1])
        
        if increases > decreases * 1.5:
            pattern = '持续上升'
        elif decreases > increases * 1.5:
            pattern = '持续下降'
        else:
            pattern = '波动变化'
        
        return {
            'pattern': pattern,
            'increases_count': increases,
            'decreases_count': decreases,
            'stability': 'stable' if abs(increases - decreases) <= 1 else 'volatile'
        }
    
    def _analyze_regional_patterns(self, location_trends: list) -> dict:
        """分析区域模式"""
        if not location_trends:
            return {}
        
        # 按地区分类（简化版）
        regions = {
            '一线城市': ['北京', '上海', '深圳', '广州'],
            '新一线城市': ['杭州', '成都', '南京', '武汉', '西安', '苏州'],
            '其他城市': []
        }
        
        regional_analysis = {}
        
        for region, cities in regions.items():
            region_data = [loc for loc in location_trends if loc['location'] in cities]
            if region_data:
                total_jobs = sum(loc['current_jobs'] for loc in region_data)
                avg_change = sum(loc['change_rate'] for loc in region_data) / len(region_data)
                
                regional_analysis[region] = {
                    'cities_count': len(region_data),
                    'total_jobs': total_jobs,
                    'average_change_rate': avg_change,
                    'trend': '增长' if avg_change > 0 else '下降' if avg_change < 0 else '稳定'
                }
        
        return regional_analysis