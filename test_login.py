#!/usr/bin/env python3
"""
独立登录功能测试脚本

测试登录管理器的功能，与内容提取完全分离
"""

import sys
import argparse
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from auth.login_manager import LoginManager
from core.config import ConfigManager


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="前程无忧独立登录功能测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python test_login.py                           # 基本登录测试
  python test_login.py --save-session           # 登录并保存会话
  python test_login.py --session-file data/my_session.json  # 指定会话文件
  python test_login.py --check-status           # 检查当前登录状态
        """
    )
    
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="配置文件路径 (默认: config/config.yaml)"
    )
    
    parser.add_argument(
        "--save-session",
        action="store_true",
        help="登录成功后保存会话"
    )
    
    parser.add_argument(
        "--session-file",
        help="会话文件路径"
    )
    
    parser.add_argument(
        "--check-status",
        action="store_true",
        help="检查当前登录状态"
    )
    
    parser.add_argument(
        "--force-login",
        action="store_true",
        help="强制重新登录（忽略保存的会话）"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    args = parser.parse_args()
    
    try:
        print("🚀 启动前程无忧独立登录测试")
        print("="*60)
        
        # 加载配置
        config_manager = ConfigManager(args.config)
        config = config_manager.load_config()
        
        # 如果强制登录，临时禁用保存会话的使用
        if args.force_login:
            config['mode']['use_saved_session'] = False
            print("🔄 强制重新登录模式")
        
        print(f"⚙️ 配置文件: {args.config}")
        print(f"💾 保存会话: {'是' if args.save_session else '否'}")
        if args.session_file:
            print(f"📁 会话文件: {args.session_file}")
        print(f"🐛 调试模式: {'开启' if args.debug else '关闭'}")
        print("="*60)
        
        # 创建登录管理器
        with LoginManager(config) as login_manager:
            
            if args.check_status:
                # 检查登录状态
                print("\n🔍 检查当前登录状态...")
                status_info = login_manager.check_login_status()
                
                print("\n" + "="*60)
                print("📊 登录状态信息")
                print("="*60)
                print(f"🔐 是否已登录: {'是' if status_info.get('is_logged_in', False) else '否'}")
                print(f"🌐 浏览器状态: {'活跃' if status_info.get('browser_alive', False) else '未启动'}")
                
                if status_info.get('current_session_file'):
                    print(f"📁 当前会话文件: {status_info['current_session_file']}")
                
                if status_info.get('login_start_time'):
                    print(f"⏰ 登录开始时间: {status_info['login_start_time']}")
                
                # 强制检查登录状态
                if status_info.get('browser_alive', False):
                    print("\n🔍 强制检查登录状态...")
                    is_logged_in = login_manager.force_check_login()
                    print(f"✅ 强制检查结果: {'已登录' if is_logged_in else '未登录'}")
                
            else:
                # 执行登录流程
                print("\n🔐 开始登录流程...")
                
                success = login_manager.start_login_session(
                    save_session=args.save_session,
                    session_file=args.session_file
                )
                
                if success:
                    print("\n" + "="*60)
                    print("✅ 登录测试成功!")
                    print("="*60)
                    
                    # 显示登录状态信息
                    status_info = login_manager.check_login_status()
                    print(f"🔐 登录状态: 已登录")
                    print(f"🌐 浏览器状态: {'活跃' if status_info.get('browser_alive', False) else '未启动'}")
                    
                    if status_info.get('current_session_file'):
                        print(f"💾 会话已保存到: {status_info['current_session_file']}")
                    
                    # 获取会话管理器信息
                    session_manager = login_manager.get_session_manager()
                    sessions = session_manager.list_sessions()
                    
                    if sessions:
                        print(f"\n📋 发现 {len(sessions)} 个会话文件:")
                        for i, session in enumerate(sessions[:3], 1):  # 只显示前3个
                            print(f"  {i}. {session['filepath']}")
                            print(f"     时间: {session['timestamp']}")
                            print(f"     过期: {'是' if session['is_expired'] else '否'}")
                    
                    print("\n💡 提示:")
                    print("  - 浏览器窗口将保持打开状态")
                    print("  - 您可以继续使用浏览器进行其他操作")
                    print("  - 会话信息已保存，下次可以直接使用")
                    
                else:
                    print("\n" + "="*60)
                    print("❌ 登录测试失败!")
                    print("="*60)
                    return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())