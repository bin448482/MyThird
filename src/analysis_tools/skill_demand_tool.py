
"""
技能需求分析工具

基于RAG系统和向量数据库，分析职位市场中各种技能的需求情况
结合语义搜索和数据库统计，提供更准确的技能市场洞察
"""

from typing import Optional
from pydantic import BaseModel, Field
from .base_tool import BaseAnalysisTool


class SkillDemandInput(BaseModel):
    """技能需求分析输入参数"""
    skill: Optional[str] = Field(None, description="特定技能名称，如'Python'、'Java'等")
    limit: Optional[int] = Field(20, description="返回结果数量，默认20")
    include_trend: Optional[bool] = Field(False, description="是否包含趋势分析")
    category: Optional[str] = Field(None, description="技能分类，如'编程语言'、'框架'等")


class SkillDemandAnalysisTool(BaseAnalysisTool):
    """技能需求分析工具 - 基于RAG和向量搜索"""
    
    name: str = "skill_demand_analysis"
    description: str = """
    基于RAG系统分析职位市场中的技能需求情况。结合向量搜索和数据库统计：
    1. 获取最热门的技能排行榜
    2. 通过语义搜索分析特定技能的市场需求
    3. 比较不同技能的需求量和薪资水平
    4. 基于向量相似度提供技能学习建议
    
    输入参数：
    - skill: 特定技能名称（可选）
    - limit: 返回结果数量（默认20）
    - include_trend: 是否包含趋势分析（默认false）
    - category: 技能分类过滤（可选）
    """
    args_schema: type = SkillDemandInput
    
    def __init__(self, db_manager, vector_manager=None, **kwargs):
        """
        初始化技能需求分析工具
        
        Args:
            db_manager: 数据库管理器
            vector_manager: 向量数据库管理器
            **kwargs: 其他参数
        """
        super().__init__(db_manager, vector_manager=vector_manager, **kwargs)
    
    def _run(self, skill: Optional[str] = None, limit: int = 20, 
             include_trend: bool = False, category: Optional[str] = None) -> str:
        """
        执行技能需求分析
        
        Args:
            skill: 特定技能名称
            limit: 返回结果数量
            include_trend: 是否包含趋势分析
            category: 技能分类
            
        Returns:
            分析结果文本
        """
        try:
            if skill:
                # 分析特定技能
                result = self._analyze_specific_skill(skill, include_trend)
            else:
                # 分析热门技能排行
                result = self._analyze_top_skills(limit, category, include_trend)
            
            return self._format_result(result)
            
        except Exception as e:
            self.logger.error(f"技能需求分析失败: {e}")
            return f"分析失败: {str(e)}"
    
    def _analyze_specific_skill(self, skill: str, include_trend: bool = False) -> dict:
        """
        分析特定技能的需求情况 - 结合向量搜索和数据库查询
        
        Args:
            skill: 技能名称
            include_trend: 是否包含趋势分析
            
        Returns:
            分析结果字典
        """
        # 1. 使用向量搜索找到相关职位
        vector_results = []
        if self.vector_manager:
            try:
                # 构建技能相关的查询
                skill_queries = [
                    f"{skill}开发工程师",
                    f"{skill}程序员",
                    f"{skill}技能要求",
                    f"熟悉{skill}",
                    f"{skill}经验"
                ]
                
                for query in skill_queries:
                    docs = self.vector_manager.search_similar_jobs(query, k=10)
                    vector_results.extend(docs)
                
                # 去重并获取job_id
                job_ids = list(set([doc.metadata.get('job_id') for doc in vector_results if doc.metadata.get('job_id')]))
                
            except Exception as e:
                self.logger.warning(f"向量搜索失败，使用传统查询: {e}")
                job_ids = []
        else:
            job_ids = []
        
        # 2. 结合数据库查询进行统计分析
        normalized_skill = self._standardize_skill_name(skill)
        
        # 基础统计查询
        if job_ids:
            # 使用向量搜索结果
            placeholders = ','.join('?' * len(job_ids))
            base_query = f"""
            SELECT 
                COUNT(*) as job_count,
                COUNT(DISTINCT jd.job_id) as unique_jobs,
                AVG(CASE WHEN jd.salary IS NOT NULL AND jd.salary != '' THEN 1 ELSE 0 END) as salary_info_rate
            FROM job_details jd
            JOIN jobs j ON jd.job_id = j.job_id
            WHERE j.job_id IN ({placeholders})
            """
            skill_results = self._execute_query(base_query, tuple(job_ids))
        else:
            # 传统关键词搜索
            skill_pattern = f"%{normalized_skill}%"
            base_query = """
            SELECT 
                COUNT(*) as job_count,
                COUNT(DISTINCT jd.job_id) as unique_jobs,
                AVG(CASE WHEN jd.salary IS NOT NULL AND jd.salary != '' THEN 1 ELSE 0 END) as salary_info_rate
            FROM job_details jd
            JOIN jobs j ON jd.job_id = j.job_id
            WHERE LOWER(jd.keyword) LIKE ? OR LOWER(jd.description) LIKE ? OR LOWER(jd.requirements) LIKE ?
            """
            skill_results = self._execute_query(base_query, (skill_pattern, skill_pattern, skill_pattern))
        
        if not skill_results or skill_results[0]['job_count'] == 0:
            return {
                'title': f'技能需求分析 - {skill}',
                'summary': f'未找到包含"{skill}"技能的职位',
                'data': [],
                'statistics': {'job_count': 0, 'market_share': 0.0},
                'insights': [f'"{skill}"技能在当前数据中需求较少，建议关注其他热门技能'],
                'recommendations': [f'考虑学习与{skill}相关的热门技能组合'],
                'data_source': '基于RAG向量搜索和职位数据库分析'
            }
        
        skill_data = skill_results[0]
        total_jobs = self._get_job_count()
        market_share = self._format_percentage(skill_data['job_count'], total_jobs)
        
        # 3. 获取相关职位的详细信息
        related_jobs = self._get_skill_related_jobs(job_ids if job_ids else normalized_skill, limit=10)
        
        # 4. 基于向量搜索结果进行薪资分析
        salary_analysis = self._analyze_skill_salary_vector(job_ids if job_ids else normalized_skill)
        
        # 5. 经验要求分析
        experience_analysis = self._analyze_skill_experience_vector(job_ids if job_ids else normalized_skill)
        
        # 6. 地域分布分析
        location_analysis = self._analyze_skill_location_vector(job_ids if job_ids else normalized_skill)
        
        # 7. 基于向量相似度的技能推荐
        skill_recommendations = self._get_related_skills_vector(skill)
        
        result = {
            'title': f'技能需求分析 - {skill}',
            'summary': f'基于RAG分析，"{skill}"技能在{skill_data["job_count"]}个职位中被识别，市场份额为{market_share}%',
            'data': [
                {
                    'name': '职位数量',
                    'value': self._format_number(skill_data['job_count']),
                    'description': '通过语义搜索识别的相关职位总数'
                },
                {
                    'name': '市场份额',
                    'value': f'{market_share}%',
                    'description': '在所有职位中的占比'
                },
                {
                    'name': '薪资信息完整度',
                    'value': f'{skill_data["salary_info_rate"]*100:.1f}%',
                    'description': '提供薪资信息的职位比例'
                },
                {
                    'name': '向量匹配度',
                    'value': f'{len(job_ids) if job_ids else 0}个',
                    'description': '通过语义相似度匹配的职位数量'
                }
            ],
            'statistics': {
                'job_count': skill_data['job_count'],
                'market_share': market_share,
                'unique_jobs': skill_data['unique_jobs'],
                'total_market_jobs': total_jobs,
                'vector_matches': len(job_ids) if job_ids else 0
            },
            'insights': self._generate_skill_insights_vector(skill, skill_data, market_share, salary_analysis, experience_analysis, skill_recommendations),
            'recommendations': self._generate_skill_recommendations_vector(skill, market_share, salary_analysis, skill_recommendations),
            'related_data': {
                'salary_analysis': salary_analysis,
                'experience_analysis': experience_analysis,
                'location_analysis': location_analysis,
                'related_skills': skill_recommendations,
                'sample_jobs': related_jobs[:5]
            },
            'data_source': f'基于RAG向量搜索和{total_jobs}个职位的综合分析'
        }
        
        return result
    
    def _analyze_top_skills(self, limit: int = 20, category: Optional[str] = None,
                           include_trend: bool = False) -> dict:
        """
        分析热门技能排行 - 基于向量数据库内容分析
        
        Args:
            limit: 返回数量
            category: 技能分类
            include_trend: 是否包含趋势
            
        Returns:
            分析结果字典
        """
        # 1. 定义要分析的技能列表（基于实际市场需求）
        common_skills = [
            'python', 'java', 'javascript', 'react', 'vue', 'node.js',
            'spring', 'mysql', 'redis', 'docker', 'kubernetes', 'git',
            'linux', 'aws', 'azure', 'tensorflow', 'pytorch', 'pandas',
            'numpy', 'django', 'flask', 'express', 'mongodb', 'postgresql',
            'elasticsearch', 'kafka', 'spark', 'hadoop', 'jenkins', 'nginx',
            'go', 'rust', 'typescript', 'angular', 'svelte', 'php', 'laravel',
            'ruby', 'rails', 'c++', 'c#', '.net', 'unity', 'android', 'ios',
            'swift', 'kotlin', 'flutter', 'react native', 'webpack', 'babel'
        ]
        
        if not self.vector_manager:
            return {
                'title': '热门技能需求排行',
                'summary': '向量数据库不可用，无法进行技能分析',
                'data': [],
                'statistics': {},
                'insights': ['需要向量数据库支持进行准确的技能分析'],
                'data_source': '基于向量搜索的技能内容分析'
            }
        
        # 2. 使用向量搜索分析每个技能的市场需求
        enhanced_skills = []
        total_jobs = self._get_job_count()
        
        self.logger.info(f"开始分析 {len(common_skills)} 个技能的市场需求...")
        
        for skill in common_skills:
            try:
                # 使用向量搜索获取技能相关职位数量
                vector_job_count = self._get_vector_skill_count(skill)
                
                if vector_job_count > 0:  # 只包含有需求的技能
                    market_share = self._format_percentage(vector_job_count, total_jobs)
                    
                    # 获取薪资信息
                    salary_info = self._get_skill_salary_summary_by_vector(skill)
                    
                    # 获取公司数量（通过向量搜索）
                    company_count = self._get_skill_company_count_by_vector(skill)
                    
                    enhanced_skills.append({
                        'rank': 0,  # 稍后排序时设置
                        'name': skill.title(),
                        'value': self._format_number(vector_job_count),
                        'percentage': market_share,
                        'description': f'{company_count}家公司需要，平均薪资{salary_info["avg_salary"]}k',
                        'job_count': vector_job_count,
                        'company_count': company_count,
                        'keyword_matches': 0,  # 不再依赖keyword字段
                        'vector_matches': vector_job_count,
                        'salary_info': salary_info
                    })
                    
            except Exception as e:
                self.logger.warning(f"分析技能 {skill} 时出错: {e}")
                continue
        
        # 3. 按职位数量排序并设置排名
        enhanced_skills.sort(key=lambda x: x['job_count'], reverse=True)
        for i, skill in enumerate(enhanced_skills[:limit]):
            skill['rank'] = i + 1
        
        enhanced_skills = enhanced_skills[:limit]
        
        if not enhanced_skills:
            return {
                'title': '热门技能需求排行',
                'summary': '未找到技能需求数据',
                'data': [],
                'statistics': {},
                'insights': ['向量数据库中暂无足够的技能信息'],
                'data_source': '基于向量搜索的技能内容分析'
            }
        
        # 4. 计算市场洞察
        total_skill_mentions = sum(skill['job_count'] for skill in enhanced_skills)
        top_5_share = sum(skill['job_count'] for skill in enhanced_skills[:5])
        top_5_percentage = self._format_percentage(top_5_share, total_skill_mentions)
        
        result = {
            'title': '热门技能需求排行榜（基于向量内容分析）',
            'summary': f'基于向量搜索分析{total_jobs}个职位的实际内容，识别出前{len(enhanced_skills)}个热门技能',
            'data': enhanced_skills,
            'statistics': {
                'total_jobs_analyzed': total_jobs,
                'total_skills_found': len(enhanced_skills),
                'total_skill_mentions': total_skill_mentions,
                'top_5_market_share': top_5_percentage,
                'average_jobs_per_skill': total_skill_mentions // len(enhanced_skills) if enhanced_skills else 0,
                'vector_enhanced': True,
                'analysis_method': 'vector_content_based'
            },
            'insights': self._generate_market_insights_vector(enhanced_skills, total_jobs),
            'recommendations': self._generate_market_recommendations_vector(enhanced_skills),
            'data_source': f'基于向量搜索分析{total_jobs}个职位的实际内容，而非数据库关键词字段'
        }
        
        return result
    
    def _get_vector_skill_count(self, skill: str) -> int:
        """使用向量搜索获取技能相关职位数量"""
        if not self.vector_manager:
            return 0
        
        try:
            # 构建多个查询来捕获技能相关职位
            queries = [
                f"{skill}开发",
                f"{skill}工程师", 
                f"熟悉{skill}",
                f"{skill}经验"
            ]
            
            job_ids = set()
            for query in queries:
                docs = self.vector_manager.search_similar_jobs(query, k=20)
                for doc in docs:
                    if doc.metadata.get('job_id'):
                        job_ids.add(doc.metadata['job_id'])
            
            return len(job_ids)
            
        except Exception as e:
            self.logger.warning(f"向量搜索技能计数失败: {e}")
            return 0
    
    def _get_skill_salary_summary(self, skill: str) -> dict:
        """获取技能薪资摘要"""
        try:
            # 使用向量搜索找到相关职位
            if self.vector_manager:
                docs = self.vector_manager.search_similar_jobs(f"{skill}薪资待遇", k=10)
                job_ids = [doc.metadata.get('job_id') for doc in docs if doc.metadata.get('job_id')]
                
                if job_ids:
                    placeholders = ','.join('?' * len(job_ids))
                    query = f"""
                    SELECT jd.salary
                    FROM job_details jd
                    WHERE jd.job_id IN ({placeholders})
                    AND jd.salary IS NOT NULL AND jd.salary != ''
                    """
                    salary_results = self._execute_query(query, tuple(job_ids))
                else:
                    salary_results = []
            else:
                # 传统查询
                skill_pattern = f"%{skill}%"
                query = """
                SELECT jd.salary
                FROM job_details jd
                WHERE LOWER(jd.keyword) LIKE ?
                AND jd.salary IS NOT NULL AND jd.salary != ''
                LIMIT 20
                """
                salary_results = self._execute_query(query, (skill_pattern,))
            
            if not salary_results:
                return {'avg_salary': 0, 'min_salary': 0, 'max_salary': 0}
            
            salaries = []
            for result in salary_results:
                salary_info = self._parse_salary_range(result['salary'])
                if salary_info['avg'] > 0:
                    salaries.append(salary_info['avg'])
            
            if not salaries:
                return {'avg_salary': 0, 'min_salary': 0, 'max_salary': 0}
            
            return {
                'avg_salary': sum(salaries) // len(salaries) // 1000,  # 转换为k
                'min_salary': min(salaries) // 1000,
                'max_salary': max(salaries) // 1000
            }
            
        except Exception as e:
            self.logger.error(f"薪资分析失败: {e}")
            return {'avg_salary': 0, 'min_salary': 0, 'max_salary': 0}
    
    def _get_skill_salary_summary_by_vector(self, skill: str) -> dict:
        """基于向量搜索获取技能薪资摘要"""
        try:
            if not self.vector_manager:
                return {'avg_salary': 0, 'min_salary': 0, 'max_salary': 0}
            
            # 使用向量搜索找到相关职位
            docs = self.vector_manager.search_similar_jobs(f"{skill}开发工程师", k=20)
            job_ids = [doc.metadata.get('job_id') for doc in docs if doc.metadata.get('job_id')]
            
            if not job_ids:
                return {'avg_salary': 0, 'min_salary': 0, 'max_salary': 0}
            
            # 查询这些职位的薪资信息
            placeholders = ','.join('?' * len(job_ids))
            query = f"""
            SELECT jd.salary
            FROM job_details jd
            WHERE jd.job_id IN ({placeholders})
            AND jd.salary IS NOT NULL AND jd.salary != ''
            """
            salary_results = self._execute_query(query, tuple(job_ids))
            
            if not salary_results:
                return {'avg_salary': 0, 'min_salary': 0, 'max_salary': 0}
            
            salaries = []
            for result in salary_results:
                salary_info = self._parse_salary_range(result['salary'])
                if salary_info['avg'] > 0:
                    salaries.append(salary_info['avg'])
            
            if not salaries:
                return {'avg_salary': 0, 'min_salary': 0, 'max_salary': 0}
            
            return {
                'avg_salary': sum(salaries) // len(salaries) // 1000,  # 转换为k
                'min_salary': min(salaries) // 1000,
                'max_salary': max(salaries) // 1000
            }
            
        except Exception as e:
            self.logger.error(f"基于向量的薪资分析失败: {e}")
            return {'avg_salary': 0, 'min_salary': 0, 'max_salary': 0}
    
    def _get_skill_company_count_by_vector(self, skill: str) -> int:
        """基于向量搜索获取使用该技能的公司数量"""
        try:
            if not self.vector_manager:
                return 0
            
            # 使用向量搜索找到相关职位
            docs = self.vector_manager.search_similar_jobs(f"{skill}开发工程师", k=30)
            job_ids = [doc.metadata.get('job_id') for doc in docs if doc.metadata.get('job_id')]
            
            if not job_ids:
                return 0
            
            # 查询这些职位对应的公司数量
            placeholders = ','.join('?' * len(job_ids))
            query = f"""
            SELECT COUNT(DISTINCT j.company) as company_count
            FROM jobs j
            WHERE j.job_id IN ({placeholders})
            AND j.company IS NOT NULL AND j.company != ''
            """
            result = self._execute_query(query, tuple(job_ids))
            
            if result and result[0]:
                return result[0]['company_count']
            return 0
            
        except Exception as e:
            self.logger.error(f"基于向量的公司统计失败: {e}")
            return 0
    
    def _get_related_skills_vector(self, skill: str) -> list:
        """基于向量相似度获取相关技能推荐"""
        if not self.vector_manager:
            return []
        
        try:
            # 搜索与该技能相关的职位描述
            docs = self.vector_manager.search_similar_jobs(f"{skill}相关技能要求", k=20)
            
            # 从文档中提取其他技能关键词
            skill_mentions = {}
            common_skills = ['python', 'java', 'javascript', 'react', 'vue', 'node.js', 'mysql', 'redis', 'docker', 'kubernetes']
            
            for doc in docs:
                content = doc.page_content.lower()
                for common_skill in common_skills:
                    if common_skill != skill.lower() and common_skill in content:
                        skill_mentions[common_skill] = skill_mentions.get(common_skill, 0) + 1
            
            # 按出现频率排序
            related_skills = sorted(skill_mentions.items(), key=lambda x: x[1], reverse=True)[:5]
            return [{'skill': skill, 'frequency': freq} for skill, freq in related_skills]
            
        except Exception as e:
            self.logger.warning(f"相关技能分析失败: {e}")
            return []
    
    def _get_skill_related_jobs(self, job_ids_or_skill, limit: int = 10) -> list:
        """获取技能相关的职位信息"""
        try:
            if isinstance(job_ids_or_skill, list):
                # 使用job_ids查询
                if not job_ids_or_skill:
                    return []
                placeholders = ','.join('?' * len(job_ids_or_skill))
                query = f"""
                SELECT j.title, j.company, jd.location, jd.salary, jd.experience
                FROM jobs j
                JOIN job_details jd ON j.job_id = jd.job_id
                WHERE j.job_id IN ({placeholders})
                LIMIT ?
                """
                params = tuple(job_ids_or_skill) + (limit,)
            else:
                # 使用技能名称查询
                skill_pattern = f"%{job_ids_or_skill}%"
                query = """
                SELECT j.title, j.company, jd.location, jd.salary, jd.experience
                FROM jobs j
                JOIN job_details jd ON j.job_id = jd.job_id
                WHERE LOWER(jd.keyword) LIKE ? OR LOWER(jd.description) LIKE ? OR LOWER(jd.requirements) LIKE ?
                LIMIT ?
                """
                params = (skill_pattern, skill_pattern, skill_pattern, limit)
            
            return self._execute_query(query, params)
            
        except Exception as e:
            self.logger.error(f"获取相关职位失败: {e}")
            return []
    
    def _analyze_skill_salary_vector(self, job_ids_or_skill) -> dict:
        """基于向量搜索结果分析薪资"""
        try:
            if isinstance(job_ids_or_skill, list) and job_ids_or_skill:
                placeholders = ','.join('?' * len(job_ids_or_skill))
                query = f"""
                SELECT jd.salary
                FROM job_details jd
                WHERE jd.job_id IN ({placeholders})
                AND jd.salary IS NOT NULL AND jd.salary != ''
                """
                params = tuple(job_ids_or_skill)
            else:
                skill_pattern = f"%{job_ids_or_skill}%"
                query = """
                SELECT jd.salary
                FROM job_details jd
                WHERE LOWER(jd.keyword) LIKE ? OR LOWER(jd.description) LIKE ? OR LOWER(jd.requirements) LIKE ?
                AND jd.salary IS NOT NULL AND jd.salary != ''
                """
                params = (skill_pattern, skill_pattern, skill_pattern)
            
            salary_results = self._execute_query(query, params)
            
            if not salary_results:
                return {'average': 0, 'min': 0, 'max': 0, 'count': 0}
            
            salaries = []
            for result in salary_results:
                salary_info = self._parse_salary_range(result['salary'])
                if salary_info['avg'] > 0:
                    salaries.append(salary_info['avg'])
            
            if not salaries:
                return {'average': 0, 'min': 0, 'max': 0, 'count': 0}
            
            return {
                'average': sum(salaries) // len(salaries),
                'min': min(salaries),
                'max': max(salaries),
                'count': len(salaries)
            }
            
        except Exception as e:
            self.logger.error(f"薪资分析失败: {e}")
            return {'average': 0, 'min': 0, 'max': 0, 'count': 0}
    
    def _analyze_skill_experience_vector(self, job_ids_or_skill) -> dict:
        """基于向量搜索结果分析经验要求"""
        try:
            if isinstance(job_ids_or_skill, list) and job_ids_or_skill:
                placeholders = ','.join('?' * len(job_ids_or_skill))
                query = f"""
                SELECT jd.experience, COUNT(*) as count
                FROM job_details jd
                WHERE jd.job_id IN ({placeholders})
                AND jd.experience IS NOT NULL AND jd.experience != ''
                GROUP BY jd.experience
                ORDER BY count DESC
                """
                params = tuple(job_ids_or_skill)
            else:
                skill_pattern = f"%{job_ids_or_skill}%"
                query = """
                SELECT jd.experience, COUNT(*) as count
                FROM job_details jd
                WHERE LOWER(jd.keyword) LIKE ? OR LOWER(jd.description) LIKE ? OR LOWER(jd.requirements) LIKE ?
                AND jd.experience IS NOT NULL AND jd.experience != ''
                GROUP BY jd.experience
                ORDER BY count DESC
                """
                params = (skill_pattern, skill_pattern, skill_pattern)
            
            exp_results = self._execute_query(query, params)
            
            return {
                'distribution': exp_results[:5],
                'total_count': sum(result['count'] for result in exp_results)
            }
            
        except Exception as e:
            self.logger.error(f"经验分析失败: {e}")
            return {'distribution': [], 'total_count': 0}
    
    def _analyze_skill_location_vector(self, job_ids_or_skill) -> dict:
        """基于向量搜索结果分析地域分布"""
        try:
            if isinstance(job_ids_or_skill, list) and job_ids_or_skill:
                placeholders = ','.join('?' * len(job_ids_or_skill))
                query = f"""
                SELECT jd.location, COUNT(*) as count
                FROM job_details jd
                WHERE jd.job_id IN ({placeholders})
                AND jd.location IS NOT NULL AND jd.location != ''
                GROUP BY jd.location
                ORDER BY count DESC
                LIMIT 10
                """
                params = tuple(job_ids_or_skill)
            else:
                skill_pattern = f"%{job_ids_or_skill}%"
                query = """
                SELECT jd.location, COUNT(*) as count
                FROM job_details jd
                WHERE LOWER(jd.keyword) LIKE ? OR LOWER(jd.description) LIKE ? OR LOWER(jd.requirements) LIKE ?
                AND jd.location IS NOT NULL AND jd.location != ''
                GROUP BY jd.location
                ORDER BY count DESC
                LIMIT 10
                """
                params = (skill_pattern, skill_pattern, skill_pattern)
            
            location_results = self._execute_query(query, params)
            
            return {
                'top_locations': location_results,
                'total_count': sum(result['count'] for result in location_results)
            }
            
        except Exception as e:
            self.logger.error(f"地域分析失败: {e}")
            return {'top_locations': [], 'total_count': 0}
    
    def _generate_skill_insights_vector(self, skill: str, skill_data: dict, market_share: float, 
                                       salary_analysis: dict, experience_analysis: dict, 
                                       related_skills: list) -> list:
        """生成基于向量分析的技能洞察"""
        insights = []
        
        # 市场需求洞察
        if market_share > 10:
            insights.append(f"{skill}是市场热门技能，通过语义分析发现需求量很大")
        elif market_share > 5:
            insights.append(f"{skill}在市场上有稳定需求，向量搜索显示相关职位较多")
        else:
            insights.append(f"{skill}属于小众技能，但在特定领域通过语义匹配发现有需求")
        
        # 薪资洞察
        if salary_analysis['average'] > 0:
            avg_salary = salary_analysis['average']
            avg_annual = avg_salary * 12
            if avg_salary > 300000:
                insights.append(f"基于向量搜索分析，{skill}技能薪资水平较高，平均月薪{avg_salary//1000}k，年薪约{avg_annual//10000}万元")
            elif avg_salary > 200000:
                insights.append(f"RAG分析显示{skill}技能薪资水平中等偏上，平均月薪{avg_salary//1000}k，年薪约{avg_annual//10000}万元")
            else:
                insights.append(f"综合分析显示{skill}技能薪资水平一般，平均月薪{avg_salary//1000}k，年薪约{avg_annual//10000}万元")
        
        # 相关技能洞察
        if related_skills:
            top_related = related_skills[0]['skill']
            insights.append(f"向量分析发现{skill}经常与{top_related}一起出现在职位要求中")
        
        # 经验要求洞察
        if experience_analysis['distribution']:
            top_exp = experience_analysis['distribution'][0]['experience']
            insights.append(f"语义搜索显示大多数{skill}职位要求{top_exp}经验")
        
        return insights
    
    def _generate_skill_recommendations_vector(self, skill: str, market_share: float, 
                                             salary_analysis: dict, related_skills: list) -> list:
        """生成基于向量分析的技能建议"""
        recommendations = []
        
        if market_share > 10:
            recommendations.append(f"强烈推荐学习{skill}，RAG分析显示市场需求旺盛")
        elif market_share > 5:
            recommendations.append(f"建议掌握{skill}技能，向量搜索显示有助于职业发展")
        else:
            recommendations.append(f"可以考虑学习{skill}作为技能补充，在特定领域有价值")
        
        if salary_analysis['average'] > 250000:
            skill_annual = salary_analysis['average'] * 12
            recommendations.append(f"基于薪资分析，{skill}技能可以带来较高薪资回报，年薪可达{skill_annual//10000}万元")
        
        # 基于相关技能的建议
        if related_skills:
            related_names = [rs['skill'] for rs in related_skills[:3]]
            recommendations.append(f"建议同时学习相关技能：{', '.join(related_names)}，形成技能组合优势")
        
        recommendations.append(f"利用RAG系统持续跟踪{skill}技能的市场变化和新趋势")
        
        return recommendations
    
    def _generate_market_insights_vector(self, skills: list, total_jobs: int) -> list:
        """生成基于向量分析的市场洞察"""
        insights = []
        
        if skills:
            top_skill = skills[0]
            insights.append(f"基于RAG分析，当前最热门的技能是{top_skill['name']}，在{top_skill['percentage']}%的职位中被识别")
            
            # 分析向量匹配vs关键词匹配的差异
            vector_enhanced_count = sum(1 for skill in skills if skill.get('vector_matches', 0) > skill.get('keyword_matches', 0))
            if vector_enhanced_count > 0:
                insights.append(f"向量搜索发现了{vector_enhanced_count}个技能的隐含需求，超越了传统关键词匹配")
            
            # 分析技能集中度
            top_3_share = sum(skill['job_count'] for skill in skills[:3])
            top_3_percentage = self._format_percentage(top_3_share, total_jobs)
            insights.append(f"前3个热门技能通过语义分析占据了{top_3_percentage}%的市场份额")
            
            # 技能多样性分析
            if len(skills) > 10:
                insights.append("RAG分析显示技能市场呈现多样化趋势，语义搜索发现了更多潜在技能需求")
            else:
                insights.append("技能市场相对集中，向量分析确认了核心技能的重要性")
        
        return insights
    
    def _generate_market_recommendations_vector(self, skills: list) -> list:
        """生成基于向量分析的市场建议"""
        recommendations = []
        
        if skills:
            # 推荐前3个技能
            top_3 = skills[:3]
            skill_names = [skill['name'] for skill in top_3]
            recommendations.append(f"基于RAG分析，优先学习热门技能：{', '.join(skill_names)}")
            
            # 基于薪资的建议
            high_salary_skills = [skill for skill in skills if skill.get('salary_info', {}).get('avg_salary', 0) > 25]
            if high_salary_skills:
                high_salary_names = [skill['name'] for skill in high_salary_skills[:3]]
                recommendations.append(f"高薪资技能推荐：{', '.join(high_salary_names)}（年薪通常超过30万元）")
            
            # 技能组合建议
            if len(skills) >= 5:
                recommendations.append("建议掌握2-3个核心技能，利用向量搜索发现的技能关联性形成组合优势")
            
            recommendations.append("利用RAG系统持续监控技能市场变化，发现新兴技能趋势")
            recommendations.append("结合个人兴趣和职业规划，选择与现有技能栈语义相关的技能方向")
        
        return recommendations