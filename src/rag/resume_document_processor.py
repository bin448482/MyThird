#!/usr/bin/env python3
"""
简历文档RAG处理器
使用LLM从简历文档中提取结构化信息
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from .llm_factory import create_llm
from .exceptions import (
    ResumeProcessingError, RAGExtractionError, DataValidationError,
    LLMCallError, TimeoutError, handle_exception, log_exception
)
from ..matcher.generic_resume_models import (
    GenericResumeProfile, SkillCategory, WorkExperience,
    Education, Project
)

logger = logging.getLogger(__name__)


class ResumeDocumentProcessor:
    """简历文档RAG处理器"""
    
    def __init__(self, llm_client, config: Dict = None):
        """
        初始化处理器
        
        Args:
            llm_client: LLM客户端实例
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.max_retries = self.config.get('max_retries', 3)
        self.timeout_seconds = self.config.get('timeout_seconds', 60)
        
        logger.info("初始化简历文档RAG处理器")
    
    async def process_resume_document(self, content: str, 
                                    user_hints: Dict = None) -> GenericResumeProfile:
        """
        处理简历文档，生成结构化数据
        
        Args:
            content: 简历文本内容
            user_hints: 用户提供的额外信息提示
            
        Returns:
            GenericResumeProfile: 结构化简历数据
            
        Raises:
            RAGExtractionError: 处理失败
        """
        try:
            logger.info(f"开始处理简历文档，内容长度: {len(content)} 字符")
            
            # 并行提取各部分信息
            tasks = [
                self.extract_basic_info(content),
                self.extract_skills_by_category(content),
                self.extract_work_experience(content),
                self.extract_education(content),
                self.extract_projects(content)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 检查是否有异常
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"提取任务 {i} 失败: {result}")
                    raise RAGExtractionError(f"信息提取失败: {result}")
            
            basic_info, skills_data, work_history, education, projects = results
            
            # 验证和清洗数据
            validated_data = self.validate_and_clean_data({
                'basic_info': basic_info,
                'skill_categories': skills_data.get('skill_categories', []),
                'work_history': work_history.get('work_history', []),
                'education': education.get('education', []),
                'projects': projects.get('projects', [])
            })
            
            # 创建GenericResumeProfile实例
            profile = self.map_to_generic_resume_profile(validated_data, user_hints)
            
            logger.info(f"简历处理完成: {profile.name}")
            return profile
            
        except Exception as e:
            logger.error(f"简历文档处理失败: {e}")
            raise RAGExtractionError(f"处理失败: {e}")
    
    async def extract_basic_info(self, content: str) -> dict:
        """提取基本信息"""
        prompt = self._get_basic_info_prompt(content)
        
        try:
            response = await self._call_llm_with_retry(prompt)
            basic_info = self._parse_json_response(response)
            
            logger.debug(f"提取基本信息: {basic_info}")
            return basic_info
            
        except Exception as e:
            logger.error(f"基本信息提取失败: {e}")
            raise RAGExtractionError(f"基本信息提取失败: {e}")
    
    async def extract_skills_by_category(self, content: str) -> dict:
        """按分类提取技能"""
        prompt = self._get_skills_extraction_prompt(content)
        
        try:
            response = await self._call_llm_with_retry(prompt)
            skills_data = self._parse_json_response(response)
            
            logger.debug(f"提取技能分类: {len(skills_data.get('skill_categories', []))} 个分类")
            return skills_data
            
        except Exception as e:
            logger.error(f"技能提取失败: {e}")
            raise RAGExtractionError(f"技能提取失败: {e}")
    
    async def extract_work_experience(self, content: str) -> dict:
        """提取工作经验"""
        prompt = self._get_work_experience_prompt(content)
        
        try:
            response = await self._call_llm_with_retry(prompt)
            work_data = self._parse_json_response(response)
            
            logger.debug(f"提取工作经验: {len(work_data.get('work_history', []))} 段经历")
            return work_data
            
        except Exception as e:
            logger.error(f"工作经验提取失败: {e}")
            raise RAGExtractionError(f"工作经验提取失败: {e}")
    
    async def extract_education(self, content: str) -> dict:
        """提取教育背景"""
        prompt = self._get_education_prompt(content)
        
        try:
            response = await self._call_llm_with_retry(prompt)
            education_data = self._parse_json_response(response)
            
            logger.debug(f"提取教育背景: {len(education_data.get('education', []))} 条记录")
            return education_data
            
        except Exception as e:
            logger.error(f"教育背景提取失败: {e}")
            raise RAGExtractionError(f"教育背景提取失败: {e}")
    
    async def extract_projects(self, content: str) -> dict:
        """提取项目经验"""
        prompt = self._get_projects_prompt(content)
        
        try:
            response = await self._call_llm_with_retry(prompt)
            projects_data = self._parse_json_response(response)
            
            logger.debug(f"提取项目经验: {len(projects_data.get('projects', []))} 个项目")
            return projects_data
            
        except Exception as e:
            logger.error(f"项目经验提取失败: {e}")
            raise RAGExtractionError(f"项目经验提取失败: {e}")
    
    def validate_and_clean_data(self, data: dict) -> dict:
        """验证和清洗数据"""
        try:
            cleaned_data = {}
            
            # 验证基本信息
            basic_info = data.get('basic_info', {})
            cleaned_data['basic_info'] = {
                'name': str(basic_info.get('name', '')).strip(),
                'phone': str(basic_info.get('phone', '')).strip(),
                'email': str(basic_info.get('email', '')).strip(),
                'location': str(basic_info.get('location', '')).strip(),
                'current_position': str(basic_info.get('current_position', '')).strip(),
                'current_company': str(basic_info.get('current_company', '')).strip(),
                'total_experience_years': max(0, int(basic_info.get('total_experience_years', 0)))
            }
            
            # 验证技能分类
            skill_categories = data.get('skill_categories', [])
            cleaned_skills = []
            for category in skill_categories:
                if isinstance(category, dict) and category.get('skills'):
                    cleaned_category = {
                        'category_name': str(category.get('category_name', '')).strip(),
                        'skills': [str(skill).strip() for skill in category.get('skills', []) if str(skill).strip()],
                        'proficiency_level': str(category.get('proficiency_level', 'intermediate')).strip()
                    }
                    if cleaned_category['skills']:
                        cleaned_skills.append(cleaned_category)
            cleaned_data['skill_categories'] = cleaned_skills
            
            # 验证工作经验
            work_history = data.get('work_history', [])
            cleaned_work = []
            for work in work_history:
                if isinstance(work, dict) and work.get('company'):
                    cleaned_work_item = {
                        'company': str(work.get('company', '')).strip(),
                        'position': str(work.get('position', '')).strip(),
                        'start_date': str(work.get('start_date', '')).strip(),
                        'end_date': work.get('end_date'),
                        'duration_years': max(0, float(work.get('duration_years', 0))),
                        'responsibilities': [str(r).strip() for r in work.get('responsibilities', []) if str(r).strip()],
                        'achievements': [str(a).strip() for a in work.get('achievements', []) if str(a).strip()],
                        'technologies': [str(t).strip() for t in work.get('technologies', []) if str(t).strip()],
                        'industry': str(work.get('industry', '')).strip()
                    }
                    if cleaned_work_item['end_date']:
                        cleaned_work_item['end_date'] = str(cleaned_work_item['end_date']).strip()
                    cleaned_work.append(cleaned_work_item)
            cleaned_data['work_history'] = cleaned_work
            
            # 验证教育背景
            education = data.get('education', [])
            cleaned_education = []
            for edu in education:
                if isinstance(edu, dict) and edu.get('university'):
                    cleaned_edu = {
                        'degree': str(edu.get('degree', '')).strip(),
                        'major': str(edu.get('major', '')).strip(),
                        'university': str(edu.get('university', '')).strip(),
                        'graduation_year': str(edu.get('graduation_year', '')).strip(),
                        'gpa': edu.get('gpa'),
                        'honors': [str(h).strip() for h in edu.get('honors', []) if str(h).strip()]
                    }
                    if cleaned_edu['gpa'] is not None:
                        try:
                            cleaned_edu['gpa'] = float(cleaned_edu['gpa'])
                        except (ValueError, TypeError):
                            cleaned_edu['gpa'] = None
                    cleaned_education.append(cleaned_edu)
            cleaned_data['education'] = cleaned_education
            
            # 验证项目经验
            projects = data.get('projects', [])
            cleaned_projects = []
            for project in projects:
                if isinstance(project, dict) and project.get('name'):
                    cleaned_project = {
                        'name': str(project.get('name', '')).strip(),
                        'description': str(project.get('description', '')).strip(),
                        'technologies': [str(t).strip() for t in project.get('technologies', []) if str(t).strip()],
                        'duration': str(project.get('duration', '')).strip(),
                        'achievements': [str(a).strip() for a in project.get('achievements', []) if str(a).strip()],
                        'role': str(project.get('role', '')).strip(),
                        'url': project.get('url')
                    }
                    if cleaned_project['url']:
                        cleaned_project['url'] = str(cleaned_project['url']).strip()
                    cleaned_projects.append(cleaned_project)
            cleaned_data['projects'] = cleaned_projects
            
            logger.info("数据验证和清洗完成")
            return cleaned_data
            
        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise DataValidationError(f"数据验证失败: {e}")
    
    def map_to_generic_resume_profile(self, extracted_data: dict, user_hints: Dict = None) -> GenericResumeProfile:
        """
        将RAG提取的数据映射到GenericResumeProfile
        
        Args:
            extracted_data: RAG提取的原始数据
            user_hints: 用户提供的额外信息提示
            
        Returns:
            GenericResumeProfile: 标准化的简历档案
        """
        try:
            # 基本信息映射
            basic_info = extracted_data.get('basic_info', {})
            
            # 创建GenericResumeProfile实例
            profile = GenericResumeProfile(
                name=basic_info.get('name', ''),
                phone=basic_info.get('phone', ''),
                email=basic_info.get('email', ''),
                location=basic_info.get('location', ''),
                total_experience_years=basic_info.get('total_experience_years', 0),
                current_position=basic_info.get('current_position', ''),
                current_company=basic_info.get('current_company', ''),
                profile_type='rag_generated',
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            # 技能分类映射
            for category_data in extracted_data.get('skill_categories', []):
                skill_category = SkillCategory(
                    category_name=category_data['category_name'],
                    skills=category_data['skills'],
                    proficiency_level=category_data.get('proficiency_level', 'intermediate')
                )
                profile.skill_categories.append(skill_category)
            
            # 工作经验映射
            for work_data in extracted_data.get('work_history', []):
                work_exp = WorkExperience(
                    company=work_data['company'],
                    position=work_data['position'],
                    start_date=work_data['start_date'],
                    end_date=work_data.get('end_date'),
                    duration_years=work_data['duration_years'],
                    responsibilities=work_data.get('responsibilities', []),
                    achievements=work_data.get('achievements', []),
                    technologies=work_data.get('technologies', []),
                    industry=work_data.get('industry', '')
                )
                profile.work_history.append(work_exp)
            
            # 教育背景映射
            for edu_data in extracted_data.get('education', []):
                education = Education(
                    degree=edu_data['degree'],
                    major=edu_data['major'],
                    university=edu_data['university'],
                    graduation_year=edu_data['graduation_year'],
                    gpa=edu_data.get('gpa'),
                    honors=edu_data.get('honors', [])
                )
                profile.education.append(education)
            
            # 项目经验映射
            for proj_data in extracted_data.get('projects', []):
                project = Project(
                    name=proj_data['name'],
                    description=proj_data['description'],
                    technologies=proj_data['technologies'],
                    duration=proj_data['duration'],
                    achievements=proj_data.get('achievements', []),
                    role=proj_data.get('role', ''),
                    url=proj_data.get('url')
                )
                profile.projects.append(project)
            
            # 应用用户提示信息
            if user_hints:
                self._apply_user_hints(profile, user_hints)
            
            logger.info(f"成功映射简历档案: {profile.name}")
            return profile
            
        except Exception as e:
            logger.error(f"数据映射失败: {e}")
            raise DataValidationError(f"数据映射失败: {e}")
    
    def _apply_user_hints(self, profile: GenericResumeProfile, user_hints: Dict):
        """应用用户提示信息"""
        try:
            # 更新期望职位
            if 'preferred_positions' in user_hints:
                profile.preferred_positions = user_hints['preferred_positions']
            
            # 更新薪资期望
            if 'expected_salary_range' in user_hints:
                profile.expected_salary_range = user_hints['expected_salary_range']
            
            # 更新职业目标
            if 'career_objectives' in user_hints:
                profile.career_objectives = user_hints['career_objectives']
            
            # 更新行业经验权重
            if 'industry_experience' in user_hints:
                profile.industry_experience = user_hints['industry_experience']
            
            logger.debug("用户提示信息应用完成")
            
        except Exception as e:
            logger.warning(f"应用用户提示失败: {e}")
    
    async def _call_llm_with_retry(self, prompt: str) -> str:
        """带重试的LLM调用"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"LLM调用尝试 {attempt + 1}/{self.max_retries}")
                
                # 异步调用LLM
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.llm_client, prompt),
                    timeout=self.timeout_seconds
                )
                
                if response and response.strip():
                    return response.strip()
                else:
                    raise RAGExtractionError("LLM返回空响应")
                    
            except asyncio.TimeoutError:
                last_error = f"LLM调用超时 ({self.timeout_seconds}秒)"
                logger.warning(f"尝试 {attempt + 1} 超时")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"尝试 {attempt + 1} 失败: {e}")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避
        
        raise RAGExtractionError(f"LLM调用失败，已重试 {self.max_retries} 次: {last_error}")
    
    def _parse_json_response(self, response: str) -> dict:
        """解析JSON响应"""
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 尝试查找花括号包围的内容
            brace_match = re.search(r'\{.*\}', response, re.DOTALL)
            if brace_match:
                try:
                    return json.loads(brace_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            raise RAGExtractionError(f"无法解析JSON响应: {response[:200]}...")
    
    def _get_basic_info_prompt(self, content: str) -> str:
        """获取基本信息提取Prompt"""
        return f"""
你是一个专业的简历信息提取助手。请从以下简历内容中提取基本信息，并以JSON格式返回。

简历内容：
{content}

请提取以下信息：
1. 姓名 (name)
2. 电话 (phone) 
3. 邮箱 (email)
4. 地址/位置 (location)
5. 当前职位 (current_position)
6. 当前公司 (current_company)
7. 总工作年限 (total_experience_years)

返回格式：
```json
{{
  "name": "姓名",
  "phone": "电话号码",
  "email": "邮箱地址",
  "location": "地址",
  "current_position": "当前职位",
  "current_company": "当前公司",
  "total_experience_years": 数字
}}
```

注意：
- 如果某项信息未找到，请设置为空字符串或0
- 工作年限请根据工作经历计算得出
- 确保返回有效的JSON格式
"""
    
    def _get_skills_extraction_prompt(self, content: str) -> str:
        """获取技能分类提取Prompt"""
        return f"""
你是一个专业的技能分析师。请从以下简历内容中提取技能，并按照指定分类整理。

简历内容：
{content}

请按以下分类提取技能：

1. **核心技能** (core_skills): 最重要的专业技能
2. **编程语言** (programming_languages): 编程语言技能
3. **云平台** (cloud_platforms): 云服务和平台
4. **AI/ML技能** (ai_ml_skills): 人工智能和机器学习相关
5. **数据工程技能** (data_engineering_skills): 数据处理和工程
6. **管理技能** (management_skills): 管理和领导相关

返回格式：
```json
{{
  "skill_categories": [
    {{
      "category_name": "core_skills",
      "skills": ["技能1", "技能2"],
      "proficiency_level": "advanced"
    }},
    {{
      "category_name": "programming_languages", 
      "skills": ["Python", "Java"],
      "proficiency_level": "expert"
    }}
  ]
}}
```

注意：
- proficiency_level可选值：beginner, intermediate, advanced, expert
- 根据简历描述判断技能熟练程度
- 每个分类至少包含相关技能，如无相关技能则skills为空数组
"""
    
    def _get_work_experience_prompt(self, content: str) -> str:
        """获取工作经验提取Prompt"""
        return f"""
你是一个专业的工作经历分析师。请从以下简历内容中提取工作经验信息。

简历内容：
{content}

请提取每段工作经历的以下信息：
1. 公司名称 (company)
2. 职位名称 (position)
3. 开始时间 (start_date) - 格式：YYYY-MM
4. 结束时间 (end_date) - 格式：YYYY-MM，如果是当前工作则为null
5. 工作时长年数 (duration_years) - 精确到小数点后1位
6. 工作职责 (responsibilities) - 数组格式
7. 主要成就 (achievements) - 数组格式  
8. 使用技术 (technologies) - 数组格式
9. 所属行业 (industry)

返回格式：
```json
{{
  "work_history": [
    {{
      "company": "公司名称",
      "position": "职位名称", 
      "start_date": "2022-01",
      "end_date": "2024-01",
      "duration_years": 2.0,
      "responsibilities": [
        "职责描述1",
        "职责描述2"
      ],
      "achievements": [
        "成就描述1", 
        "成就描述2"
      ],
      "technologies": [
        "技术1",
        "技术2"
      ],
      "industry": "行业名称"
    }}
  ]
}}
```

注意：
- 按时间倒序排列（最新的工作在前）
- 如果信息不完整，相关字段设为空数组或空字符串
- duration_years根据start_date和end_date计算
"""
    
    def _get_education_prompt(self, content: str) -> str:
        """获取教育背景提取Prompt"""
        return f"""
你是一个专业的教育背景分析师。请从以下简历内容中提取教育背景信息。

简历内容：
{content}

请提取每个教育经历的以下信息：
1. 学位 (degree)
2. 专业 (major)
3. 学校 (university)
4. 毕业年份 (graduation_year)
5. GPA (gpa) - 可选
6. 荣誉 (honors) - 数组格式

返回格式：
```json
{{
  "education": [
    {{
      "degree": "学士",
      "major": "计算机科学",
      "university": "清华大学",
      "graduation_year": "2020",
      "gpa": 3.8,
      "honors": ["优秀毕业生", "奖学金"]
    }}
  ]
}}
```

注意：
- 按时间倒序排列（最新的教育经历在前）
- 如果信息不完整，相关字段设为空字符串或null
- GPA如果没有明确提及则设为null
"""
    
    def _get_projects_prompt(self, content: str) -> str:
        """获取项目经验提取Prompt"""
        return f"""
你是一个专业的项目经验分析师。请从以下简历内容中提取项目经验信息。

简历内容：
{content}

请提取每个项目的以下信息：
1. 项目名称 (name)
2. 项目描述 (description)
3. 使用技术 (technologies) - 数组格式
4. 项目周期 (duration)
5. 项目成果 (achievements) - 数组格式
6. 担任角色 (role)
7. 项目链接 (url) - 可选

返回格式：
```json
{{
  "projects": [
    {{
      "name": "项目名称",
      "description": "项目描述",
      "technologies": ["Python", "Django", "MySQL"],
      "duration": "6个月",
      "achievements": [
        "成果1",
        "成果2"
      ],
      "role": "技术负责人",
      "url": "https://github.com/example"
    }}
  ]
}}
```

注意：
- 按时间倒序排列（最新的项目在前）
- 如果信息不完整，相关字段设为空字符串或空数组
- url如果没有则设为null
"""


def create_resume_processor(llm_client, config: Dict = None) -> ResumeDocumentProcessor:
    """
    创建简历文档处理器的便捷函数
    
    Args:
        llm_client: LLM客户端实例
        config: 配置字典
        
    Returns:
        ResumeDocumentProcessor: 处理器实例
    """
    return ResumeDocumentProcessor(llm_client, config)


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 示例：创建处理器
    try:
        from .llm_factory import create_llm
        
        # 创建LLM客户端
        llm_client = create_llm("zhipu", api_key="your-api-key")
        
        # 创建处理器
        processor = ResumeDocumentProcessor(llm_client, {
            'max_retries': 3,
            'timeout_seconds': 60
        })
        
        print("简历文档处理器初始化完成")
    except Exception as e:
        print(f"初始化失败: {e}")