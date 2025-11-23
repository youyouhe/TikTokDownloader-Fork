#!/usr/bin/env python3
"""
Cookie 管理脚本
用于将 Netscape 格式的 cookie 文件转换为 TikTokDownloader 项目配置格式
支持抖音和 TikTok 两个平台，更新配置文件以支持API模式
"""

import re
import sys
import json
from pathlib import Path
from argparse import ArgumentParser
from platform import system


def parse_netscape_cookies(cookie_file_path):
    """
    解析 Netscape 格式的 cookie 文件
    """
    cookies = []
    platform = None

    try:
        with open(cookie_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue

                # 解析 cookie 行
                parts = line.split('\t')
                if len(parts) >= 7:
                    domain, flag, path, secure, expiration, name, value = parts[:7]

                    # 智能识别平台
                    if 'douyin.com' in domain or 'iesdouyin.com' in domain:
                        platform = 'douyin'
                    elif 'tiktok.com' in domain:
                        platform = 'tiktok'
                    elif 'kuaishou.com' in domain:
                        platform = 'kuaishou'

                    # 只保留支持的平台域名
                    if any(domain_keyword in domain for domain_keyword in
                          ['douyin.com', 'iesdouyin.com', 'tiktok.com', 'kuaishou.com']):
                        cookies.append({
                            'name': name,
                            'value': value,
                            'domain': domain,
                            'platform': platform
                        })

    except Exception as e:
        print(f"解析 cookie 文件失败: {e}")
        return None, None

    return cookies, platform


def cookies_to_header_format(cookies, platform=None):
    """
    将 cookies 转换为 HTTP header 格式
    支持不同平台的优先级 Cookie
    """
    if not cookies:
        return ""

    # 根据平台设置优先级 cookies
    priority_cookies = {
        'douyin': ['sessionid', 'sid_guard', 'uid_tt', 'sid_tt', 'ttwid', 'msToken'],
        'tiktok': ['sessionid_ss', 'sessionid', 'ttwid', 'msToken', 'tt_csstoken'],
        'kuaishou': ['userId', 'kpn', 'kpf', 'did', 'clientid', 'kuaishou.server.webday7_st']
    }

    # 使用指定平台的优先级，如果无法识别则使用通用优先级
    current_priority = priority_cookies.get(platform, ['sessionid', 'sessionid_ss', 'userid', 'uid', 'ttwid'])

    # 处理重复的cookie名称，保留最后一个（后面的通常会覆盖前面的）
    cookie_dict = {}
    for cookie in cookies:
        cookie_dict[cookie['name']] = cookie['value']

    # 优先添加重要的 cookies
    header_parts = []
    for priority_name in current_priority:
        if priority_name in cookie_dict:
            header_parts.append(f"{priority_name}={cookie_dict[priority_name]}")
            del cookie_dict[priority_name]

    # 添加其他 cookies
    for name, value in cookie_dict.items():
        header_parts.append(f"{name}={value}")

    return "; ".join(header_parts)


def detect_platform_from_cookies(cookies):
    """
    从 cookies 中检测平台类型
    """
    domains = [cookie.get('domain', '') for cookie in cookies]

    if any('douyin.com' in domain or 'iesdouyin.com' in domain for domain in domains):
        return 'douyin'
    elif any('tiktok.com' in domain for domain in domains):
        return 'tiktok'
    elif any('kuaishou.com' in domain for domain in domains):
        return 'kuaishou'
    else:
        return None


def update_config_cookie(cookie_string, platform, config_file=None):
    """
    更新配置文件中的 cookie
    """
    project_root = Path(__file__).parent

    if config_file is None:
        # 尝试多个可能的配置文件位置
        config_files = [
            project_root / "src" / "config" / "settings.json",
            project_root / "settings.json",
            project_root / "config.json",
        ]
        config_file = next((f for f in config_files if f.exists()), None)

    if config_file is None:
        # 如果没有找到配置文件，使用默认位置
        config_file = project_root / "src" / "config" / "settings.json"
    else:
        # 确保config_file是Path对象
        config_file = Path(config_file)

    encode = "UTF-8-SIG" if system() == "Windows" else "UTF-8"

    try:
        # 读取现有配置
        if config_file.exists():
            with config_file.open('r', encoding=encode) as f:
                config = json.load(f)
        else:
            print("配置文件不存在，将创建新配置文件")
            config = {}

        # 根据平台更新对应的 cookie
        if platform == 'tiktok':
            config['cookie_tiktok'] = cookie_string
            cookie_key = 'cookie_tiktok'
            platform_name = 'TikTok'
        elif platform == 'douyin':
            config['cookie'] = cookie_string
            cookie_key = 'cookie'
            platform_name = '抖音'
        elif platform == 'kuaishou':
            config['cookie'] = cookie_string  # 快手使用抖音的配置键
            cookie_key = 'cookie'
            platform_name = '快手'
        else:
            print(f"❌ 不支持的平台: {platform}")
            return False

        # 确保目录存在
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # 写入配置文件
        with config_file.open('w', encoding=encode) as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        print(f"✅ {platform_name} Cookie 已成功更新到配置文件: {config_file}")
        print(f"   配置键: {cookie_key}")

        # 🎯 同时更新Volume目录下的配置文件（API模式使用）
        volume_config = project_root / "Volume" / "settings.json"
        try:
            if volume_config.exists():
                with volume_config.open('r', encoding=encode) as f:
                    volume_data = json.load(f)
            else:
                volume_data = config.copy()

            # 同步cookie配置
            if platform == 'tiktok':
                volume_data['cookie_tiktok'] = cookie_string
            else:
                volume_data['cookie'] = cookie_string

            # 确保Volume目录存在
            volume_config.parent.mkdir(parents=True, exist_ok=True)

            with volume_config.open('w', encoding=encode) as f:
                json.dump(volume_data, f, indent=4, ensure_ascii=False)

            print(f"✅ {platform_name} Cookie 已同步到API配置文件: {volume_config}")

        except Exception as e:
            print(f"⚠️  同步API配置文件失败: {e}")

        return True

    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")
        return False


def main():
    """
    主函数
    """
    parser = ArgumentParser(description='TikTokDownloader Cookie 管理工具')
    parser.add_argument('cookie_file', help='Netscape格式的cookie文件路径')
    parser.add_argument('--platform', choices=['douyin', 'tiktok', 'kuaishou', 'auto'],
                       default='auto', help='指定平台类型 (默认: auto)')
    parser.add_argument('--config', help='指定配置文件路径')
    parser.add_argument('--dry-run', action='store_true', help='仅解析不更新配置')

    args = parser.parse_args()

    cookie_file = Path(args.cookie_file)

    # 检查文件是否存在
    if not cookie_file.exists():
        print(f"❌ Cookie 文件不存在: {cookie_file}")
        sys.exit(1)

    print(f"📖 正在解析 cookie 文件: {cookie_file}")

    # 解析 cookie
    cookies, detected_platform = parse_netscape_cookies(cookie_file)
    if not cookies:
        print("❌ 未能解析到有效的 cookies")
        sys.exit(1)

    print(f"✅ 解析到 {len(cookies)} 个 cookies")

    # 确定平台
    if args.platform == 'auto':
        platform = detected_platform or detect_platform_from_cookies(cookies)
    else:
        platform = args.platform

    if not platform:
        print("❌ 无法确定平台类型，请手动指定 --platform 参数")
        sys.exit(1)

    platform_names = {
        'douyin': '抖音',
        'tiktok': 'TikTok',
        'kuaishou': '快手'
    }
    print(f"🎯 检测到平台: {platform_names.get(platform, platform)}")

    # 转换格式
    cookie_header = cookies_to_header_format(cookies, platform)
    print(f"🔄 转换后的 cookie 长度: {len(cookie_header)} 字符")

    # 显示前100个字符作为预览
    preview = cookie_header[:100] + "..." if len(cookie_header) > 100 else cookie_header
    print(f"📝 Cookie 预览: {preview}")

    if args.dry_run:
        print("🔍 模式：仅解析，不更新配置文件")
        return

    # 更新配置文件
    print("🔄 正在更新配置文件...")
    if update_config_cookie(cookie_header, platform, args.config):
        print("🎉 Cookie 更新完成！")

        # 显示使用建议
        print("\n💡 使用建议:")
        print("   - 重启应用程序使配置生效")
        print("   - API 模式现在可以读取到正确的 cookie 配置")
        print("   - 现在可以不传 cookie 参数直接调用相关 API")

        if platform == 'tiktok':
            print("   - 可以调用 TikTok 相关 API")
        else:
            print("   - 可以调用抖音相关 API")
    else:
        print("❌ Cookie 更新失败")
        sys.exit(1)


if __name__ == "__main__":
    main()