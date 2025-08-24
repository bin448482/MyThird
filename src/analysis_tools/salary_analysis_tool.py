
"""
薪资分析工具

基于RAG系统和向量数据库，分析职位市场中的薪资情况
结合语义搜索和数据库统计，提供准确的薪资市场洞察
"""

from typing import Optional
from pydantic import BaseModel, Field
from .base_tool import BaseAnalysisTool


class SalaryAnalysisInput(BaseModel):
    """薪资分析输入参数"""
    skill: Optional[str] = Field(None, description="特定技能名称，如'Python'、'Java'等")
    location: Optional[str] = Field(None, description="地区名称，如'北京'、'上海'等")
    experience: Optional[str] = Field(None, description="经验要求，如'3-5年'、'5年以上'等")
    position: Optional[str] = Field(None, description="职位名称，如'开发工程师'、'架构师'等")
    compare_locations: Optional[bool] = Field(False, description="是否比较不同地区薪资")
    include_percentiles: Optional[bool] = Field(True, description="是否包含薪资分位数分析")


class SalaryAnalysisTool(BaseAnalysisTool):
    """薪资分析工具 - 基于RAG和向量搜索"""
    
    name: str = "salary_analysis"
    description: str = """
    基于RAG系统分析职位市场中的薪资情况。结合向量搜索和数据库统计：
    1. 分析特定技能的薪资水平和分布
    2. 比较不同地区的薪资差异
    3. 分析经验对薪资的影响
    4. 通过语义搜索发现薪资趋势
    5. 提供薪资谈判建议
    
    输入参数：
    - skill: 特定技能名称（可选）
    - location: 地区名称（可选）
    - experience: 经验要求（可选）
    - position: 职位名称（可选）
    - compare_locations: 是否比较不同地区薪资（默认false）
    - include_percentiles: 是否包含薪资分位数分析（默认true）
    """
    args_schema: type = SalaryAnalysisInput
    
    def __init__(self, db_manager, vector_manager=None, **kwargs):
        """
        初始化薪资分析工具
        
        Args:
            db_manager: 数据库管理器
            vector_manager: 向量数据库管理器
            **kwargs: 其他参数
        """
        super().__init__(db_manager, vector_manager=vector_manager, **kwargs)
    
    def _run(self, skill: Optional[str] = None, location: Optional[str] = None,
             experience: Optional[str] = None, position: Optional[str] = None,
             compare_locations: bool = False, include_percentiles: bool = True) -> str:
        """
        执行薪资分析
        
        Args:
            skill: 特定技能名称
            location: 地区名称
            experience: 经验要求
            position: 职位名称
            compare_locations: 是否比较不同地区薪资
            include_percentiles: 是否包含薪资分位数分析
            
        Returns:
            分析结果文本
        """
        try:
            if compare_locations:
                # 地区薪资对比分析
                result = self._analyze_location_salary_comparison(skill, experience, position)
            elif skill or position:
                # 特定技能或职位的薪资分析
                result = self._analyze_specific_salary(skill, location, experience, position, include_percentiles)
            else:
                # 整体薪资市场分析
                result = self._analyze_overall_salary_market(location, include_percentiles)
            
            return self._format_result(result)
            
        except Exception as e:
            self.logger.error(f"薪资分析失败: {e}")
            return f"分析失败: {str(e)}"
    
    def _analyze_specific_salary(self, skill: Optional[str] = None, location: Optional[str] = None,
                                experience: Optional[str] = None, position: Optional[str] = None,
                                include_percentiles: bool = True) -> dict:
        """
        分析特定条件下的薪资情况
        
        Args:
            skill: 技能名称
            location: 地区名称
            experience: 经验要求
            position: 职位名称
            include_percentiles: 是否包含分位数分析
            
        Returns:
            分析结果字典
        """
        # 1. 使用向量搜索找到相关职位
        job_ids = self._get_relevant_jobs_vector(skill, location, experience, position)
        
        # 2. 构建查询条件
        conditions = []
        params = []
        
        if job_ids:
            # 使用向量搜索结果
            placeholders = ','.join('?' * len(job_ids))
            base_condition = f"j.job_id IN ({placeholders})"
            conditions.append(base_condition)
            params.extend(job_ids)
        else:
            # 使用传统查询条件
            if skill:
                skill_pattern = f"%{self._standardize_skill_name(skill)}%"
                conditions.append("(LOWER(jd.keyword) LIKE ? OR LOWER(jd.description) LIKE ? OR LOWER(jd.requirements) LIKE ?)")
                params.extend([skill_pattern, skill_pattern, skill_pattern])
            
            if location:
                location_pattern = f"%{location}%"
                conditions.append("LOWER(jd.location) LIKE ?")
                params.append(location_pattern)
            
            if experience:
                exp_pattern = f"%{experience}%"
                conditions.append("LOWER(jd.experience) LIKE ?")
                params.append(exp_pattern)
            
            if position:
                pos_pattern = f"%{position}%"
                conditions.append("LOWER(j.title) LIKE ?")
                params.append(pos_pattern)
        
        # 3. 执行薪资查询
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        salary_query = f"""
        SELECT 
            jd.salary,
            j.title,
            j.company,
            jd.location,
            jd.experience,
            jd.keyword
        FROM jobs j
        JOIN job_details jd ON j.job_id = jd.job_id
        WHERE {where_clause}
        AND jd.salary IS NOT NULL AND jd.salary != ''
        """
        
        salary_results = self._execute_query(salary_query, tuple(params))
        
        if not salary_results:
            return {
                'title': '薪资分析',
                'summary': '未找到符合条件的薪资数据',
                'data': [],
                'statistics': {},
                'insights': ['当前条件下暂无薪资数据，建议放宽搜索条件'],
                'recommendations': ['尝试搜索相关技能或扩大地区范围'],
                'data_source': '基于RAG向量搜索和薪资数据库分析'
            }
        
        # 4. 解析和统计薪资数据
        salary_stats = self._calculate_salary_statistics(salary_results, include_percentiles)
        
        # 5. 生成分析标题
        title_parts = []
        if skill:
            title_parts.append(f"{skill}技能")
        if position:
            title_parts.append(f"{position}职位")
        if location:
            title_parts.append(f"{location}地区")
        if experience:
            title_parts.append(f"{experience}经验")
        
        title = f"{'、'.join(title_parts)}薪资分析" if title_parts else "薪资分析"
        
        # 计算年薪（月薪 * 12）
        avg_annual_salary = salary_stats["average"] * 12
        min_annual_salary = salary_stats["min"] * 12
        max_annual_salary = salary_stats["max"] * 12
        median_annual_salary = salary_stats["median"] * 12
        
        # 6. 构建结果
        result = {
            'title': title,
            'summary': f'基于{len(salary_results)}个职位的薪资数据分析，平均月薪{salary_stats["average"]//1000}k，年薪约{avg_annual_salary//10000}万元',
            'data': [
                {
                    'name': '平均月薪',
                    'value': f'{salary_stats["average"]//1000}k',
                    'description': f'月薪{salary_stats["average"]//1000}千元，年薪约{avg_annual_salary//10000}万元'
                },
                {
                    'name': '平均年薪',
                    'value': f'{avg_annual_salary//10000}万元',
                    'description': f'基于月薪计算的年薪水平'
                },
                {
                    'name': '薪资范围',
                    'value': f'{salary_stats["min"]//1000}k - {salary_stats["max"]//1000}k',
                    'description': f'月薪范围，年薪约{min_annual_salary//10000}-{max_annual_salary//10000}万元'
                },
                {
                    'name': '中位数薪资',
                    'value': f'{salary_stats["median"]//1000}k',
                    'description': f'50%的职位薪资水平，年薪约{median_annual_salary//10000}万元'
                },
                {
                    'name': '样本数量',
                    'value': str(len(salary_results)),
                    'description': '分析的职位数量'
                }
            ],
            'statistics': salary_stats,
            'insights': self._generate_salary_insights(salary_stats, skill, location, experience, position),
            'recommendations': self._generate_salary_recommendations(salary_stats, skill, location),
            'related_data': {
                'salary_distribution': salary_stats.get('distribution', []),
                'top_companies': self._get_top_paying_companies(salary_results),
                'experience_impact': self._analyze_experience_salary_impact(salary_results),
                'location_breakdown': self._analyze_location_salary_breakdown(salary_results)
            },
            'data_source': f'基于RAG向量搜索和{len(salary_results)}个职位的薪资分析'
        }
        
        return result
    
    def _analyze_location_salary_comparison(self, skill: Optional[str] = None,
                                          experience: Optional[str] = None,
                                          position: Optional[str] = None) -> dict:
        """
        分析不同地区的薪资对比
        
        Args:
            skill: 技能名称
            experience: 经验要求
            position: 职位名称
            
        Returns:
            地区薪资对比结果
        """
        # 1. 获取主要城市列表
        major_cities = ['北京', '上海', '深圳', '杭州', '广州', '成都', '南京', '武汉', '西安', '苏州']
        
        location_salary_data = []
        
        for city in major_cities:
            # 使用向量搜索获取该城市的相关职位
            job_ids = self._get_relevant_jobs_vector(skill, city, experience, position)
            
            if job_ids:
                # 查询该城市的薪资数据
                placeholders = ','.join('?' * len(job_ids))
                query = f"""
                SELECT jd.salary, COUNT(*) as job_count
                FROM job_details jd
                JOIN jobs j ON jd.job_id = j.job_id
                WHERE j.job_id IN ({placeholders})
                AND jd.salary IS NOT NULL AND jd.salary != ''
                """
                
                city_results = self._execute_query(query, tuple(job_ids))
            else:
                # 传统查询方式
                conditions = [f"LOWER(jd.location) LIKE '%{city.lower()}%'"]
                params = []
                
                if skill:
                    skill_pattern = f"%{self._standardize_skill_name(skill)}%"
                    conditions.append("(LOWER(jd.keyword) LIKE ? OR LOWER(jd.description) LIKE ? OR LOWER(jd.requirements) LIKE ?)")
                    params.extend([skill_pattern, skill_pattern, skill_pattern])
                
                if experience:
                    exp_pattern = f"%{experience}%"
                    conditions.append("LOWER(jd.experience) LIKE ?")
                    params.append(exp_pattern)
                
                if position:
                    pos_pattern = f"%{position}%"
                    conditions.append("LOWER(j.title) LIKE ?")
                    params.append(pos_pattern)
                
                where_clause = " AND ".join(conditions)
                
                query = f"""
                SELECT jd.salary
                FROM jobs j
                JOIN job_details jd ON j.job_id = jd.job_id
                WHERE {where_clause}
                AND jd.salary IS NOT NULL AND jd.salary != ''
                """
                
                city_results = self._execute_query(query, tuple(params))
            
            if city_results:
                # 计算该城市的薪资统计
                city_salaries = []
                for result in city_results:
                    salary_info = self._parse_salary_range(result['salary'])
                    if salary_info['avg'] > 0:
                        city_salaries.append(salary_info['avg'])
                
                if city_salaries:
                    avg_salary = sum(city_salaries) // len(city_salaries)
                    location_salary_data.append({
                        'city': city,
                        'average_salary': avg_salary,
                        'job_count': len(city_salaries),
                        'min_salary': min(city_salaries),
                        'max_salary': max(city_salaries)
                    })
        
        # 按平均薪资排序
        location_salary_data.sort(key=lambda x: x['average_salary'], reverse=True)
        
        if not location_salary_data:
            return {
                'title': '地区薪资对比分析',
                'summary': '未找到足够的地区薪资数据',
                'data': [],
                'statistics': {},
                'insights': ['当前条件下各地区薪资数据不足'],
                'recommendations': ['建议放宽搜索条件或关注主要一线城市'],
                'data_source': '基于RAG向量搜索和地区薪资数据库分析'
            }
        
        # 构建对比结果
        title_parts = []
        if skill:
            title_parts.append(f"{skill}技能")
        if position:
            title_parts.append(f"{position}职位")
        if experience:
            title_parts.append(f"{experience}经验")
        
        title = f"{'、'.join(title_parts)}地区薪资对比" if title_parts else "地区薪资对比"
        
        # 计算薪资差异
        highest_city = location_salary_data[0]
        lowest_city = location_salary_data[-1]
        salary_gap = highest_city['average_salary'] - lowest_city['average_salary']
        gap_percentage = (salary_gap / lowest_city['average_salary']) * 100
        
        # 计算年薪
        highest_annual = highest_city['average_salary'] * 12
        lowest_annual = lowest_city['average_salary'] * 12
        
        result = {
            'title': title,
            'summary': f'分析了{len(location_salary_data)}个主要城市的薪资水平，{highest_city["city"]}薪资最高(月薪{highest_city["average_salary"]//1000}k，年薪约{highest_annual//10000}万元)，{lowest_city["city"]}相对较低(月薪{lowest_city["average_salary"]//1000}k，年薪约{lowest_annual//10000}万元)',
            'data': [
                {
                    'rank': i + 1,
                    'name': city_data['city'],
                    'value': f'{city_data["average_salary"]//1000}k',
                    'percentage': self._format_percentage(city_data['average_salary'], highest_city['average_salary']),
                    'description': f'{city_data["job_count"]}个职位，月薪范围{city_data["min_salary"]//1000}k-{city_data["max_salary"]//1000}k，年薪约{city_data["average_salary"]*12//10000}万元'
                }
                for i, city_data in enumerate(location_salary_data)
            ],
            'statistics': {
                'cities_analyzed': len(location_salary_data),
                'highest_salary_city': highest_city['city'],
                'highest_salary': highest_city['average_salary'],
                'lowest_salary_city': lowest_city['city'],
                'lowest_salary': lowest_city['average_salary'],
                'salary_gap': salary_gap,
                'gap_percentage': gap_percentage,
                'total_jobs_analyzed': sum(city['job_count'] for city in location_salary_data)
            },
            'insights': self._generate_location_comparison_insights(location_salary_data, highest_city, lowest_city, gap_percentage),
            'recommendations': self._generate_location_recommendations(location_salary_data, skill),
            'data_source': f'基于RAG向量搜索和{sum(city["job_count"] for city in location_salary_data)}个职位的地区薪资对比分析'
        }
        
        return result
    
    def _analyze_overall_salary_market(self, location: Optional[str] = None,
                                     include_percentiles: bool = True) -> dict:
        """
        分析整体薪资市场情况
        
        Args:
            location: 地区限制
            include_percentiles: 是否包含分位数分析
            
        Returns:
            整体薪资市场分析结果
        """
        # 构建查询条件
        conditions = ["jd.salary IS NOT NULL AND jd.salary != ''"]
        params = []
        
        if location:
            location_pattern = f"%{location}%"
            conditions.append("LOWER(jd.location) LIKE ?")
            params.append(location_pattern)
        
        where_clause = " AND ".join(conditions)
        
        # 查询所有薪资数据
        query = f"""
        SELECT 
            jd.salary,
            j.title,
            j.company,
            jd.location,
            jd.experience,
            jd.keyword
        FROM jobs j
        JOIN job_details jd ON j.job_id = jd.job_id
        WHERE {where_clause}
        """
        
        salary_results = self._execute_query(query, tuple(params))
        
        if not salary_results:
            return {
                'title': '整体薪资市场分析',
                'summary': '未找到薪资数据',
                'data': [],
                'statistics': {},
                'insights': ['当前数据库中暂无薪资信息'],
                'recommendations': ['建议更新职位数据或检查数据质量'],
                'data_source': '基于薪资数据库分析'
            }
        
        # 计算薪资统计
        salary_stats = self._calculate_salary_statistics(salary_results, include_percentiles)
        
        # 分析薪资分布
        salary_ranges = self._analyze_salary_ranges(salary_results)
        
        # 分析热门技能薪资
        top_skill_salaries = self._analyze_top_skills_salary(salary_results)
        
        title = f"{location}地区整体薪资市场分析" if location else "整体薪资市场分析"
        
        # 计算年薪
        avg_annual = salary_stats["average"] * 12
        median_annual = salary_stats["median"] * 12
        min_annual = salary_stats["min"] * 12
        max_annual = salary_stats["max"] * 12
        
        result = {
            'title': title,
            'summary': f'分析了{len(salary_results)}个职位的薪资数据，市场平均月薪{salary_stats["average"]//1000}k，年薪约{avg_annual//10000}万元，中位数月薪{salary_stats["median"]//1000}k',
            'data': [
                {
                    'name': '市场平均月薪',
                    'value': f'{salary_stats["average"]//1000}k',
                    'description': f'所有职位的平均月薪水平，年薪约{avg_annual//10000}万元'
                },
                {
                    'name': '市场平均年薪',
                    'value': f'{avg_annual//10000}万元',
                    'description': '基于月薪计算的平均年薪水平'
                },
                {
                    'name': '薪资中位数',
                    'value': f'{salary_stats["median"]//1000}k',
                    'description': f'50%职位的月薪分界线，年薪约{median_annual//10000}万元'
                },
                {
                    'name': '薪资范围',
                    'value': f'{salary_stats["min"]//1000}k - {salary_stats["max"]//1000}k',
                    'description': f'市场月薪的最低到最高范围，年薪约{min_annual//10000}-{max_annual//10000}万元'
                },
                {
                    'name': '高薪职位比例',
                    'value': f'{salary_ranges["high_salary_percentage"]:.1f}%',
                    'description': '薪资超过30k的职位占比'
                }
            ],
            'statistics': salary_stats,
            'insights': self._generate_market_salary_insights(salary_stats, salary_ranges, location),
            'recommendations': self._generate_market_salary_recommendations(salary_stats, top_skill_salaries),
            'related_data': {
                'salary_ranges': salary_ranges,
                'top_skill_salaries': top_skill_salaries,
                'percentile_analysis': salary_stats.get('percentiles', {}),
                'experience_salary_correlation': self._analyze_experience_salary_correlation(salary_results)
            },
            'data_source': f'基于{len(salary_results)}个职位的整体薪资市场分析'
        }
        
        return result
    
    def _get_relevant_jobs_vector(self, skill: Optional[str] = None, location: Optional[str] = None,
                                 experience: Optional[str] = None, position: Optional[str] = None) -> list:
        """使用向量搜索获取相关职位ID"""
        if not self.vector_manager:
            return []
        
        try:
            # 构建搜索查询
            query_parts = []
            if skill:
                query_parts.append(f"{skill}技能")
            if position:
                query_parts.append(f"{position}职位")
            if location:
                query_parts.append(f"{location}地区")
            if experience:
                query_parts.append(f"{experience}经验")
            
            if not query_parts:
                return []
            
            query = " ".join(query_parts)
            
            # 执行向量搜索
            docs = self.vector_manager.search_similar_jobs(query, k=50)
            
            # 提取job_id
            job_ids = []
            for doc in docs:
                job_id = doc.metadata.get('job_id')
                if job_id:
                    job_ids.append(job_id)
            
            return list(set(job_ids))  # 去重
            
        except Exception as e:
            self.logger.warning(f"向量搜索失败: {e}")
            return []
    
    def _calculate_salary_statistics(self, salary_results: list, include_percentiles: bool = True) -> dict:
        """计算薪资统计信息"""
        salaries = []
        
        for result in salary_results:
            salary_info = self._parse_salary_range(result['salary'])
            if salary_info['avg'] > 0:
                salaries.append(salary_info['avg'])
        
        if not salaries:
            return {'average': 0, 'median': 0, 'min': 0, 'max': 0, 'count': 0}
        
        salaries.sort()
        count = len(salaries)
        
        stats = {
            'average': sum(salaries) // count,
            'median': salaries[count // 2],
            'min': min(salaries),
            'max': max(salaries),
            'count': count,
            'std_dev': self._calculate_std_dev(salaries)
        }
        
        if include_percentiles:
            stats['percentiles'] = {
                'p25': salaries[int(count * 0.25)],
                'p50': salaries[int(count * 0.50)],
                'p75': salaries[int(count * 0.75)],
                'p90': salaries[int(count * 0.90)]
            }
        
        return stats
    
    def _calculate_std_dev(self, salaries: list) -> float:
        """计算标准差"""
        if len(salaries) < 2:
            return 0
        
        mean = sum(salaries) / len(salaries)
        variance = sum((x - mean) ** 2 for x in salaries) / len(salaries)
        return variance ** 0.5
    
    def _analyze_salary_ranges(self, salary_results: list) -> dict:
        """分析薪资范围分布"""
        ranges = {
            'low': 0,      # <15k
            'medium': 0,   # 15k-30k
            'high': 0,     # 30k-50k
            'very_high': 0 # >50k
        }
        
        total_count = 0
        
        for result in salary_results:
            salary_info = self._parse_salary_range(result['salary'])
            if salary_info['avg'] > 0:
                total_count += 1
                avg_salary = salary_info['avg']
                
                if avg_salary < 15000:
                    ranges['low'] += 1
                elif avg_salary < 30000:
                    ranges['medium'] += 1
                elif avg_salary < 50000:
                    ranges['high'] += 1
                else:
                    ranges['very_high'] += 1
        
        if total_count == 0:
            return ranges
        
        # 计算百分比
        for key in ranges:
            ranges[f'{key}_percentage'] = (ranges[key] / total_count) * 100
        
        ranges['high_salary_percentage'] = ranges['high'] + ranges['very_high']
        ranges['total_count'] = total_count
        
        return ranges
    
    def _analyze_top_skills_salary(self, salary_results: list) -> list:
        """分析热门技能的薪资水平"""
        skill_salaries = {}
        
        for result in salary_results:
            if result.get('keyword'):
                skill = self._standardize_skill_name(result['keyword'])
                salary_info = self._parse_salary_range(result['salary'])
                
                if salary_info['avg'] > 0:
                    if skill not in skill_salaries:
                        skill_salaries[skill] = []
                    skill_salaries[skill].append(salary_info['avg'])
        
        # 计算每个技能的平均薪资
        skill_avg_salaries = []
        for skill, salaries in list(skill_salaries.items()):
            if len(salaries) >= 3:  # 至少3个样本
                avg_salary = sum(salaries) // len(salaries)
                skill_avg_salaries.append({
                    'skill': skill,
                    'average_salary': avg_salary,
                    'job_count': len(salaries),
                    'min_salary': min(salaries),
                    'max_salary': max(salaries)
                })
        
        # 按平均薪资排序
        skill_avg_salaries.sort(key=lambda x: x['average_salary'], reverse=True)
        
        return skill_avg_salaries[:10]  # 返回前10个
    
    def _get_top_paying_companies(self, salary_results: list) -> list:
        """获取薪资最高的公司"""
        company_salaries = {}
        
        for result in salary_results:
            company = result.get('company', '').strip()
            if company:
                salary_info = self._parse_salary_range(result['salary'])
                if salary_info['avg'] > 0:
                    if company not in company_salaries:
                        company_salaries[company] = []
                    company_salaries[company].append(salary_info['avg'])
        
        # 计算公司平均薪资
        company_avg_salaries = []
        for company, salaries in list(company_salaries.items()):
            if len(salaries) >= 2:  # 至少2个职位
                avg_salary = sum(salaries) // len(salaries)
                company_avg_salaries.append({
                    'company': company,
                    'average_salary': avg_salary,
                    'job_count': len(salaries)
                })
        
        # 按平均薪资排序
        company_avg_salaries.sort(key=lambda x: x['average_salary'], reverse=True)
        
        return company_avg_salaries[:5]  # 返回前5个
    
    def _analyze_experience_salary_impact(self, salary_results: list) -> dict:
        """分析经验对薪资的影响"""
        exp_salaries = {}
        
        for result in salary_results:
            experience = result.get('experience', '').strip()
            if experience:
                salary_info = self._parse_salary_range(result['salary'])
                if salary_info['avg'] > 0:
                    if experience not in exp_salaries:
                        exp_salaries[experience] = []
                    exp_salaries[experience].append(salary_info['avg'])
        
        # 计算各经验水平的平均薪资
        exp_analysis = []
        for exp, salaries in list(exp_salaries.items()):
            if len(salaries) >= 2:
                avg_salary = sum(salaries) // len(salaries)
                exp_analysis.append({
                    'experience': exp,
                    'average_salary': avg_salary,
                    'job_count': len(salaries)
                })
        
        # 按平均薪资排序
        exp_analysis.sort(key=lambda x: x['average_salary'], reverse=True)
        
        return {
            'experience_levels': exp_analysis,
            'total_analyzed': len(exp_analysis)
        }
    
    def _analyze_location_salary_breakdown(self, salary_results: list) -> dict:
        """分析地区薪资分布"""
        location_salaries = {}
        
        for result in salary_results:
            location = result.get('location', '').strip()
            if location:
                # 提取主要城市名
                for city in ['北京', '上海', '深圳', '杭州', '广州', '成都', '南京', '武汉', '西安', '苏州']:
                    if city in location:
                        salary_info = self._parse_salary_range(result['salary'])
                        if salary_info['avg'] > 0:
                            if city not in location_salaries:
                                location_salaries[city] = []
                            location_salaries[city].append(salary_info['avg'])
                        break
        
        # 计算各城市平均薪资
        location_analysis = []
        for city, salaries in list(location_salaries.items()):
            if len(salaries) >= 2:
                avg_salary = sum(salaries) // len(salaries)
                location_analysis.append({
                    'city': city,
                    'average_salary': avg_salary,
                    'job_count': len(salaries)
                })
        
        # 按平均薪资排序
        location_analysis.sort(key=lambda x: x['average_salary'], reverse=True)
        
        return {
            'locations': location_analysis,
            'total_cities': len(location_analysis)
        }
    
    def _analyze_experience_salary_correlation(self, salary_results: list) -> dict:
        """分析经验与薪资的相关性"""
        # 简化的经验分类
        exp_categories = {
            '应届生': [],
            '1-3年': [],
            '3-5年': [],
            '5-10年': [],
            '10年以上': []
        }
        
        for result in salary_results:
            experience = result.get('experience', '').lower()
            salary_info = self._parse_salary_range(result['salary'])
            
            if salary_info['avg'] > 0:
                if '应届' in experience or '0年' in experience:
                    exp_categories['应届生'].append(salary_info['avg'])
                elif '1年' in experience or '2年' in experience or '3年' in experience:
                    exp_categories['1-3年'].append(salary_info['avg'])
                elif '4年' in experience or '5年' in experience:
                    exp_categories['3-5年'].append(salary_info['avg'])
                elif any(year in experience for year in ['6年', '7年', '8年', '9年', '10年']):
                    exp_categories['5-10年'].append(salary_info['avg'])
                elif any(year in experience for year in ['10年以上', '15年', '20年']):
                    exp_categories['10年以上'].append(salary_info['avg'])
        
        # 计算各经验段的平均薪资
        correlation_data = []
        for exp_level, salaries in list(exp_categories.items()):
            if salaries:
                avg_salary = sum(salaries) // len(salaries)
                correlation_data.append({
                    'experience_level': exp_level,
                    'average_salary': avg_salary,
                    'sample_count': len(salaries)
                })
        
        return {
            'correlation_data': correlation_data,
            'total_categories': len([cat for cat in correlation_data if cat['sample_count'] > 0])
        }
    
    def _generate_salary_insights(self, salary_stats: dict, skill: Optional[str] = None,
                                 location: Optional[str] = None, experience: Optional[str] = None,
                                 position: Optional[str] = None) -> list:
        """生成薪资洞察"""
        insights = []
        
        avg_salary = salary_stats['average']
        median_salary = salary_stats['median']
        
        # 薪资水平洞察
        if avg_salary > 400000:
            insights.append("薪资水平非常高，属于市场顶级薪资范围")
        elif avg_salary > 300000:
            insights.append("薪资水平较高，超过大多数职位的薪资水平")
        elif avg_salary > 200000:
            insights.append("薪资水平中等偏上，具有一定竞争力")
        elif avg_salary > 150000:
            insights.append("薪资水平中等，符合市场平均水平")
        else:
            insights.append("薪资水平相对较低，可能需要提升技能或经验")
        
        # 薪资分布洞察
        if abs(avg_salary - median_salary) > avg_salary * 0.2:
            insights.append("薪资分布不均匀，存在较大的薪资差异")
        else:
            insights.append("薪资分布相对均匀，市场薪资较为稳定")
        
        # 特定条件洞察
        if skill:
            insights.append(f"基于向量搜索分析，{skill}技能在当前市场条件下的薪资表现")
        
        if location:
            insights.append(f"{location}地区的薪资水平反映了当地的经济发展和人才需求")
        
        # 样本量洞察
        sample_count = salary_stats['count']
        if sample_count < 10:
            insights.append("样本数量较少，建议扩大搜索范围获取更准确的分析")
        elif sample_count > 50:
            insights.append("样本数量充足，分析结果具有较高的可信度")
        
        return insights
    
    def _generate_salary_recommendations(self, salary_stats: dict, skill: Optional[str] = None,
                                       location: Optional[str] = None) -> list:
        """生成薪资建议"""
        recommendations = []
        
        avg_salary = salary_stats['average']
        percentiles = salary_stats.get('percentiles', {})
        
        # 薪资谈判建议
        if percentiles:
            p75_salary = percentiles.get('p75', avg_salary)
            p75_annual = p75_salary * 12
            recommendations.append(f"薪资谈判建议：可以月薪{p75_salary//1000}k（年薪约{p75_annual//10000}万元）作为目标薪资进行谈判")
        
        # 技能提升建议
        if skill and avg_salary < 250000:
            recommendations.append(f"建议深化{skill}技能，学习相关高级技术以提升薪资水平")
        
        # 地区建议
        if location and avg_salary < 200000:
            recommendations.append("可以考虑关注一线城市的机会，通常薪资水平更高")
        
        # 职业发展建议
        if avg_salary < 300000:
            recommendations.append("建议关注技术管理或架构师方向，通常薪资增长空间更大")
        
        recommendations.append("持续关注市场薪资变化，定期评估自身薪资竞争力")
        
        return recommendations
    
    def _generate_location_comparison_insights(self, location_data: list, highest_city: dict,
                                             lowest_city: dict, gap_percentage: float) -> list:
        """生成地区对比洞察"""
        insights = []
        
        highest_annual = highest_city['average_salary'] * 12
        lowest_annual = lowest_city['average_salary'] * 12
        insights.append(f"{highest_city['city']}薪资最高（年薪约{highest_annual//10000}万元），比{lowest_city['city']}（年薪约{lowest_annual//10000}万元）高出{gap_percentage:.1f}%")
        
        # 一线城市分析
        tier1_cities = ['北京', '上海', '深圳', '杭州']
        tier1_data = [city for city in location_data if city['city'] in tier1_cities]
        
        if tier1_data:
            tier1_avg = sum(city['average_salary'] for city in tier1_data) // len(tier1_data)
            tier1_annual = tier1_avg * 12
            insights.append(f"一线城市平均月薪{tier1_avg//1000}k（年薪约{tier1_annual//10000}万元），明显高于其他城市")
        
        # 薪资梯度分析
        if len(location_data) >= 3:
            top3_avg = sum(city['average_salary'] for city in location_data[:3]) // 3
            top3_annual = top3_avg * 12
            insights.append(f"薪资前三城市平均月薪{top3_avg//1000}k（年薪约{top3_annual//10000}万元），形成明显的薪资梯度")
        
        return insights
    
    def _generate_location_recommendations(self, location_data: list, skill: Optional[str] = None) -> list:
        """生成地区建议"""
        recommendations = []
        
        if location_data:
            top_city = location_data[0]
            recommendations.append(f"推荐关注{top_city['city']}的机会，薪资水平最高")
            
            # 性价比城市推荐
            if len(location_data) >= 4:
                mid_cities = location_data[2:4]
                city_names = [city['city'] for city in mid_cities]
                recommendations.append(f"性价比较高的城市：{', '.join(city_names)}")
        
        if skill:
            recommendations.append(f"建议在选择城市时考虑{skill}技能的产业集中度")
        
        recommendations.append("选择城市时要综合考虑薪资水平、生活成本和发展机会")
        
        return recommendations
    
    def _generate_market_salary_insights(self, salary_stats: dict, salary_ranges: dict,
                                       location: Optional[str] = None) -> list:
        """生成市场薪资洞察"""
        insights = []
        
        avg_salary = salary_stats['average']
        high_salary_pct = salary_ranges.get('high_salary_percentage', 0)
        
        # 市场整体水平
        if avg_salary > 250000:
            insights.append("整体薪资市场水平较高，反映了良好的就业环境")
        elif avg_salary > 200000:
            insights.append("薪资市场处于中等偏上水平，有一定的发展空间")
        else:
            insights.append("薪资市场相对保守，可能受到经济环境影响")
        
        # 高薪职位分析
        if high_salary_pct > 20:
            insights.append(f"高薪职位(30k+)占比{high_salary_pct:.1f}%，市场机会较多")
        elif high_salary_pct > 10:
            insights.append(f"高薪职位占比{high_salary_pct:.1f}%，需要具备核心竞争力")
        else:
            insights.append("高薪职位相对稀少，竞争较为激烈")
        
        # 地区特色
        if location:
            insights.append(f"{location}地区的薪资结构反映了当地的产业特点和人才供需")
        
        return insights
    
    def _generate_market_salary_recommendations(self, salary_stats: dict, top_skill_salaries: list) -> list:
        """生成市场薪资建议"""
        recommendations = []
        
        # 技能建议
        if top_skill_salaries:
            top_skill = top_skill_salaries[0]
            skill_annual = top_skill['average_salary'] * 12
            recommendations.append(f"高薪技能推荐：{top_skill['skill']}，平均月薪{top_skill['average_salary']//1000}k（年薪约{skill_annual//10000}万元）")
        
        # 职业规划建议
        avg_salary = salary_stats['average']
        if avg_salary < 200000:
            recommendations.append("建议关注新兴技术领域，通常薪资增长潜力更大")
        
        recommendations.append("定期关注薪资市场变化，及时调整职业发展策略")
        recommendations.append("提升核心技能和综合能力，争取进入高薪资区间")
        
        return recommendations