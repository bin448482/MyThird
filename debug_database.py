#!/usr/bin/env python3
"""
调试数据库中的技能数据
"""

import sqlite3
import sys
from pathlib import Path

def check_database():
    """检查数据库中的技能数据"""
    db_path = Path('./data/jobs.db')
    
    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print('=== 检查 job_details 表中的 keyword 字段 ===')
        cursor.execute('''
            SELECT keyword, COUNT(*) as count 
            FROM job_details 
            WHERE keyword IS NOT NULL AND keyword != "" 
            GROUP BY keyword 
            ORDER BY count DESC 
            LIMIT 20
        ''')
        results = cursor.fetchall()
        
        print('前20个最常见的关键词:')
        for row in results:
            print(f'  {row["keyword"]}: {row["count"]}次')
        
        print('\n=== 检查是否存在 Detail_Extraction ===')
        cursor.execute('''
            SELECT * FROM job_details 
            WHERE keyword LIKE "%Detail_Extraction%" OR keyword LIKE "%detail_extraction%" 
            LIMIT 5
        ''')
        detail_results = cursor.fetchall()
        
        if detail_results:
            print('找到包含 Detail_Extraction 的记录:')
            for row in detail_results:
                print(f'  job_id: {row["job_id"]}, keyword: {row["keyword"]}')
        else:
            print('未找到包含 Detail_Extraction 的记录')
        
        print('\n=== 检查包含 extraction 的关键词 ===')
        cursor.execute('''
            SELECT keyword, COUNT(*) as count 
            FROM job_details 
            WHERE keyword LIKE "%extraction%" 
            GROUP BY keyword 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        extraction_results = cursor.fetchall()
        
        if extraction_results:
            print('包含 extraction 的关键词:')
            for row in extraction_results:
                print(f'  {row["keyword"]}: {row["count"]}次')
        else:
            print('未找到包含 extraction 的关键词')
        
        print('\n=== 检查包含 detail 的关键词 ===')
        cursor.execute('''
            SELECT keyword, COUNT(*) as count 
            FROM job_details 
            WHERE keyword LIKE "%detail%" 
            GROUP BY keyword 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        detail_keywords = cursor.fetchall()
        
        if detail_keywords:
            print('包含 detail 的关键词:')
            for row in detail_keywords:
                print(f'  {row["keyword"]}: {row["count"]}次')
        else:
            print('未找到包含 detail 的关键词')
        
        print('\n=== 检查数据库总体统计 ===')
        cursor.execute('SELECT COUNT(*) as total_jobs FROM jobs')
        total_jobs = cursor.fetchone()['total_jobs']
        
        cursor.execute('SELECT COUNT(*) as total_details FROM job_details')
        total_details = cursor.fetchone()['total_details']
        
        cursor.execute('SELECT COUNT(*) as keyword_count FROM job_details WHERE keyword IS NOT NULL AND keyword != ""')
        keyword_count = cursor.fetchone()['keyword_count']
        
        print(f'总职位数: {total_jobs}')
        print(f'总详情记录数: {total_details}')
        print(f'有关键词的记录数: {keyword_count}')
        
        print('\n=== 检查可能的异常关键词 ===')
        cursor.execute('''
            SELECT keyword, COUNT(*) as count 
            FROM job_details 
            WHERE keyword IS NOT NULL AND keyword != "" 
            AND (keyword LIKE "%_%_%" OR keyword LIKE "%[%]%" OR LENGTH(keyword) > 50)
            GROUP BY keyword 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        unusual_keywords = cursor.fetchall()
        
        if unusual_keywords:
            print('可能异常的关键词:')
            for row in unusual_keywords:
                print(f'  {row["keyword"]}: {row["count"]}次')
        else:
            print('未找到异常关键词')
        
        conn.close()
        
    except Exception as e:
        print(f"检查数据库时出错: {e}")

if __name__ == "__main__":
    check_database()