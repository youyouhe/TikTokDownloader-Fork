#!/bin/bash

# TikTokDownloader Cookie 自动更新脚本
# 支持抖音、TikTok、快手三个平台
# 使用方法: ./auto_update_cookie.sh [cookie_file_path] [platform]

# 默认参数
DEFAULT_COOKIE_FILE=""
DEFAULT_PLATFORM="auto"
DEFAULT_API_PORT="5555"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 函数：打印彩色消息
print_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

print_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

print_warning() {
    echo -e "\033[33m[WARNING]\033[0m $1"
}

print_success() {
    echo -e "\033[32m[SUCCESS]\033[0m $1"
}

# 函数：检查文件是否存在
check_file() {
    local file_path="$1"
    if [[ ! -f "$file_path" ]]; then
        print_error "文件不存在: $file_path"
        return 1
    fi
    return 0
}

# 函数：备份当前配置
backup_config() {
    local config_file="config.json"
    local config_paths=(
        "$config_file"
        "src/config/settings.json"
        "settings.json"
    )

    # 查找存在的配置文件
    local found_config=""
    for path in "${config_paths[@]}"; do
        if [[ -f "$path" ]]; then
            found_config="$path"
            break
        fi
    done

    if [[ -n "$found_config" ]]; then
        local backup_file="${found_config}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$found_config" "$backup_file"
        print_info "配置文件已备份到: $backup_file"
    else
        print_warning "未找到现有配置文件，将创建新配置"
    fi
}

# 函数：重启API服务器
restart_api_server() {
    local port="$1"
    print_info "正在重启API服务器 (端口: $port)..."

    # 查找并终止现有的API服务器进程
    local pids=$(pgrep -f "python.*main.py.*api")
    if [[ -n "$pids" ]]; then
        print_info "发现运行中的API服务器进程: $pids"
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 3
        print_info "已终止现有API服务器进程"
    fi

    # 检查进程是否完全终止
    local remaining_pids=$(pgrep -f "python.*main.py.*api")
    if [[ -n "$remaining_pids" ]]; then
        print_warning "强制终止残留进程: $remaining_pids"
        echo "$remaining_pids" | xargs kill -KILL 2>/dev/null || true
        sleep 2
    fi

    # 启动新的API服务器
    print_info "启动新的API服务器..."
    nohup python main.py api --host 0.0.0.0 --port "$port" > api_server.log 2>&1 &
    local new_pid=$!

    sleep 5

    if ps -p "$new_pid" > /dev/null 2>&1; then
        print_success "API服务器已启动，PID: $new_pid"
        print_info "API访问地址: http://localhost:$port"
        print_info "API文档地址: http://localhost:$port/docs"
        return 0
    else
        print_error "API服务器启动失败"
        print_info "查看日志: tail -f api_server.log"
        return 1
    fi
}

# 函数：测试API连接
test_api() {
    local port="$1"
    print_info "正在测试API连接..."

    # 测试根路径
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:"$port"/ 2>/dev/null)

    if [[ "$response_code" =~ ^(200|307|404)$ ]]; then
        print_success "✅ API服务器响应正常 (HTTP $response_code)"
    else
        print_error "❌ API服务器响应异常 (HTTP $response_code)"
        return 1
    fi

    # 测试API文档端点
    local docs_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:"$port"/docs 2>/dev/null)
    if [[ "$docs_response" == "200" ]]; then
        print_success "✅ API文档页面可访问"
    else
        print_warning "⚠️ API文档页面不可访问 (HTTP $docs_response)"
    fi

    print_info "API连接测试完成"
}

# 函数：验证Cookie更新结果
verify_cookie_update() {
    local platform="$1"
    print_info "正在验证Cookie更新结果..."

    # 查找配置文件
    local config_files=("config.json" "src/config/settings.json" "settings.json")
    local found_config=""

    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            found_config="$config_file"
            break
        fi
    done

    if [[ -z "$found_config" ]]; then
        print_error "未找到配置文件，无法验证"
        return 1
    fi

    # 检查对应的cookie字段
    local cookie_key=""
    local platform_name=""

    case "$platform" in
        "tiktok")
            cookie_key="cookie_tiktok"
            platform_name="TikTok"
            ;;
        "douyin"|"kuaishou")
            cookie_key="cookie"
            platform_name="抖音/快手"
            ;;
        *)
            print_error "未知平台: $platform"
            return 1
            ;;
    esac

    # 使用python提取配置值
    local cookie_value=$(python3 -c "
import json
try:
    with open('$found_config', 'r', encoding='utf-8') as f:
        config = json.load(f)
    cookie = config.get('$cookie_key', '')
    if cookie:
        print(f'长度: {len(cookie)} 字符')
        print(f'前100字符: {cookie[:100]}...')
    else:
        print('未找到')
except Exception as e:
    print(f'读取失败: {e}')
" 2>/dev/null)

    if [[ "$cookie_value" == *"未找到"* ]]; then
        print_error "❌ 配置文件中未找到 $platform_name Cookie"
        return 1
    elif [[ "$cookie_value" == *"读取失败"* ]]; then
        print_error "❌ 读取配置文件失败"
        return 1
    else
        print_success "✅ $platform_name Cookie 验证成功"
        print_info "   $cookie_value"
        return 0
    fi
}

# 主函数
main() {
    local cookie_file="$1"
    local platform="$2"
    local api_port="${3:-$DEFAULT_API_PORT}"

    print_info "=== TikTokDownloader Cookie 自动更新脚本 ==="

    # 处理参数
    if [[ -z "$cookie_file" ]]; then
        print_error "请指定cookie文件路径"
        print_info "使用方法: $0 <cookie_file_path> [platform] [api_port]"
        print_info "示例: $0 cookies.txt tiktok 5555"
        exit 1
    fi

    if [[ -z "$platform" ]]; then
        platform="auto"
        print_warning "未指定平台，使用自动检测: $platform"
    fi

    # 验证平台参数
    if [[ ! "$platform" =~ ^(douyin|tiktok|kuaishou|auto)$ ]]; then
        print_error "无效的平台: $platform"
        print_info "支持的平台: douyin, tiktok, kuaishou, auto"
        exit 1
    fi

    # 检查cookie文件
    if ! check_file "$cookie_file"; then
        print_info "请确保cookie文件存在"
        print_info "支持的格式: Netscape Cookie 格式"
        exit 1
    fi

    print_info "使用cookie文件: $cookie_file"
    print_info "目标平台: $platform"
    print_info "API端口: $api_port"

    # 备份当前配置
    backup_config

    # 更新cookie
    print_info "正在更新cookie配置..."
    local update_args=("$cookie_file" "--platform" "$platform")

    if python update_cookie.py "${update_args[@]}"; then
        print_success "✅ Cookie更新成功"
    else
        print_error "❌ Cookie更新失败"
        exit 1
    fi

    # 验证更新结果
    local detected_platform
    if [[ "$platform" == "auto" ]]; then
        # 自动检测实际平台
        detected_platform=$(python update_cookie.py "$cookie_file" --platform auto --dry-run 2>/dev/null | grep "检测到平台" | awk '{print $4}' || echo "")
    else
        detected_platform="$platform"
    fi

    if verify_cookie_update "$detected_platform"; then
        print_success "✅ Cookie验证通过"
    else
        print_error "❌ Cookie验证失败"
        exit 1
    fi

    # 重启API服务器
    if restart_api_server "$api_port"; then
        print_success "✅ API服务器重启成功"
    else
        print_error "❌ API服务器重启失败"
        exit 1
    fi

    # 测试API
    if test_api "$api_port"; then
        print_success "✅ 所有检查通过"
        print_info ""
        print_success "🎉 Cookie更新完成！现在可以不传cookie参数直接调用API"
        print_info ""

        # 根据平台显示示例API调用
        case "$detected_platform" in
            "tiktok")
                print_info "TikTok API调用示例:"
                print_info "curl -X POST \"http://localhost:$api_port/detail/\" \\"
                print_info "  -H \"Content-Type: application/json\" \\"
                print_info "  -d '{\"text\": \"你的TikTok链接\", \"proxy\": \"\"}'"
                ;;
            "douyin")
                print_info "抖音API调用示例:"
                print_info "curl -X POST \"http://localhost:$api_port/detail/\" \\"
                print_info "  -H \"Content-Type: application/json\" \\"
                print_info "  -d '{\"text\": \"你的抖音链接\", \"proxy\": \"\"}'"
                ;;
            "kuaishou")
                print_info "快手API调用示例:"
                print_info "curl -X POST \"http://localhost:$api_port/detail/\" \\"
                print_info "  -H \"Content-Type: application/json\" \\"
                print_info "  -d '{\"text\": \"你的快手链接\", \"proxy\": \"\"}'"
                ;;
        esac

        print_info ""
        print_info "📖 更多信息请查看API文档: http://localhost:$api_port/docs"
    else
        print_error "❌ API测试失败"
        print_info "查看API服务器日志: tail -f api_server.log"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "TikTokDownloader Cookie 自动更新脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 <cookie_file_path> [platform] [api_port]"
    echo ""
    echo "参数:"
    echo "  cookie_file_path  Netscape格式的cookie文件路径"
    echo "  platform          目标平台 (douyin|tiktok|kuaishou|auto)"
    echo "                    (可选，默认为 auto)"
    echo "  api_port          API服务器端口"
    echo "                    (可选，默认为 5555)"
    echo ""
    echo "功能:"
    echo "  1. 解析Netscape格式的cookie文件"
    echo "  2. 智能识别平台类型 (抖音/TikTok/快手)"
    echo "  3. 更新项目配置文件中的cookie"
    echo "  4. 重启API服务器使配置生效"
    echo "  5. 验证Cookie更新结果"
    echo "  6. 测试API连接是否正常"
    echo ""
    echo "示例:"
    echo "  $0 cookies.txt"
    echo "  $0 cookies.txt tiktok 5555"
    echo "  $0 /path/to/douyin_cookies.txt douyin 5556"
    echo ""
    echo "说明:"
    echo "  - cookie文件可以是浏览器导出的Netscape格式"
    echo "  - 脚本会自动识别域名并分类到对应平台"
    echo "  - 支持多种配置文件位置自动检测"
    echo "  - 提供配置文件备份功能"
}

# 检查命令行参数
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# 检查Python环境
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    print_error "未找到Python环境，请确保已安装Python"
    exit 1
fi

# 检查update_cookie.py脚本
if [[ ! -f "update_cookie.py" ]]; then
    print_error "未找到update_cookie.py脚本，请确保文件存在"
    exit 1
fi

# 执行主函数
main "$@"