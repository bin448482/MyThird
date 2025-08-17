#!/usr/bin/env python3
"""
Resume Auto Submitter - 主入口文件

自动投递简历工具的主入口点
"""

import sys
import argparse
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from core.controller import ResumeSubmitterController
from core.config import ConfigManager
from utils.logger import setup_logger


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="自动投递简历工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py --website zhilian
  python main.py --website boss --debug
  python main.py --config custom_config.yaml
        """
    )
    
    parser.add_argument(
        "--website",
        choices=["zhilian", "qiancheng", "boss"],
        required=True,
        help="选择招聘网站"
    )
    
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="配置文件路径 (默认: config/config.yaml)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，不实际投递简历"
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 加载配置
        config_manager = ConfigManager(args.config)
        config = config_manager.load_config()
        
        # 设置调试模式
        if args.debug:
            config['app']['debug'] = True
        
        # 设置日志
        logger = setup_logger(config)
        logger.info("=== 自动投递简历工具启动 ===")
        logger.info(f"选择网站: {args.website}")
        logger.info(f"配置文件: {args.config}")
        logger.info(f"调试模式: {args.debug}")
        logger.info(f"试运行模式: {args.dry_run}")
        
        # 创建控制器并运行
        controller = ResumeSubmitterController(config, args.website, args.dry_run)
        controller.run()
        
        logger.info("=== 程序执行完成 ===")
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"程序执行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()