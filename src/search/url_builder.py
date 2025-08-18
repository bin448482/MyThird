"""
搜索URL构建器

负责构建前程无忧搜索页面的URL
"""

import urllib.parse
from typing import Dict, List, Optional


class SearchURLBuilder:
    """搜索URL构建器"""
    
    def __init__(self, config: Dict):
        """
        初始化URL构建器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.search_config = config['search']
    
    def build_search_url(self, keyword: Optional[str] = None, **kwargs) -> str:
        """
        构建搜索URL
        
        Args:
            keyword: 搜索关键词，如果为None则使用配置中的默认关键词
            **kwargs: 其他URL参数
            
        Returns:
            完整的搜索URL
        """
        if keyword is None:
            keyword = self.search_config['current_keyword']
        
        # 基础参数
        params = {
            'jobArea': self.search_config['job_area'],
            'keyword': keyword,
            'searchType': self.search_config['search_type'],
            'keywordType': self.search_config['keyword_type']
        }
        
        # 添加额外参数
        params.update(kwargs)
        
        # 构建URL
        base_url = self.search_config['base_url']
        query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        
        return f"{base_url}?{query_string}"
    
    def get_keywords_by_priority(self, priority_level: int = 1) -> List[str]:
        """
        获取指定优先级的关键词
        
        Args:
            priority_level: 优先级级别 (1, 2, 3)
            
        Returns:
            关键词列表
        """
        priority_key = f"priority_{priority_level}"
        return self.search_config['keywords'].get(priority_key, [])
    
    def get_all_keywords(self) -> List[str]:
        """
        获取所有关键词
        
        Returns:
            所有关键词的列表
        """
        all_keywords = []
        for priority in ['priority_1', 'priority_2', 'priority_3']:
            all_keywords.extend(
                self.search_config['keywords'].get(priority, [])
            )
        return all_keywords
    
    def get_current_keyword(self) -> str:
        """
        获取当前配置的关键词
        
        Returns:
            当前关键词
        """
        return self.search_config['current_keyword']
    
    def set_current_keyword(self, keyword: str) -> None:
        """
        设置当前关键词
        
        Args:
            keyword: 要设置的关键词
        """
        self.search_config['current_keyword'] = keyword
    
    def build_multiple_search_urls(self, keywords: Optional[List[str]] = None) -> Dict[str, str]:
        """
        为多个关键词构建搜索URL
        
        Args:
            keywords: 关键词列表，如果为None则使用所有配置的关键词
            
        Returns:
            关键词到URL的映射字典
        """
        if keywords is None:
            keywords = self.get_all_keywords()
        
        urls = {}
        for keyword in keywords:
            urls[keyword] = self.build_search_url(keyword)
        
        return urls
    
    def get_search_config(self) -> Dict:
        """
        获取搜索配置
        
        Returns:
            搜索配置字典
        """
        return self.search_config.copy()
    
    def validate_keyword(self, keyword: str) -> bool:
        """
        验证关键词是否在配置的关键词列表中
        
        Args:
            keyword: 要验证的关键词
            
        Returns:
            是否为有效关键词
        """
        all_keywords = self.get_all_keywords()
        return keyword in all_keywords
    
    def get_priority_for_keyword(self, keyword: str) -> Optional[int]:
        """
        获取关键词的优先级
        
        Args:
            keyword: 关键词
            
        Returns:
            优先级级别，如果关键词不存在则返回None
        """
        for priority in [1, 2, 3]:
            if keyword in self.get_keywords_by_priority(priority):
                return priority
        return None