#!/usr/bin/env python3
"""
测试删除操作
"""

import sqlite3
import os

def test_delete_operation():
    """测试删除 processed = 0 的记录"""
    db_path = "./data/jobs.db"
    
    if not os.path.exists(db_path):
        print(f"数据库文件 {db_path} 不存在")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 查看删除前的记录数量
        cursor.execute("SELECT COUNT(*) FROM resume_matches WHERE processed = 0")
        before_count = cursor.fetchone()[0]
        print(f"删除前 processed = 0 的记录数量: {before_count}")
        
        cursor.execute("SELECT COUNT(*) FROM resume_matches")
        total_before = cursor.fetchone()[0]
        print(f"删除前总记录数量: {total_before}")
        
        # 2. 执行删除操作
        print("\n执行删除操作...")
        cursor.execute("DELETE FROM resume_matches WHERE processed = 0")
        deleted_count = cursor.rowcount
        print(f"成功删除 {deleted_count} 条记录")
        
        # 3. 查看删除后的记录数量
        cursor.execute("SELECT COUNT(*) FROM resume_matches WHERE processed = 0")
        after_count = cursor.fetchone()[0]
        print(f"删除后 processed = 0 的记录数量: {after_count}")
        
        cursor.execute("SELECT COUNT(*) FROM resume_matches")
        total_after = cursor.fetchone()[0]
        print(f"删除后总记录数量: {total_after}")
        
        # 4. 提交更改
        conn.commit()
        print("\n删除操作成功完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    test_delete_operation()