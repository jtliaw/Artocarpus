#!/bin/bash
# Artocarpus (Scrcpy GUI) 绿色版安装脚本
# 完全独立安装，不影响系统环境
# 删除文件夹即可完全卸载

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# 配置
APP_NAME="Artocarpus"
APP_VERSION="5.3"
GITHUB_REPO="jtliaw/Artocarpus"
SCRCPY_REPO="Genymobile/scrcpy"

# 获取脚本所在目录（安装根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$SCRIPT_DIR"

# 子目录
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$INSTALL_DIR/bin"
SCRCPY_DIR="$INSTALL_DIR/scrcpy"
APP_DIR="$INSTALL_DIR/app"

# 打印函数
print_header() {
    echo -e "\n${BLUE}${BOLD}============================================================${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}============================================================${NC}\n"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 检查系统
check_system() {
    print_info "检查操作系统..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_success "操作系统: Linux"
    else
        print_error "此脚本仅支持 Linux 系统"
        exit 1
    fi
}

# 检查 Python
check_python() {
    print_info "检查 Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python 版本: $PYTHON_VERSION"
        PYTHON_CMD="python3"
        return 0
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version | cut -d' ' -f2)
        print_success "Python 版本: $PYTHON_VERSION"
        PYTHON_CMD="python"
        return 0
    else
        print_error "未找到 Python！请先安装 Python 3.6+"
        exit 1
    fi
}

# 创建目录结构
create_directories() {
    print_info "创建目录结构..."
    
    mkdir -p "$VENV_DIR"
    mkdir -p "$BIN_DIR"
    mkdir -p "$SCRCPY_DIR"
    mkdir -p "$APP_DIR"
    
    print_success "目录创建完成"
}

# 创建 Python 虚拟环境
create_venv() {
    print_header "创建 Python 虚拟环境"
    
    if [ -d "$VENV_DIR/bin" ]; then
        print_warning "虚拟环境已存在，跳过创建"
        return 0
    fi
    
    print_info "创建虚拟环境到: $VENV_DIR"
    $PYTHON_CMD -m venv "$VENV_DIR"
    
    if [ $? -eq 0 ]; then
        print_success "虚拟环境创建成功"
    else
        print_error "虚拟环境创建失败"
        exit 1
    fi
}

# 安装 Python 依赖
install_python_deps() {
    print_header "安装 Python 依赖"
    
    print_info "激活虚拟环境..."
    source "$VENV_DIR/bin/activate"
    
    print_info "升级 pip..."
    pip install --upgrade pip -q
    
    print_info "安装 ttkthemes..."
    pip install ttkthemes -q
    
    if [ $? -eq 0 ]; then
        print_success "Python 依赖安装完成"
    else
        print_error "依赖安装失败"
        exit 1
    fi
}

# 获取最新版本信息
get_latest_release() {
    local repo=$1
    local api_url="https://api.github.com/repos/$repo/releases/latest"
    
    if command -v curl &> /dev/null; then
        curl -s "$api_url"
    elif command -v wget &> /dev/null; then
        wget -qO- "$api_url"
    else
        print_error "需要 curl 或 wget 来下载文件"
        exit 1
    fi
}

# 下载文件
download_file() {
    local url=$1
    local output=$2
    
    print_info "下载: $url"
    
    if command -v curl &> /dev/null; then
        curl -L --progress-bar "$url" -o "$output"
    elif command -v wget &> /dev/null; then
        wget --show-progress -q "$url" -O "$output"
    else
        print_error "需要 curl 或 wget 来下载文件"
        return 1
    fi
    
    if [ $? -eq 0 ]; then
        print_success "下载完成: $output"
        return 0
    else
        print_error "下载失败"
        return 1
    fi
}

# 下载并安装 scrcpy
install_scrcpy() {
    print_header "安装 Scrcpy"
    
    # 检查是否已安装
    if [ -f "$SCRCPY_DIR/scrcpy" ]; then
        print_warning "Scrcpy 已存在，跳过下载"
        return 0
    fi
    
    print_info "获取最新版本信息..."
    local release_json=$(get_latest_release "$SCRCPY_REPO")
    local version=$(echo "$release_json" | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ -z "$version" ]; then
        print_error "无法获取 scrcpy 版本信息"
        exit 1
    fi
    
    print_info "最新版本: $version"
    
    # 查找 Linux 版本下载链接
    local download_url=$(echo "$release_json" | grep -o '"browser_download_url": *"[^"]*linux[^"]*\.tar\.gz"' | head -1 | cut -d'"' -f4)
    
    if [ -z "$download_url" ]; then
        print_error "未找到适合的 Linux 版本"
        exit 1
    fi
    
    # 下载
    local archive_file="$INSTALL_DIR/scrcpy.tar.gz"
    download_file "$download_url" "$archive_file"
    
    # 解压
    print_info "解压 scrcpy..."
    tar -xzf "$archive_file" -C "$SCRCPY_DIR" --strip-components=1
    rm "$archive_file"
    
    # 验证
    if [ -f "$SCRCPY_DIR/scrcpy" ] && [ -f "$SCRCPY_DIR/adb" ]; then
        chmod +x "$SCRCPY_DIR/scrcpy"
        chmod +x "$SCRCPY_DIR/adb"
        print_success "Scrcpy 安装成功"
        print_success "✓ scrcpy 已安装到: $SCRCPY_DIR/scrcpy"
        print_success "✓ adb 已安装到: $SCRCPY_DIR/adb"
    else
        print_error "Scrcpy 安装验证失败"
        exit 1
    fi
}

# 下载应用程序文件
install_app_files() {
    print_header "安装应用程序文件"
    
    # 检查本地是否有文件
    if [ -f "$INSTALL_DIR/scrcpy_gui.py" ]; then
        print_info "从本地复制文件..."
        cp "$INSTALL_DIR/scrcpy_gui.py" "$APP_DIR/"
        print_success "已复制: scrcpy_gui.py"
        
        if [ -f "$INSTALL_DIR/artocarpus_icon.png" ]; then
            cp "$INSTALL_DIR/artocarpus_icon.png" "$APP_DIR/"
            print_success "已复制: artocarpus_icon.png"
        fi
    else
        print_info "从 GitHub 下载文件..."
        
        # 下载主程序
        download_file "https://raw.githubusercontent.com/$GITHUB_REPO/main/scrcpy_gui.py" "$APP_DIR/scrcpy_gui.py"
        
        # 下载图标
        download_file "https://raw.githubusercontent.com/$GITHUB_REPO/main/artocarpus_icon.png" "$APP_DIR/artocarpus_icon.png" || true
    fi
    
    print_success "应用程序文件安装完成"
}

# 创建启动脚本
create_launcher() {
    print_header "创建启动脚本"
    
    # 创建主启动脚本
    cat > "$BIN_DIR/artocarpus" << 'EOF'
#!/bin/bash
# Artocarpus 启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"

# 设置环境变量
export PATH="$SCRIPT_DIR/scrcpy:$PATH"
export PYTHONPATH="$SCRIPT_DIR/app:$PYTHONPATH"

# 激活虚拟环境
source "$SCRIPT_DIR/venv/bin/activate"

# 启动应用
cd "$SCRIPT_DIR/app"
python scrcpy_gui.py "$@"
EOF
    
    chmod +x "$BIN_DIR/artocarpus"
    print_success "启动脚本已创建: $BIN_DIR/artocarpus"
    
    # 创建桌面快捷方式
    local desktop_file="$HOME/Desktop/${APP_NAME}.desktop"
    cat > "$desktop_file" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Scrcpy GUI v$APP_VERSION
Exec=$BIN_DIR/artocarpus
Icon=$APP_DIR/artocarpus_icon.png
Terminal=false
Categories=Utility;System;
Path=$APP_DIR
EOF
    
    chmod +x "$desktop_file"
    print_success "桌面快捷方式已创建: $desktop_file"
    
    # 创建应用程序菜单项
    local apps_dir="$HOME/.local/share/applications"
    mkdir -p "$apps_dir"
    cp "$desktop_file" "$apps_dir/artocarpus.desktop"
    print_success "应用程序菜单项已创建"
}

# 创建卸载脚本
create_uninstall_script() {
    print_info "创建卸载脚本..."
    
    cat > "$INSTALL_DIR/uninstall.sh" << 'EOF'
#!/bin/bash
# Artocarpus 卸载脚本

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}准备卸载 Artocarpus...${NC}"
echo "这将删除以下内容:"
echo "  • 桌面快捷方式"
echo "  • 应用程序菜单项"
echo "  • 所有安装文件"
echo ""
read -p "确认卸载？[y/N] " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}已取消卸载${NC}"
    exit 0
fi

# 删除桌面快捷方式
rm -f "$HOME/Desktop/Artocarpus.desktop"
echo -e "${GREEN}[✓]${NC} 已删除桌面快捷方式"

# 删除应用程序菜单项
rm -f "$HOME/.local/share/applications/artocarpus.desktop"
echo -e "${GREEN}[✓]${NC} 已删除应用程序菜单项"

# 获取安装目录
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${YELLOW}请手动删除安装目录:${NC}"
echo -e "${YELLOW}  rm -rf \"$INSTALL_DIR\"${NC}"
echo ""
echo -e "${GREEN}卸载完成！${NC}"
EOF
    
    chmod +x "$INSTALL_DIR/uninstall.sh"
    print_success "卸载脚本已创建: $INSTALL_DIR/uninstall.sh"
}

# 创建 README
create_readme() {
    cat > "$INSTALL_DIR/README.txt" << EOF
====================================
  $APP_NAME v$APP_VERSION
  绿色版 - 完全独立安装
====================================

安装位置: $INSTALL_DIR

目录结构:
  venv/       - Python 虚拟环境
  scrcpy/     - Scrcpy 和 ADB
  app/        - 应用程序文件
  bin/        - 启动脚本

使用方法:
  1. 双击桌面上的 $APP_NAME 图标
  2. 或运行: $BIN_DIR/artocarpus

卸载方法:
  运行: $INSTALL_DIR/uninstall.sh
  或直接删除整个文件夹: rm -rf "$INSTALL_DIR"

注意事项:
  • 这是绿色版安装，不会影响系统环境
  • scrcpy 和 adb 仅在此目录中有效
  • 删除文件夹即可完全卸载，无残留

====================================
EOF
    
    print_success "README 已创建"
}

# 主安装流程
main() {
    print_header "$APP_NAME v$APP_VERSION 绿色版安装"
    
    echo "安装位置: $INSTALL_DIR"
    echo ""
    echo "此安装完全独立，不会影响系统环境"
    echo "要卸载，只需删除整个文件夹"
    echo ""
    read -p "是否继续安装？[Y/n] " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "安装已取消"
        exit 0
    fi
    
    # 执行安装步骤
    check_system
    check_python
    create_directories
    create_venv
    install_python_deps
    install_scrcpy
    install_app_files
    create_launcher
    create_uninstall_script
    create_readme
    
    # 安装完成
    print_header "安装完成！"
    
    echo -e "${GREEN}${BOLD}✓ $APP_NAME 已成功安装${NC}"
    echo ""
    echo "安装位置: $INSTALL_DIR"
    echo ""
    echo "启动方式:"
    echo "  • 双击桌面上的 $APP_NAME 图标"
    echo "  • 运行命令: $BIN_DIR/artocarpus"
    echo ""
    echo "卸载方式:"
    echo "  • 运行: $INSTALL_DIR/uninstall.sh"
    echo "  • 或直接删除: rm -rf \"$INSTALL_DIR\""
    echo ""
    echo -e "${BLUE}感谢使用 $APP_NAME！${NC}"
    echo ""
}

# 运行主函数
main "$@"