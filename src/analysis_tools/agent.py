"""
就业市场分析智能Agent

基于LangChain框架的智能分析Agent，整合所有分析工具，
提供自然语言问答和智能分析功能
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage
from langchain.callbacks.base import BaseCallbackHandler

from .skill_demand_tool import SkillDemandAnalysisTool
from .salary_analysis_tool import SalaryAnalysisTool
from .trend_analysis_tool import TrendAnalysisTool
from ..rag.llm_factory import create_llm

logger = logging.getLogger(__name__)


class AnalysisCallbackHandler(BaseCallbackHandler):
    """分析过程回调处理器"""
    
    def __init__(self):
        self.steps = []
        self.current_step = None
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """工具开始执行时的回调"""
        tool_name = serialized.get("name", "unknown")
        self.current_step = {
            "tool": tool_name,
            "input": input_str,
            "start_time": datetime.now(),
            "status": "running"
        }
        logger.info(f"开始执行工具: {tool_name}")
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """工具执行完成时的回调"""
        if self.current_step:
            self.current_step.update({
                "output": output[:200] + "..." if len(output) > 200 else output,
                "end_time": datetime.now(),
                "status": "completed"
            })
            self.steps.append(self.current_step)
            logger.info(f"工具执行完成: {self.current_step['tool']}")
    
    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """工具执行错误时的回调"""
        if self.current_step:
            self.current_step.update({
                "error": str(error),
                "end_time": datetime.now(),
                "status": "error"
            })
            self.steps.append(self.current_step)
            logger.error(f"工具执行错误: {self.current_step['tool']} - {error}")


class JobMarketAnalysisAgent:
    """就业市场分析智能Agent"""
    
    def __init__(self, coordinator, config: Dict[str, Any]):
        """
        初始化分析Agent
        
        Args:
            coordinator: RAG系统协调器
            config: 配置字典
        """
        self.coordinator = coordinator
        self.config = config
        self.agent_config = config.get('langchain_agent', {})
        
        # 初始化LLM
        self.llm = self._initialize_llm()
        
        # 初始化分析工具
        self.tools = self._initialize_tools()
        
        # 初始化记忆
        self.memory = self._initialize_memory()
        
        # 初始化回调处理器
        self.callback_handler = AnalysisCallbackHandler()
        
        # 创建Agent
        self.agent = self._create_agent()
        
        logger.info("就业市场分析Agent初始化完成")
    
    def _initialize_llm(self):
        """初始化LLM"""
        try:
            llm_config = self.agent_config.get('llm', {})
            
            llm = create_llm(
                provider=llm_config.get('provider', 'zhipu'),
                api_key=llm_config.get('api_key'),
                model=llm_config.get('model', 'glm-4-flash'),
                temperature=llm_config.get('temperature', 0.1),
                max_tokens=llm_config.get('max_tokens', 2000)
            )
            
            logger.info(f"LLM初始化成功: {llm_config.get('provider', 'zhipu')}")
            return llm
            
        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            raise
    
    def _initialize_tools(self) -> List:
        """初始化分析工具"""
        tools = []
        tool_config = self.agent_config.get('tools', {})
        
        try:
            # 获取数据库管理器和向量管理器
            db_manager = self.coordinator.db_reader
            vector_manager = self.coordinator.vector_manager
            
            # 技能需求分析工具
            if tool_config.get('skill_demand_analysis', {}).get('enabled', True):
                skill_tool = SkillDemandAnalysisTool(
                    db_manager=db_manager,
                    vector_manager=vector_manager
                )
                tools.append(skill_tool)
                logger.info("技能需求分析工具已加载")
            
            # 薪资分析工具
            if tool_config.get('salary_analysis', {}).get('enabled', True):
                salary_tool = SalaryAnalysisTool(
                    db_manager=db_manager,
                    vector_manager=vector_manager
                )
                tools.append(salary_tool)
                logger.info("薪资分析工具已加载")
            
            # 趋势分析工具
            if tool_config.get('trend_analysis', {}).get('enabled', True):
                trend_tool = TrendAnalysisTool(
                    db_manager=db_manager,
                    vector_manager=vector_manager
                )
                tools.append(trend_tool)
                logger.info("趋势分析工具已加载")
            
            logger.info(f"共加载了 {len(tools)} 个分析工具")
            return tools
            
        except Exception as e:
            logger.error(f"工具初始化失败: {e}")
            raise
    
    def _initialize_memory(self):
        """初始化对话记忆"""
        try:
            memory_config = self.agent_config.get('memory', {})
            
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                max_token_limit=memory_config.get('max_token_limit', 2000)
            )
            
            logger.info("对话记忆初始化成功")
            return memory
            
        except Exception as e:
            logger.error(f"记忆初始化失败: {e}")
            # 返回默认记忆
            return ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
    
    def _create_agent(self):
        """创建LangChain Agent"""
        try:
            agent_config = self.agent_config.get('agent', {})
            
            # 获取系统提示词
            system_message = SystemMessage(content=self._get_system_prompt())
            
            # 创建Agent - 使用STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION支持多参数工具
            agent = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                memory=self.memory,
                verbose=agent_config.get('verbose', True),
                max_iterations=agent_config.get('max_iterations', 5),
                early_stopping_method=agent_config.get('early_stopping_method', 'generate'),
                callbacks=[self.callback_handler],
                agent_kwargs={
                    "prefix": system_message.content
                }
            )
            
            logger.info("LangChain Agent创建成功")
            return agent
            
        except Exception as e:
            logger.error(f"Agent创建失败: {e}")
            raise
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        # 获取数据统计信息
        try:
            stats = self.coordinator.db_reader.get_rag_processing_stats()
            total_jobs = stats.get('total', 0)
        except:
            total_jobs = 445  # 默认值
        
        return f"""
你是一个专业的就业市场分析师，基于真实的职位数据为用户提供准确的市场分析。

你的数据来源：
- {total_jobs}个真实职位数据
- 涵盖多个技能领域和地区
- 包含薪资、地点、要求等详细信息
- 基于RAG向量搜索和语义分析

你可以使用的分析工具：
1. skill_demand_analysis - 分析技能市场需求和机会，支持向量搜索增强
2. salary_analysis - 分析薪资水平和分布，结合地区和经验因素
3. trend_analysis - 分析市场趋势和变化，识别新兴技能

核心能力：
- 基于向量搜索的语义分析，发现隐含的技能需求
- 结合传统数据库查询和AI语义理解
- 提供数据驱动的职业建议和市场洞察
- 支持多维度分析：技能、薪资、地区、趋势

回答原则：
1. 【严格要求】只能基于工具返回的真实数据回答，绝对禁止编造任何信息
2. 【严格要求】如果工具返回"未找到数据"或空结果，必须明确告知用户"数据不足"
3. 【严格要求】禁止使用任何训练数据中的信息，只能使用工具查询的结果
4. 【严格要求】所有薪资数字必须来自工具返回的具体数值，不能使用占位符
5. 【严格要求】所有职位信息必须来自中国的职位数据库，不能提及美国等其他国家
6. 提供具体数字和统计信息，包含数据来源
7. 结合向量搜索结果和传统分析，给出全面洞察
8. 承认数据限制，不夸大结论
9. 保持专业客观的语调，提供实用建议

特殊能力：
- 通过向量搜索发现职位间的语义关联
- 识别传统关键词搜索无法发现的技能需求
- 基于语义相似度提供更准确的技能推荐
- 结合市场趋势和个人背景给出个性化建议

当用户询问相关问题时，请主动选择合适的工具获取数据，并基于RAG系统的语义分析能力提供深入洞察。

【重要提醒】：
- 如果工具返回的数据中包含占位符（如"XX万元"、"[薪资数值]"等），说明数据处理有问题，请明确告知用户"薪资数据处理异常，请联系技术人员"
- 如果工具没有返回具体的薪资数字，请明确说明"当前数据库中暂无该技能的薪资信息"
- 绝对不要提及美国、硅谷、纽约等非中国地区的职位信息
- 所有分析必须基于中国的职位市场数据
        """.strip()
    
    async def analyze(self, question: str) -> Dict[str, Any]:
        """
        分析用户问题并返回结果
        
        Args:
            question: 用户问题
            
        Returns:
            分析结果字典
        """
        try:
            start_time = datetime.now()
            
            # 重置回调处理器
            self.callback_handler.steps = []
            
            logger.info(f"开始分析问题: {question}")
            
            # 使用Agent处理问题
            response = await self.agent.arun(question)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # 构建结果
            result = {
                'question': question,
                'response': response,
                'processing_time': processing_time,
                'timestamp': end_time.isoformat(),
                'tools_used': [step['tool'] for step in self.callback_handler.steps],
                'analysis_steps': self.callback_handler.steps,
                'success': True
            }
            
            logger.info(f"问题分析完成，用时 {processing_time:.2f} 秒")
            return result
            
        except Exception as e:
            logger.error(f"问题分析失败: {e}")
            return {
                'question': question,
                'response': f"分析过程中出现错误: {str(e)}",
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def run(self, question: str) -> Dict[str, Any]:
        """
        同步版本的分析方法
        
        Args:
            question: 用户问题
            
        Returns:
            分析结果字典
        """
        try:
            start_time = datetime.now()
            
            # 重置回调处理器
            self.callback_handler.steps = []
            
            logger.info(f"开始分析问题: {question}")
            
            # 使用Agent处理问题
            response = self.agent.run(question)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # 构建结果
            result = {
                'question': question,
                'response': response,
                'processing_time': processing_time,
                'timestamp': end_time.isoformat(),
                'tools_used': [step['tool'] for step in self.callback_handler.steps],
                'analysis_steps': self.callback_handler.steps,
                'success': True
            }
            
            logger.info(f"问题分析完成，用时 {processing_time:.2f} 秒")
            return result
            
        except Exception as e:
            logger.error(f"问题分析失败: {e}")
            return {
                'question': question,
                'response': f"分析过程中出现错误: {str(e)}",
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        try:
            messages = self.memory.chat_memory.messages
            history = []
            
            for message in messages:
                history.append({
                    'type': message.__class__.__name__,
                    'content': message.content,
                    'timestamp': getattr(message, 'timestamp', None)
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []
    
    def clear_memory(self):
        """清除对话记忆"""
        try:
            self.memory.clear()
            logger.info("对话记忆已清除")
        except Exception as e:
            logger.error(f"清除记忆失败: {e}")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """获取Agent状态信息"""
        return {
            'tools_count': len(self.tools),
            'tools_available': [tool.name for tool in self.tools],
            'memory_messages_count': len(self.memory.chat_memory.messages),
            'llm_provider': self.agent_config.get('llm', {}).get('provider', 'unknown'),
            'agent_type': 'OPENAI_FUNCTIONS',
            'callback_steps': len(self.callback_handler.steps),
            'last_analysis_time': self.callback_handler.steps[-1].get('end_time') if self.callback_handler.steps else None
        }
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        try:
            # 统计工具使用情况
            tool_usage = {}
            total_analyses = 0
            successful_analyses = 0
            
            for step in self.callback_handler.steps:
                tool_name = step['tool']
                tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
                total_analyses += 1
                if step['status'] == 'completed':
                    successful_analyses += 1
            
            # 计算平均处理时间
            processing_times = []
            for step in self.callback_handler.steps:
                if step.get('start_time') and step.get('end_time'):
                    duration = (step['end_time'] - step['start_time']).total_seconds()
                    processing_times.append(duration)
            
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            return {
                'total_analyses': total_analyses,
                'successful_analyses': successful_analyses,
                'success_rate': (successful_analyses / total_analyses * 100) if total_analyses > 0 else 0,
                'tool_usage': tool_usage,
                'average_processing_time': avg_processing_time,
                'conversation_length': len(self.memory.chat_memory.messages)
            }
            
        except Exception as e:
            logger.error(f"获取分析统计失败: {e}")
            return {}
    
    def optimize_performance(self):
        """优化Agent性能"""
        try:
            # 清理过长的对话历史
            max_messages = self.agent_config.get('memory', {}).get('max_token_limit', 2000) // 100
            messages = self.memory.chat_memory.messages
            
            if len(messages) > max_messages:
                # 保留最近的消息
                self.memory.chat_memory.messages = messages[-max_messages:]
                logger.info(f"对话历史已优化，保留最近 {max_messages} 条消息")
            
            # 清理回调步骤历史
            if len(self.callback_handler.steps) > 50:
                self.callback_handler.steps = self.callback_handler.steps[-25:]
                logger.info("回调步骤历史已优化")
            
        except Exception as e:
            logger.error(f"性能优化失败: {e}")


def create_analysis_agent(coordinator, config: Dict[str, Any]) -> JobMarketAnalysisAgent:
    """
    创建分析Agent实例的工厂函数
    
    Args:
        coordinator: RAG系统协调器
        config: 配置字典
        
    Returns:
        JobMarketAnalysisAgent实例
    """
    try:
        agent = JobMarketAnalysisAgent(coordinator, config)
        logger.info("分析Agent创建成功")
        return agent
    except Exception as e:
        logger.error(f"创建分析Agent失败: {e}")
        raise