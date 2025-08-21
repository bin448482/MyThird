"""
向量数据库内容测试脚本

用于验证向量数据库的内容是否达到预期，包括：
1. 数据库统计信息
2. 文档内容检查
3. 搜索功能测试
4. 元数据验证
5. 相似度测试
"""

import yaml
import json
from datetime import datetime
from typing import List, Dict, Any
from src.rag.vector_manager import ChromaDBManager
from src.rag.rag_system_coordinator import RAGSystemCoordinator


class VectorDatabaseTester:
    """向量数据库测试器"""
    
    def __init__(self, config_path: str = 'config/test_config.yaml'):
        """
        初始化测试器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.load_config()
        self.init_vector_manager()
        
    def load_config(self):
        """加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            print(f"✅ 配置加载成功: {self.config_path}")
        except Exception as e:
            print(f"❌ 配置加载失败: {e}")
            raise
    
    def init_vector_manager(self):
        """初始化向量管理器"""
        try:
            vector_config = self.config.get('vector_store', {})
            self.vector_manager = ChromaDBManager(vector_config)
            print(f"✅ 向量管理器初始化成功")
        except Exception as e:
            print(f"❌ 向量管理器初始化失败: {e}")
            raise
    
    def test_database_stats(self) -> Dict[str, Any]:
        """测试数据库统计信息"""
        print("\n" + "="*50)
        print("📊 数据库统计信息测试")
        print("="*50)
        
        try:
            stats = self.vector_manager.get_collection_stats()
            
            print(f"📋 集合名称: {stats.get('collection_name', 'unknown')}")
            print(f"📁 存储路径: {stats.get('persist_directory', 'unknown')}")
            print(f"📄 文档数量: {stats.get('document_count', 0)}")
            
            # 检查是否有文档
            if stats.get('document_count', 0) > 0:
                print("✅ 数据库包含文档")
                return {"status": "success", "stats": stats}
            else:
                print("⚠️ 数据库为空")
                return {"status": "empty", "stats": stats}
                
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def test_document_content(self, sample_size: int = 5) -> Dict[str, Any]:
        """测试文档内容"""
        print("\n" + "="*50)
        print("📝 文档内容测试")
        print("="*50)
        
        try:
            # 获取样本文档
            collection = self.vector_manager.vectorstore._collection
            all_data = collection.get(limit=sample_size)
            
            if not all_data['ids']:
                print("⚠️ 没有找到任何文档")
                return {"status": "empty", "documents": []}
            
            documents = []
            for i, doc_id in enumerate(all_data['ids']):
                doc_info = {
                    "id": doc_id,
                    "content": all_data['documents'][i][:200] + "..." if len(all_data['documents'][i]) > 200 else all_data['documents'][i],
                    "metadata": all_data['metadatas'][i] if all_data['metadatas'] else {},
                    "content_length": len(all_data['documents'][i])
                }
                documents.append(doc_info)
                
                print(f"\n📄 文档 {i+1}:")
                print(f"   ID: {doc_id}")
                print(f"   内容长度: {doc_info['content_length']} 字符")
                print(f"   内容预览: {doc_info['content']}")
                print(f"   元数据: {doc_info['metadata']}")
            
            print(f"\n✅ 成功检查 {len(documents)} 个文档")
            return {"status": "success", "documents": documents}
            
        except Exception as e:
            print(f"❌ 文档内容检查失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def test_search_functionality(self, test_queries: List[str] = None) -> Dict[str, Any]:
        """测试搜索功能"""
        print("\n" + "="*50)
        print("🔍 搜索功能测试")
        print("="*50)
        
        if test_queries is None:
            test_queries = [
                "Python开发工程师",
                "前端开发",
                "数据分析师",
                "机器学习",
                "软件工程师"
            ]
        
        search_results = {}
        
        for query in test_queries:
            try:
                print(f"\n🔎 测试查询: '{query}'")
                
                # 基础搜索
                results = self.vector_manager.search_similar_jobs(query, k=3)
                print(f"   基础搜索结果: {len(results)} 个文档")
                
                # 带分数搜索
                scored_results = self.vector_manager.similarity_search_with_score(query, k=3)
                print(f"   带分数搜索结果: {len(scored_results)} 个文档")
                
                # 显示前3个结果
                for i, (doc, score) in enumerate(scored_results[:3], 1):
                    print(f"   结果 {i}: 相似度={score:.3f}, 类型={doc.metadata.get('document_type', '未知')}")
                    print(f"           内容预览: {doc.page_content[:100]}...")
                
                search_results[query] = {
                    "basic_count": len(results),
                    "scored_count": len(scored_results),
                    "top_scores": [score for _, score in scored_results[:3]]
                }
                
            except Exception as e:
                print(f"   ❌ 查询失败: {e}")
                search_results[query] = {"error": str(e)}
        
        print(f"\n✅ 搜索功能测试完成")
        return {"status": "success", "results": search_results}
    
    def test_metadata_validation(self) -> Dict[str, Any]:
        """测试元数据验证"""
        print("\n" + "="*50)
        print("🏷️ 元数据验证测试")
        print("="*50)
        
        try:
            collection = self.vector_manager.vectorstore._collection
            all_data = collection.get()
            
            if not all_data['metadatas']:
                print("⚠️ 没有找到元数据")
                return {"status": "no_metadata"}
            
            # 统计元数据字段
            field_stats = {}
            job_ids = set()
            document_types = set()
            
            for metadata in all_data['metadatas']:
                if metadata:
                    for key, value in metadata.items():
                        if key not in field_stats:
                            field_stats[key] = {"count": 0, "sample_values": set()}
                        field_stats[key]["count"] += 1
                        if len(field_stats[key]["sample_values"]) < 5:
                            field_stats[key]["sample_values"].add(str(value)[:50])
                    
                    # 收集特定字段
                    if 'job_id' in metadata:
                        job_ids.add(metadata['job_id'])
                    if 'document_type' in metadata:
                        document_types.add(metadata['document_type'])
            
            print(f"📊 元数据字段统计:")
            for field, stats in field_stats.items():
                sample_values = list(stats["sample_values"])[:3]
                print(f"   {field}: {stats['count']} 个文档, 样本值: {sample_values}")
            
            print(f"\n📋 职位ID数量: {len(job_ids)}")
            print(f"📋 文档类型: {list(document_types)}")
            
            validation_result = {
                "status": "success",
                "field_stats": {k: {"count": v["count"], "sample_values": list(v["sample_values"])} 
                               for k, v in field_stats.items()},
                "unique_job_ids": len(job_ids),
                "document_types": list(document_types)
            }
            
            print(f"✅ 元数据验证完成")
            return validation_result
            
        except Exception as e:
            print(f"❌ 元数据验证失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def test_similarity_quality(self) -> Dict[str, Any]:
        """测试相似度质量"""
        print("\n" + "="*50)
        print("🎯 相似度质量测试")
        print("="*50)
        
        try:
            # 测试用例：相关和不相关的查询
            test_cases = [
                {
                    "query": "Python开发工程师",
                    "expected_keywords": ["python", "开发", "工程师", "编程"],
                    "type": "relevant"
                },
                {
                    "query": "销售经理",
                    "expected_keywords": ["销售", "经理", "市场"],
                    "type": "relevant"
                },
                {
                    "query": "随机无关内容xyz123",
                    "expected_keywords": [],
                    "type": "irrelevant"
                }
            ]
            
            quality_results = {}
            
            for test_case in test_cases:
                query = test_case["query"]
                print(f"\n🧪 测试查询: '{query}' ({test_case['type']})")
                
                scored_results = self.vector_manager.similarity_search_with_score(query, k=5)
                
                if scored_results:
                    scores = [score for _, score in scored_results]
                    avg_score = sum(scores) / len(scores)
                    max_score = max(scores)
                    min_score = min(scores)
                    
                    print(f"   平均相似度: {avg_score:.3f}")
                    print(f"   最高相似度: {max_score:.3f}")
                    print(f"   最低相似度: {min_score:.3f}")
                    
                    # 检查关键词匹配
                    keyword_matches = 0
                    for doc, score in scored_results[:3]:
                        content_lower = doc.page_content.lower()
                        for keyword in test_case["expected_keywords"]:
                            if keyword.lower() in content_lower:
                                keyword_matches += 1
                                break
                    
                    keyword_match_rate = keyword_matches / min(3, len(scored_results)) if scored_results else 0
                    print(f"   关键词匹配率: {keyword_match_rate:.2%}")
                    
                    quality_results[query] = {
                        "avg_score": avg_score,
                        "max_score": max_score,
                        "min_score": min_score,
                        "keyword_match_rate": keyword_match_rate,
                        "result_count": len(scored_results)
                    }
                else:
                    print(f"   ⚠️ 没有找到结果")
                    quality_results[query] = {"result_count": 0}
            
            print(f"\n✅ 相似度质量测试完成")
            return {"status": "success", "results": quality_results}
            
        except Exception as e:
            print(f"❌ 相似度质量测试失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合测试"""
        print("🚀 开始向量数据库综合测试")
        print("="*60)
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "config_path": self.config_path,
            "tests": {}
        }
        
        # 运行所有测试
        test_results["tests"]["stats"] = self.test_database_stats()
        test_results["tests"]["content"] = self.test_document_content()
        test_results["tests"]["search"] = self.test_search_functionality()
        test_results["tests"]["metadata"] = self.test_metadata_validation()
        test_results["tests"]["similarity"] = self.test_similarity_quality()
        
        # 生成测试报告
        self.generate_test_report(test_results)
        
        print("\n" + "="*60)
        print("📋 测试总结")
        print("="*60)
        
        success_count = 0
        total_tests = len(test_results["tests"])
        
        for test_name, result in test_results["tests"].items():
            status = result.get("status", "unknown")
            if status == "success":
                print(f"✅ {test_name}: 通过")
                success_count += 1
            elif status == "empty":
                print(f"⚠️ {test_name}: 数据为空")
            else:
                print(f"❌ {test_name}: 失败")
        
        print(f"\n📊 测试通过率: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
        
        return test_results
    
    def generate_test_report(self, test_results: Dict[str, Any]):
        """生成测试报告"""
        try:
            report_filename = f"vector_db_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(test_results, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"\n📄 测试报告已保存: {report_filename}")
            
        except Exception as e:
            print(f"⚠️ 保存测试报告失败: {e}")
    
    def close(self):
        """关闭连接"""
        if hasattr(self, 'vector_manager'):
            self.vector_manager.close()


def main():
    """主函数"""
    try:
        # 创建测试器
        tester = VectorDatabaseTester()
        
        # 运行综合测试
        results = tester.run_comprehensive_test()
        
        # 关闭连接
        tester.close()
        
        print("\n🎉 向量数据库测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()