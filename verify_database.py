#!/usr/bin/env python3
"""
验证数据库中的测试结果
"""

import sqlite3
from pathlib import Path

def verify_database():
    """验证数据库中的数据"""
    db_path = './data/jobs.db'
    
    if not Path(db_path).exists():
        print('数据库文件不存在')
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print('=== 数据库验证结果 ===')
    
    # 总数统计
    cursor.execute('SELECT COUNT(*) as total FROM jobs')
    total = cursor.fetchone()['total']
    print(f'总职位数: {total}')
    
    # 今日统计
    cursor.execute("SELECT COUNT(*) as today_count FROM jobs WHERE DATE(created_at) = DATE('now')")
    today_count = cursor.fetchone()['today_count']
    print(f'今日新增: {today_count}')
    
    # 最近的职位记录
    cursor.execute('''
        SELECT job_id, title, company, url, job_fingerprint, created_at 
        FROM jobs 
        ORDER BY created_at DESC 
        LIMIT 5
    ''')
    jobs = cursor.fetchall()
    
    print('\n最近的职位记录:')
    for i, job in enumerate(jobs, 1):
        title = job['title'] or '无标题'
        company = job['company'] or '无公司'
        job_id = job['job_id']
        url = job['url'][:80] + '...' if job['url'] and len(job['url']) > 80 else job['url'] or '无URL'
        fingerprint = job['job_fingerprint'][:20] + '...' if job['job_fingerprint'] else '无指纹'
        created_at = job['created_at']
        
        print(f'{i}. {title} - {company}')
        print(f'   ID: {job_id}')
        print(f'   URL: {url}')
        print(f'   指纹: {fingerprint}')
        print(f'   时间: {created_at}')
        print()
    
    # 指纹去重统计
    cursor.execute('''
        SELECT COUNT(*) as total, COUNT(DISTINCT job_fingerprint) as unique_fingerprints
        FROM jobs
        WHERE job_fingerprint IS NOT NULL
    ''')
    dedup_stats = cursor.fetchone()
    if dedup_stats:
        total_with_fp = dedup_stats['total']
        unique_fp = dedup_stats['unique_fingerprints']
        duplicate_rate = ((total_with_fp - unique_fp) / total_with_fp * 100) if total_with_fp > 0 else 0
        print(f'去重统计: 总数{total_with_fp}, 唯一{unique_fp}, 重复率{duplicate_rate:.1f}%')
    
    conn.close()

if __name__ == "__main__":
    verify_database()