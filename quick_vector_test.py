"""
快速向量数据库测试脚本

简单快速地检查向量数据库的基本状态和内容
"""

import yaml
from src.rag.vector_manager import ChromaDBManager


def quick_test():
    """快速测试向量数据库"""
    print("🔍 快速向量数据库测试")
    print("="*40)
    
    try:
        # 加载配置
        with open('config/test_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 初始化向量管理器
        vector_config = config.get('vector_store', {})
        vector_manager = ChromaDBManager(vector_config)
        
        # 1. 检查统计信息
        print("\n📊 数据库统计:")
        stats = vector_manager.get_collection_stats()
        print(f"   文档数量: {stats.get('document_count', 0)}")
        print(f"   集合名称: {stats.get('collection_name', 'unknown')}")
        print(f"   存储路径: {stats.get('persist_directory', 'unknown')}")
        
        # 2. 检查文档样本
        print("\n📄 文档样本:")
        collection = vector_manager.vectorstore._collection
        sample_data = collection.get(limit=3)
        
        if sample_data['ids']:
            for i, doc_id in enumerate(sample_data['ids']):
                content = sample_data['documents'][i]
                metadata = sample_data['metadatas'][i] if sample_data['metadatas'] else {}
                
                print(f"   文档 {i+1}:")
                print(f"     ID: {doc_id}")
                print(f"     长度: {len(content)} 字符")
                print(f"     预览: {content[:100]}...")
                print(f"     职位ID: {metadata.get('job_id', '未知')}")
                print(f"     类型: {metadata.get('document_type', '未知')}")
                print()
        else:
            print("   ⚠️ 数据库为空")
        
        # 3. 测试搜索功能
        print("🔍 搜索测试:")
        test_queries = ["Python", "开发工程师", "前端"]
        
        for query in test_queries:
            results = vector_manager.search_similar_jobs(query, k=2)
            scored_results = vector_manager.similarity_search_with_score(query, k=2)
            
            print(f"   查询 '{query}': {len(results)} 个结果")
            if scored_results:
                top_score = scored_results[0][1]
                print(f"     最高相似度: {top_score:.3f}")
        
        # 4. 检查元数据字段
        print("\n🏷️ 元数据字段:")
        if sample_data['metadatas']:
            all_fields = set()
            for metadata in sample_data['metadatas']:
                if metadata:
                    all_fields.update(metadata.keys())
            print(f"   字段: {list(all_fields)}")
        else:
            print("   ⚠️ 没有元数据")
        
        # 关闭连接
        vector_manager.close()
        
        print("\n✅ 快速测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    quick_test()