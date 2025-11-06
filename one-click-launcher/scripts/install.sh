#!/bin/bash

# ===================================================================
# 量化交易平台一键安装脚本 (Unix/Linux/macOS增强版)
# 版本: 1.0.0
# 更新: 2025-11-06
# ===================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 版本要求
PYTHON_MIN_VERSION="3.11"
NODE_MIN_VERSION="18"

# 脚本信息
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/tmp/trading_platform_install.log"

# 创建日志文件
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始安装量化交易平台 v$SCRIPT_VERSION" > "$LOG_FILE"

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_info() {
    print_message "$BLUE" "$1"
}

print_success() {
    print_message "$GREEN" "✅ $1"
}

print_warning() {
    print_message "$YELLOW" "⚠️  $1"
}

print_error() {
    print_message "$RED" "❌ $1"
}

print_header() {
    print_message "$CYAN" "$1"
}

# 显示欢迎界面
show_welcome() {
    clear
    echo -e "${WHITE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${WHITE}║              量化交易平台一键安装器 v$SCRIPT_VERSION               ║${NC}"
    echo -e "${WHITE}║                                                              ║${NC}"
    echo -e "${WHITE}║  此安装器将自动检查环境并安装所有必需的依赖包             ║${NC}"
    echo -e "${WHITE}║  支持macOS、Linux多种发行版的自动环境检测和配置            ║${NC}"
    echo -e "${WHITE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    print_info "安装目录: $LAUNCHER_DIR"
    print_info "安装日志: $LOG_FILE"
    echo
}

# 检测操作系统和架构
detect_system() {
    OS=$(uname -s)
    ARCH=$(uname -m)

    print_header "[1/6] 系统环境检测"
    echo

    case "$OS" in
        Darwin*)
            print_success "操作系统: macOS"
            # 获取macOS版本
            if command -v sw_vers &> /dev/null; then
                MACOS_VERSION=$(sw_vers -productVersion)
                print_info "macOS版本: $MACOS_VERSION"
            fi
            ;;
        Linux*)
            print_success "操作系统: Linux"
            # 获取Linux发行版信息
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                print_info "发行版: $NAME $VERSION"
            elif [ -f /etc/lsb-release ]; then
                . /etc/lsb-release
                print_info "发行版: $DISTRIB_DESCRIPTION"
            else
                print_info "发行版: 未知"
            fi
            ;;
        CYGWIN*|MINGW*|MSYS*)
            print_success "操作系统: Windows (Git Bash)"
            ;;
        *)
            print_warning "未知操作系统: $OS"
            ;;
    esac

    print_info "系统架构: $ARCH"

    # 检查系统资源
    if command -v free &> /dev/null; then
        MEMORY_INFO=$(free -h | grep "Mem:" | awk '{print $2 "/" $3 "/" $7}')
        print_info "内存状态: $MEMORY_INFO (总量/已用/可用)"
    fi

    if command -v df &> /dev/null; then
        DISK_INFO=$(df -h . | tail -1 | awk '{print $2 " 总量, " $4 " 可用"}')
        print_info "磁盘空间: $DISK_INFO"
    fi
}

# 检查网络连接
check_network() {
    echo
    print_info "检查网络连接..."

    # 检查基本网络连接
    if ping -c 1 8.8.8.8 &> /dev/null; then
        print_success "网络连接正常"
    else
        print_warning "网络连接可能有问题"
        return 1
    fi

    # 检查PyPI连接
    if curl -s --connect-timeout 5 https://pypi.org > /dev/null; then
        print_success "PyPI连接正常"
    else
        print_warning "PyPI连接异常，可能影响包安装"
        return 1
    fi

    return 0
}

# Python环境检查和安装
check_python() {
    echo
    print_header "[2/6] Python环境检查"
    echo

    PYTHON_CMD=""
    PIP_CMD=""

    # 查找Python命令
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        PIP_CMD="pip"
    else
        print_error "Python未安装"
        echo
        print_info "请安装Python $PYTHON_MIN_VERSION+："

        case "$OS" in
            Darwin*)
                print_info "  方法1 (推荐): 使用Homebrew"
                print_info "    brew install python@3.11"
                print_info "  方法2: 官方下载"
                print_info "    https://www.python.org/downloads/macos/"
                ;;
            Linux*)
                print_info "  Ubuntu/Debian:"
                print_info "    sudo apt-get update"
                print_info "    sudo apt-get install python3.11 python3.11-pip python3.11-venv"
                print_info "  CentOS/RHEL/Rocky:"
                print_info "    sudo yum install python3.11 python3.11-pip"
                print_info "  Fedora:"
                print_info "    sudo dnf install python3.11 python3.11-pip"
                ;;
        esac

        return 1
    fi

    # 获取Python版本
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    print_success "Python版本: $PYTHON_VERSION"

    # 检查版本兼容性
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d' ' -f2 | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d' ' -f2 | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        print_error "Python版本过低，需要Python $PYTHON_MIN_VERSION+"
        print_info "当前版本: $PYTHON_VERSION"

        case "$OS" in
            Darwin*)
                print_info "升级建议: brew install python@3.11"
                ;;
            Linux*)
                print_info "升级建议: 安装Python 3.11+包"
                ;;
        esac

        return 1
    fi

    print_success "Python版本满足要求"
    return 0
}

# 安装Python依赖
install_python_deps() {
    echo
    print_header "[3/6] Python依赖安装"
    echo

    cd "$LAUNCHER_DIR"

    # 升级pip，使用国内镜像源
    print_info "升级pip..."
    if $PYTHON_CMD -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/; then
        print_success "pip升级完成 (国内镜像源)"
    else
        print_warning "国内镜像源升级失败，尝试默认源..."
        $PYTHON_CMD -m pip install --upgrade pip
        if [ $? -eq 0 ]; then
            print_success "pip升级完成 (默认源)"
        else
            print_error "pip升级失败"
            return 1
        fi
    fi

    # 检查requirements.txt
    if [ -f "requirements.txt" ]; then
        print_info "安装Python依赖包..."
        print_info "使用国内镜像源加速下载..."

        # 尝试使用清华镜像源
        if $PYTHON_CMD -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --progress-bar off; then
            print_success "Python依赖包安装完成 (国内镜像源)"
        else
            print_warning "国内镜像源安装失败，尝试默认源..."
            if $PYTHON_CMD -m pip install -r requirements.txt --progress-bar off; then
                print_success "Python依赖包安装完成 (默认源)"
            else
                print_error "Python依赖包安装失败"
                print_info "请检查网络连接或手动安装依赖"
                return 1
            fi
        fi
    else
        print_warning "未找到requirements.txt文件"
        print_info "安装基础依赖..."
        $PYTHON_CMD -m pip install psutil rich requests fastapi uvicorn sqlalchemy pandas pydantic
    fi

    return 0
}

# Node.js环境检查和安装
check_nodejs() {
    echo
    print_header "[4/6] Node.js环境检查"
    echo

    NODE_AVAILABLE=0
    NODE_DEPS_OK=0

    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js版本: $NODE_VERSION"

        # 检查版本兼容性
        NODE_VERSION_NUMBER=${NODE_VERSION#v}
        NODE_MAJOR=$(echo $NODE_VERSION_NUMBER | cut -d'.' -f1)

        if [ "$NODE_MAJOR" -ge $NODE_MIN_VERSION ]; then
            print_success "Node.js版本满足要求"
            NODE_AVAILABLE=1

            # 安装Node.js依赖
            if [ -f "frontend/package.json" ]; then
                print_info "安装Node.js依赖包..."
                cd frontend

                # 配置npm镜像源
                npm config set registry https://registry.npmmirror.com

                if npm install; then
                    print_success "Node.js依赖包安装完成 (国内镜像源)"
                    NODE_DEPS_OK=1
                else
                    print_warning "国内镜像源安装失败，尝试默认源..."
                    npm config set registry https://registry.npmjs.org/
                    if npm install; then
                        print_success "Node.js依赖包安装完成 (默认源)"
                        NODE_DEPS_OK=1
                    else
                        print_error "Node.js依赖包安装失败"
                    fi
                fi

                cd ..
            else
                print_warning "未找到frontend/package.json文件"
            fi
        else
            print_warning "Node.js版本较低，建议升级到$NODE_MIN_VERSION+"
            print_info "当前版本: $NODE_VERSION"
        fi
    else
        print_warning "Node.js未安装，前端功能将不可用"
        echo
        print_info "可选安装Node.js $NODE_MIN_VERSION+："

        case "$OS" in
            Darwin*)
                print_info "  使用Homebrew: brew install node"
                print_info "  或从官网下载: https://nodejs.org/"
                ;;
            Linux*)
                print_info "  Ubuntu/Debian:"
                print_info "    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -"
                print_info "    sudo apt-get install -y nodejs"
                print_info "  CentOS/RHEL/Rocky:"
                print_info "    curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -"
                print_info "    sudo yum install -y nodejs npm"
                print_info "  Fedora:"
                print_info "    sudo dnf install nodejs"
                ;;
        esac
    fi

    return 0
}

# 创建桌面快捷方式
create_desktop_shortcut() {
    echo
    print_header "[5/6] 创建桌面快捷方式"
    echo

    case "$OS" in
        Darwin*)
            # macOS
            DESKTOP_DIR="$HOME/Desktop"
            if [ -d "$DESKTOP_DIR" ]; then
                cat > "$DESKTOP_DIR/量化交易平台.command" << EOF
#!/bin/bash
cd "$LAUNCHER_DIR"
$PYTHON_CMD launcher.py
EOF
                chmod +x "$DESKTOP_DIR/量化交易平台.command"
                print_success "macOS桌面快捷方式创建完成"
            else
                print_warning "桌面目录不存在，跳过快捷方式创建"
            fi
            ;;
        Linux*)
            # Linux
            DESKTOP_DIR="$HOME/Desktop"
            APPS_DIR="$HOME/.local/share/applications"

            # 创建.desktop文件
            mkdir -p "$APPS_DIR"
            cat > "$APPS_DIR/quant-trading-platform.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=量化交易平台
Name[en]=Quantitative Trading Platform
Comment=量化交易平台一键启动器
Comment[en]=Quantitative Trading Platform Launcher
Exec=$PYTHON_CMD $LAUNCHER_DIR/launcher.py
Icon=$LAUNCHER_DIR/assets/icon.png
Terminal=true
Categories=Office;Finance;Development;
EOF

            # 如果桌面目录存在，也创建一个副本
            if [ -d "$DESKTOP_DIR" ]; then
                cp "$APPS_DIR/quant-trading-platform.desktop" "$DESKTOP_DIR/"
                chmod +x "$DESKTOP_DIR/quant-trading-platform.desktop"
                print_success "Linux桌面快捷方式创建完成"
            else
                print_success "应用程序菜单项创建完成"
            fi
            ;;
        *)
            print_warning "当前系统不支持自动创建桌面快捷方式"
            ;;
    esac
}

# 显示安装总结
show_summary() {
    echo
    print_header "[6/6] 安装完成总结"
    echo

    echo -e "${WHITE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${WHITE}║                        安装完成！                           ║${NC}"
    echo -e "${WHITE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo

    print_info "安装结果总结:"
    print_success "Python环境: $PYTHON_VERSION"

    if [ "$NODE_AVAILABLE" -eq 1 ]; then
        if [ "$NODE_DEPS_OK" -eq 1 ]; then
            print_success "Node.js环境: $(node --version)"
            print_success "前端依赖: 安装完成"
            FRONTEND_AVAILABLE="可用"
        else
            print_success "Node.js环境: $(node --version)"
            print_warning "前端依赖: 安装失败"
            FRONTEND_AVAILABLE="部分可用"
        fi
    else
        print_warning "Node.js环境: 未安装"
        print_warning "前端功能: 不可用"
        FRONTEND_AVAILABLE="不可用"
    fi

    echo
    print_info "启动方式:"
    print_info "  1. 命令行: $PYTHON_CMD launcher.py"
    print_info "  2. 调试模式: $PYTHON_CMD launcher.py --debug"

    if [ "$OS" = "Darwin" ] && [ -f "$HOME/Desktop/量化交易平台.command" ]; then
        print_info "  3. 桌面快捷方式: 双击「量化交易平台.command」"
    elif [ "$OS" = "Linux" ] && [ -f "$HOME/Desktop/quant-trading-platform.desktop" ]; then
        print_info "  3. 桌面快捷方式: 双击「量化交易平台」"
    fi

    echo
    print_info "访问地址:"
    if [ "$FRONTEND_AVAILABLE" = "可用" ]; then
        print_info "  🌐 前端应用: http://localhost:3000"
    elif [ "$FRONTEND_AVAILABLE" = "部分可用" ]; then
        print_info "  🌐 前端应用: http://localhost:3000 (可能有问题)"
    else
        print_warning "  🌐 前端应用: 不可用 (Node.js未安装)"
    fi
    print_info "  🔧 后端API:  http://localhost:8000"
    print_info "  📚 API文档:  http://localhost:8000/docs"

    echo
    print_info "技术支持:"
    print_info "  📧 邮箱: support@quant-trading.example.com"
    print_info "  📞 电话: 400-123-4567"
    print_info "  📖 文档: https://docs.quant-trading.example.com"
    print_info "  🐛 问题反馈: https://github.com/your-repo/issues"

    echo
    print_info "安装日志已保存到: $LOG_FILE"
}

# 主函数
main() {
    # 检查是否在正确的目录
    if [ ! -f "$LAUNCHER_DIR/launcher.py" ]; then
        print_error "找不到launcher.py文件"
        print_info "请确保在正确的目录中运行此脚本"
        print_info "当前目录: $(pwd)"
        print_info "预期目录: $LAUNCHER_DIR"
        exit 1
    fi

    show_welcome
    detect_system

    # 网络检查（非致命）
    check_network || print_warning "网络检查失败，继续安装..."

    # 环境检查（致命）
    if ! check_python; then
        print_error "Python环境检查失败，无法继续安装"
        exit 1
    fi

    # 依赖安装（致命）
    if ! install_python_deps; then
        print_error "Python依赖安装失败"
        exit 1
    fi

    # Node.js检查（非致命）
    check_nodejs

    # 创建快捷方式（非致命）
    create_desktop_shortcut

    show_summary

    # 询问是否立即启动
    echo
    read -p "是否现在启动平台？ (Y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo
        print_info "正在启动量化交易平台..."
        cd "$LAUNCHER_DIR"
        $PYTHON_CMD launcher.py
        EXIT_CODE=$?

        if [ $EXIT_CODE -ne 0 ]; then
            echo
            print_error "启动失败，退出代码: $EXIT_CODE"
            print_info "可能的解决方案:"
            print_info "1. 检查端口占用: netstat -an | grep -E ':(3000|8000|6379|5432)'"
            print_info "2. 查看详细日志: $PYTHON_CMD launcher.py --debug"
            print_info "3. 检查系统资源: free -h && df -h"
        fi
    fi

    echo
    print_success "安装脚本执行完成"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 安装完成" >> "$LOG_FILE"
}

# 错误处理
trap 'print_error "安装过程中发生错误，请查看日志: $LOG_FILE"; exit 1' ERR

# 运行主函数
main "$@"