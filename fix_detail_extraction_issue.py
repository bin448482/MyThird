#!/usr/bin/env python3
"""
修复 detail_extraction 关键词污染问题
"""

import sqlite3
import sys
from pathlib import Path

def fix_database_keywords():
    """修复数据库中的关键词问题"""
    db_path = Path('./data/jobs.db')
    
    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print('=== 检查当前关键词分布 ===')
        cursor.execute('''
            SELECT keyword, COUNT(*) as count 
            FROM job_details 
            WHERE keyword IS NOT NULL AND keyword != "" 
            GROUP BY keyword 
            ORDER BY count DESC
        ''')
        results = cursor.fetchall()
        
        print('关键词分布:')
        for row in results:
            print(f'  {row["keyword"]}: {row["count"]}次')
        
        # 检查是否所有记录都是 detail_extraction
        detail_extraction_count = 0
        total_count = 0
        for row in results:
            total_count += row["count"]
            if row["keyword"] == "detail_extraction":
                detail_extraction_count = row["count"]
        
        print(f'\n总记录数: {total_count}')
        print(f'detail_extraction 记录数: {detail_extraction_count}')
        
        if detail_extraction_count == total_count and total_count > 0:
            print('\n⚠️ 发现问题：所有记录的关键词都是 detail_extraction')
            
            # 提供修复选项
            print('\n修复选项:')
            print('1. 将所有 detail_extraction 改为 unknown')
            print('2. 根据职位标题推断关键词')
            print('3. 清空所有关键词字段')
            print('4. 不修复，仅查看')
            
            choice = input('\n请选择修复方式 (1-4): ').strip()
            
            if choice == '1':
                # 将所有 detail_extraction 改为 unknown
                cursor.execute('''
                    UPDATE job_details 
                    SET keyword = 'unknown' 
                    WHERE keyword = 'detail_extraction'
                ''')
                updated_count = cursor.rowcount
                conn.commit()
                print(f'✅ 已将 {updated_count} 条记录的关键词从 detail_extraction 改为 unknown')
                
            elif choice == '2':
                # 根据职位标题推断关键词
                print('🔄 开始根据职位标题推断关键词...')
                
                # 获取所有需要更新的记录
                cursor.execute('''
                    SELECT jd.id, jd.job_id, j.title 
                    FROM job_details jd
                    JOIN jobs j ON jd.job_id = j.job_id
                    WHERE jd.keyword = 'detail_extraction'
                ''')
                records = cursor.fetchall()
                
                updated_count = 0
                keyword_mapping = {}
                
                for record in records:
                    title = record["title"].lower()
                    inferred_keyword = infer_keyword_from_title(title)
                    
                    cursor.execute('''
                        UPDATE job_details 
                        SET keyword = ? 
                        WHERE id = ?
                    ''', (inferred_keyword, record["id"]))
                    
                    updated_count += 1
                    keyword_mapping[inferred_keyword] = keyword_mapping.get(inferred_keyword, 0) + 1
                
                conn.commit()
                print(f'✅ 已更新 {updated_count} 条记录的关键词')
                print('新的关键词分布:')
                for keyword, count in sorted(keyword_mapping.items(), key=lambda x: x[1], reverse=True):
                    print(f'  {keyword}: {count}次')
                
            elif choice == '3':
                # 清空所有关键词字段
                cursor.execute('''
                    UPDATE job_details 
                    SET keyword = '' 
                    WHERE keyword = 'detail_extraction'
                ''')
                updated_count = cursor.rowcount
                conn.commit()
                print(f'✅ 已清空 {updated_count} 条记录的关键词字段')
                
            elif choice == '4':
                print('🔍 仅查看模式，未进行任何修改')
            else:
                print('❌ 无效选择，未进行任何修改')
        else:
            print('✅ 关键词分布正常，无需修复')
        
        conn.close()
        
    except Exception as e:
        print(f"处理数据库时出错: {e}")

def infer_keyword_from_title(title: str) -> str:
    """根据职位标题推断关键词"""
    title = title.lower()
    
    # 定义关键词映射规则
    keyword_rules = [
        (['python', 'django', 'flask'], 'python'),
        (['java', 'spring', 'springboot'], 'java'),
        (['javascript', 'js', 'react', 'vue', 'angular', 'node'], 'javascript'),
        (['前端', 'frontend', 'web前端'], 'frontend'),
        (['后端', 'backend', 'server'], 'backend'),
        (['全栈', 'fullstack'], 'fullstack'),
        (['数据', 'data', '数据分析', '数据科学'], 'data'),
        (['算法', 'algorithm', 'ai', '人工智能', '机器学习'], 'ai'),
        (['测试', 'test', 'qa'], 'testing'),
        (['运维', 'devops', 'ops'], 'devops'),
        (['产品', 'product'], 'product'),
        (['设计', 'design', 'ui', 'ux'], 'design'),
        (['移动', 'mobile', 'android', 'ios'], 'mobile'),
        (['c++', 'cpp'], 'cpp'),
        (['go', 'golang'], 'go'),
        (['php'], 'php'),
        (['.net', 'c#'], 'dotnet'),
    ]
    
    # 按优先级匹配
    for keywords, category in keyword_rules:
        if any(keyword in title for keyword in keywords):
            return category
    
    # 如果没有匹配到，返回通用关键词
    if '工程师' in title or 'engineer' in title:
        return 'engineer'
    elif '开发' in title or 'developer' in title:
        return 'developer'
    else:
        return 'unknown'

def check_vector_database():
    """检查向量数据库"""
    try:
        sys.path.append('.')
        from src.rag.vector_manager import ChromaDBManager
        
        config = {
            'persist_directory': './data/test_chroma_db',
            'collection_name': 'job_positions',
            'embeddings': {
                'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'device': 'cpu',
                'normalize_embeddings': True
            }
        }
        
        print('\n=== 检查向量数据库 ===')
        vector_manager = ChromaDBManager(config)
        stats = vector_manager.get_collection_stats()
        print(f'向量数据库统计:')
        print(f'  文档数量: {stats.get("document_count", 0)}')
        print(f'  集合名称: {stats.get("collection_name", "unknown")}')
        
        if stats.get('document_count', 0) > 0:
            # 获取样本文档
            collection = vector_manager.vectorstore._collection
            sample_data = collection.get(limit=3)
            
            if sample_data['metadatas']:
                print(f'\n样本文档的metadata:')
                for i, metadata in enumerate(sample_data['metadatas']):
                    if metadata:
                        print(f'  文档 {i+1}: job_id={metadata.get("job_id", "unknown")}, type={metadata.get("document_type", "unknown")}')
        
        vector_manager.close()
        
    except Exception as e:
        print(f'检查向量数据库时出错: {e}')

def clear_vector_database():
    """清理向量数据库"""
    try:
        sys.path.append('.')
        from src.rag.vector_manager import ChromaDBManager
        
        config = {
            'persist_directory': './data/test_chroma_db',
            'collection_name': 'job_positions',
            'embeddings': {
                'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'device': 'cpu',
                'normalize_embeddings': True
            }
        }
        
        print('\n=== 清理向量数据库 ===')
        vector_manager = ChromaDBManager(config)
        stats = vector_manager.get_collection_stats()
        doc_count = stats.get('document_count', 0)
        
        if doc_count > 0:
            confirm = input(f'确定要清空向量数据库中的 {doc_count} 个文档吗？(y/N): ')
            if confirm.lower() == 'y':
                # 清空集合
                collection = vector_manager.vectorstore._collection
                all_data = collection.get()
                
                if all_data['ids']:
                    collection.delete(ids=all_data['ids'])
                    print(f'✅ 已清空向量数据库中的 {len(all_data["ids"])} 个文档')
                else:
                    print('向量数据库已经是空的')
            else:
                print('取消清理操作')
        else:
            print('向量数据库已经是空的')
        
        vector_manager.close()
        
    except Exception as e:
        print(f'清理向量数据库时出错: {e}')

if __name__ == "__main__":
    print("🔧 修复 detail_extraction 关键词污染问题")
    print("=" * 50)
    
    # 1. 修复数据库关键词
    fix_database_keywords()
    
    # 2. 检查向量数据库
    check_vector_database()
    
    # 3. 询问是否清理向量数据库
    print("\n" + "=" * 50)
    clear_vector = input("是否需要清理向量数据库？(y/N): ")
    if clear_vector.lower() == 'y':
        clear_vector_database()
    
    print("\n✅ 修复完成！")