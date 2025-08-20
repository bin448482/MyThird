#!/usr/bin/env python3
"""
RAG数据流水线运行脚本

提供命令行接口来运行RAG数据处理流水线
"""

import sys
import asyncio
import argparse
import logging
from pathlib import Path
import json

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.rag.data_pipeline import RAGDataPipeline, create_progress_callback

def setup_logging(log_level: str = 'INFO'):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('./logs/rag_pipeline.log', encoding='utf-8')
        ]
    )

def load_config(config_file: str = None) -> dict:
    """加载配置文件"""
    if config_file and Path(config_file).exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 默认配置
    return {
        'rag_system': {
            'database': {
                'path': './data/jobs.db',
                'batch_size': 50
            },
            'llm': {
                'provider': 'zhipu',
                'model': 'glm-4-flash',
                'api_key': 'your-api-key-here',
                'temperature': 0.1,
                'max_tokens': 1500
            },
            'vector_db': {
                'persist_directory': './chroma_db',
                'collection_name': 'job_positions',
                'embeddings': {
                    'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                    'device': 'cpu',
                    'normalize_embeddings': True
                }
            },
            'documents': {
                'types': ['overview', 'responsibility', 'requirement', 'skills', 'basic_requirements'],
                'create_comprehensive_doc': False
            },
            'processing': {
                'skip_processed': True,
                'force_reprocess': False,
                'batch_size': 50,
                'max_retry_attempts': 3
            }
        }
    }

async def run_pipeline_command(args):
    """运行流水线命令"""
    print("🚀 启动RAG数据流水线")
    print("=" * 50)
    
    try:
        # 加载配置
        config = load_config(args.config)
        
        # 覆盖命令行参数
        if args.batch_size:
            config['rag_system']['processing']['batch_size'] = args.batch_size
        if args.force_reprocess:
            config['rag_system']['processing']['force_reprocess'] = True
        
        # 创建进度回调
        progress_callback = create_progress_callback() if args.show_progress else None
        
        # 初始化流水线
        pipeline = RAGDataPipeline(config, progress_callback)
        
        # 运行流水线
        result = await pipeline.run_full_pipeline(
            batch_size=args.batch_size or 50,
            max_jobs=args.max_jobs,
            force_reprocess=args.force_reprocess,
            save_progress=not args.no_save
        )
        
        # 显示结果
        print("\n📊 流水线执行结果:")
        print("=" * 30)
        
        exec_summary = result.get('execution_summary', {})
        proc_stats = result.get('processing_statistics', {})
        data_quality = result.get('data_quality', {})
        
        print(f"执行状态: {exec_summary.get('status', 'unknown')}")
        print(f"执行时间: {exec_summary.get('execution_time', 0):.1f} 秒")
        print(f"处理职位: {proc_stats.get('processed_jobs', 0)} / {proc_stats.get('total_jobs', 0)}")
        print(f"成功率: {proc_stats.get('success_rate', 0):.1f}%")
        print(f"处理速率: {proc_stats.get('processing_rate', 0):.2f} 职位/秒")
        print(f"数据质量评分: {data_quality.get('quality_score', 0):.2f}")
        
        # 显示建议
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"\n💡 建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        # 显示问题
        issues = result.get('issues', [])
        if issues:
            print(f"\n⚠️ 问题:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
        
        print(f"\n✅ 流水线执行完成!")
        return True
        
    except Exception as e:
        print(f"❌ 流水线执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def status_command(args):
    """状态查询命令"""
    print("📊 RAG系统状态查询")
    print("=" * 30)
    
    try:
        config = load_config(args.config)
        pipeline = RAGDataPipeline(config)
        
        # 初始化系统（仅用于状态查询）
        await pipeline._initialize_pipeline()
        
        # 获取状态
        status = pipeline.get_pipeline_status()
        
        # 显示系统状态
        system_status = status.get('system_status', {})
        print(f"系统初始化: {'✅' if system_status.get('is_initialized') else '❌'}")
        
        components = system_status.get('components', {})
        print("组件状态:")
        for comp_name, comp_status in components.items():
            status_icon = "✅" if comp_status else "❌"
            print(f"  {comp_name}: {status_icon}")
        
        # 显示处理进度
        progress = status.get('processing_progress', {})
        db_stats = progress.get('database_stats', {})
        
        print(f"\n数据库统计:")
        print(f"  总职位数: {db_stats.get('total', 0)}")
        print(f"  已处理: {db_stats.get('processed', 0)}")
        print(f"  未处理: {db_stats.get('unprocessed', 0)}")
        print(f"  处理率: {db_stats.get('processing_rate', 0):.1f}%")
        
        vector_stats = progress.get('vector_stats', {})
        print(f"\n向量数据库统计:")
        print(f"  文档数量: {vector_stats.get('document_count', 0)}")
        print(f"  集合名称: {vector_stats.get('collection_name', 'N/A')}")
        
        # 估算处理时间
        if args.estimate_time:
            estimate = pipeline.estimate_processing_time(args.batch_size or 50)
            if 'error' not in estimate:
                print(f"\n⏱️ 处理时间估算:")
                print(f"  未处理职位: {estimate.get('unprocessed_jobs', 0)}")
                print(f"  预计时间: {estimate.get('estimated_time_minutes', 0):.1f} 分钟")
                print(f"  预计批次: {estimate.get('estimated_batches', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 状态查询失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RAG数据流水线管理工具')
    
    # 全局参数
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 运行流水线命令
    run_parser = subparsers.add_parser('run', help='运行RAG数据流水线')
    run_parser.add_argument('--batch-size', '-b', type=int, help='批处理大小')
    run_parser.add_argument('--max-jobs', '-m', type=int, help='最大处理职位数量')
    run_parser.add_argument('--force-reprocess', '-f', action='store_true', help='强制重新处理所有职位')
    run_parser.add_argument('--no-save', action='store_true', help='不保存处理结果')
    run_parser.add_argument('--show-progress', '-p', action='store_true', help='显示处理进度')
    
    # 状态查询命令
    status_parser = subparsers.add_parser('status', help='查询系统状态')
    status_parser.add_argument('--estimate-time', '-e', action='store_true', help='估算处理时间')
    status_parser.add_argument('--batch-size', '-b', type=int, default=50, help='用于时间估算的批处理大小')
    
    # 恢复流水线命令
    resume_parser = subparsers.add_parser('resume', help='恢复中断的流水线')
    resume_parser.add_argument('--batch-size', '-b', type=int, default=50, help='批处理大小')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level)
    
    # 确保logs目录存在
    Path('./logs').mkdir(exist_ok=True)
    
    # 执行命令
    if args.command == 'run':
        success = asyncio.run(run_pipeline_command(args))
    elif args.command == 'status':
        success = asyncio.run(status_command(args))
    elif args.command == 'resume':
        # 恢复命令使用run命令的逻辑，但不强制重处理
        args.force_reprocess = False
        args.show_progress = True
        success = asyncio.run(run_pipeline_command(args))
    else:
        parser.print_help()
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()