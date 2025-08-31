#!/usr/bin/env python3
"""
本地模型快速设置脚本

一键设置本地向量模型环境，避免代理依赖问题。
"""

import os
import sys
import yaml
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_requirements():
    """检查依赖包"""
    required_imports = [
        ('sentence_transformers', 'sentence-transformers'),
        ('huggingface_hub', 'huggingface-hub'), 
        ('transformers', 'transformers'),
        ('torch', 'torch'),
        ('yaml', 'pyyaml')
    ]
    
    missing_packages = []
    
    for import_name, package_name in required_imports:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        logger.error(f"缺少依赖包: {missing_packages}")
        logger.info("请运行: pip install sentence-transformers huggingface-hub pyyaml")
        return False
    
    return True


def setup_local_models(performance_level: str = "balanced"):
    """设置本地模型环境"""
    
    logger.info(f"开始设置本地模型环境 (性能级别: {performance_level})")
    
    # 1. 创建模型目录
    models_dir = Path("./models/embeddings")
    models_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"创建模型目录: {models_dir}")
    
    # 2. 下载模型
    logger.info("开始下载推荐模型...")
    
    try:
        # 导入下载脚本
        sys.path.insert(0, str(Path(__file__).parent))
        from download_models import ModelManager
        
        manager = ModelManager(str(models_dir.parent))
        downloaded_models = manager.download_recommended_set(performance_level)
        
        if not downloaded_models:
            logger.error("没有成功下载任何模型")
            return False
            
        logger.info(f"成功下载 {len(downloaded_models)} 个模型")
        
        # 3. 生成配置文件
        config_path = "config/local_models_config.yaml"
        manager.save_config_template(config_path)
        
        # 4. 更新主配置文件
        update_main_config(downloaded_models[0])
        
        logger.info("✅ 本地模型环境设置完成!")
        print_usage_instructions(downloaded_models[0])
        
        return True
        
    except Exception as e:
        logger.error(f"设置失败: {e}")
        return False


def update_main_config(model_path: Path):
    """更新主配置文件"""
    
    config_files = [
        "config/integration_config.yaml",
        "config/config.yaml"
    ]
    
    for config_file in config_files:
        if Path(config_file).exists():
            try:
                logger.info(f"更新配置文件: {config_file}")
                
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 更新向量模型配置
                if 'rag_system' in config and 'vector_db' in config['rag_system']:
                    embeddings_config = config['rag_system']['vector_db'].get('embeddings', {})
                    embeddings_config.update({
                        'offline_mode': True,
                        'local_model_path': str(model_path),
                        'cache_folder': './models/embeddings'
                    })
                    config['rag_system']['vector_db']['embeddings'] = embeddings_config
                    
                    # 备份原配置
                    backup_file = f"{config_file}.backup"
                    if not Path(backup_file).exists():
                        Path(config_file).rename(backup_file)
                        logger.info(f"备份原配置: {backup_file}")
                    
                    # 保存更新后的配置
                    with open(config_file, 'w', encoding='utf-8') as f:
                        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                    
                    logger.info(f"配置文件已更新: {config_file}")
                    break
                    
            except Exception as e:
                logger.warning(f"更新配置文件失败 {config_file}: {e}")


def print_usage_instructions(model_path: Path):
    """打印使用说明"""
    
    print("\n" + "="*60)
    print("本地模型环境设置完成!")
    print("="*60)
    
    print(f"\n模型位置: {model_path}")
    print(f"配置文件: config/integration_config.yaml")
    
    print("\n使用方法:")
    print("1. 确认配置文件中 offline_mode: true")
    print("2. 确认 local_model_path 指向正确路径")
    print("3. 运行你的RAG系统:")
    print("   python rag_cli.py status")
    print("   python rag_cli.py pipeline run")
    
    print("\n手动配置 (如果自动配置失败):")
    print("在你的配置文件中添加:")
    print("```yaml")
    print("rag_system:")
    print("  vector_db:")
    print("    embeddings:")
    print("      offline_mode: true")
    print(f"      local_model_path: \"{model_path}\"")
    print("      cache_folder: \"./models/embeddings\"")
    print("```")
    
    print("\n其他有用命令:")
    print("- 列出可用模型: python scripts/download_models.py list")
    print("- 验证模型: python scripts/download_models.py verify <model_path>")
    print("- 下载其他模型: python scripts/download_models.py download <model_key>")


def main():
    """主函数"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="本地模型快速设置")
    parser.add_argument("--performance", choices=["fast", "balanced", "high"],
                       default="balanced", help="性能级别")
    parser.add_argument("--check-only", action="store_true", help="仅检查环境")
    
    args = parser.parse_args()
    
    print("本地模型快速设置工具")
    print("解决向量模型代理依赖问题")
    print("-" * 40)
    
    # 检查依赖
    if not check_requirements():
        print("环境检查失败，请先安装依赖包")
        sys.exit(1)
    
    if args.check_only:
        print("环境检查通过")
        return
    
    # 设置本地模型
    success = setup_local_models(args.performance)
    
    if success:
        print("设置完成! 现在可以离线使用向量模型了。")
    else:
        print("设置失败，请检查错误信息并重试。")
        sys.exit(1)


if __name__ == "__main__":
    main()