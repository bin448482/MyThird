#!/usr/bin/env python3
"""
修复数据库重复记录脚本
"""

import sqlite3
import logging
from datetime import datetime

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def fix_job_details_duplicates(db_path: str):
    """修复job_details表的重复记录"""
    logger = setup_logging()
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 1. 统计重复情况
            cursor.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT job_id) as unique_jobs,
                       COUNT(*) - COUNT(DISTINCT job_id) as duplicates
                FROM job_details
            """)
            total, unique, duplicates = cursor.fetchone()
            
            logger.info(f"修复前统计:")
            logger.info(f"  总记录数: {total}")
            logger.info(f"  唯一职位数: {unique}")
            logger.info(f"  重复记录数: {duplicates}")
            
            if duplicates == 0:
                logger.info("没有发现重复记录，无需修复")
                return
            
            # 2. 显示重复记录详情
            cursor.execute("""
                SELECT job_id, COUNT(*) as count
                FROM job_details
                GROUP BY job_id
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """)
            duplicate_jobs = cursor.fetchall()
            
            logger.info(f"发现 {len(duplicate_jobs)} 个职位有重复记录:")
            for job_id, count in duplicate_jobs:
                logger.info(f"  {job_id}: {count} 条记录")
            
            # 3. 创建临时表保存去重后的数据
            logger.info("创建临时表...")
            cursor.execute("""
                CREATE TEMPORARY TABLE job_details_temp AS
                SELECT 
                    MIN(id) as id,
                    job_id,
                    salary,
                    location,
                    experience,
                    education,
                    description,
                    requirements,
                    benefits,
                    publish_time,
                    company_scale,
                    industry,
                    keyword,
                    MAX(extracted_at) as extracted_at  -- 保留最新的提取时间
                FROM job_details
                GROUP BY job_id
            """)
            
            # 4. 删除原表中的所有记录
            logger.info("清空原表...")
            cursor.execute("DELETE FROM job_details")
            
            # 5. 从临时表恢复去重后的数据
            logger.info("恢复去重后的数据...")
            cursor.execute("""
                INSERT INTO job_details (
                    job_id, salary, location, experience, education,
                    description, requirements, benefits, publish_time,
                    company_scale, industry, keyword, extracted_at
                )
                SELECT 
                    job_id, salary, location, experience, education,
                    description, requirements, benefits, publish_time,
                    company_scale, industry, keyword, extracted_at
                FROM job_details_temp
            """)
            
            # 6. 验证修复结果
            cursor.execute("SELECT COUNT(*) FROM job_details")
            final_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) - COUNT(DISTINCT job_id) as remaining_duplicates
                FROM job_details
            """)
            remaining_duplicates = cursor.fetchone()[0]
            
            conn.commit()
            
            logger.info(f"修复完成!")
            logger.info(f"  修复后记录数: {final_count}")
            logger.info(f"  剩余重复数: {remaining_duplicates}")
            logger.info(f"  删除重复记录: {duplicates}")
            
            return True
            
    except Exception as e:
        logger.error(f"修复失败: {e}")
        return False

def verify_data_consistency(db_path: str):
    """验证数据一致性"""
    logger = setup_logging()
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 统计jobs表
            cursor.execute("SELECT COUNT(*) FROM jobs")
            jobs_count = cursor.fetchone()[0]
            
            # 统计job_details表
            cursor.execute("SELECT COUNT(*) FROM job_details")
            details_count = cursor.fetchone()[0]
            
            # 统计匹配的记录
            cursor.execute("""
                SELECT COUNT(*) 
                FROM jobs j 
                INNER JOIN job_details jd ON j.job_id = jd.job_id
            """)
            matched_count = cursor.fetchone()[0]
            
            # 统计孤立记录
            cursor.execute("""
                SELECT COUNT(*) 
                FROM jobs j 
                LEFT JOIN job_details jd ON j.job_id = jd.job_id 
                WHERE jd.job_id IS NULL
            """)
            orphan_jobs = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM job_details jd 
                LEFT JOIN jobs j ON jd.job_id = j.job_id 
                WHERE j.job_id IS NULL
            """)
            orphan_details = cursor.fetchone()[0]
            
            logger.info("=== 数据一致性验证 ===")
            logger.info(f"Jobs表记录数: {jobs_count}")
            logger.info(f"Job_details表记录数: {details_count}")
            logger.info(f"匹配的记录数: {matched_count}")
            logger.info(f"Jobs表中孤立记录: {orphan_jobs}")
            logger.info(f"Job_details表中孤立记录: {orphan_details}")
            
            if jobs_count == details_count == matched_count and orphan_jobs == 0 and orphan_details == 0:
                logger.info("✅ 数据一致性检查通过！")
                return True
            else:
                logger.warning("⚠️ 数据一致性检查未通过")
                return False
                
    except Exception as e:
        logger.error(f"验证失败: {e}")
        return False

if __name__ == "__main__":
    db_path = "data/jobs.db"
    
    print("🔧 开始修复数据库重复记录...")
    
    # 修复重复记录
    if fix_job_details_duplicates(db_path):
        print("✅ 重复记录修复完成")
        
        # 验证数据一致性
        if verify_data_consistency(db_path):
            print("✅ 数据库修复成功，数据一致性良好")
        else:
            print("⚠️ 数据库修复完成，但仍存在一致性问题")
    else:
        print("❌ 数据库修复失败")