#!/usr/bin/env python3
"""
简历管理模块
负责简历的存储、缓存和检索，避免重复处理
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .resume_document_parser import ResumeDocumentParser
from .resume_document_processor import ResumeDocumentProcessor
from ..matcher.generic_resume_models import GenericResumeProfile

logger = logging.getLogger(__name__)


class ResumeManager:
    """简历管理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.cache_dir = Path(self.config.get('cache_dir', './resume_cache'))
        self.enable_cache = self.config.get('enable_cache', True)
        
        # 确保缓存目录存在
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"简历管理器初始化完成，缓存目录: {self.cache_dir}")
    
    def get_file_hash(self, file_path: str) -> str:
        """
        计算文件哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件的MD5哈希值
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_cache_path(self, file_hash: str) -> Path:
        """
        获取缓存文件路径
        
        Args:
            file_hash: 文件哈希值
            
        Returns:
            Path: 缓存文件路径
        """
        return self.cache_dir / f"{file_hash}.json"
    
    def is_cached(self, file_path: str) -> bool:
        """
        检查文件是否已缓存
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否已缓存
        """
        if not self.enable_cache:
            return False
            
        try:
            file_hash = self.get_file_hash(file_path)
            cache_path = self.get_cache_path(file_hash)
            return cache_path.exists()
        except Exception as e:
            logger.warning(f"检查缓存失败: {e}")
            return False
    
    def load_from_cache(self, file_path: str) -> Optional[GenericResumeProfile]:
        """
        从缓存加载简历
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[GenericResumeProfile]: 缓存的简历档案，如果不存在则返回None
        """
        if not self.enable_cache:
            return None
            
        try:
            file_hash = self.get_file_hash(file_path)
            cache_path = self.get_cache_path(file_hash)
            
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查缓存是否过期
            cache_time = datetime.fromisoformat(cache_data['cached_at'])
            cache_ttl_hours = self.config.get('cache_ttl_hours', 24)
            
            if (datetime.now() - cache_time).total_seconds() > cache_ttl_hours * 3600:
                logger.info(f"缓存已过期: {file_path}")
                cache_path.unlink()  # 删除过期缓存
                return None
            
            # 从缓存数据创建简历档案
            profile = GenericResumeProfile.from_dict(cache_data['profile'])
            logger.info(f"从缓存加载简历: {profile.name}")
            return profile
            
        except Exception as e:
            logger.error(f"从缓存加载简历失败: {e}")
            return None
    
    def save_to_cache(self, file_path: str, profile: GenericResumeProfile):
        """
        保存简历到缓存
        
        Args:
            file_path: 文件路径
            profile: 简历档案
        """
        if not self.enable_cache:
            return
            
        try:
            file_hash = self.get_file_hash(file_path)
            cache_path = self.get_cache_path(file_hash)
            
            cache_data = {
                'file_path': file_path,
                'file_hash': file_hash,
                'cached_at': datetime.now().isoformat(),
                'profile': profile.to_dict()
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"简历已缓存: {profile.name}")
            
        except Exception as e:
            logger.error(f"保存简历到缓存失败: {e}")
    
    async def process_resume_with_cache(self, file_path: str, 
                                      parser: ResumeDocumentParser,
                                      processor: ResumeDocumentProcessor,
                                      force_reprocess: bool = False) -> GenericResumeProfile:
        """
        带缓存的简历处理
        
        Args:
            file_path: 文件路径
            parser: 文档解析器
            processor: RAG处理器
            force_reprocess: 是否强制重新处理
            
        Returns:
            GenericResumeProfile: 简历档案
        """
        # 检查缓存
        if not force_reprocess:
            cached_profile = self.load_from_cache(file_path)
            if cached_profile:
                logger.info(f"使用缓存的简历: {cached_profile.name}")
                return cached_profile
        
        # 处理简历
        logger.info(f"处理简历文档: {file_path}")
        content = parser.extract_content(file_path)
        profile = await processor.process_resume_document(content)
        
        # 保存到缓存
        self.save_to_cache(file_path, profile)
        
        return profile
    
    def list_cached_resumes(self) -> List[Dict[str, Any]]:
        """
        列出所有缓存的简历
        
        Returns:
            List[Dict]: 缓存的简历列表
        """
        cached_resumes = []
        
        if not self.enable_cache or not self.cache_dir.exists():
            return cached_resumes
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cached_resumes.append({
                    'file_path': cache_data.get('file_path', ''),
                    'file_hash': cache_data.get('file_hash', ''),
                    'cached_at': cache_data.get('cached_at', ''),
                    'name': cache_data.get('profile', {}).get('name', '未知'),
                    'cache_file': str(cache_file)
                })
                
            except Exception as e:
                logger.warning(f"读取缓存文件失败 {cache_file}: {e}")
        
        return cached_resumes
    
    def clear_cache(self, file_path: str = None):
        """
        清理缓存
        
        Args:
            file_path: 特定文件路径，None表示清理所有缓存
        """
        if not self.enable_cache:
            return
        
        try:
            if file_path:
                # 清理特定文件的缓存
                file_hash = self.get_file_hash(file_path)
                cache_path = self.get_cache_path(file_hash)
                if cache_path.exists():
                    cache_path.unlink()
                    logger.info(f"已清理缓存: {file_path}")
            else:
                # 清理所有缓存
                if self.cache_dir.exists():
                    for cache_file in self.cache_dir.glob("*.json"):
                        cache_file.unlink()
                    logger.info("已清理所有简历缓存")
                    
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict: 缓存统计信息
        """
        if not self.enable_cache:
            return {'cache_enabled': False}
        
        cached_resumes = self.list_cached_resumes()
        
        return {
            'cache_enabled': True,
            'cache_dir': str(self.cache_dir),
            'total_cached': len(cached_resumes),
            'cache_size_mb': sum(
                cache_file.stat().st_size 
                for cache_file in self.cache_dir.glob("*.json")
            ) / 1024 / 1024 if self.cache_dir.exists() else 0,
            'oldest_cache': min(
                (r['cached_at'] for r in cached_resumes), 
                default=None
            ),
            'newest_cache': max(
                (r['cached_at'] for r in cached_resumes), 
                default=None
            )
        }


def create_resume_manager(config: Dict = None) -> ResumeManager:
    """
    创建简历管理器的便捷函数
    
    Args:
        config: 配置字典
        
    Returns:
        ResumeManager: 简历管理器实例
    """
    return ResumeManager(config)


if __name__ == "__main__":
    # 示例用法
    import asyncio
    from .resume_document_parser import ResumeDocumentParser
    from .resume_document_processor import ResumeDocumentProcessor
    from .llm_factory import create_llm
    
    async def example_usage():
        # 创建管理器
        manager = ResumeManager({
            'cache_dir': './test_resume_cache',
            'enable_cache': True,
            'cache_ttl_hours': 24
        })
        
        # 创建解析器和处理器
        parser = ResumeDocumentParser()
        llm_client = create_llm("zhipu", api_key="your-api-key")
        processor = ResumeDocumentProcessor(llm_client)
        
        # 处理简历（带缓存）
        # profile = await manager.process_resume_with_cache(
        #     "resume.md", parser, processor
        # )
        
        # 获取缓存统计
        stats = manager.get_cache_stats()
        print("缓存统计:", stats)
        
        # 列出缓存的简历
        cached = manager.list_cached_resumes()
        print("缓存的简历:", cached)
    
    # asyncio.run(example_usage())
    print("简历管理器模块加载完成")