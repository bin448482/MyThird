#!/usr/bin/env python3
"""
RAG系统统一CLI接口

提供完整的RAG系统命令行接口，包括数据处理、简历优化、职位匹配等功能
"""

import sys
import asyncio
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from src.rag.rag_system_coordinator import RAGSystemCoordinator
from src.rag.data_pipeline import RAGDataPipeline, create_progress_callback
from src.rag.resume_optimizer import ResumeOptimizer

def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """设置日志配置"""
    handlers = [logging.StreamHandler()]
    
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def load_config(config_file: str = None) -> dict:
    """加载配置文件"""
    if config_file and Path(config_file).exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            if config_file.endswith('.json'):
                return json.load(f)
            else:
                import yaml
                return yaml.safe_load(f)
    
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
                'max_tokens': 2000
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

def load_resume(resume_file: str) -> dict:
    """加载简历文件"""
    if not Path(resume_file).exists():
        raise FileNotFoundError(f"简历文件不存在: {resume_file}")
    
    with open(resume_file, 'r', encoding='utf-8') as f:
        if resume_file.endswith('.json'):
            return json.load(f)
        else:
            import yaml
            return yaml.safe_load(f)

async def pipeline_command(args):
    """数据流水线命令"""
    print("🚀 RAG数据流水线")
    print("=" * 40)
    
    try:
        config = load_config(args.config)
        
        # 覆盖命令行参数
        if args.batch_size:
            config['rag_system']['processing']['batch_size'] = args.batch_size
        if args.force_reprocess:
            config['rag_system']['processing']['force_reprocess'] = True
        
        # 创建进度回调
        progress_callback = create_progress_callback() if args.show_progress else None
        
        # 运行流水线
        pipeline = RAGDataPipeline(config, progress_callback)
        result = await pipeline.run_full_pipeline(
            batch_size=args.batch_size or 50,
            max_jobs=args.max_jobs,
            force_reprocess=args.force_reprocess,
            save_progress=not args.no_save
        )
        
        # 显示结果摘要
        print("\n📊 执行结果摘要:")
        exec_summary = result.get('execution_summary', {})
        proc_stats = result.get('processing_statistics', {})
        
        print(f"   状态: {exec_summary.get('status', 'unknown')}")
        print(f"   执行时间: {exec_summary.get('execution_time', 0):.1f} 秒")
        print(f"   处理职位: {proc_stats.get('processed_jobs', 0)}")
        print(f"   成功率: {proc_stats.get('success_rate', 0):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ 流水线执行失败: {e}")
        return False

async def status_command(args):
    """系统状态命令"""
    print("📊 RAG系统状态")
    print("=" * 30)
    
    try:
        config = load_config(args.config)
        coordinator = RAGSystemCoordinator(config)
        
        if not coordinator.initialize_system():
            print("❌ 系统初始化失败")
            return False
        
        # 获取系统状态
        system_status = coordinator.get_system_status()
        progress = coordinator.get_processing_progress()
        
        # 显示组件状态
        print("组件状态:")
        components = system_status.get('components', {})
        for comp_name, comp_status in components.items():
            status_icon = "✅" if comp_status else "❌"
            print(f"  {comp_name}: {status_icon}")
        
        # 显示数据统计
        db_stats = progress.get('database_stats', {})
        print(f"\n数据库统计:")
        print(f"  总职位数: {db_stats.get('total', 0)}")
        print(f"  已处理: {db_stats.get('processed', 0)}")
        print(f"  未处理: {db_stats.get('unprocessed', 0)}")
        print(f"  处理率: {db_stats.get('processing_rate', 0):.1f}%")
        
        vector_stats = progress.get('vector_stats', {})
        print(f"\n向量数据库:")
        print(f"  文档数量: {vector_stats.get('document_count', 0)}")
        print(f"  集合名称: {vector_stats.get('collection_name', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 状态查询失败: {e}")
        return False

async def optimize_command(args):
    """简历优化命令"""
    print("📝 简历优化")
    print("=" * 20)
    
    try:
        # 加载配置和简历
        config = load_config(args.config)
        resume = load_resume(args.resume)
        
        # 初始化系统
        coordinator = RAGSystemCoordinator(config)
        if not coordinator.initialize_system():
            print("❌ 系统初始化失败")
            return False
        
        optimizer = ResumeOptimizer(coordinator, config['rag_system']['llm'])
        
        # 根据子命令执行不同操作
        if args.action == 'analyze':
            # 简历差距分析
            target_jobs = args.target_jobs.split(',') if args.target_jobs else []
            if not target_jobs:
                # 自动查找相关职位
                all_jobs = coordinator.db_reader.get_jobs_for_rag_processing(limit=5)
                target_jobs = [job['job_id'] for job in all_jobs[:3]]
            
            print(f"分析目标职位: {len(target_jobs)} 个")
            
            if not args.dry_run:
                result = await optimizer.analyze_resume_gaps(resume, target_jobs)
                
                if 'error' in result:
                    print(f"❌ 分析失败: {result['error']}")
                    return False
                
                # 显示分析结果
                summary = result.get('summary', {})
                print(f"\n📊 分析结果:")
                print(f"   平均匹配度: {summary.get('average_match_score', 0)}")
                print(f"   分析职位数: {summary.get('total_jobs_analyzed', 0)}")
                
                # 保存结果
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                    print(f"   结果已保存到: {args.output}")
            else:
                print("🔍 干运行模式 - 跳过实际分析")
        
        elif args.action == 'optimize':
            # 简历内容优化
            target_job_id = args.target_job or coordinator.db_reader.get_jobs_for_rag_processing(limit=1)[0]['job_id']
            
            print(f"优化目标职位: {target_job_id}")
            
            if not args.dry_run:
                result = await optimizer.optimize_resume_content(
                    resume, 
                    target_job_id, 
                    args.focus_areas.split(',') if args.focus_areas else None
                )
                
                if 'error' in result:
                    print(f"❌ 优化失败: {result['error']}")
                    return False
                
                print("✅ 简历优化完成")
                
                # 保存结果
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                    print(f"   结果已保存到: {args.output}")
            else:
                print("🔍 干运行模式 - 跳过实际优化")
        
        elif args.action == 'cover-letter':
            # 生成求职信
            target_job_id = args.target_job or coordinator.db_reader.get_jobs_for_rag_processing(limit=1)[0]['job_id']
            
            print(f"生成求职信，目标职位: {target_job_id}")
            
            if not args.dry_run:
                cover_letter = await optimizer.generate_cover_letter(resume, target_job_id)
                
                print("✅ 求职信生成完成")
                print(f"   长度: {len(cover_letter)} 字符")
                
                # 保存求职信
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(cover_letter)
                    print(f"   求职信已保存到: {args.output}")
                else:
                    print("\n" + "="*50)
                    print(cover_letter)
                    print("="*50)
            else:
                print("🔍 干运行模式 - 跳过实际生成")
        
        return True
        
    except Exception as e:
        print(f"❌ 简历优化失败: {e}")
        return False

async def search_command(args):
    """职位搜索命令"""
    print("🔍 职位搜索")
    print("=" * 20)
    
    try:
        config = load_config(args.config)
        coordinator = RAGSystemCoordinator(config)
        
        if not coordinator.initialize_system():
            print("❌ 系统初始化失败")
            return False
        
        # 执行搜索
        query = args.query
        k = args.limit or 10
        
        print(f"搜索查询: {query}")
        print(f"返回数量: {k}")
        
        # 使用向量搜索
        similar_docs = coordinator.vector_manager.search_similar_jobs(query, k=k)
        
        if not similar_docs:
            print("❌ 没有找到相关职位")
            return False
        
        print(f"\n📋 搜索结果 ({len(similar_docs)} 个):")
        
        for i, doc in enumerate(similar_docs, 1):
            metadata = doc.metadata
            print(f"\n{i}. {metadata.get('job_title', '未知职位')}")
            print(f"   公司: {metadata.get('company', '未知公司')}")
            print(f"   地点: {metadata.get('location', '未知地点')}")
            print(f"   类型: {metadata.get('type', '未知类型')}")
            print(f"   内容: {doc.page_content[:100]}...")
        
        # 保存搜索结果
        if args.output:
            results = []
            for doc in similar_docs:
                results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata
                })
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n💾 搜索结果已保存到: {args.output}")
        
        return True
        
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='RAG智能简历投递系统CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 运行数据流水线
  python rag_cli.py pipeline run --batch-size 20 --show-progress
  
  # 查看系统状态
  python rag_cli.py status
  
  # 分析简历差距
  python rag_cli.py optimize analyze --resume resume.json --output analysis.json
  
  # 优化简历内容
  python rag_cli.py optimize optimize --resume resume.json --target-job job123
  
  # 生成求职信
  python rag_cli.py optimize cover-letter --resume resume.json --target-job job123
  
  # 搜索相关职位
  python rag_cli.py search "Python开发工程师" --limit 5
        """
    )
    
    # 全局参数
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       help='日志级别')
    parser.add_argument('--log-file', help='日志文件路径')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 流水线命令
    pipeline_parser = subparsers.add_parser('pipeline', help='数据流水线管理')
    pipeline_parser.add_argument('action', choices=['run', 'resume'], help='流水线操作')
    pipeline_parser.add_argument('--batch-size', '-b', type=int, help='批处理大小')
    pipeline_parser.add_argument('--max-jobs', '-m', type=int, help='最大处理职位数量')
    pipeline_parser.add_argument('--force-reprocess', '-f', action='store_true', help='强制重新处理')
    pipeline_parser.add_argument('--no-save', action='store_true', help='不保存处理结果')
    pipeline_parser.add_argument('--show-progress', '-p', action='store_true', help='显示处理进度')
    
    # 状态命令
    status_parser = subparsers.add_parser('status', help='查询系统状态')
    
    # 简历优化命令
    optimize_parser = subparsers.add_parser('optimize', help='简历优化')
    optimize_parser.add_argument('action', choices=['analyze', 'optimize', 'cover-letter'], help='优化操作')
    optimize_parser.add_argument('--resume', '-r', required=True, help='简历文件路径')
    optimize_parser.add_argument('--target-jobs', help='目标职位ID列表（逗号分隔）')
    optimize_parser.add_argument('--target-job', help='单个目标职位ID')
    optimize_parser.add_argument('--focus-areas', help='优化重点领域（逗号分隔）')
    optimize_parser.add_argument('--output', '-o', help='输出文件路径')
    optimize_parser.add_argument('--dry-run', action='store_true', help='干运行模式（不调用LLM）')
    
    # 搜索命令
    search_parser = subparsers.add_parser('search', help='职位搜索')
    search_parser.add_argument('query', help='搜索查询')
    search_parser.add_argument('--limit', '-l', type=int, default=10, help='返回结果数量')
    search_parser.add_argument('--output', '-o', help='输出文件路径')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level, args.log_file)
    
    # 确保必要目录存在
    Path('./logs').mkdir(exist_ok=True)
    Path('./pipeline_results').mkdir(exist_ok=True)
    
    # 执行命令
    success = False
    
    try:
        if args.command == 'pipeline':
            success = asyncio.run(pipeline_command(args))
        elif args.command == 'status':
            success = asyncio.run(status_command(args))
        elif args.command == 'optimize':
            success = asyncio.run(optimize_command(args))
        elif args.command == 'search':
            success = asyncio.run(search_command(args))
        else:
            parser.print_help()
            success = False
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        success = False
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()