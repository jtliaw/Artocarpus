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
APP_VERSION="7.1"
GITHUB_REPO="jtliaw/Artocarpus"
SCRCPY_REPO="Genymobile/scrcpy"

# scrcpy 来源（按顺序尝试，前一个成功就不再往下）：
#   1. 你自己提供的：  ./Install_Artocarpus.sh --scrcpy /路径  （文件夹 / .zip / .tar.gz）
#                      或把 scrcpy.zip 放在本脚本旁边
#   2. 本项目发布页里已测试过的固定版本（带校验码，防止下载损坏）
#   3. scrcpy 官方最新版（最后的备用；新版可能改了指令，所以不是首选）
# 注意：如果你重新上传了发布页里的 scrcpy.zip，要把下面的校验码一起更新
#       （sha256sum scrcpy.zip 可以得到新的校验码）
SCRCPY_BUNDLE_TAG="v7.1"
SCRCPY_BUNDLE_URL="https://github.com/$GITHUB_REPO/releases/download/$SCRCPY_BUNDLE_TAG/scrcpy.zip"
SCRCPY_BUNDLE_SHA256="84579e9b312b2518793a378d56eeebab59f9ce96412cc73b2f1330735be71a02"
SCRCPY_LOCAL="${SCRCPY_LOCAL:-}"

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

# 安装系统依赖（在这里集成了图形界面、剪贴板、以及完整的 Tesseract 词库）
install_system_deps() {
    print_header "安装系统依赖 (apt)"
    
    print_info "更新软件源并安装必要的系统组件（Tkinter、PIL、xclip、Tesseract 词库）..."
    sudo apt update -q
    sudo apt install -y python3-tk python3-pil python3-pil.imagetk xclip tesseract-ocr-all
    
    if [ $? -eq 0 ]; then
        print_success "系统依赖安装完成"
    else
        print_error "系统依赖安装失败，请检查网络或软件源"
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

    print_info "安装 python-xlib..."
    pip install python-xlib -q
    
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

# 安装 Python 依赖（集成了 pynput、python-xlib、ttkthemes）
install_python_deps() {
    print_header "安装 Python 依赖"
    
    print_info "激活虚拟环境..."
    source "$VENV_DIR/bin/activate"
    
    print_info "升级 pip..."
    pip install --upgrade pip -q
    
    print_info "安装 ttkthemes..."
    pip install ttkthemes -q

    print_info "安装 python-xlib..."
    pip install python-xlib -q

    print_info "安装 pynput (用于屏幕翻译的全局鼠标监听)..."
    pip install pynput -q
    
    if [ $? -eq 0 ]; then
        print_success "Python 依赖安装完成"
    else
        print_error "依赖安装失败"
        exit 1
    fi
}

# 下载文件
download_file() {
    local url=$1
    local output=$2
    
    print_info "下载: $url"
    
    if command -v curl &> /dev/null; then
        curl -fL --progress-bar "$url" -o "$output"
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


# 检查内核头文件是否与当前内核匹配（DKMS 编译模块的必需依赖）
# 缺少这一步是导致 "modprobe: FATAL: Module v4l2loopback not found" 的最常见原因
_ensure_kernel_headers() {
    local kernel_ver
    kernel_ver="$(uname -r)"

    if dpkg -l 2>/dev/null | grep -q "linux-headers-$kernel_ver"; then
        print_success "内核头文件已就绪 (linux-headers-$kernel_ver)"
        return 0
    fi

    print_warning "未找到匹配当前内核的头文件 (linux-headers-$kernel_ver)"
    print_info "尝试安装精确匹配版本..."

    if sudo apt-get install -y "linux-headers-$kernel_ver" 2>/dev/null; then
        print_success "已安装 linux-headers-$kernel_ver"
        return 0
    fi

    print_warning "精确版本包不存在，改用通用元包 linux-headers-amd64"
    if sudo apt-get install -y linux-headers-amd64; then
        print_success "已安装 linux-headers-amd64"
        print_warning "若这是首次安装该元包，可能需要重启后模块才能编译成功"
        return 0
    fi

    print_error "内核头文件安装失败，无法编译 v4l2loopback 模块"
    print_error "请手动检查网络/软件源后重试："
    print_error "  sudo apt update && sudo apt install linux-headers-amd64"
    return 1
}

# 检查并安装 v4l2loopback（摄像头模式所需）
install_v4l2loopback() {
    print_header "检查 v4l2loopback 模块"

    # 检查模块是否已加载
    if lsmod 2>/dev/null | grep -q "v4l2loopback"; then
        print_success "v4l2loopback 模块已加载，跳过安装"
        # 确保开机自动加载已配置
        _configure_v4l2_autoload
        return 0
    fi

    # 检查模块是否已安装但未加载
    if modinfo v4l2loopback &>/dev/null; then
        print_warning "v4l2loopback 已安装但未加载，正在加载模块..."
        sudo modprobe v4l2loopback exclusive_caps=1 video_nr=10 card_label="Phone Camera"
        if lsmod | grep -q "v4l2loopback"; then
            print_success "v4l2loopback 模块加载成功 (exclusive_caps=1 video_nr=10)"
        else
            print_warning "模块加载失败，摄像头功能可能无法使用"
        fi
        _configure_v4l2_autoload
        return 0
    fi

    # 需要安装
    print_info "未检测到 v4l2loopback，需要安装（摄像头模式所需）"
    print_info "需要 sudo 权限，请输入密码："

    if command -v apt &>/dev/null; then
        sudo apt-get update -q && sudo apt-get install -y v4l2loopback-dkms v4l2loopback-utils

        if [ $? -ne 0 ]; then
            print_warning "v4l2loopback-dkms 安装失败，摄像头功能可能无法使用"
            return 0
        fi

        # DKMS 需要匹配当前内核的头文件才能真正编译出模块
        # 若跳过这步，dkms status 会一直停留在 "added"，modprobe 会报 "not found"
        if ! _ensure_kernel_headers; then
            print_warning "跳过模块编译，摄像头功能暂时无法使用"
            return 0
        fi

        local module_ver
        module_ver="$(dkms status 2>/dev/null | grep '^v4l2loopback' | head -1 | sed -E 's#v4l2loopback/([0-9.]+).*#\1#')"

        if [ -z "$module_ver" ]; then
            print_error "DKMS 未识别到 v4l2loopback 源码，安装包可能不完整"
            print_error "请尝试: sudo apt install --reinstall v4l2loopback-dkms"
            return 0
        fi

        print_info "正在为当前内核编译 v4l2loopback 模块 (版本 $module_ver)..."
        if sudo dkms install "v4l2loopback/$module_ver" --force; then
            print_success "模块编译安装成功"
        else
            print_error "模块编译失败，常见原因：缺少 gcc/make，或头文件版本仍不匹配"
            print_error "可尝试: sudo apt install -y build-essential，然后重新运行本脚本"
            return 0
        fi

    elif command -v dnf &>/dev/null; then
        sudo dnf install -y v4l2loopback
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm v4l2loopback-dkms
    elif command -v zypper &>/dev/null; then
        sudo zypper install -y v4l2loopback-kmp-default
    else
        print_warning "无法识别包管理器，跳过 v4l2loopback 安装"
        print_warning "如需使用摄像头功能，请手动安装: sudo apt install v4l2loopback-dkms"
        return 0
    fi

    # 加载模块（带完整参数）
    print_info "正在加载 v4l2loopback 模块..."
    sudo modprobe v4l2loopback exclusive_caps=1 video_nr=10 card_label="Phone Camera"
    if lsmod | grep -q "v4l2loopback"; then
        print_success "v4l2loopback 安装并加载成功 (exclusive_caps=1 video_nr=10)"
    else
        print_warning "模块编译成功但加载失败，重启后可能自动加载"
    fi

    # 配置开机自动加载
    _configure_v4l2_autoload
}

# 配置 v4l2loopback 开机自动加载（含完整参数）
_configure_v4l2_autoload() {
    # 配置模块参数（让开机加载时也带参数）
    if [ -d /etc/modprobe.d ]; then
        echo 'options v4l2loopback exclusive_caps=1 video_nr=10 card_label="Phone Camera"' | \
            sudo tee /etc/modprobe.d/v4l2loopback.conf > /dev/null
        print_success "已配置模块参数: /etc/modprobe.d/v4l2loopback.conf"
    fi

    # 配置开机自动加载模块名
    if [ -d /etc/modules-load.d ]; then
        if ! grep -q "v4l2loopback" /etc/modules-load.d/v4l2loopback.conf 2>/dev/null; then
            echo "v4l2loopback" | sudo tee /etc/modules-load.d/v4l2loopback.conf > /dev/null
            print_success "已配置开机自动加载: /etc/modules-load.d/v4l2loopback.conf"
        fi
    elif [ -f /etc/modules ]; then
        if ! grep -q "v4l2loopback" /etc/modules; then
            echo "v4l2loopback" | sudo tee -a /etc/modules > /dev/null
            print_success "已配置开机自动加载: /etc/modules"
        fi
    fi
}

# ---------- scrcpy 安装（多来源）----------

# 确认这份 scrcpy 能在本机运行；不能就清空，让下一个来源接手
_verify_scrcpy() {
    if timeout 10 "$SCRCPY_DIR/scrcpy" --version > /dev/null 2>&1; then
        return 0
    fi
    print_warning "这份 scrcpy 在本机无法运行（可能是系统架构不符或缺少库），已丢弃"
    rm -rf "${SCRCPY_DIR:?}"/* 2>/dev/null
    return 1
}

# 从压缩包（.zip / .tar.gz）安装：自动找到里面同时有 scrcpy 和 adb 的那一层目录
_install_scrcpy_from_archive() {
    local archive="$1"
    local tmp="$INSTALL_DIR/.scrcpy_tmp"
    rm -rf "$tmp"; mkdir -p "$tmp"
    case "$archive" in
        *.zip)
            python3 -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$archive" "$tmp" 2>/dev/null || { print_warning "压缩包无法解压，文件可能已损坏: $archive"; rm -rf "$tmp"; return 1; } ;;
        *.tar.gz|*.tgz)
            tar -xzf "$archive" -C "$tmp" 2>/dev/null || { print_warning "压缩包无法解压，文件可能已损坏: $archive"; rm -rf "$tmp"; return 1; } ;;
        *)
            print_warning "不支持的压缩格式: $archive"; rm -rf "$tmp"; return 1 ;;
    esac
    local bin src
    bin=$(find "$tmp" -maxdepth 3 -type f -name scrcpy | head -1)
    if [ -z "$bin" ]; then
        print_warning "压缩包里没有找到 scrcpy"; rm -rf "$tmp"; return 1
    fi
    src=$(dirname "$bin")
    if [ ! -f "$src/adb" ]; then
        print_warning "压缩包里没有找到 adb"; rm -rf "$tmp"; return 1
    fi
    mkdir -p "$SCRCPY_DIR"
    cp -a "$src"/. "$SCRCPY_DIR"/
    rm -rf "$tmp"
    chmod +x "$SCRCPY_DIR/scrcpy" "$SCRCPY_DIR/adb"
    _verify_scrcpy
}

# 来源 1：你自己提供的
_scrcpy_from_local() {
    local src="$SCRCPY_LOCAL" c
    if [ -z "$src" ]; then
        for c in "$SCRIPT_DIR/scrcpy.zip" "$SCRIPT_DIR/scrcpy.tar.gz"; do
            if [ -f "$c" ]; then src="$c"; break; fi
        done
    fi
    if [ -z "$src" ]; then return 1; fi
    print_info "使用你提供的 scrcpy: $src"
    if [ -d "$src" ]; then
        if [ ! -f "$src/scrcpy" ] || [ ! -f "$src/adb" ]; then
            print_warning "该文件夹里没有同时找到 scrcpy 和 adb: $src"; return 1
        fi
        mkdir -p "$SCRCPY_DIR"
        cp -a "$src"/. "$SCRCPY_DIR"/ || return 1
        chmod +x "$SCRCPY_DIR/scrcpy" "$SCRCPY_DIR/adb"
        _verify_scrcpy
    elif [ -f "$src" ]; then
        _install_scrcpy_from_archive "$src"
    else
        print_warning "找不到你指定的路径: $src"; return 1
    fi
}

# 来源 2：本项目发布页里已测试过的固定版本
_scrcpy_from_release() {
    local tmp="$INSTALL_DIR/scrcpy_bundle.zip"
    print_info "从本项目发布页下载已测试版本的 scrcpy ($SCRCPY_BUNDLE_TAG)..."
    if ! download_file "$SCRCPY_BUNDLE_URL" "$tmp"; then
        rm -f "$tmp"; return 1
    fi
    if [ -n "$SCRCPY_BUNDLE_SHA256" ]; then
        local got
        got=$(sha256sum "$tmp" 2>/dev/null | cut -d' ' -f1)
        if [ "$got" != "$SCRCPY_BUNDLE_SHA256" ]; then
            print_warning "校验码不一致：文件可能损坏，或发布页里的 scrcpy.zip 被重新上传过而脚本里的校验码没更新"
            rm -f "$tmp"; return 1
        fi
        print_success "校验码一致"
    fi
    local rc=0
    _install_scrcpy_from_archive "$tmp" || rc=1
    rm -f "$tmp"
    return $rc
}

# 来源 3：scrcpy 官方最新版（最后的备用）
_scrcpy_from_upstream() {
    print_info "尝试从 scrcpy 官方获取最新版..."
    local release_json version download_url
    release_json=$(get_latest_release "$SCRCPY_REPO") || return 1
    version=$(echo "$release_json" | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4)
    if [ -z "$version" ]; then
        print_warning "无法获取 scrcpy 官方版本信息（网络问题，或 GitHub 接口次数限制）"; return 1
    fi
    print_info "官方最新版本: $version"
    download_url=$(echo "$release_json" | grep -o '"browser_download_url": *"[^"]*linux[^"]*\.tar\.gz"' | head -1 | cut -d'"' -f4)
    if [ -z "$download_url" ]; then
        print_warning "官方发布页里没有找到 Linux 版本的下载包"; return 1
    fi
    local archive_file="$INSTALL_DIR/scrcpy_upstream.tar.gz"
    if ! download_file "$download_url" "$archive_file"; then
        rm -f "$archive_file"; return 1
    fi
    local rc=0
    _install_scrcpy_from_archive "$archive_file" || rc=1
    rm -f "$archive_file"
    return $rc
}

# 下载并安装 scrcpy
install_scrcpy() {
    print_header "安装 Scrcpy"

    # 检查是否已安装
    if [ -f "$SCRCPY_DIR/scrcpy" ]; then
        print_warning "Scrcpy 已存在，跳过下载"
        return 0
    fi
    mkdir -p "$SCRCPY_DIR"

    local source=""
    if _scrcpy_from_local; then
        source="你提供的文件"
    elif _scrcpy_from_release; then
        source="本项目发布页 ($SCRCPY_BUNDLE_TAG)"
    elif _scrcpy_from_upstream; then
        source="scrcpy 官方最新版"
    fi

    if [ -z "$source" ]; then
        # 不再中断整个安装：界面程序照常装好，scrcpy 可以之后再补
        print_warning "没有成功安装 scrcpy，但界面程序会继续安装。之后可以用下面任意一种方式补上："
        echo "  1) 把 scrcpy.zip 放到 $SCRIPT_DIR 后重新运行本脚本"
        echo "  2) 运行: ./Install_Artocarpus.sh --scrcpy /你的/scrcpy路径   （文件夹或压缩包都可以）"
        echo "  3) 用系统自带的: sudo apt install scrcpy ，再在程序里点“浏览”选择 scrcpy 路径"
        return 0
    fi

    print_success "Scrcpy 安装成功（来源: $source）"
    print_success "✓ scrcpy 已安装到: $SCRCPY_DIR/scrcpy"
    print_success "✓ adb 已安装到: $SCRCPY_DIR/adb"
    print_info "版本: $("$SCRCPY_DIR/scrcpy" --version 2>&1 | head -1)"
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
local desktop_dir
desktop_dir=$(xdg-user-dir DESKTOP 2>/dev/null)

# 如果 xdg-user-dir 不可用或返回空，则手动检测回退
if [ -z "$desktop_dir" ] || [ ! -d "$desktop_dir" ]; then
    if [ -d "$HOME/桌面" ]; then
        desktop_dir="$HOME/桌面"
    elif [ -d "$HOME/Desktop" ]; then
        desktop_dir="$HOME/Desktop"
    else
        desktop_dir="$HOME/Desktop"
        mkdir -p "$desktop_dir"
    fi
fi

local desktop_file="$desktop_dir/${APP_NAME}.desktop"
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

# 使用 xdg-user-dir 获取当前的桌面路径
DESKTOP_DIR=$(xdg-user-dir DESKTOP)

# 如果 xdg-user-dir 没安装，回退到默认的 ~/Desktop
if [ -z "$DESKTOP_DIR" ]; then
    DESKTOP_DIR="$HOME/Desktop"
fi

# 删除桌面快捷方式
rm -f "$DESKTOP_DIR/Artocarpus.desktop"
echo -e "${GREEN}[✓]${NC} 已删除桌面快捷方式 ($DESKTOP_DIR)"

# 删除应用程序菜单项
rm -f "$HOME/.local/share/applications/artocarpus.desktop"
echo -e "${GREEN}[✓]${NC} 已删除应用程序菜单项"

# 删除用户设定
rm -f "$HOME/.scrcpy_gui_v4.json"
echo -e "${GREEN}[✓]${NC} 已删除用户设定"

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
    # 可选参数：--scrcpy 路径   指定你自己的 scrcpy（文件夹 / .zip / .tar.gz）
    while [ $# -gt 0 ]; do
        case "$1" in
            --scrcpy)   SCRCPY_LOCAL="$2"; shift 2 ;;
            --scrcpy=*) SCRCPY_LOCAL="${1#*=}"; shift ;;
            *)          shift ;;
        esac
    done

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
    
    # 执行安装步骤（已包含系统依赖和虚拟环境扩展包）
    check_system
    check_python
    install_system_deps      # 👈 自动安装 tkinter、pil、xclip、tesseract-ocr-all
    create_directories
    create_venv
    install_python_deps      # 👈 自动安装 ttkthemes、python-xlib、pynput
    install_v4l2loopback
    install_scrcpy
    install_app_files
    create_launcher
    
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
