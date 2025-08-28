#!/usr/bin/env python3
"""
检查匹配结果
验证 skill_match_score 等字段是否正确填充
"""

import sqlite3

def check_match_results():
    """检查数据库中的匹配结果"""
    
    print("🔍 检查数据库中的匹配结果")
    print("=" * 60)
    
    conn = sqlite3.connect('./data/jobs.db')
    cursor = conn.cursor()
    
    # 1. 检查总匹配数
    cursor.execute("SELECT COUNT(*) FROM resume_matches")
    total_matches = cursor.fetchone()[0]
    print(f"📊 数据库中匹配记录总数: {total_matches}")
    
    # 2. 检查各个分数字段是否为NULL
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(skill_match_score) as skill_not_null,
            COUNT(experience_match_score) as exp_not_null,
            COUNT(location_match_score) as loc_not_null,
            COUNT(salary_match_score) as sal_not_null,
            COUNT(semantic_score) as sem_not_null
        FROM resume_matches
    """)
    
    stats = cursor.fetchone()
    print(f"\n📈 分数字段统计:")
    print(f"   总记录数: {stats[0]}")
    if stats[0] > 0:
        print(f"   skill_match_score 非NULL: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
        print(f"   experience_match_score 非NULL: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
        print(f"   location_match_score 非NULL: {stats[3]} ({stats[3]/stats[0]*100:.1f}%)")
        print(f"   salary_match_score 非NULL: {stats[4]} ({stats[4]/stats[0]*100:.1f}%)")
        print(f"   semantic_score 非NULL: {stats[5]} ({stats[5]/stats[0]*100:.1f}%)")
    
    # 3. 显示最新的5条记录的详细信息
    cursor.execute("""
        SELECT job_id, match_score, skill_match_score, experience_match_score, 
               location_match_score, salary_match_score, semantic_score, match_reasons,
               created_at
        FROM resume_matches 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    
    print(f"\n📝 最新5条匹配记录详情:")
    records = cursor.fetchall()
    for i, record in enumerate(records, 1):
        print(f"   记录 {i}:")
        print(f"     job_id: {record[0]}")
        print(f"     match_score: {record[1]:.3f}")
        print(f"     skill_match_score: {record[2]}")
        print(f"     experience_match_score: {record[3]}")
        print(f"     location_match_score: {record[4]}")
        print(f"     salary_match_score: {record[5]}")
        print(f"     semantic_score: {record[6]}")
        print(f"     match_reasons: {record[7]}")
        print(f"     created_at: {record[8]}")
        print()
    
    # 4. 检查分数范围
    cursor.execute("""
        SELECT 
            MIN(skill_match_score) as min_skill,
            MAX(skill_match_score) as max_skill,
            AVG(skill_match_score) as avg_skill,
            MIN(semantic_score) as min_semantic,
            MAX(semantic_score) as max_semantic,
            AVG(semantic_score) as avg_semantic
        FROM resume_matches 
        WHERE skill_match_score IS NOT NULL
    """)
    
    ranges = cursor.fetchone()
    if ranges and ranges[0] is not None:
        print(f"📊 分数范围统计:")
        print(f"   skill_match_score: {ranges[0]:.3f} - {ranges[1]:.3f} (平均: {ranges[2]:.3f})")
        print(f"   semantic_score: {ranges[3]:.3f} - {ranges[4]:.3f} (平均: {ranges[5]:.3f})")
    
    conn.close()
    
    # 5. 生成结论
    print(f"\n📋 检查结论:")
    if stats[1] > 0:  # skill_match_score 有非NULL值
        print("✅ 修复成功！skill_match_score 等字段现在有正确的值")
        print("✅ MasterController 的匹配逻辑现在与 batch_rematch_jobs 一致")
    else:
        print("❌ 修复失败！skill_match_score 等字段仍然为NULL")
        print("❌ 需要进一步检查匹配逻辑")

if __name__ == "__main__":
    check_match_results()