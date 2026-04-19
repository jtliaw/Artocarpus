"""
Artocarpus (Scrcpy GUI)

Copyright (C) 2025 JTLIAW

Licensed under the MIT License. See the LICENSE file for details.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import sys
import threading
import re
import datetime
import json

# 确保 ttkthemes 已安装 (pip install ttkthemes)
try:
    from ttkthemes import ThemedTk
    TTKTHEMES_AVAILABLE = True
except ImportError:
    TTKTHEMES_AVAILABLE = False

class PhoneFileBrowser(tk.Toplevel):
    def __init__(self, master, adb_path, device_serial, callback_func):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.title("浏览手机文件")
        self.geometry("500x600")

        self.adb_path = adb_path
        self.device_serial = device_serial
        self.callback = callback_func
        self.current_path = "/sdcard/"

        nav_frame = ttk.Frame(self)
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        self.btn_up = ttk.Button(nav_frame, text="⬅ 返回上一级", command=self._go_up)
        self.btn_up.pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=self.current_path)
        self.entry_path = ttk.Entry(nav_frame, textvariable=self.path_var)
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry_path.bind("<Return>", lambda e: self._populate_list(self.path_var.get()))

        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        self.tree = ttk.Treeview(list_frame, columns=("name",), show="headings", selectmode="browse")
        self.tree.heading("name", text="文件名")
        self.tree.column("name", anchor="w")
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._on_item_double_click)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT)
        self._populate_list(self.current_path)

    def _populate_list(self, path):
        if path == "/":
            self.current_path = path
        else:
            self.current_path = path.rstrip('/') + '/'
        self.path_var.set(self.current_path)
        self.tree.delete(*self.tree.get_children())
        self.update_idletasks()
        cmd = [self.adb_path, "-s", self.device_serial, "shell", "ls", "-F", self.current_path]
        def target():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15, encoding='utf-8', errors='replace')
                folders = sorted([item for item in result.stdout.strip().splitlines() if item.endswith('/')])
                files = sorted([item for item in result.stdout.strip().splitlines() if not item.endswith('/')])
                self.master.after(0, lambda: self._insert_items(folders, files))
            except Exception as e:
                self.master.after(0, lambda: messagebox.showerror("错误", f"无法读取目录 {self.current_path}:\n{e}", parent=self))
        threading.Thread(target=target, daemon=True).start()

    def _insert_items(self, folders, files):
        # 去除文件夹条目的'/'后缀
        for item in folders:
            folder_name = item.rstrip('/')  # 关键修改：去除后缀
            self.tree.insert("", "end", values=(f"📁 {folder_name}",))
        for item in files:
            self.tree.insert("", "end", values=(f"📄 {item}",))

    def _on_item_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id: return
        item_text_with_icon = self.tree.item(item_id, "values")[0]
        if item_text_with_icon.startswith("📁"):
            item_text = item_text_with_icon[2:]  # 去掉图标前缀
            # 正确拼接路径（当前路径 + 文件夹名 + '/'）
            new_path = os.path.join(self.current_path, item_text) + '/'
            self._populate_list(new_path)

    def _go_up(self):
        if self.current_path in ["", "/"]: 
            return  # 已经在根目录
        
        # 使用os.path处理路径
        parent_path = os.path.dirname(self.current_path.rstrip('/'))
        if parent_path:
            parent_path += '/'  # 确保非根目录以'/'结尾
        else:
            parent_path = '/'  # 根目录
        
        self._populate_list(parent_path)

    def _on_ok(self):
        selected_path = self.current_path
        item_id = self.tree.focus()
        if item_id:
            item_text_with_icon = self.tree.item(item_id, "values")[0]
            item_text = item_text_with_icon[2:]  # 去掉图标前缀
            # 正确拼接路径
            selected_path = os.path.join(self.current_path, item_text)
        
        # 返回前去除多余的'/'（根目录除外）
        if selected_path != "/":
            selected_path = selected_path.rstrip('/')
        
        self.callback(selected_path)
        self.destroy()
        
class DeviceSelector(tk.Toplevel):
    def __init__(self, master, devices, callback):
        super().__init__(master)
        self.title("选择 USB 设备")
        self.geometry("400x300")
        self.callback = callback
        self.transient(master)
        self.grab_set()

        ttk.Label(self, text="检测到多个设备，请选择要开启 TCP/IP 的设备：", padding=10).pack()
        
        self.listbox = tk.Listbox(self, font=("Arial", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for dev in devices:
            self.listbox.insert(tk.END, dev)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.RIGHT, padx=10)
        
    def _on_ok(self):
        selection = self.listbox.curselection()
        if selection:
            serial = self.listbox.get(selection[0]).split()[0] # 提取序列号
            self.callback(serial)
            self.destroy()  

class PCFileBrowser(tk.Toplevel):
    def __init__(self, master, callback_func):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.title("浏览电脑文件")
        self.geometry("600x600")
        self.callback = callback_func
        self.current_path = os.path.expanduser("~")

        nav_frame = ttk.Frame(self)
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        self.btn_up = ttk.Button(nav_frame, text="⬅ 返回上一级", command=self._go_up)
        self.btn_up.pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=self.current_path)
        self.entry_path = ttk.Entry(nav_frame, textvariable=self.path_var)
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry_path.bind("<Return>", lambda e: self._populate_list(self.path_var.get()))

        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        self.tree = ttk.Treeview(list_frame, columns=("name",), show="headings", selectmode="browse")
        self.tree.heading("name", text="文件名")
        self.tree.column("name", anchor="w")
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._on_item_double_click)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT)
        self._populate_list(self.current_path)

    def _populate_list(self, path):
        try:
            if not os.path.isdir(path):
                messagebox.showerror("路径错误", f"路径不存在或不是一个文件夹:\n{path}", parent=self)
                return
            self.current_path = os.path.abspath(path)
            self.path_var.set(self.current_path)
            self.tree.delete(*self.tree.get_children())
            self.update_idletasks()
            items = os.listdir(path)
            folders = sorted([f for f in items if os.path.isdir(os.path.join(path, f))])
            files = sorted([f for f in items if os.path.isfile(os.path.join(path, f))])
            self._insert_items(folders, files)
        except PermissionError:
            messagebox.showwarning("权限错误", f"无法访问此文件夹:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("错误", f"读取目录时发生错误:\n{e}", parent=self)

    def _insert_items(self, folders, files):
        for folder in folders: self.tree.insert("", "end", values=(f"📁 {folder}",))
        for file in files: self.tree.insert("", "end", values=(f"📄 {file}",))

    def _on_item_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id: return
        item_text_with_icon = self.tree.item(item_id, "values")[0]
        if item_text_with_icon.startswith("📁"):
            folder_name = item_text_with_icon[2:]
            new_path = os.path.join(self.current_path, folder_name)
            self._populate_list(new_path)

    def _go_up(self):
        new_path = os.path.dirname(self.current_path)
        if new_path != self.current_path: self._populate_list(new_path)

    def _on_ok(self):
        selected_path = self.current_path
        item_id = self.tree.focus()
        if item_id:
            item_text_with_icon = self.tree.item(item_id, "values")[0]
            item_name = item_text_with_icon[2:]
            selected_path = os.path.join(self.current_path, item_name)
        self.callback(selected_path)
        self.destroy()

# --- 语言字典 ---
LANGUAGES = {
    "app_title": {"zh": "Artocarpus (Scrcpy 图形界面) v5.6", "en": "Artocarpus (Scrcpy GUI) v5.6"},
    "tab_single_device": {"zh": "精细控制", "en": "Fine Control"},
    "tab_multi_device": {"zh": "多设备预设", "en": "Multi-Device Profiles"},
    "profile_label": {"zh": "预设 P{}", "en": "Profile P{}"},
    "profile_enable_checkbox": {"zh": "启用", "en": "Enable"},
    "connect_selected_profiles_button": {"zh": "连接所有启用的预设", "en": "Connect Enabled Profiles"},
    "disconnect_all_profiles_button": {"zh": "断开所有预设连接", "en": "Disconnect All Profiles"},
    "duplicate_device_error_title": {"zh": "设备重复错误", "en": "Duplicate Device Error"},
    "duplicate_device_error_message": {"zh": "设备 '{}' 在多个启用的预设中被选中。请确保每个启用的预设都选择一个独一无二的设备。", "en": "Device '{}' is selected in multiple enabled profiles. Please ensure each enabled profile uses a unique device."},
    "error": {"zh": "错误", "en": "Error"}, "info": {"zh": "提示", "en": "Info"}, "warning": {"zh": "警告", "en": "Warning"},
    "notice_label": {"zh": "手机重启后需先通过USB启用TCPIP模式才可以使用wifi连接。", "en": "After restart the phone, you need to enable TCPIP mode via USB before you can use the wifi connection."},
    "config_frame": {"zh": "全局配置", "en": "Global Configuration"}, "scrcpy_path_label": {"zh": "Scrcpy 命令/路径:", "en": "Scrcpy Command/Path:"},
    "browse_button": {"zh": "浏览", "en": "Browse"}, "browse_scrcpy_title": {"zh": "选择 scrcpy 可执行文件", "en": "Select scrcpy Executable"},
    "scrcpy_path_set_log": {"zh": "Scrcpy路径已设置为", "en": "Scrcpy path has been set to"},
    "scrcpy_path_invalid": {"zh": "Scrcpy路径无效或无执行权限", "en": "Scrcpy path is invalid or lacks execute permission"},
    "theme_label": {"zh": "界面主题:", "en": "Theme:"}, "language_label": {"zh": "语言:", "en": "Language:"},
    "connection_frame": {"zh": "连接与设备", "en": "Connection & Devices"}, "bitrate_label": {"zh": "比特率 (Mbps):", "en": "Bitrate (Mbps):"},
    "usb_tcpip_button": {"zh": "USB启TCPIP", "en": "USB TCPIP"}, "target_ip_label": {"zh": "目标IP (建连用):", "en": "Target IP (for connection):"},
    "connect_ip_button": {"zh": "连接此IP", "en": "Connect IP"}, "enter_ip_error": {"zh": "请输入IP地址！", "en": "Please enter an IP address!"},
    "autostart_checkbox": {"zh": "启动时自动连接", "en": "Auto-connect on startup"}, "devices_label": {"zh": "可用设备:", "en": "Available Devices:"},
    "refresh_button": {"zh": "刷新列表", "en": "Refresh"}, "select_device_error": {"zh": "请选择一个设备！", "en": "Please select a device!"},
    "scrcpy_already_running_error": {"zh": "Scrcpy已在运行，请先断开。", "en": "Scrcpy is already running. Please disconnect first."},
    "scrcpy_options_frame": {"zh": "Scrcpy 控制选项", "en": "Scrcpy Control Options"}, "crop_label": {"zh": "裁剪 (W:H:X:Y):", "en": "Crop (W:H:X:Y):"},
    "crop_warning": {"zh": "如需裁剪，所有W,H,X,Y参数必须填写有效非负数字。\nW和H必须大于0。", "en": "For cropping, all W,H,X,Y parameters must be valid non-negative numbers.\nW and H must be greater than 0."},
    "turn_off_screen_checkbox": {"zh": "关闭手机屏幕", "en": "Turn off screen"}, "large_window_checkbox": {"zh": "默认最大化启动", "en": "Start maximized by default"},
    "fullscreen_checkbox": {"zh": "全屏", "en": "Fullscreen"},
    "fullscreen_exit_hint": {"zh": "全屏时浮动退出按钮", "en": "Fullscreen exit button"},
    "h265_checkbox": {"zh": "使用 H.265 编码", "en": "Use H.265 codec"}, "video_encoder_label": {"zh": "视频编码器:", "en": "Video Encoder:"},
    "encoder_default": {"zh": "自动 (Scrcpy 默认)", "en": "Auto (Scrcpy Default)"}, "custom_res_checkbox": {"zh": "自定义分辨率 (最大边):", "en": "Custom Resolution (max side):"},
    "record_checkbox": {"zh": "录制视频:", "en": "Record Video:"}, "record_path_button": {"zh": "选择保存位置", "en": "Select Save Location"},
    "record_path_label": {"zh": "保存至:", "en": "Save to:"}, "record_path_error": {"zh": "已启用录制但未指定保存路径。", "en": "Recording is enabled but no save path is specified."},
    "save_settings_button": {"zh": "保存所有设置", "en": "Save All Settings"}, "connect_device_button": {"zh": "连接选中设备", "en": "Connect Selected Device"},
    "disconnect_button": {"zh": "断开连接", "en": "Disconnect"}, "status_frame": {"zh": "状态显示栏", "en": "Status Log"},
    "settings_loaded": {"zh": "设置已加载。", "en": "Settings loaded."}, "settings_saved": {"zh": "设置已保存。", "en": "Settings saved."},
    "settings_load_fail": {"zh": "加载设置失败", "en": "Failed to load settings"}, "no_settings_file": {"zh": "未找到设置文件，使用默认设置。", "en": "Settings file not found, using defaults."},
    "theme_changed": {"zh": "界面主题已切换为", "en": "Theme changed to"}, "theme_change_fail": {"zh": "错误: 切换主题", "en": "Error: Failed to switch theme"},
    "language_changed": {"zh": "语言已切换为", "en": "Language changed to"},
    "tab_file_transfer": {"zh": "文件传输", "en": "File Transfer"},
    "pull_from_phone_frame": {"zh": "从手机复制到电脑 (adb pull)", "en": "Copy from Phone to PC (adb pull)"},
    "push_to_phone_frame": {"zh": "从电脑复制到手机 (adb push)", "en": "Copy from PC to Phone (adb push)"},
    "phone_source_path_label": {"zh": "手机源路径:", "en": "Phone Source Path:"},
    "pc_dest_path_label": {"zh": "电脑目标文件夹:", "en": "PC Destination Folder:"},
    "pc_source_path_label": {"zh": "电脑源文件/夹:", "en": "PC Source File/Folder:"},
    "phone_dest_path_label": {"zh": "手机目标路径:", "en": "Phone Destination Path:"},
    "browse_phone_button": {"zh": "浏览手机...", "en": "Browse Phone..."},
    "browse_pc_button": {"zh": "浏览电脑...", "en": "Browse PC..."},
    "path_not_selected": {"zh": "尚未选择", "en": "Not Selected"},
    "start_pull_button": {"zh": "开始复制 (手机 -> 电脑)", "en": "Start Copy (Phone -> PC)"},
    "start_push_button": {"zh": "开始复制 (电脑 -> 手机)", "en": "Start Copy (PC -> Phone)"},
    "tab_shortcuts": {"zh": "组合键用法", "en": "Shortcuts"},
    "tab_about": {"zh": "关于 & 更新", "en": "About & Update"},
    "about_app_frame": {"zh": "关于 Artocarpus", "en": "About Artocarpus"},
    "about_app_desc": {"zh": "Artocarpus 是一款 Scrcpy 图形界面工具，\n让你更方便地控制和管理 Android 设备。", "en": "Artocarpus is a GUI tool for Scrcpy,\nmaking it easier to control and manage Android devices."},
    "about_author": {"zh": "作者: JTLIAW", "en": "Author: JTLIAW"},
    "about_github_link": {"zh": "项目主页 (GitHub)", "en": "Project Homepage (GitHub)"},
    "scrcpy_version_frame": {"zh": "Scrcpy 版本管理", "en": "Scrcpy Version Manager"},
    "current_version_label": {"zh": "当前版本:", "en": "Current Version:"},
    "latest_version_label": {"zh": "最新版本:", "en": "Latest Version:"},
    "version_unknown": {"zh": "未知", "en": "Unknown"},
    "version_checking": {"zh": "检查中...", "en": "Checking..."},
    "version_up_to_date": {"zh": "✓ 已是最新版本", "en": "✓ Already up to date"},
    "version_outdated": {"zh": "⚠ 有新版本可用！", "en": "⚠ New version available!"},
    "version_check_failed": {"zh": "检查失败", "en": "Check failed"},
    "btn_check_update": {"zh": "检查更新", "en": "Check for Updates"},
    "btn_do_update": {"zh": "一键更新 Scrcpy", "en": "Update Scrcpy Now"},
    "btn_open_release": {"zh": "打开 GitHub 下载页", "en": "Open GitHub Releases"},
    "update_downloading": {"zh": "正在下载", "en": "Downloading"},
    "update_extracting": {"zh": "正在解压...", "en": "Extracting..."},
    "update_success": {"zh": "✓ Scrcpy 已更新完成！", "en": "✓ Scrcpy updated successfully!"},
    "update_failed": {"zh": "更新失败", "en": "Update failed"},
    "update_in_progress": {"zh": "正在准备更新...", "en": "Preparing update..."},
    "scrcpy_running_warning": {"zh": "Scrcpy 正在运行中，请先断开连接再更新。", "en": "Scrcpy is running. Please disconnect before updating."},
}

def get_executable_path(name):
    # Windows 需要 .exe 后缀
    if os.name == 'nt' and not name.endswith('.exe'):
        name_with_exe = name + '.exe'
    else:
        name_with_exe = name
    
    # 1. 检查打包后的路径 (PyInstaller)
    if hasattr(sys, '_MEIPASS'):
        bundled_path = os.path.join(sys._MEIPASS, name_with_exe if os.name == 'nt' else name)
        if os.path.exists(bundled_path): 
            return bundled_path
    
    # 2. 检查 AppImage 路径
    appdir = os.environ.get('APPDIR')
    if appdir:
        bundled_path = os.path.join(appdir, 'usr/bin', name)
        if os.path.exists(bundled_path) and os.access(bundled_path, os.X_OK): 
            return bundled_path
    
    # 3. 检查当前脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, name_with_exe if os.name == 'nt' else name)
    if os.path.exists(local_path):
        return local_path
    
    # 4. 检查系统 PATH（使用 shutil.which）
    import shutil
    which_result = shutil.which(name_with_exe if os.name == 'nt' else name)
    if which_result:
        return which_result
    
    # 5. 最后返回原名称（可能会失败，但会给出清晰的错误信息）
    return name_with_exe if os.name == 'nt' else name

class ScrcpyGUI:
    def __init__(self, master, initial_theme, initial_lang):
        self.master = master
        self.scrcpy_process = None
        self.multi_scrcpy_processes = {}
        self.current_language = initial_lang
        self.auto_connect_performed = False
        
        # 修改主题列表，只保留指定的主题
        if TTKTHEMES_AVAILABLE: 
            # 定义允许的主题列表
            allowed_themes = ["yaru", "ubuntu", "radiance", "clam", "breeze", "arc", 
                            "scidgreen", "scidgery", "scidmint", "scidpink", "scidpurple", "scidsand"]
            
            # 获取可用的主题并过滤
            all_themes = sorted(self.master.get_themes())
            self.available_themes = [theme for theme in all_themes if theme in allowed_themes]
            
            # 如果没有找到任何允许的主题，使用默认主题
            if not self.available_themes:
                self.available_themes = ["default"]
        else: 
            self.available_themes = ["default"]
            
        self.available_languages = ["中文 (Chinese)", "英文 (English)"]
        self.profile_widgets = []
        self.last_connected_serial = None
        self.settings_file = os.path.join(os.path.expanduser("~"), ".scrcpy_gui_v4.json")
        self.scrcpy_launched = False
        self.adb_executable_path = get_executable_path("adb")
        self.default_scrcpy_path = get_executable_path("scrcpy")
        self.custom_scrcpy_path = ""  # 存储用户自定义的scrcpy路径
        self.pull_dest_pc_path_var = tk.StringVar()
        self.push_source_pc_path_var = tk.StringVar()

        self.master.title(self._("app_title"))
        self.master.geometry("720x730")

    # 设置窗口图标
        try:
            # 使用我们已有的 get_executable_path 函数来确保打包后也能找到图标
            icon_path = get_executable_path("artocarpus_icon.png")
            if os.path.exists(icon_path):
                icon_image = tk.PhotoImage(file=icon_path)
                self.master.iconphoto(True, icon_image)
            else:
                # 如果找不到图标文件，只在日志中提示，不影响程序运行
                self.log_status("图标文件 'artocarpus_icon.png' 未找到。")
        except Exception as e:
            self.log_status(f"加载图标时出错: {e}")

        self.lbl_notice = ttk.Label(self.master, text=self._("notice_label"), foreground="red", font=("Arial", 10, "bold"), anchor="center")
        self.lbl_notice.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(5, 0))

        self.notebook = ttk.Notebook(self.master); self.notebook.pack(pady=5, padx=10, fill="both", expand=True)
        self.tab1_frame = ttk.Frame(self.notebook); self.tab1_frame.columnconfigure(0, weight=1); self.tab1_frame.rowconfigure(999, weight=1); self.tab2_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1_frame, text=self._("tab_single_device"))
        self.notebook.add(self.tab2_frame, text=self._("tab_multi_device"))
        self.tab3_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab3_frame, text=self._("tab_file_transfer"))
        self.tab4_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab4_frame, text=self._("tab_shortcuts"))
        self.tab5_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tab5_frame, text=self._("tab_about"))

        self._create_tab1_widgets()
        self._create_tab2_widgets()
        self._create_tab3_widgets()
        self._create_tab4_shortcuts()
        self._create_tab5_about()

        self.status_frame_container = ttk.Frame(self.master); self.status_frame_container.pack(pady=(0, 10), padx=10, fill="x", expand=False)
        self.status_frame = ttk.LabelFrame(self.status_frame_container, text=self._("status_frame")); self.status_frame.pack(fill="both", expand=True)
        self._create_status_log(self.status_frame)
        
        self.apply_custom_styles()
        self.load_settings()
        self.update_all_ui_texts()
        self.toggle_resolution_controls_state()
        self.toggle_recording_controls_state()
        self.refresh_device_list()
        self.master.after(1000, self.perform_startup_auto_connect)

    def _try_auto_launch_scrcpy(self, success, device_address_used):
        if success:
            self.scrcpy_process = None
            self.log_status(f"自动连接成功: {device_address_used}。尝试启动 Scrcpy。")
            self.master.after(2000, lambda: self._select_and_launch_scrcpy(device_address_used))
        else:
            self.log_status(f"自动连接失败: {device_address_used}。Scrcpy 未启动。")

    def _select_and_launch_scrcpy(self, device_to_select):
        if self.scrcpy_launched:
            self.log_status("⚠️ scrcpy 已启动，跳过重复启动")
            return

        self.scrcpy_launched = True  # 标记已启动
        # 确保我们切换到正确的页面来触发连接
        self.notebook.select(self.tab1_frame)
        self.master.update_idletasks()

        available_devices = self.combo_devices['values']
        if device_to_select in available_devices:
            self.combo_devices_var.set(device_to_select)
            self.log_status(f"自动启动: 已在列表中选中 {device_to_select}，启动 Scrcpy...")

            self.connect_selected_device()
        else:
            self.log_status(f"自动启动失败: 在设备列表中未找到 {device_to_select}。")

    def _(self, key):
        return LANGUAGES.get(key, {}).get(self.current_language, key)

    def _create_tab1_widgets(self):
        parent = self.tab1_frame; current_row=0

        self.config_frame = ttk.LabelFrame(parent, text=self._("config_frame")); self.config_frame.grid(row=current_row, column=0, columnspan=4, padx=5, pady=3, sticky="ew"); self.config_frame.grid_columnconfigure(1, weight=1); current_row+=1
        self.lbl_scrcpy_path = ttk.Label(self.config_frame, text=self._("scrcpy_path_label")); self.lbl_scrcpy_path.grid(row=0, column=0, padx=5, pady=3, sticky="w"); self.entry_scrcpy_path = ttk.Entry(self.config_frame); self.entry_scrcpy_path.grid(row=0, column=1, padx=5, pady=3, sticky="ew"); self.btn_browse_scrcpy = ttk.Button(self.config_frame, text=self._("browse_button"), command=self.browse_scrcpy_path, width=8); self.btn_browse_scrcpy.grid(row=0, column=4, padx=5, pady=3)
        self.lbl_theme = ttk.Label(self.config_frame, text=self._("theme_label")); self.lbl_theme.grid(row=1, column=0, padx=5, pady=3, sticky="w"); self.theme_var = tk.StringVar(); self.combo_theme = ttk.Combobox(self.config_frame, textvariable=self.theme_var, values=self.available_themes, state="readonly", width=15);
        if TTKTHEMES_AVAILABLE: self.combo_theme.bind("<<ComboboxSelected>>", self.change_theme)
        self.combo_theme.grid(row=1, column=1, padx=5, pady=3, sticky="w")
        self.lbl_language = ttk.Label(self.config_frame, text=self._("language_label")); self.lbl_language.grid(row=1, column=2, padx=(10, 5), pady=3, sticky="e"); self.language_var = tk.StringVar(); lang_map = {"zh": "中文 (Chinese)", "en": "英文 (English)"}; self.language_var.set(lang_map.get(self.current_language)); self.combo_language = ttk.Combobox(self.config_frame, textvariable=self.language_var, values=self.available_languages, state="readonly", width=12); self.combo_language.bind("<<ComboboxSelected>>", self.change_language); self.combo_language.grid(row=1, column=4, padx=5, pady=3, sticky="e")


        
        self.conn_params_frame = ttk.LabelFrame(parent, text=self._("connection_frame")); self.conn_params_frame.grid(row=current_row, column=0, columnspan=4, padx=5, pady=3, sticky="ew"); self.conn_params_frame.grid_columnconfigure(3, weight=1); current_row+=1
        conn_frame_row = 0; self.lbl_bitrate = ttk.Label(self.conn_params_frame, text=self._("bitrate_label")); self.lbl_bitrate.grid(row=conn_frame_row, column=0, padx=5, pady=3, sticky="w"); self.scale_bitrate_var = tk.DoubleVar(value=5); self.scale_bitrate = ttk.Scale(self.conn_params_frame, from_=1, to=20, orient=tk.HORIZONTAL, length=150, variable=self.scale_bitrate_var, command=self.update_bitrate_label_display); self.scale_bitrate.grid(row=conn_frame_row, column=1, padx=5, pady=3, sticky="w"); self.lbl_bitrate_value = ttk.Label(self.conn_params_frame, text=f"{int(self.scale_bitrate_var.get())} Mbps"); self.lbl_bitrate_value.grid(row=conn_frame_row, column=2, padx=5, pady=3, sticky="w"); self.btn_tcpip_mode = ttk.Button(self.conn_params_frame, text=self._("usb_tcpip_button"), command=self.enable_tcpip_mode, width=12); self.btn_tcpip_mode.grid(row=conn_frame_row, column=3, padx=5, pady=3, sticky="e"); conn_frame_row += 1
        self.lbl_wifi_ip = ttk.Label(self.conn_params_frame, text=self._("target_ip_label")); self.lbl_wifi_ip.grid(row=conn_frame_row, column=0, padx=5, pady=3, sticky="w"); ip_auto_frame = ttk.Frame(self.conn_params_frame); ip_auto_frame.grid(row=conn_frame_row, column=1, columnspan=2, padx=0, pady=0, sticky="ew"); self.target_ip_var = tk.StringVar(); self.entry_wifi_ip = ttk.Entry(ip_auto_frame, textvariable=self.target_ip_var, width=18); self.entry_wifi_ip.pack(side=tk.LEFT, padx=(5,2)); self.var_auto_connect_startup = tk.BooleanVar(); self.chk_auto_connect_startup = ttk.Checkbutton(ip_auto_frame, text=self._("autostart_checkbox"), variable=self.var_auto_connect_startup); self.chk_auto_connect_startup.pack(side=tk.LEFT, padx=(2,5)); self.btn_adb_connect_ip = ttk.Button(self.conn_params_frame, text=self._("connect_ip_button"), command=self.adb_connect_wifi_ip_manual, width=12); self.btn_adb_connect_ip.grid(row=conn_frame_row, column=3, padx=5, pady=3, sticky="e"); conn_frame_row += 1
        self.lbl_devices = ttk.Label(self.conn_params_frame, text=self._("devices_label")); self.lbl_devices.grid(row=conn_frame_row, column=0, padx=5, pady=3, sticky="w"); self.combo_devices_var = tk.StringVar(); self.combo_devices = ttk.Combobox(self.conn_params_frame, textvariable=self.combo_devices_var, width=35, state="readonly"); self.combo_devices.grid(row=conn_frame_row, column=1, columnspan=2, padx=5, pady=3, sticky="ew"); self.btn_refresh_devices_tab1 = ttk.Button(self.conn_params_frame, text=self._("refresh_button"), command=self.refresh_device_list, width=12); self.btn_refresh_devices_tab1.grid(row=conn_frame_row, column=3, padx=5, pady=3, sticky="e")

        self.scrcpy_ctrl_frame = ttk.LabelFrame(parent, text=self._("scrcpy_options_frame")); self.scrcpy_ctrl_frame.grid(row=current_row, column=0, columnspan=4, padx=5, pady=3, sticky="ew"); self.scrcpy_ctrl_frame.grid_columnconfigure(1, weight=1); current_row+=1
        ctrl_row = 0
        self.lbl_video_encoder = ttk.Label(self.scrcpy_ctrl_frame, text=self._("video_encoder_label")); self.lbl_video_encoder.grid(row=ctrl_row, column=0, padx=5, pady=3, sticky="w"); self.encoder_options = [self._("encoder_default"), "c2.android.avc.encoder", "OMX.google.h264.encoder"]; self.video_encoder_var = tk.StringVar(value=self.encoder_options[0]); self.combo_video_encoder = ttk.Combobox(self.scrcpy_ctrl_frame, textvariable=self.video_encoder_var, values=self.encoder_options, width=30, state="readonly"); self.combo_video_encoder.grid(row=ctrl_row, column=1, columnspan=3, padx=5, pady=3, sticky="ew"); ctrl_row += 1
        self.var_enable_recording = tk.BooleanVar(value=False); self.chk_enable_recording = ttk.Checkbutton(self.scrcpy_ctrl_frame, text=self._("record_checkbox"), variable=self.var_enable_recording, command=self.toggle_recording_controls_state); self.chk_enable_recording.grid(row=ctrl_row, column=0, padx=5, pady=3, sticky="w"); self.record_format_var = tk.StringVar(value="mp4"); self.combo_record_format = ttk.Combobox(self.scrcpy_ctrl_frame, textvariable=self.record_format_var, values=["mp4", "mkv"], width=6, state="disabled"); self.combo_record_format.grid(row=ctrl_row, column=1, padx=(5,0), pady=3, sticky="w"); self.btn_browse_record_path = ttk.Button(self.scrcpy_ctrl_frame, text=self._("record_path_button"), command=self.browse_record_save_path, state=tk.DISABLED); self.btn_browse_record_path.grid(row=ctrl_row, column=2, columnspan=2, padx=5, pady=3, sticky="ew"); ctrl_row += 1
        self.lbl_record_path_display_label = ttk.Label(self.scrcpy_ctrl_frame, text=self._("record_path_label"), state=tk.DISABLED); self.lbl_record_path_display_label.grid(row=ctrl_row, column=0, padx=5, pady=3, sticky="w"); self.entry_record_path_var = tk.StringVar(); self.lbl_record_path_display = ttk.Label(self.scrcpy_ctrl_frame, textvariable=self.entry_record_path_var, relief="sunken", width=40, state=tk.DISABLED, anchor="w", wraplength=350); self.lbl_record_path_display.grid(row=ctrl_row, column=1, columnspan=3, padx=5, pady=3, sticky="ew"); ctrl_row += 1
        self.lbl_crop = ttk.Label(self.scrcpy_ctrl_frame, text=self._("crop_label")); self.lbl_crop.grid(row=ctrl_row, column=0, padx=5, pady=3, sticky="w"); crop_inputs_frame = ttk.Frame(self.scrcpy_ctrl_frame); crop_inputs_frame.grid(row=ctrl_row, column=1, columnspan=2, padx=5, pady=3, sticky="ew"); self.entry_crop_w = ttk.Entry(crop_inputs_frame, width=5); self.entry_crop_w.pack(side=tk.LEFT, padx=(0,1)); ttk.Label(crop_inputs_frame, text=":").pack(side=tk.LEFT, padx=1); self.entry_crop_h = ttk.Entry(crop_inputs_frame, width=5); self.entry_crop_h.pack(side=tk.LEFT, padx=1); ttk.Label(crop_inputs_frame, text=":").pack(side=tk.LEFT, padx=1); self.entry_crop_x = ttk.Entry(crop_inputs_frame, width=5); self.entry_crop_x.pack(side=tk.LEFT, padx=1); ttk.Label(crop_inputs_frame, text=":").pack(side=tk.LEFT, padx=1); self.entry_crop_y = ttk.Entry(crop_inputs_frame, width=5); self.entry_crop_y.pack(side=tk.LEFT, padx=1); self.btn_save_settings = ttk.Button(self.scrcpy_ctrl_frame, text=self._("save_settings_button"), command=self.save_settings); self.btn_save_settings.grid(row=ctrl_row, column=3, padx=5, pady=3, sticky="e"); ctrl_row += 1
        self.var_custom_resolution = tk.BooleanVar(value=True); self.chk_custom_resolution = ttk.Checkbutton(self.scrcpy_ctrl_frame, text=self._("custom_res_checkbox"), variable=self.var_custom_resolution, command=self.toggle_resolution_controls_state); self.chk_custom_resolution.grid(row=ctrl_row, column=0, padx=5, pady=3, sticky="w"); self.resolution_scale_var = tk.IntVar(value=720); self.scale_resolution = ttk.Scale(self.scrcpy_ctrl_frame, from_=480, to=2560, orient=tk.HORIZONTAL, length=150, variable=self.resolution_scale_var, command=self.update_resolution_label_display, state=tk.DISABLED); self.scale_resolution.grid(row=ctrl_row, column=1, padx=5, pady=3, sticky="ew"); self.lbl_resolution_value = ttk.Label(self.scrcpy_ctrl_frame, text=f"{self.resolution_scale_var.get()}px", state=tk.DISABLED); self.lbl_resolution_value.grid(row=ctrl_row, column=2, columnspan=2, padx=5, pady=3, sticky="w"); ctrl_row += 1
        checkbox_options_frame = ttk.Frame(self.scrcpy_ctrl_frame); checkbox_options_frame.grid(row=ctrl_row, column=0, columnspan=4, padx=0, pady=0, sticky="w")
        self.var_turn_off_screen = tk.BooleanVar(); self.chk_turn_off_screen = ttk.Checkbutton(checkbox_options_frame, text=self._("turn_off_screen_checkbox"), variable=self.var_turn_off_screen); self.chk_turn_off_screen.pack(side=tk.LEFT, padx=5, pady=3)
        self.var_maximize_window = tk.BooleanVar(); self.chk_maximize_window = ttk.Checkbutton(checkbox_options_frame, text=self._("large_window_checkbox"), variable=self.var_maximize_window, command=self._on_maximize_toggled); self.chk_maximize_window.pack(side=tk.LEFT, padx=5, pady=3)
        self.var_use_h265 = tk.BooleanVar(); self.chk_use_h265 = ttk.Checkbutton(checkbox_options_frame, text=self._("h265_checkbox"), variable=self.var_use_h265); self.chk_use_h265.pack(side=tk.LEFT, padx=5, pady=3)
        self.var_fullscreen = tk.BooleanVar(); self.chk_fullscreen = ttk.Checkbutton(checkbox_options_frame, text=self._("fullscreen_checkbox"), variable=self.var_fullscreen, command=self._on_fullscreen_toggled); self.chk_fullscreen.pack(side=tk.LEFT, padx=5, pady=3)
        ctrl_row += 1
        

        action_frame = ttk.Frame(parent); action_frame.grid(row=current_row, column=0, columnspan=4, sticky="ew", padx=5, pady=5); action_frame.grid_columnconfigure(0, weight=1); action_frame.grid_columnconfigure(1, weight=1)
        self.btn_connect_selected = ttk.Button(action_frame, text=self._("connect_device_button"), command=self.connect_selected_device); self.btn_connect_selected.grid(row=0, column=0, padx=5, pady=3, sticky="ew"); self.btn_disconnect = ttk.Button(action_frame, text=self._("disconnect_button"), command=self.disconnect_scrcpy); self.btn_disconnect.grid(row=0, column=1, padx=5, pady=3, sticky="ew")

    def _create_tab2_widgets(self):
        parent = self.tab2_frame; profiles_container = ttk.Frame(parent); profiles_container.pack(pady=3, padx=5, fill="both", expand=True)
        for i in range(4):
            profile_frame = ttk.LabelFrame(profiles_container, text=self._("profile_label").format(i + 1)); profile_frame.pack(pady=3, padx=5, fill="x", expand=False)
            top_row = ttk.Frame(profile_frame); top_row.pack(fill="x", expand=True)
            enable_var = tk.BooleanVar(value=False); chk_enable = ttk.Checkbutton(top_row, text=self._("profile_enable_checkbox"), variable=enable_var); chk_enable.pack(side=tk.LEFT, padx=5, pady=3)
            lbl_device = ttk.Label(top_row, text=self._("devices_label")); lbl_device.pack(side=tk.LEFT, padx=5, pady=3)
            device_var = tk.StringVar(); combo_device = ttk.Combobox(top_row, textvariable=device_var, state="readonly", width=25); combo_device.pack(side=tk.LEFT, padx=5, pady=3, fill="x", expand=True)

            bottom_row = ttk.Frame(profile_frame); bottom_row.pack(fill="x", expand=True)
            lbl_crop = ttk.Label(bottom_row, text=self._("crop_label")); lbl_crop.pack(side=tk.LEFT, padx=5, pady=3)
            crop_entries = {}; crop_frame = ttk.Frame(bottom_row)
            crop_frame.pack(side=tk.LEFT, padx=5, pady=3)
            entry_w = ttk.Entry(crop_frame, width=5); entry_w.pack(side=tk.LEFT); crop_entries['w'] = entry_w
            ttk.Label(crop_frame, text=":").pack(side=tk.LEFT)
            entry_h = ttk.Entry(crop_frame, width=5); entry_h.pack(side=tk.LEFT); crop_entries['h'] = entry_h
            ttk.Label(crop_frame, text=":").pack(side=tk.LEFT)
            entry_x = ttk.Entry(crop_frame, width=5); entry_x.pack(side=tk.LEFT); crop_entries['x'] = entry_x
            ttk.Label(crop_frame, text=":").pack(side=tk.LEFT)
            entry_y = ttk.Entry(crop_frame, width=5); entry_y.pack(side=tk.LEFT); crop_entries['y'] = entry_y
            lbl_encoder = ttk.Label(bottom_row, text=self._("video_encoder_label")); lbl_encoder.pack(side=tk.LEFT, padx=(15, 3), pady=3)
            encoder_options = [self._("encoder_default"), "c2.android.avc.encoder", "OMX.google.h264.encoder"]
            encoder_var = tk.StringVar(value=encoder_options[0])
            combo_encoder = ttk.Combobox(bottom_row, textvariable=encoder_var, values=encoder_options, width=26, state="readonly"); combo_encoder.pack(side=tk.LEFT, padx=5, pady=3)

            self.profile_widgets.append({"frame": profile_frame, "enable_var": enable_var, "device_var": device_var, "combo_device": combo_device, "crop_entries": crop_entries, "encoder_var": encoder_var, "combo_encoder": combo_encoder, "lbl_encoder": lbl_encoder})

        action_frame = ttk.Frame(parent); action_frame.pack(pady=(3, 3), padx=5, fill="x", side="bottom")
        action_frame.columnconfigure(0, weight=1); action_frame.columnconfigure(1, weight=1); action_frame.columnconfigure(2, weight=1)
        btn_refresh_tab2 = ttk.Button(action_frame, text=self._("refresh_button"), command=self.refresh_device_list); btn_refresh_tab2.grid(row=0, column=0, padx=5, sticky="ew")
        btn_connect_multi = ttk.Button(action_frame, text=self._("connect_selected_profiles_button"), command=self.connect_multi_devices); btn_connect_multi.grid(row=0, column=1, padx=5, sticky="ew")
        btn_disconnect_multi = ttk.Button(action_frame, text=self._("disconnect_all_profiles_button"), command=self.disconnect_all_multi); btn_disconnect_multi.grid(row=0, column=2, padx=5, sticky="ew")

    def _create_status_log(self, parent_frame):
        parent_frame.grid_columnconfigure(0, weight=1); parent_frame.grid_rowconfigure(0, weight=1)
        self.txt_status_sb = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL)
        self.txt_status = tk.Text(parent_frame, height=8, relief="solid", borderwidth=1, yscrollcommand=self.txt_status_sb.set, wrap=tk.WORD, font=("Arial", 9))
        self.txt_status_sb.config(command=self.txt_status.yview); self.txt_status.grid(row=0, column=0, sticky="nsew"); self.txt_status_sb.grid(row=0, column=1, sticky="ns"); self.txt_status.config(state=tk.DISABLED)

    def _create_tab3_widgets(self):
        parent = self.tab3_frame
        parent.columnconfigure(0, weight=1)

        # 设备选择
        device_frame = ttk.Frame(parent)
        device_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.lbl_tab3_devices = ttk.Label(device_frame, text=self._("devices_label"))
        self.lbl_tab3_devices.pack(side=tk.LEFT, padx=5)
        self.combo_devices_tab3_var = tk.StringVar()
        self.combo_devices_tab3 = ttk.Combobox(device_frame, textvariable=self.combo_devices_tab3_var, state="readonly")
        self.combo_devices_tab3.pack(side=tk.LEFT, padx=5, fill="x", expand=True)

        # --- 从手机 Pull 到电脑 ---
        self.pull_frame = ttk.LabelFrame(parent, text=self._("pull_from_phone_frame"))
        self.pull_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.pull_frame.columnconfigure(1, weight=1)

        self.lbl_phone_source = ttk.Label(self.pull_frame, text=self._("phone_source_path_label"))
        self.lbl_phone_source.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_pull_source_phone = ttk.Entry(self.pull_frame)
        self.entry_pull_source_phone.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn_browse_phone_pull = ttk.Button(self.pull_frame, text=self._("browse_phone_button"), command=lambda: self._open_phone_browser(self.entry_pull_source_phone))
        self.btn_browse_phone_pull.grid(row=0, column=2, padx=5, pady=5)

        self.lbl_pc_dest = ttk.Label(self.pull_frame, text=self._("pc_dest_path_label"))
        self.lbl_pc_dest.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.pull_dest_pc_path_var = tk.StringVar(value=self._("path_not_selected"))
        ttk.Label(self.pull_frame, textvariable=self.pull_dest_pc_path_var, relief="sunken", anchor="w").grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.btn_browse_pc_pull = ttk.Button(self.pull_frame, text=self._("browse_pc_button"), command=lambda: self._open_pc_browser(self.pull_dest_pc_path_var))
        self.btn_browse_pc_pull.grid(row=1, column=2, padx=5, pady=5)

        self.btn_start_pull = ttk.Button(self.pull_frame, text=self._("start_pull_button"), command=self._execute_pull)
        self.btn_start_pull.grid(row=2, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        # --- 从电脑 Push 到手机 ---
        self.push_frame = ttk.LabelFrame(parent, text=self._("push_to_phone_frame"))
        self.push_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        self.push_frame.columnconfigure(1, weight=1)

        self.lbl_pc_source = ttk.Label(self.push_frame, text=self._("pc_source_path_label"))
        self.lbl_pc_source.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.push_source_pc_path_var = tk.StringVar(value=self._("path_not_selected"))
        ttk.Label(self.push_frame, textvariable=self.push_source_pc_path_var, relief="sunken", anchor="w").grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn_browse_pc_push = ttk.Button(self.push_frame, text=self._("browse_pc_button"), command=lambda: self._open_pc_browser(self.push_source_pc_path_var))
        self.btn_browse_pc_push.grid(row=0, column=2, padx=5, pady=5)

        self.lbl_phone_dest = ttk.Label(self.push_frame, text=self._("phone_dest_path_label"))
        self.lbl_phone_dest.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_push_dest_phone = ttk.Entry(self.push_frame)
        self.entry_push_dest_phone.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.btn_browse_phone_push = ttk.Button(self.push_frame, text=self._("browse_phone_button"), command=lambda: self._open_phone_browser(self.entry_push_dest_phone))
        self.btn_browse_phone_push.grid(row=1, column=2, padx=5, pady=5)

        self.btn_start_push = ttk.Button(self.push_frame, text=self._("start_push_button"), command=self._execute_push)
        self.btn_start_push.grid(row=2, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

    def _open_phone_browser(self, target_entry):
        serial = self.combo_devices_tab3_var.get()
        if not serial:
            messagebox.showerror(self._("error"), self._("select_device_error"), parent=self.master)
            return
        def update_path_callback(path):
            target_entry.delete(0, tk.END)
            target_entry.insert(0, path)
        browser = PhoneFileBrowser(master=self.master, adb_path=self.adb_executable_path, device_serial=serial, callback_func=update_path_callback)
        browser.wait_window()
        
    def _open_pc_browser(self, target_var):
        def update_path_callback(path):
            target_var.set(path)
        browser = PCFileBrowser(master=self.master, callback_func=update_path_callback)
        browser.wait_window()

    def _open_phone_browser(self, target_entry):
        serial = self.combo_devices_tab3_var.get()
        if not serial:
            messagebox.showerror(self._("error"), self._("select_device_error"), parent=self.master)
            return
        def update_path_callback(path):
            target_entry.delete(0, tk.END)
            target_entry.insert(0, path)
        browser = PhoneFileBrowser(master=self.master, adb_path=self.adb_executable_path, device_serial=serial, callback_func=update_path_callback)
        browser.wait_window()
        
    def _open_pc_browser(self, target_var):
        def update_path_callback(path):
            target_var.set(path)
        browser = PCFileBrowser(master=self.master, callback_func=update_path_callback)
        browser.wait_window()

    def _run_adb_transfer_thread(self, cmd, success_msg, failure_msg):
        self.log_status(f"执行: {' '.join(cmd)}")
        def target():
            try:
                # 使用 Popen 来实时读取输出
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                # 逐行读取，实时更新到状态栏
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.log_status(output.strip())
                
                # 检查最终结果
                if process.poll() == 0:
                    self.log_status(success_msg)
                else:
                    self.log_status(failure_msg)
            except Exception as e:
                self.log_status(f"执行传输时出错: {e}")

        threading.Thread(target=target, daemon=True).start()

    def _execute_pull(self):
        serial = self.combo_devices_tab3_var.get()
        phone_path = self.entry_pull_source_phone.get().strip()
        phone_path = phone_path.rstrip('*')  # 去掉可能的 *
        pc_path = self.pull_dest_pc_path_var.get()

        if not all([serial, phone_path, pc_path != self._("path_not_selected")]):
            messagebox.showerror(self._("error"), "请确保已选择设备，并已填写手机源路径和电脑目标文件夹。", parent=self.master)
            return
            
        cmd = [self.adb_executable_path, "-s", serial, "pull", phone_path, pc_path]
        self._run_adb_transfer_thread(cmd, f"成功将 {phone_path} 复制到 {pc_path}", "从手机复制失败。")

    def _execute_push(self):
        serial = self.combo_devices_tab3_var.get()
        pc_path = self.push_source_pc_path_var.get()
        phone_path = self.entry_push_dest_phone.get().strip()

        if not all([serial, phone_path, pc_path != self._("path_not_selected")]):
            messagebox.showerror(self._("error"), "请确保已选择设备，并已选择电脑源文件夹和填写手机目标路径。", parent=self.master)
            return
            
        cmd = [self.adb_executable_path, "-s", serial, "push", pc_path, phone_path]
        self._run_adb_transfer_thread(cmd, f"成功将 {pc_path} 复制到 {phone_path}", "向手机复制失败。")

    def _create_tab4_shortcuts(self):
        parent = self.tab4_frame
        
        # 创建带滚动条的Text控件
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, bd=0, highlightthickness=0, font=("Arial", 11), relief="sunken", padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 定义快捷键和说明
        shortcuts = {
    		"切换全屏模式": "Alt + f",
   		 "Toggle fullscreen mode": "Alt + f",
   		 "旋转设备屏幕": "Alt + r",
    		"Rotate device screen": "Alt + r",
   		 "将窗口调整为1:1像素匹配（去除黑边）": "Alt + g",
    		"Resize window to 1:1 pixel perfect (remove black borders)": "Alt + g",
  		  "调整窗口大小以移除黑边": "Alt + x | 双击黑边",
   		 "Resize window to remove black borders": "Alt + x | Double-click black borders",
    		"点击 HOME 键": "Alt + h | 鼠标中键",
   		 "Click HOME key": "Alt + h | Middle mouse button",
    		"点击 BACK 键": "Alt + b | 鼠标右键",
    		"Click BACK key": "Alt + b | Right mouse button",
  		  "点击 APP_SWITCH 键 (多任务切换)": "Alt + s",
   		 "Click APP_SWITCH key (multi-tasking)": "Alt + s",
  		  "点击 MENU 键": "Alt + m",
   		 "Click MENU key": "Alt + m",
   		 "音量增加": "Alt + ↑ (上箭头)",
   		 "Volume up": "Alt + ↑ (Up arrow)",
   		 "音量减小": "Alt + ↓ (下箭头)",
   		 "Volume down": "Alt + ↓ (Down arrow)",
   		 "电源键 (锁屏/亮屏)": "Alt + p",
   		 "Power button (lock/unlock screen)": "Alt + p",
   		 "关闭手机屏幕 (保持投屏)": "Alt + o",
    		"Turn off device screen (keep mirroring)": "Alt + o",
   		 "开启手机屏幕": "Alt + Shift + o",
   		 "Turn on device screen": "Alt + Shift + o",
   		 "展开通知面板": "Alt + n",
  		  "Expand notification panel": "Alt + n",
   		 "展开设置面板": "Alt + Shift + n",
   		 "Expand settings panel": "Alt + Shift + n",
    		"折叠所有面板": "Alt + Shift + s",
   		 "Collapse all panels": "Alt + Shift + s",
   		 "复制内容到电脑剪贴板": "Alt + c",
    		"Copy content to computer clipboard": "Alt + c",
    		"粘贴电脑剪贴板内容到手机": "Alt + v",
    		"Paste computer clipboard content to device": "Alt + v",
   		 "注入电脑剪贴板内容为手机按键序列": "Alt + Shift + v",
    		"Inject computer clipboard content as device key events": "Alt + Shift + v",
    		"将设备文件拖拽到窗口以安装APK": "拖放 APK",
    		"Drag device file to window to install APK": "Drag and drop APK",
   		 "将文件推送到手机 /sdcard/Download/": "拖放 非APK文件",
    		"Push file to device /sdcard/Download/": "Drag and drop non-APK file"
}

        # 定义文本样式
        text_widget.tag_configure("key", font=("Arial", 11, "bold"), foreground="#007acc")
        text_widget.tag_configure("desc", font=("Arial", 11))

        # 插入内容
        for desc, key in shortcuts.items():
            text_widget.insert(tk.END, f"  • {desc}: ", "desc")
            text_widget.insert(tk.END, f"{key}\n\n", "key")

        # 设置为只读
        text_widget.config(state=tk.DISABLED)

    def _get_scrcpy_install_dir(self):
        """
        可靠地获取 scrcpy 安装目录。
        优先使用当前 scrcpy_gui.py 文件所在目录的同级 scrcpy/ 子目录，
        这样无论 Artocarpus 文件夹改名到什么版本都能正确找到。
        如果找不到则退回到 entry_scrcpy_path 的父目录。
        """
        # 方法1: 根据本脚本位置推算（最可靠，不受保存路径影响）
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # scrcpy_gui.py 在 app/ 下，往上一级再进 scrcpy/
            candidate = os.path.join(os.path.dirname(script_dir), "scrcpy")
            if os.path.isdir(candidate):
                return candidate
            # 也可能直接在同一层
            candidate2 = os.path.join(script_dir, "scrcpy")
            if os.path.isdir(candidate2):
                return candidate2
        except Exception:
            pass
        # 方法2: 退回到 entry_scrcpy_path 的父目录
        scrcpy_exec = self.entry_scrcpy_path.get().strip()
        return os.path.dirname(scrcpy_exec) if scrcpy_exec else ""

    def _create_tab5_about(self):
        parent = self.tab5_frame
        parent.columnconfigure(0, weight=1)

        # --- 关于软件 ---
        about_frame = ttk.LabelFrame(parent, text=self._("about_app_frame"))
        about_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        about_frame.columnconfigure(0, weight=1)

        self.lbl_about_desc = ttk.Label(about_frame, text=self._("about_app_desc"), justify=tk.CENTER, anchor="center")
        self.lbl_about_desc.grid(row=0, column=0, padx=10, pady=(8, 2), sticky="ew")
        self.lbl_about_author = ttk.Label(about_frame, text=self._("about_author"), anchor="center")
        self.lbl_about_author.grid(row=1, column=0, padx=10, pady=2, sticky="ew")
        self.lbl_artocarpus_link = ttk.Label(about_frame, text=self._("about_github_link"),
                                              foreground="#0066cc", cursor="hand2", font=("Arial", 10, "underline"))
        self.lbl_artocarpus_link.grid(row=2, column=0, padx=10, pady=(2, 8))
        self.lbl_artocarpus_link.bind("<Button-1>", lambda e: self._open_url("https://github.com/jtliaw/Artocarpus"))

        # --- Scrcpy 版本管理 ---
        ver_frame = ttk.LabelFrame(parent, text=self._("scrcpy_version_frame"))
        ver_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        ver_frame.columnconfigure(1, weight=1)

        self.lbl_cur_ver_title = ttk.Label(ver_frame, text=self._("current_version_label"))
        self.lbl_cur_ver_title.grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.lbl_current_version = ttk.Label(ver_frame, text=self._("version_unknown"), font=("Arial", 10, "bold"))
        self.lbl_current_version.grid(row=0, column=1, padx=5, pady=8, sticky="w")
        self.btn_check_update = ttk.Button(ver_frame, text=self._("btn_check_update"), command=self.check_scrcpy_update, width=16)
        self.btn_check_update.grid(row=0, column=2, padx=10, pady=8, sticky="e")

        self.lbl_lat_ver_title = ttk.Label(ver_frame, text=self._("latest_version_label"))
        self.lbl_lat_ver_title.grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.lbl_latest_version = ttk.Label(ver_frame, text="—", font=("Arial", 10, "bold"))
        self.lbl_latest_version.grid(row=1, column=1, padx=5, pady=8, sticky="w")
        self.btn_do_update = ttk.Button(ver_frame, text=self._("btn_do_update"), command=self.do_scrcpy_update, width=16, state=tk.DISABLED)
        self.btn_do_update.grid(row=1, column=2, padx=10, pady=8, sticky="e")

        self.lbl_update_status = ttk.Label(ver_frame, text="", foreground="gray")
        self.lbl_update_status.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 8), sticky="w")
        self.lbl_scrcpy_release_link = ttk.Label(ver_frame, text=self._("btn_open_release"),
                                                   foreground="#0066cc", cursor="hand2", font=("Arial", 10, "underline"))
        self.lbl_scrcpy_release_link.grid(row=2, column=2, padx=10, pady=(0, 8), sticky="e")
        self.lbl_scrcpy_release_link.bind("<Button-1>", lambda e: self._open_url("https://github.com/Genymobile/scrcpy/releases/latest"))

        self.master.after(800, self.fetch_current_scrcpy_version)

    def _open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def fetch_current_scrcpy_version(self):
        def target():
            try:
                scrcpy_exec = self.entry_scrcpy_path.get().strip()
                if not scrcpy_exec or not os.path.isfile(scrcpy_exec):
                    version_str = self._("version_unknown")
                else:
                    result = subprocess.run(
                        [scrcpy_exec, "--version"],
                        capture_output=True, text=True, timeout=5,
                        encoding='utf-8', errors='replace'
                    )
                    output = (result.stdout + result.stderr).strip()
                    match = re.search(r'(\d+\.\d+[\.\d]*)', output)
                    version_str = match.group(1) if match else self._("version_unknown")
            except Exception as e:
                version_str = self._("version_unknown")
                self.log_status(f"读取 scrcpy 版本时出错: {e}")
            self.master.after(0, lambda: self.lbl_current_version.config(text=version_str))
        threading.Thread(target=target, daemon=True).start()

    def check_scrcpy_update(self):
        self.lbl_latest_version.config(text=self._("version_checking"), foreground="gray")
        self.lbl_update_status.config(text="", foreground="gray")
        self.btn_check_update.config(state=tk.DISABLED)
        self.btn_do_update.config(state=tk.DISABLED)
        self.fetch_current_scrcpy_version()
        def target():
            try:
                import urllib.request, json as _json, time
                req = urllib.request.Request(
                    "https://api.github.com/repos/Genymobile/scrcpy/releases/latest",
                    headers={"User-Agent": "Artocarpus-GUI"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = _json.loads(resp.read().decode())
                latest_tag = data.get("tag_name", "").lstrip("v")
                if not latest_tag:
                    raise ValueError("无法解析版本号")
                time.sleep(0.8)  # 等 fetch_current_scrcpy_version 完成
                current = self.lbl_current_version.cget("text")
                if current in (self._("version_unknown"), ""):
                    status_text = f"当前版本读取失败，最新版为 v{latest_tag}，可尝试手动更新"
                    status_color = "orange"; enable_update = True
                elif current == latest_tag:
                    status_text = self._("version_up_to_date")
                    status_color = "green"; enable_update = False
                else:
                    status_text = self._("version_outdated")
                    status_color = "orange"; enable_update = True
                def update_ui():
                    self.lbl_latest_version.config(text=latest_tag, foreground="black")
                    self.lbl_update_status.config(text=status_text, foreground=status_color)
                    self.btn_check_update.config(state=tk.NORMAL)
                    if enable_update:
                        self.btn_do_update.config(state=tk.NORMAL)
                self.master.after(0, update_ui)
            except Exception as e:
                def fail_ui():
                    self.lbl_latest_version.config(text=self._("version_check_failed"), foreground="red")
                    self.lbl_update_status.config(text=str(e), foreground="red")
                    self.btn_check_update.config(state=tk.NORMAL)
                self.master.after(0, fail_ui)
                self.log_status(f"检查更新失败: {e}")
        threading.Thread(target=target, daemon=True).start()

    def do_scrcpy_update(self):
        if self.scrcpy_process and self.scrcpy_process.poll() is None:
            messagebox.showwarning(self._("warning"), self._("scrcpy_running_warning"), parent=self.master)
            return
        self.btn_do_update.config(state=tk.DISABLED)
        self.btn_check_update.config(state=tk.DISABLED)
        self.lbl_update_status.config(text=self._("update_in_progress"), foreground="gray")

        def target():
            try:
                import urllib.request, json as _json, tarfile, zipfile, tempfile

                # 1. 获取 release 信息
                req = urllib.request.Request(
                    "https://api.github.com/repos/Genymobile/scrcpy/releases/latest",
                    headers={"User-Agent": "Artocarpus-GUI"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = _json.loads(resp.read().decode())
                assets = data.get("assets", [])
                latest_tag = data.get("tag_name", "").lstrip("v")

                # 2. 根据平台选择下载包
                is_windows = os.name == 'nt'
                if is_windows:
                    asset = next(
                        (a for a in assets if "win64" in a["name"].lower() and a["name"].endswith(".zip")),
                        None
                    )
                else:
                    asset = next(
                        (a for a in assets if "linux" in a["name"].lower() and a["name"].endswith(".tar.gz")),
                        None
                    )
                if not asset:
                    raise ValueError("未找到适合当前系统的下载包")
                download_url = asset["browser_download_url"]
                total_size = asset.get("size", 0)

                # 3. 确定安装目录（用脚本位置推算，不依赖保存的路径）
                scrcpy_dir = self._get_scrcpy_install_dir()
                if not scrcpy_dir or not os.path.isdir(scrcpy_dir):
                    raise ValueError(f"无法确定 scrcpy 安装目录: {scrcpy_dir}")
                self.log_status(f"scrcpy 安装目录: {scrcpy_dir}")

                # 4. 分块下载，实时显示进度
                ext = ".zip" if is_windows else ".tar.gz"
                tmp_file = os.path.join(tempfile.gettempdir(), f"scrcpy_update{ext}")
                req2 = urllib.request.Request(download_url, headers={"User-Agent": "Artocarpus-GUI"})
                downloaded = 0
                chunk_size = 65536
                with urllib.request.urlopen(req2, timeout=60) as resp2, open(tmp_file, "wb") as f:
                    while True:
                        chunk = resp2.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int(downloaded * 100 / total_size)
                            msg = f"{self._('update_downloading')} {downloaded/1048576:.1f} / {total_size/1048576:.1f} MB ({pct}%)"
                        else:
                            msg = f"{self._('update_downloading')} {downloaded/1048576:.1f} MB..."
                        self.master.after(0, lambda m=msg: self.lbl_update_status.config(text=m, foreground="gray"))

                # 5. 解压覆盖，去除顶层目录
                self.master.after(0, lambda: (
                    self.lbl_update_status.config(text=self._("update_extracting"), foreground="gray"),
                    self.log_status(self._("update_extracting"))
                ))
                if is_windows:
                    with zipfile.ZipFile(tmp_file, "r") as zf:
                        for member in zf.infolist():
                            # 去除顶层目录
                            parts = member.filename.split("/", 1)
                            if len(parts) < 2 or not parts[1]:
                                continue
                            member.filename = parts[1]
                            zf.extract(member, scrcpy_dir)
                else:
                    with tarfile.open(tmp_file, "r:gz") as tar:
                        for member in tar.getmembers():
                            parts = member.name.split("/", 1)
                            if len(parts) < 2 or not parts[1]:
                                continue
                            member.name = parts[1]
                            tar.extract(member, scrcpy_dir)
                os.remove(tmp_file)

                # 6. 确保可执行权限（Linux）
                if not is_windows:
                    for fname in ["scrcpy", "adb"]:
                        fp = os.path.join(scrcpy_dir, fname)
                        if os.path.exists(fp):
                            os.chmod(fp, 0o755)

                def success_ui():
                    self.lbl_current_version.config(text=latest_tag)
                    self.lbl_latest_version.config(text=latest_tag)
                    self.lbl_update_status.config(text=self._("update_success"), foreground="green")
                    self.btn_do_update.config(state=tk.DISABLED)
                    self.btn_check_update.config(state=tk.NORMAL)
                    self.log_status(self._("update_success"))
                self.master.after(0, success_ui)

            except Exception as e:
                err_msg = f"{self._('update_failed')}: {e}"
                def fail_ui():
                    self.lbl_update_status.config(text=err_msg, foreground="red")
                    self.btn_do_update.config(state=tk.NORMAL)
                    self.btn_check_update.config(state=tk.NORMAL)
                self.master.after(0, fail_ui)
                self.log_status(err_msg)

        threading.Thread(target=target, daemon=True).start()

    def update_all_ui_texts(self):
        self.master.title(self._("app_title")); self.notebook.tab(self.tab1_frame, text=self._("tab_single_device")); self.notebook.tab(self.tab2_frame, text=self._("tab_multi_device"))
        if self.notebook.index("end") > 2:
             self.notebook.tab(self.tab3_frame, text=self._("tab_file_transfer"))
             self.lbl_tab3_devices.config(text=self._("devices_label"))
             self.pull_frame.config(text=self._("pull_from_phone_frame"))
             self.lbl_phone_source.config(text=self._("phone_source_path_label"))
             self.lbl_pc_dest.config(text=self._("pc_dest_path_label"))
             self.btn_browse_phone_pull.config(text=self._("browse_phone_button"))
             self.btn_browse_pc_pull.config(text=self._("browse_pc_button"))
             self.btn_start_pull.config(text=self._("start_pull_button"))
             self.push_frame.config(text=self._("push_to_phone_frame"))
             self.lbl_pc_source.config(text=self._("pc_source_path_label"))
             self.lbl_phone_dest.config(text=self._("phone_dest_path_label"))
             self.btn_browse_pc_push.config(text=self._("browse_pc_button"))
             self.btn_browse_phone_push.config(text=self._("browse_phone_button"))
             self.btn_start_push.config(text=self._("start_push_button"))
        if self.notebook.index("end") > 3:
             self.notebook.tab(self.tab4_frame, text=self._("tab_shortcuts"))
        if self.notebook.index("end") > 4:
             self.notebook.tab(self.tab5_frame, text=self._("tab_about"))
             self.lbl_about_desc.config(text=self._("about_app_desc"))
             self.lbl_about_author.config(text=self._("about_author"))
             self.lbl_artocarpus_link.config(text=self._("about_github_link"))
             self.lbl_cur_ver_title.config(text=self._("current_version_label"))
             self.lbl_lat_ver_title.config(text=self._("latest_version_label"))
             self.btn_check_update.config(text=self._("btn_check_update"))
             self.btn_do_update.config(text=self._("btn_do_update"))
             self.lbl_scrcpy_release_link.config(text=self._("btn_open_release"))
        self.config_frame.config(text=self._("config_frame")); self.lbl_scrcpy_path.config(text=self._("scrcpy_path_label")); self.btn_browse_scrcpy.config(text=self._("browse_button")); self.lbl_theme.config(text=self._("theme_label")); self.lbl_language.config(text=self._("language_label"))
        self.lbl_notice.config(text=self._("notice_label")); self.conn_params_frame.config(text=self._("connection_frame")); self.lbl_bitrate.config(text=self._("bitrate_label")); self.btn_tcpip_mode.config(text=self._("usb_tcpip_button")); self.lbl_wifi_ip.config(text=self._("target_ip_label")); self.btn_adb_connect_ip.config(text=self._("connect_ip_button")); self.chk_auto_connect_startup.config(text=self._("autostart_checkbox")); self.lbl_devices.config(text=self._("devices_label")); self.btn_refresh_devices_tab1.config(text=self._("refresh_button"))
        self.scrcpy_ctrl_frame.config(text=self._("scrcpy_options_frame")); self.lbl_video_encoder.config(text=self._("video_encoder_label")); self.chk_enable_recording.config(text=self._("record_checkbox")); self.btn_browse_record_path.config(text=self._("record_path_button")); self.lbl_record_path_display_label.config(text=self._("record_path_label")); self.lbl_crop.config(text=self._("crop_label")); self.chk_turn_off_screen.config(text=self._("turn_off_screen_checkbox")); self.chk_maximize_window.config(text=self._("large_window_checkbox")); self.chk_use_h265.config(text=self._("h265_checkbox")); self.chk_custom_resolution.config(text=self._("custom_res_checkbox")); self.btn_save_settings.config(text=self._("save_settings_button")); self.chk_fullscreen.config(text=self._("fullscreen_checkbox"))
        self.btn_connect_selected.config(text=self._("connect_device_button")); self.btn_disconnect.config(text=self._("disconnect_button"))
        self.encoder_options[0] = self._("encoder_default"); self.combo_video_encoder.config(values=self.encoder_options); 
        if "Auto" in self.video_encoder_var.get() or "自动" in self.video_encoder_var.get(): self.video_encoder_var.set(self._("encoder_default"))
        for i, widgets in enumerate(self.profile_widgets):
            widgets["frame"].config(text=self._("profile_label").format(i + 1))
            widgets["frame"].winfo_children()[0].winfo_children()[0].config(text=self._("profile_enable_checkbox"))
            widgets["frame"].winfo_children()[0].winfo_children()[1].config(text=self._("devices_label"))
            widgets["frame"].winfo_children()[1].winfo_children()[0].config(text=self._("crop_label"))
            widgets["lbl_encoder"].config(text=self._("video_encoder_label"))
            new_enc_options = [self._("encoder_default"), "c2.android.avc.encoder", "OMX.google.h264.encoder"]
            widgets["combo_encoder"].config(values=new_enc_options)
            if "Auto" in widgets["encoder_var"].get() or "自动" in widgets["encoder_var"].get():
                widgets["encoder_var"].set(self._("encoder_default"))
        tab2_actions = self.tab2_frame.winfo_children()[1]; tab2_actions.winfo_children()[0].config(text=self._("refresh_button")); tab2_actions.winfo_children()[1].config(text=self._("connect_selected_profiles_button")); tab2_actions.winfo_children()[2].config(text=self._("disconnect_all_profiles_button"))
        self.status_frame.config(text=self._("status_frame"))

    def change_language(self, event=None): self.current_language = "zh" if "中文" in self.language_var.get() else "en"; self.update_all_ui_texts(); self.save_settings()
    def change_theme(self, event=None):
        if not TTKTHEMES_AVAILABLE: return
        try: self.master.set_theme(self.theme_var.get()); self.log_status(f"{self._('theme_changed')}: {self.theme_var.get()}"); self.save_settings()
        except tk.TclError: self.log_status(f"{self._('theme_change_fail')}: '{self.theme_var.get()}'")
        
    def save_settings(self):
        profile_settings = [{"crop": {k: e.get() for k, e in p["crop_entries"].items()}, "encoder": p["encoder_var"].get()} for p in self.profile_widgets]
        settings = {
            "scrcpy_path": self.entry_scrcpy_path.get().strip(),  # 保存当前scrcpy路径
            "language": self.current_language,
            "selected_theme": self.theme_var.get(),
            "auto_connect_ip": self.target_ip_var.get().strip(),
            "auto_connect_enabled": self.var_auto_connect_startup.get(),
            "maximize_window_enabled": self.var_maximize_window.get(),
            "fullscreen_enabled": self.var_fullscreen.get(),
            "video_encoder": self.video_encoder_var.get(),
            "crop_w": self.entry_crop_w.get().strip(),
            "crop_h": self.entry_crop_h.get().strip(),
            "crop_x": self.entry_crop_x.get().strip(),
            "crop_y": self.entry_crop_y.get().strip(),
            "profiles": profile_settings
        }
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            self.log_status(self._("settings_saved"))
        except Exception as e:
            self.log_status(f"保存设置失败: {e}")

    def load_settings(self):
        try:
            if not os.path.exists(self.settings_file): 
                self.log_status(self._("no_settings_file"))
                # 如果没有设置文件，使用默认路径
                self.entry_scrcpy_path.delete(0, tk.END)
                self.entry_scrcpy_path.insert(0, self.default_scrcpy_path)
                return
                
            with open(self.settings_file, 'r', encoding='utf-8') as f: 
                settings = json.load(f)
            
            # 加载scrcpy路径设置
            self.custom_scrcpy_path = settings.get("scrcpy_path", "")
            if self.custom_scrcpy_path:
                self.entry_scrcpy_path.delete(0, tk.END)
                self.entry_scrcpy_path.insert(0, self.custom_scrcpy_path)
            else:
                # 如果没有保存的自定义路径，使用默认路径
                self.entry_scrcpy_path.delete(0, tk.END)
                self.entry_scrcpy_path.insert(0, self.default_scrcpy_path)
            
            # 其他设置加载保持不变...
            self.current_language = settings.get("language", "zh")
            lang_map = {"zh": "中文 (Chinese)", "en": "英文 (English)"}
            self.language_var.set(lang_map.get(self.current_language, "中文 (Chinese)"))
            self.theme_var.set(settings.get("selected_theme", "arc"))
            self.target_ip_var.set(settings.get("auto_connect_ip", ""))
            self.var_auto_connect_startup.set(settings.get("auto_connect_enabled", False))
            self.var_maximize_window.set(settings.get("maximize_window_enabled", False))
            self.var_fullscreen.set(settings.get("fullscreen_enabled", False))
            # 恢复互斥状态
            if self.var_fullscreen.get():
                self.chk_maximize_window.config(state=tk.DISABLED)
            elif self.var_maximize_window.get():
                self.chk_fullscreen.config(state=tk.DISABLED)
            
            saved_encoder = settings.get("video_encoder", "")
            if saved_encoder and saved_encoder in self.encoder_options:
                self.video_encoder_var.set(saved_encoder)
            else:
                self.video_encoder_var.set(self.encoder_options[0])
            
            self.entry_crop_w.delete(0, tk.END)
            self.entry_crop_w.insert(0, settings.get("crop_w", ""))
            self.entry_crop_h.delete(0, tk.END)
            self.entry_crop_h.insert(0, settings.get("crop_h", ""))
            self.entry_crop_x.delete(0, tk.END)
            self.entry_crop_x.insert(0, settings.get("crop_x", ""))
            self.entry_crop_y.delete(0, tk.END)
            self.entry_crop_y.insert(0, settings.get("crop_y", ""))
            
            profile_settings = settings.get("profiles", [])
            for i, p_setting in enumerate(profile_settings):
                if i < len(self.profile_widgets):
                    for key, entry_widget in self.profile_widgets[i]["crop_entries"].items():
                        entry_widget.delete(0, tk.END)
                        entry_widget.insert(0, p_setting.get("crop", {}).get(key, ""))
                    saved_enc = p_setting.get("encoder", "")
                    enc_options = self.profile_widgets[i]["encoder_var"]
                    combo = self.profile_widgets[i]["combo_encoder"]
                    if saved_enc and saved_enc in combo["values"]:
                        enc_options.set(saved_enc)
                    else:
                        enc_options.set(combo["values"][0])
                        
            self.log_status(self._("settings_loaded"))
        except Exception as e: 
            self.log_status(f"{self._('settings_load_fail')}: {e}")

    def refresh_device_list(self):
        self.log_status(self._("refresh_button") + "...");
        try:
            result = subprocess.run([self.adb_executable_path, "devices"], capture_output=True, text=True, check=True, timeout=10)
            device_list = sorted([line.split('\t')[0] for line in result.stdout.strip().splitlines()[1:] if '\tdevice' in line])
            
            # 更新“精细控制”页面的设备列表
            self.combo_devices['values'] = device_list
            if device_list:
                self.combo_devices.current(0)
            else:
                self.combo_devices_var.set('')
            
            # 更新“多设备预设”页面的设备列表
            for profile in self.profile_widgets:
                profile['combo_device']['values'] = device_list
            
            # 【修正部分】更新“文件传输”页面的设备列表
            if hasattr(self, 'combo_devices_tab3'):
                self.combo_devices_tab3['values'] = device_list
                if device_list:
                    self.combo_devices_tab3.current(0)
                else:
                    self.combo_devices_tab3.set('')
            
            if device_list:
                self.log_status(f"找到设备: {', '.join(device_list)}")
            else:
                self.log_status("未找到已连接的ADB设备。")
        except Exception as e:
            self.log_status(f"刷新设备列表时发生错误: {e}")

    def connect_multi_devices(self):
        devices_to_launch = {}; enabled_profiles = [p for p in self.profile_widgets if p["enable_var"].get()]
        for profile in enabled_profiles:
            serial = profile["device_var"].get()
            if not serial: continue
            if serial in devices_to_launch: messagebox.showerror(self._("duplicate_device_error_title"), self._("duplicate_device_error_message").format(serial), parent=self.master); return
            crop_dict = {k: v.get().strip() for k, v in profile["crop_entries"].items()}
            devices_to_launch[serial] = {"crop": crop_dict, "encoder": profile["encoder_var"].get()}
        
        for serial, config in devices_to_launch.items():
            if serial in self.multi_scrcpy_processes: self.log_status(f"设备 {serial} 已连接，跳过。"); continue
            scrcpy_exec = self.entry_scrcpy_path.get().strip()
            if not os.path.isfile(scrcpy_exec) or not os.access(scrcpy_exec, os.X_OK): messagebox.showerror(self._("error"), f"{self._('scrcpy_path_invalid')}: '{scrcpy_exec}'", parent=self.master); return
            cmd = [scrcpy_exec, f"--serial={serial}", f"--window-title={serial}"]
            crop = config.get("crop", {}); w, h, x, y = crop.get('w'), crop.get('h'), crop.get('x'), crop.get('y')
            if all(s.isdigit() for s in [w, h, x, y]) and int(w) > 0 and int(h) > 0: cmd.append(f"--crop={w}:{h}:{x}:{y}")
            sel_enc = config.get("encoder", "")
            if sel_enc and sel_enc != self._("encoder_default"): cmd.extend(["--video-encoder", sel_enc])
            self._run_scrcpy_thread(cmd, serial, is_multi=True)

    def disconnect_all_multi(self):
        self.log_status("正在断开所有预设连接..."); serials_to_kill = list(self.multi_scrcpy_processes.keys())
        for serial in serials_to_kill:
            proc = self.multi_scrcpy_processes.pop(serial, None)
            if proc and proc.poll() is None: proc.terminate()
        if serials_to_kill: self._kill_scrcpy_fallback()
    
    def _run_scrcpy_thread(self, cmd_list, serial, is_multi=False):
        # 音频不支持时 scrcpy 输出的关键词
        AUDIO_ERROR_KEYWORDS = [
            "audio", "Audio", "AUDIO",
            "sound", "Sound",
        ]

        def _launch(cmd):
            return subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

        def target():
            proc = None
            try:
                self.log_status(f"为 {serial} 启动Scrcpy: {' '.join(cmd_list)}")
                proc = _launch(cmd_list)
                if is_multi: self.multi_scrcpy_processes[serial] = proc
                else: self.scrcpy_process = proc
                stdout, stderr = proc.communicate()

                if proc.returncode != 0:
                    # 检查是否是音频不支持导致的退出
                    combined = (stdout + stderr).lower()
                    audio_failed = any(kw.lower() in combined for kw in AUDIO_ERROR_KEYWORDS)

                    if audio_failed and "--no-audio" not in cmd_list:
                        self.log_status(f"⚠ Scrcpy ({serial}) 检测到音频不支持，自动加上 --no-audio 重试...")
                        retry_cmd = cmd_list + ["--no-audio"]
                        self.log_status(f"重试: {' '.join(retry_cmd)}")
                        proc = _launch(retry_cmd)
                        if is_multi: self.multi_scrcpy_processes[serial] = proc
                        else: self.scrcpy_process = proc
                        stdout, stderr = proc.communicate()
                        if proc.returncode != 0:
                            self.log_status(f"Scrcpy ({serial}) 重试后仍异常退出: {stderr.strip()}")
                        else:
                            self.log_status(f"Scrcpy ({serial}) 已禁用音频，会话正常结束。")
                    else:
                        self.log_status(f"Scrcpy ({serial}) 异常退出: {stderr.strip()}")
                else:
                    self.log_status(f"Scrcpy ({serial}) 会话正常结束。")

            except Exception as e:
                self.log_status(f"Scrcpy ({serial}) 启动时发生错误: {e}")
            finally:
                if is_multi and serial in self.multi_scrcpy_processes: del self.multi_scrcpy_processes[serial]
                if not is_multi and self.scrcpy_process and proc and self.scrcpy_process.pid == proc.pid: self.scrcpy_process = None

        threading.Thread(target=target, daemon=True).start()

    def log_status(self, message):
        if not hasattr(self, 'txt_status') or not self.txt_status.winfo_exists(): return
        self.txt_status.config(state=tk.NORMAL); self.txt_status.insert(tk.END, f"{message}\n"); self.txt_status.see(tk.END); self.txt_status.config(state=tk.DISABLED); print(message)
    def browse_scrcpy_path(self):
        path = filedialog.askopenfilename(title=self._("browse_scrcpy_title"), parent=self.master)
        if path: 
            self.entry_scrcpy_path.delete(0, tk.END)
            self.entry_scrcpy_path.insert(0, path)
            self.log_status(f"{self._('scrcpy_path_set_log')}: {path}")
            self.save_settings()  # 选择路径后自动保存设置
    def apply_custom_styles(self):
        try: s = ttk.Style(); s.configure("Accent.TButton", font=('Arial', 10, 'bold')); self.btn_connect_selected.config(style="Accent.TButton"); s.configure("Danger.TButton", font=('Arial', 10, 'bold')); self.btn_disconnect.config(style="Danger.TButton")
        except tk.TclError: pass
    def update_bitrate_label_display(self, value): self.lbl_bitrate_value.config(text=f"{int(float(value))} Mbps")
    def run_command_thread(self, command_list, success_message, failure_message):
        def target():
            try:
                self.log_status(f"执行: {' '.join(command_list)}"); subprocess.run(command_list, check=True, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0); self.log_status(success_message); self.master.after(0, self.refresh_device_list)
            except subprocess.CalledProcessError as e: self.log_status(f"{failure_message}\n{e.stderr.strip()}"); self.master.after(0, self.refresh_device_list)
            except Exception as e: self.log_status(f"{failure_message}: {e}"); self.master.after(0, self.refresh_device_list)
        threading.Thread(target=target, daemon=True).start()
    def enable_tcpip_mode(self):
        """点击『USB启动TCPIP』按钮后的入口"""
        try:
            # 1. 直接运行 adb devices 获取列表
            result = subprocess.run([self.adb_executable_path, "devices"], capture_output=True, text=True, check=True)
            
            # 2. 精确解析输出结果
            # adb devices 输出格式通常是:
            # List of devices attached
            # SN123456    device
            # SN789012    device
            lines = result.stdout.strip().splitlines()
            devices = []
            for line in lines[1:]: # 跳过第一行 "List of devices..."
                if "\tdevice" in line:
                    serial = line.split("\t")[0]
                    devices.append(serial)

            if not devices:
                messagebox.showwarning("提示", "未检测到任何通过 USB 连接的设备！")
                return

            if len(devices) == 1:
                # 只有一个设备，直接处理，不弹窗
                self._do_setup_tcpip(devices[0])
            else:
                # 多个设备，弹出你要求的小窗口让用户点选
                DeviceSelector(self.master, devices, self._do_setup_tcpip)

        except Exception as e:
            self.log_status(f"获取设备列表失败: {e}")

    def _do_setup_tcpip(self, serial):
        """终极排错版：排除网段地址的精准 IP 提取"""
        def task():
            self.log_status(f"正在操作设备: {serial}...")
            try:
                # 1. 开启 TCP 端口
                subprocess.run([self.adb_executable_path, "-s", serial, "tcpip", "5555"], 
                             check=True, capture_output=True, text=True)
                
                import time
                time.sleep(1) # 增加延迟，确保端口稳定

                found_ip = None
                debug_info = []

                # 定义 4 种最常用的获取 IP 的底层命令
                commands_to_try = [
                    ("路由表(ip route)", ["shell", "ip", "route"]),
                    ("网卡指定(ip addr wlan0)", ["shell", "ip", "addr", "show", "wlan0"]),
                    ("旧版指令(ifconfig wlan0)", ["shell", "ifconfig", "wlan0"]),
                    ("全局网卡(ip addr)", ["shell", "ip", "addr"]),
                ]

                # 智能匹配常见局域网 IP 段
                private_ip_pattern = re.compile(r'\b(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b')

                for name, cmd in commands_to_try:
                    res = subprocess.run([self.adb_executable_path, "-s", serial] + cmd, 
                                         capture_output=True, text=True, timeout=3)
                    
                    output = res.stdout.strip()
                    error = res.stderr.strip()
                    
                    if output:
                        # 查找所有类似局域网 IP 的字符串
                        matches = private_ip_pattern.findall(output)
                        for candidate in matches:
                            # 【核心修复】：过滤掉代表网段的 .0 和代表广播的 .255
                            if not candidate.endswith('.0') and not candidate.endswith('.255'):
                                found_ip = candidate
                                self.log_status(f"✓ 通过 [{name}] 成功抓取到真实 IP: {found_ip}")
                                break # 找到了有效 IP，跳出内层循环
                        
                        if found_ip:
                            break # 如果已经找到了，跳出外层尝试其他命令的循环
                    
                    log_text = output if output else (error if error else "无输出")
                    debug_info.append(f"[{name}] 返回: {log_text[:100].replace(chr(10), ' ')}") 

                def update_ui():
                    if found_ip:
                        self.target_ip_var.set(found_ip)
                        # self.log_status(f"✓ 成功！设备 {serial} IP: {found_ip}") # 上面已经打印了，这里可以省略或保留
                    else:
                        error_msg = "\n".join(debug_info)
                        self.log_status(f"× 依然无法获取有效 IP，手机的真实返回结果如下：\n{error_msg}")
                        messagebox.showwarning("提示", "无法自动获取真实IP。请确认手机已连上 WiFi。")
                
                self.master.after(0, update_ui)

            except Exception as e:
                self.log_status(f"操作失败: {e}")
                self.master.after(0, lambda: messagebox.showerror("错误", f"处理设备 {serial} 时出错:\n{e}"))

        threading.Thread(target=task, daemon=True).start()

    def _show_usb_device_picker(self, usb_devices):
        """弹出小窗口让用户选择要启用TCP/IP的USB设备"""
        win = tk.Toplevel(self.master)
        win.title("选择 USB 设备")
        win.geometry("380x200")
        win.resizable(False, False)
        win.transient(self.master)
        win.grab_set()

        ttk.Label(win, text="检测到多台 USB 设备，请选择要启用 TCP/IP 的设备：",
                  wraplength=340, justify=tk.LEFT).pack(padx=15, pady=(15, 8))

        selected_var = tk.StringVar()
        display_list = [f"{serial}  ({model})" for serial, model in usb_devices]
        combo = ttk.Combobox(win, textvariable=selected_var, values=display_list,
                             state="readonly", width=42)
        combo.current(0)
        combo.pack(padx=15, pady=5)

        def on_confirm():
            idx = combo.current()
            serial = usb_devices[idx][0]
            win.destroy()
            self._do_enable_tcpip(serial)

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=12)
        ttk.Button(btn_frame, text="确定", command=on_confirm, width=10).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="取消", command=win.destroy, width=10).pack(side=tk.LEFT, padx=8)

    def _do_enable_tcpip(self, serial):
        """对指定serial的USB设备启用TCP/IP并自动获取IP"""
        def target():
            # 步骤1: 启用 TCP/IP
            try:
                cmd_tcpip = [self.adb_executable_path, "-s", serial, "tcpip", "5555"]
                self.log_status(f"执行: {' '.join(cmd_tcpip)}")
                subprocess.run(cmd_tcpip, check=True, capture_output=True, text=True, timeout=15,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                self.log_status(f"TCP/IP 模式已在 {serial} 上启用，正在获取 IP...")
            except Exception as e:
                self.log_status(f"开启 TCP/IP 模式失败: {e}")
                return

            # 步骤2: 获取手机IP，依次尝试三种方式
            ip = None

            for cmd_args, pattern in [
                (["ip", "route"],            r'src\s+([\d]+\.[\d]+\.[\d]+\.[\d]+)'),
                (["ip", "addr", "show", "wlan0"], r'inet\s+([\d]+\.[\d]+\.[\d]+\.[\d]+)'),
                (["ifconfig", "wlan0"],      r'inet\s+addr:([\d]+\.[\d]+\.[\d]+\.[\d]+)'),
            ]:
                try:
                    res = subprocess.run(
                        [self.adb_executable_path, "-s", serial, "shell"] + cmd_args,
                        capture_output=True, text=True, timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    for line in res.stdout.splitlines():
                        match = re.search(pattern, line)
                        if match:
                            candidate = match.group(1)
                            if not candidate.startswith("127."):
                                ip = candidate
                                break
                    if ip:
                        break
                except Exception:
                    continue

            def update_ui():
                self.refresh_device_list()
                if ip:
                    self.target_ip_var.set(ip)
                    self.log_status(f"✓ 已自动获取手机 IP: {ip}，可直接点击「连接此IP」")
                else:
                    self.log_status("⚠ 无法自动获取 IP，请手动在「目标IP」栏输入手机 IP 地址")
            self.master.after(0, update_ui)

        threading.Thread(target=target, daemon=True).start()
    def generic_adb_connect(self, ip_address, post_connect_action_callback=None):
     if not ip_address:
         if post_connect_action_callback is None:
             messagebox.showerror(self._("error"), self._("enter_ip_error"), parent=self.master)
         return

     device_address = ip_address if ":" in ip_address else f"{ip_address}:5555"
     cmd = [self.adb_executable_path, "connect", device_address]

     def on_connect_done(success):
         self.refresh_device_list()
         if post_connect_action_callback:
             # 确保刷新完成后再执行回调
             self.master.after(200, lambda: post_connect_action_callback(success, device_address))

     # 使用一个简化的 run_command_thread 版本来处理这个特定任务
     def target():
         try:
             self.log_status(f"执行: {' '.join(cmd)}")
             subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=15)
             self.log_status(f"已请求连接到 {device_address}。")
             self.master.after(0, lambda: on_connect_done(True))
         except Exception as e:
             self.log_status(f"连接到 {device_address} 失败。")
             self.master.after(0, lambda: on_connect_done(False))

     threading.Thread(target=target, daemon=True).start()
    def adb_connect_wifi_ip_manual(self): self.generic_adb_connect(self.target_ip_var.get().strip())
    def _on_fullscreen_toggled(self):
        if self.var_fullscreen.get():
            self.var_maximize_window.set(False)
            self.chk_maximize_window.config(state=tk.DISABLED)
        else:
            self.chk_maximize_window.config(state=tk.NORMAL)

    def _on_maximize_toggled(self):
        if self.var_maximize_window.get():
            self.var_fullscreen.set(False)
            self.chk_fullscreen.config(state=tk.DISABLED)
        else:
            self.chk_fullscreen.config(state=tk.NORMAL)

    def _show_fullscreen_exit_button(self):
        """启动全屏后显示半透明浮动退出按钮，点击发送 Alt+F 退出全屏"""
        if hasattr(self, '_exit_btn_win') and self._exit_btn_win and self._exit_btn_win.winfo_exists():
            return
        win = tk.Toplevel(self.master)
        win.overrideredirect(True)       # 无边框
        win.attributes("-topmost", True) # 始终置顶
        win.attributes("-alpha", 0.55)   # 半透明
        # 定位到屏幕右上角
        sw = win.winfo_screenwidth()
        win.geometry(f"30x26+{sw - 40}+10")
        btn = tk.Button(
            win, text="✕", font=("Arial", 10, "bold"),
            bg="#cc3333", fg="white", relief="flat", cursor="hand2",
            command=self._exit_fullscreen
        )
        btn.pack(fill=tk.BOTH, expand=True)
        self._exit_btn_win = win
        # 监听scrcpy进程结束后自动关闭浮窗
        self._poll_scrcpy_for_exit_btn()

    def _poll_scrcpy_for_exit_btn(self):
        """每秒检查scrcpy是否还在运行，结束后自动销毁浮窗"""
        if hasattr(self, '_exit_btn_win') and self._exit_btn_win and self._exit_btn_win.winfo_exists():
            still_running = self.scrcpy_process and self.scrcpy_process.poll() is None
            if still_running:
                self.master.after(1000, self._poll_scrcpy_for_exit_btn)
            else:
                try:
                    self._exit_btn_win.destroy()
                except Exception:
                    pass

    def _exit_fullscreen(self):
        """向scrcpy窗口发送 Alt+F 退出全屏，并销毁浮窗"""
        try:
            if os.name == 'nt':
                # Windows: 用 pyautogui 或直接销毁（简单方式）
                import subprocess as _sp
                _sp.run(["powershell", "-Command",
                         "$wsh = New-Object -ComObject WScript.Shell; $wsh.AppActivate('scrcpy'); Start-Sleep -m 100; $wsh.SendKeys('%f')"],
                        capture_output=True)
            else:
                # Linux: 用 xdotool 发送 Alt+F 到 scrcpy 窗口
                result = subprocess.run(
                    ["xdotool", "search", "--name", "scrcpy", "key", "--clearmodifiers", "alt+f"],
                    capture_output=True, timeout=3
                )
                if result.returncode != 0:
                    # xdotool 不可用，退而终止 scrcpy 进程
                    self.disconnect_scrcpy()
        except Exception:
            # 最后手段：直接断开
            self.disconnect_scrcpy()
        try:
            if hasattr(self, '_exit_btn_win') and self._exit_btn_win:
                self._exit_btn_win.destroy()
        except Exception:
            pass

    def toggle_resolution_controls_state(self): state = tk.NORMAL if self.var_custom_resolution.get() else tk.DISABLED; self.scale_resolution.config(state=state); self.lbl_resolution_value.config(state=state)
    def update_resolution_label_display(self, event=None): self.lbl_resolution_value.config(text=f"{self.resolution_scale_var.get()}px")
    def toggle_recording_controls_state(self): state = tk.NORMAL if self.var_enable_recording.get() else tk.DISABLED; self.combo_record_format.config(state="readonly" if state == tk.NORMAL else "disabled"); self.btn_browse_record_path.config(state=state); self.lbl_record_path_display_label.config(state=state); self.lbl_record_path_display.config(state=state)
    def browse_record_save_path(self):
           fp = filedialog.asksaveasfilename(
                 title="选择视频保存位置",
                 initialfile=f"scrcpy_{datetime.datetime.now():%Y%m%d_%H%M%S}.{self.record_format_var.get()}",
                defaultextension=f".{self.record_format_var.get()}",
                parent=self.master
           )
           if fp:
                self.entry_record_path_var.set(fp)
                self.lbl_record_path_display.config(text=fp)
                self.log_status(f"录像保存路径已设置为: {fp}")

    def connect_selected_device(self):
        if self.scrcpy_process and self.scrcpy_process.poll() is None:
            self.log_status("已有 Scrcpy 正在运行，跳过本次启动。")
            return
        serial = self.combo_devices_var.get()
        if not serial: messagebox.showerror(self._("error"), self._("select_device_error"), parent=self.master); return
        scrcpy_exec = self.entry_scrcpy_path.get().strip();
        if not os.path.isfile(scrcpy_exec) or not os.access(scrcpy_exec, os.X_OK): messagebox.showerror(self._("error"), f"{self._('scrcpy_path_invalid')}: '{scrcpy_exec}'", parent=self.master); return
        cmd = [scrcpy_exec, f"-b{int(self.scale_bitrate_var.get())}M", f"--serial={serial}", f"--window-title={serial}"]
        if self.var_turn_off_screen.get(): cmd.append("-S");
        if self.var_use_h265.get(): cmd.append("--video-codec=h265")
        sel_enc = self.video_encoder_var.get();
        if sel_enc != self._("encoder_default"): cmd.extend(["--video-encoder", sel_enc])
        if self.var_maximize_window.get():
            try: cmd.extend([f"--window-width={self.master.winfo_screenwidth()}", f"--window-height={self.master.winfo_screenheight()}"])
            except tk.TclError: self.log_status("警告：无法获取屏幕尺寸。")
        if self.var_fullscreen.get():
            cmd.append("--fullscreen")
        crop_w, crop_h, crop_x, crop_y = (self.entry_crop_w.get().strip(), self.entry_crop_h.get().strip(), self.entry_crop_x.get().strip(), self.entry_crop_y.get().strip())
        if all(s.isdigit() for s in [crop_w, crop_h, crop_x, crop_y]) and all([crop_w, crop_h, crop_x, crop_y]) and int(crop_w) > 0 and int(crop_h) > 0: cmd.append(f"--crop={crop_w}:{crop_h}:{crop_x}:{crop_y}")
        elif any(s for s in [crop_w, crop_h, crop_x, crop_y]): messagebox.showwarning(self._("warning"), self._("crop_warning"), parent=self.master)
        if self.var_custom_resolution.get(): cmd.append(f"--max-size={self.resolution_scale_var.get()}")
        if self.var_enable_recording.get():
            rec_fp = self.entry_record_path_var.get();
            if rec_fp: cmd.extend(["--record", rec_fp, "--record-format", self.record_format_var.get()])
            else: messagebox.showerror(self._("error"), self._("record_path_error"), parent=self.master); return
        self.last_connected_serial = serial
        self._run_scrcpy_thread(cmd, serial, is_multi=False)
        if self.var_fullscreen.get():
            self.master.after(2000, self._show_fullscreen_exit_button)
    def disconnect_scrcpy(self):
        if self.scrcpy_process and self.scrcpy_process.poll() is None: self.scrcpy_process.terminate()
        else: self._kill_scrcpy_fallback()
        if self.last_connected_serial and ":" in self.last_connected_serial: self.run_command_thread([self.adb_executable_path, "disconnect", self.last_connected_serial], f"已断开 {self.last_connected_serial}", f"断开 {self.last_connected_serial} 失败")
        self.last_connected_serial = None
    def perform_startup_auto_connect(self):
        if self.auto_connect_performed:
            return  # ✅ 避免重复执行
        self.auto_connect_performed = True

        if self.var_auto_connect_startup.get():
            saved_ip = self.target_ip_var.get().strip();
            if saved_ip:
                self.scrcpy_process = None  # ✅ 强制清除状态（预防误判）
                self.log_status(f"启动时自动连接: {saved_ip}")
                self.generic_adb_connect(saved_ip, self._try_auto_launch_scrcpy)
    def _kill_scrcpy_fallback(self):
        cmd_name = os.path.basename(self.entry_scrcpy_path.get().strip() or "scrcpy");
        if os.name == 'nt':
            if not cmd_name.endswith(".exe"): cmd_name += ".exe";
            subprocess.run(["taskkill", "/F", "/IM", cmd_name], check=False, capture_output=True)
        else: subprocess.run(["pkill", "-f", cmd_name], check=False, capture_output=True)

if __name__ == '__main__':
    saved_theme = "arc"; saved_lang = "zh"
    settings_path = os.path.join(os.path.expanduser("~"), ".scrcpy_gui_v4.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                saved_theme = settings.get("selected_theme", "arc")
                saved_lang = settings.get("language", "zh")
        except Exception as e: print(f"启动时加载配置文件失败: {e}")
    root = None
    if TTKTHEMES_AVAILABLE:
        try: root = ThemedTk(theme=saved_theme)
        except tk.TclError: root = tk.Tk()
    else: root = tk.Tk()
    my_gui = ScrcpyGUI(root, initial_theme=saved_theme, initial_lang=saved_lang)
    import traceback

    root.mainloop()
