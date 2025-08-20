#!/usr/bin/env python3
"""
检查数据库结构和数据内容
"""

import sqlite3
from pathlib import Path

def check_database_structure():
    """检查数据库结构和数据内容"""
    db_path = './data/jobs.db'
    
    if not Path(db_path).exists():
        print('数据库文件不存在')
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print('=== 数据库结构分析 ===')
    
    # 检查所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'数据库中的表: {[table[0] for table in tables]}')
    
    # 检查jobs表结构
    print('\n=== jobs表结构 ===')
    cursor.execute("PRAGMA table_info(jobs)")
    jobs_columns = cursor.fetchall()
    for col in jobs_columns:
        print(f'{col["name"]}: {col["type"]} (nullable: {not col["notnull"]}, default: {col["dflt_value"]})')
    
    # 检查job_details表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_details'")
    job_details_exists = cursor.fetchone()
    
    if job_details_exists:
        print('\n=== job_details表结构 ===')
        cursor.execute("PRAGMA table_info(job_details)")
        details_columns = cursor.fetchall()
        for col in details_columns:
            print(f'{col["name"]}: {col["type"]} (nullable: {not col["notnull"]}, default: {col["dflt_value"]})')
        
        # 检查job_details表数据
        cursor.execute('SELECT COUNT(*) as count FROM job_details')
        details_count = cursor.fetchone()['count']
        print(f'\njob_details表记录数: {details_count}')
        
        if details_count > 0:
            print('\n=== job_details表样本数据 ===')
            cursor.execute('''
                SELECT job_id, salary, location, experience, education, 
                       SUBSTR(description, 1, 100) as description_preview,
                       SUBSTR(requirements, 1, 100) as requirements_preview
                FROM job_details 
                LIMIT 3
            ''')
            details_samples = cursor.fetchall()
            for i, detail in enumerate(details_samples, 1):
                print(f'\n样本 {i}:')
                print(f'  job_id: {detail["job_id"]}')
                print(f'  salary: {detail["salary"]}')
                print(f'  location: {detail["location"]}')
                print(f'  experience: {detail["experience"]}')
                print(f'  education: {detail["education"]}')
                print(f'  description: {detail["description_preview"]}...')
                print(f'  requirements: {detail["requirements_preview"]}...')
    else:
        print('\n❌ job_details表不存在')
    
    # 检查数据完整性
    print('\n=== 数据完整性检查 ===')
    cursor.execute('SELECT COUNT(*) as jobs_count FROM jobs')
    jobs_count = cursor.fetchone()['jobs_count']
    print(f'jobs表记录数: {jobs_count}')
    
    if job_details_exists:
        cursor.execute('SELECT COUNT(*) as details_count FROM job_details')
        details_count = cursor.fetchone()['details_count']
        print(f'job_details表记录数: {details_count}')
        
        # 检查关联数据
        cursor.execute('''
            SELECT COUNT(*) as linked_count 
            FROM jobs j 
            INNER JOIN job_details jd ON j.job_id = jd.job_id
        ''')
        linked_count = cursor.fetchone()['linked_count']
        print(f'有详细信息的职位数: {linked_count}')
        
        if jobs_count > 0:
            coverage = (linked_count / jobs_count) * 100
            print(f'详细信息覆盖率: {coverage:.1f}%')
    
    # 检查RAG相关字段
    print('\n=== RAG处理状态检查 ===')
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [col["name"] for col in cursor.fetchall()]
    
    rag_fields = ['rag_processed', 'rag_processed_at', 'vector_doc_count', 'semantic_score', 'vector_id', 'structured_data']
    missing_rag_fields = [field for field in rag_fields if field not in columns]
    existing_rag_fields = [field for field in rag_fields if field in columns]
    
    if existing_rag_fields:
        print(f'✅ 已存在的RAG字段: {existing_rag_fields}')
    if missing_rag_fields:
        print(f'❌ 缺失的RAG字段: {missing_rag_fields}')
    
    conn.close()

if __name__ == "__main__":
    check_database_structure()