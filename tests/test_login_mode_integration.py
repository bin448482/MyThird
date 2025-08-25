#!/usr/bin/env python3
"""
登录模式集成测试脚本
"""

import yaml
from src.extraction.content_extractor import ContentExtractor

def test_anonymous_mode():
    """测试无登录模式（现有功能）"""
    print("🔓 测试无登录模式...")
    
    # 加载配置并确保登录模式关闭
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['login_mode']['enabled'] = False
    
    # 创建提取器
    extractor = ContentExtractor(config)
    
    try:
        # 测试提取
        results = extractor.extract_from_keyword("Python开发", max_results=5, max_pages=1)
        print(f"✅ 无登录模式测试成功，提取了 {len(results)} 个职位")
        return True
    except Exception as e:
        print(f"❌ 无登录模式测试失败: {e}")
        return False
    finally:
        extractor.close()

def test_login_mode():
    """测试登录模式"""
    print("🔐 测试登录模式...")
    
    # 加载配置并启用登录模式
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['login_mode']['enabled'] = True
    
    # 创建提取器
    extractor = ContentExtractor(config)
    
    try:
        # 测试提取（会触发登录流程）
        results = extractor.extract_from_keyword("Python开发", max_results=5, max_pages=1)
        print(f"✅ 登录模式测试成功，提取了 {len(results)} 个职位")
        
        # 获取登录状态
        status = extractor.get_login_status_summary()
        print(f"执行模式: {status['extraction_mode']}")
        print(f"登录状态: {status['login_status']['is_logged_in']}")
        
        return True
    except Exception as e:
        print(f"❌ 登录模式测试失败: {e}")
        return False
    finally:
        extractor.close()

def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 登录模式集成测试")
    print("=" * 60)
    
    # 测试无登录模式
    anonymous_success = test_anonymous_mode()
    
    print("\n" + "-" * 40 + "\n")
    
    # 测试登录模式
    login_success = test_login_mode()
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"无登录模式: {'✅ 通过' if anonymous_success else '❌ 失败'}")
    print(f"登录模式: {'✅ 通过' if login_success else '❌ 失败'}")
    
    if anonymous_success and login_success:
        print("\n🎉 所有测试通过！登录功能集成成功。")
    else:
        print("\n⚠️ 部分测试失败，请检查实现。")

if __name__ == "__main__":
    main()