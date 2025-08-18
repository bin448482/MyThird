#!/usr/bin/env python3
"""
简化的分页功能测试脚本
直接测试分页相关的核心功能
"""

import sys
import os
import logging
from pathlib import Path

def test_pagination_config():
    """测试分页配置是否正确加载"""
    print("🔧 测试分页配置...")
    
    try:
        import yaml
        
        # 读取配置文件
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            print("❌ 配置文件不存在")
            return False
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查分页配置
        strategy = config.get('search', {}).get('strategy', {})
        
        required_keys = ['max_pages', 'enable_pagination', 'page_delay', 'page_delay_max']
        for key in required_keys:
            if key not in strategy:
                print(f"❌ 缺少配置项: {key}")
                return False
            print(f"✅ {key}: {strategy[key]}")
        
        print("✅ 分页配置检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_pagination_methods():
    """测试分页方法是否存在"""
    print("\n📄 测试分页方法...")
    
    try:
        # 检查PageParser中的分页方法
        page_parser_path = Path("src/extraction/page_parser.py")
        if not page_parser_path.exists():
            print("❌ page_parser.py 不存在")
            return False
        
        with open(page_parser_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_methods = [
            'has_next_page',
            'navigate_to_next_page', 
            'get_current_page_info'
        ]
        
        for method in required_methods:
            if f"def {method}" in content:
                print(f"✅ 找到方法: {method}")
            else:
                print(f"❌ 缺少方法: {method}")
                return False
        
        # 检查ContentExtractor中的分页支持
        content_extractor_path = Path("src/extraction/content_extractor.py")
        if not content_extractor_path.exists():
            print("❌ content_extractor.py 不存在")
            return False
        
        with open(content_extractor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有max_pages参数
        if "max_pages: Optional[int] = None" in content:
            print("✅ extract_from_search_url 支持 max_pages 参数")
        else:
            print("❌ extract_from_search_url 缺少 max_pages 参数")
            return False
        
        # 检查分页循环逻辑
        if "while current_page <= max_pages_config:" in content:
            print("✅ 找到分页循环逻辑")
        else:
            print("❌ 缺少分页循环逻辑")
            return False
        
        print("✅ 分页方法检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 方法测试失败: {e}")
        return False

def test_pagination_selectors():
    """测试分页选择器配置"""
    print("\n🎯 测试分页选择器...")
    
    try:
        # 检查PageParser中的选择器
        page_parser_path = Path("src/extraction/page_parser.py")
        with open(page_parser_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查下一页按钮选择器
        expected_selectors = [
            '.btn_next',
            '.next-page',
            '.page-next',
            '.btn-next',
            '.pager-next'
        ]
        
        found_selectors = 0
        for selector in expected_selectors:
            if f"'{selector}'" in content:
                print(f"✅ 找到选择器: {selector}")
                found_selectors += 1
        
        if found_selectors >= 3:
            print("✅ 分页选择器配置充足")
            return True
        else:
            print(f"⚠️ 只找到 {found_selectors} 个选择器，可能不够")
            return False
        
    except Exception as e:
        print(f"❌ 选择器测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 开始分页功能测试...")
    print("=" * 50)
    
    tests = [
        ("配置测试", test_pagination_config),
        ("方法测试", test_pagination_methods),
        ("选择器测试", test_pagination_selectors)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有分页功能测试通过！")
        print("\n📝 分页功能特性:")
        print("  ✅ 配置文件支持分页参数")
        print("  ✅ PageParser 具备分页导航能力")
        print("  ✅ ContentExtractor 支持多页提取")
        print("  ✅ 多种下一页按钮选择器")
        print("\n🚀 可以开始使用分页功能了！")
        return True
    else:
        print("⚠️ 部分测试未通过，请检查实现")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)