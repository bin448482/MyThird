#!/usr/bin/env python3
"""
模型下载和管理工具

用于下载和管理向量模型，支持离线使用。
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from huggingface_hub import snapshot_download, Repository
from sentence_transformers import SentenceTransformer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelManager:
    """模型管理器"""
    
    def __init__(self, models_dir: str = "./models"):
        """
        初始化模型管理器
        
        Args:
            models_dir: 模型存储目录
        """
        self.models_dir = Path(models_dir)
        self.embeddings_dir = self.models_dir / "embeddings"
        
        # 确保目录存在
        self.models_dir.mkdir(exist_ok=True)
        self.embeddings_dir.mkdir(exist_ok=True)
        
        # 推荐的中文模型列表
        self.recommended_models = {
            # 中文优化模型
            "text2vec-base-chinese": {
                "model_id": "shibing624/text2vec-base-chinese",
                "description": "基础中文向量模型，适合中文语义搜索",
                "size": "~400MB",
                "performance": "balanced"
            },
            "text2vec-large-chinese": {
                "model_id": "GanymedeNil/text2vec-large-chinese", 
                "description": "大型中文向量模型，更高精度",
                "size": "~1.2GB",
                "performance": "high"
            },
            "m3e-base": {
                "model_id": "moka-ai/m3e-base",
                "description": "M3E中文向量模型，综合性能好",
                "size": "~400MB", 
                "performance": "balanced"
            },
            
            # 多语言模型
            "multilingual-mpnet": {
                "model_id": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                "description": "多语言MPNet模型，支持中英文",
                "size": "~1GB",
                "performance": "high"
            },
            "multilingual-minilm": {
                "model_id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "description": "轻量级多语言模型，快速推理",
                "size": "~470MB",
                "performance": "fast"
            },
            
            # 通用英文模型（备选）
            "all-minilm": {
                "model_id": "sentence-transformers/all-MiniLM-L6-v2",
                "description": "轻量级英文模型，快速推理",
                "size": "~90MB",
                "performance": "fast"
            }
        }
        
    def list_available_models(self) -> None:
        """列出可用的预定义模型"""
        print("\n可下载的推荐模型:")
        print("=" * 80)
        
        for key, info in self.recommended_models.items():
            print(f"\n模型名称: {key}")
            print(f"  模型ID: {info['model_id']}")
            print(f"  描述: {info['description']}")
            print(f"  大小: {info['size']}")
            print(f"  性能: {info['performance']}")
            
            # 检查是否已下载
            local_path = self.get_local_model_path(key)
            if local_path and local_path.exists():
                print(f"  状态: ✅ 已下载 ({local_path})")
            else:
                print(f"  状态: ❌ 未下载")
    
    def get_local_model_path(self, model_key: str) -> Optional[Path]:
        """获取模型的本地路径"""
        if model_key in self.recommended_models:
            model_name = self.recommended_models[model_key]['model_id'].split('/')[-1]
            return self.embeddings_dir / model_name
        return None
    
    def download_model(self, model_key: str, force: bool = False) -> Optional[Path]:
        """
        下载指定模型
        
        Args:
            model_key: 模型键名
            force: 是否强制重新下载
            
        Returns:
            Optional[Path]: 下载后的本地路径
        """
        if model_key not in self.recommended_models:
            logger.error(f"未知的模型键: {model_key}")
            return None
            
        model_info = self.recommended_models[model_key]
        model_id = model_info['model_id']
        
        # 检查本地路径
        local_path = self.get_local_model_path(model_key)
        
        if local_path.exists() and not force:
            logger.info(f"模型已存在: {local_path}")
            return local_path
            
        logger.info(f"开始下载模型: {model_id}")
        logger.info(f"预计大小: {model_info['size']}")
        logger.info(f"下载位置: {local_path}")
        
        try:
            # 方法1: 使用SentenceTransformer下载（推荐）
            logger.info("使用SentenceTransformer下载模型...")
            model = SentenceTransformer(model_id, cache_folder=str(self.embeddings_dir))
            
            # 保存到指定位置
            model.save(str(local_path))
            
            logger.info(f"模型下载完成: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"SentenceTransformer下载失败: {e}")
            
            try:
                # 方法2: 使用huggingface_hub下载
                logger.info("尝试使用huggingface_hub下载...")
                snapshot_download(
                    repo_id=model_id,
                    cache_dir=str(self.embeddings_dir),
                    local_dir=str(local_path),
                    local_dir_use_symlinks=False
                )
                
                logger.info(f"模型下载完成: {local_path}")
                return local_path
                
            except Exception as e2:
                logger.error(f"huggingface_hub下载也失败: {e2}")
                return None
    
    def download_recommended_set(self, performance_level: str = "balanced") -> List[Path]:
        """
        下载推荐的模型集合
        
        Args:
            performance_level: 性能级别 (fast/balanced/high)
            
        Returns:
            List[Path]: 成功下载的模型路径列表
        """
        # 根据性能级别选择模型
        models_to_download = []
        
        if performance_level == "fast":
            models_to_download = ["multilingual-minilm", "text2vec-base-chinese"]
        elif performance_level == "high":
            models_to_download = ["text2vec-large-chinese", "multilingual-mpnet"]
        else:  # balanced
            models_to_download = ["text2vec-base-chinese", "m3e-base", "multilingual-minilm"]
        
        logger.info(f"开始下载 {performance_level} 性能级别的推荐模型集合")
        logger.info(f"计划下载: {models_to_download}")
        
        downloaded_paths = []
        
        for model_key in models_to_download:
            try:
                path = self.download_model(model_key)
                if path:
                    downloaded_paths.append(path)
            except Exception as e:
                logger.error(f"下载模型 {model_key} 失败: {e}")
                
        return downloaded_paths
    
    def verify_model(self, model_path: Path) -> bool:
        """
        验证模型是否可用
        
        Args:
            model_path: 模型路径
            
        Returns:
            bool: 模型是否可用
        """
        try:
            logger.info(f"验证模型: {model_path}")
            
            # 尝试加载模型
            model = SentenceTransformer(str(model_path))
            
            # 尝试编码测试文本
            test_texts = ["测试文本", "test text", "Python开发工程师"]
            embeddings = model.encode(test_texts)
            
            logger.info(f"模型验证成功，嵌入维度: {embeddings.shape}")
            return True
            
        except Exception as e:
            logger.error(f"模型验证失败: {e}")
            return False
    
    def generate_config_template(self) -> Dict:
        """生成配置文件模板"""
        
        # 查找已下载的模型
        available_models = {}
        
        for model_key, model_info in self.recommended_models.items():
            local_path = self.get_local_model_path(model_key)
            if local_path and local_path.exists():
                available_models[model_key] = {
                    "path": str(local_path),
                    "model_id": model_info['model_id'],
                    "performance": model_info['performance']
                }
        
        # 选择默认模型（优先级：balanced > fast > high）
        default_model = None
        for perf in ["balanced", "fast", "high"]:
            for key, info in available_models.items():
                if self.recommended_models[key]['performance'] == perf:
                    default_model = key
                    break
            if default_model:
                break
        
        config_template = {
            "rag_system": {
                "vector_db": {
                    "embeddings": {
                        # 本地模型配置
                        "offline_mode": True,
                        "local_model_path": str(available_models[default_model]['path']) if default_model else "",
                        "cache_folder": str(self.embeddings_dir),
                        
                        # 备选配置
                        "model_name": available_models[default_model]['model_id'] if default_model else "",
                        "chinese_optimized": True,
                        "performance_level": "balanced",
                        
                        # 设备配置
                        "device": "cpu",
                        "normalize_embeddings": True,
                        "batch_size": 32,
                        "trust_remote_code": True
                    }
                }
            },
            
            # 可用模型列表（供参考）
            "_available_models": available_models,
            "_model_info": {
                "description": "本地模型配置文件",
                "generated_by": "download_models.py",
                "usage": "将 local_model_path 设置为所需模型的路径"
            }
        }
        
        return config_template
    
    def save_config_template(self, output_path: str = "config/local_models_config.yaml"):
        """保存配置文件模板"""
        config = self.generate_config_template()
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
        logger.info(f"配置模板已保存到: {output_file}")
        
        # 显示使用说明
        print(f"\n配置文件已生成: {output_file}")
        print("\n使用方法:")
        print("1. 将生成的配置合并到你的主配置文件中")
        print("2. 或者设置环境变量指向此配置文件")
        print("3. 确保 local_model_path 指向正确的模型路径")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="模型下载和管理工具")
    
    parser.add_argument("--models-dir", default="./models", 
                       help="模型存储目录 (默认: ./models)")
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出模型命令
    list_parser = subparsers.add_parser('list', help='列出可用模型')
    
    # 下载模型命令
    download_parser = subparsers.add_parser('download', help='下载指定模型')
    download_parser.add_argument('model_key', help='模型键名')
    download_parser.add_argument('--force', action='store_true', help='强制重新下载')
    
    # 下载推荐集合命令
    batch_parser = subparsers.add_parser('download-set', help='下载推荐模型集合')
    batch_parser.add_argument('--performance', choices=['fast', 'balanced', 'high'],
                            default='balanced', help='性能级别')
    
    # 验证模型命令
    verify_parser = subparsers.add_parser('verify', help='验证模型')
    verify_parser.add_argument('model_path', help='模型路径')
    
    # 生成配置命令
    config_parser = subparsers.add_parser('generate-config', help='生成配置文件')
    config_parser.add_argument('--output', default='config/local_models_config.yaml',
                              help='输出路径')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建模型管理器
    manager = ModelManager(args.models_dir)
    
    try:
        if args.command == 'list':
            manager.list_available_models()
            
        elif args.command == 'download':
            path = manager.download_model(args.model_key, args.force)
            if path:
                print(f"\n✅ 模型下载完成: {path}")
            else:
                print(f"\n❌ 模型下载失败: {args.model_key}")
                
        elif args.command == 'download-set':
            paths = manager.download_recommended_set(args.performance)
            print(f"\n✅ 成功下载 {len(paths)} 个模型")
            for path in paths:
                print(f"  - {path}")
                
        elif args.command == 'verify':
            model_path = Path(args.model_path)
            if manager.verify_model(model_path):
                print(f"✅ 模型验证成功: {model_path}")
            else:
                print(f"❌ 模型验证失败: {model_path}")
                
        elif args.command == 'generate-config':
            manager.save_config_template(args.output)
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        logger.error(f"执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()