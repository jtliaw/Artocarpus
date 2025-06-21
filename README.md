![artocarpus](https://github.com/user-attachments/assets/290bbf63-14cd-4c6b-92a7-b8d732462ecc)




                              
# 🌿 Artocarpus - 多设备 scrcpy 图形界面 (Multi-device GUI for scrcpy)

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-blue)](#)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)](#)

> ✨ 由 Google Gemini 与 ChatGPT 协作打造，一款专注于多设备控制的现代图形界面工具。  
> ✨ A modern GUI for scrcpy built with the help of Google Gemini and ChatGPT, focused on multi-device control.

![Peek 2025-06-20 13-37](https://github.com/user-attachments/assets/d4f3e574-36fd-49b6-81cd-20d0b8166422)



---
## ✨ 功能特性 / Features

| 功能 Feature            | 描述 Description |
|--------------------------|------------------|
| 🔌 自动连接设备           | 自动检测设备并启动连接 / Auto-connect to Android device |
| 🎨 主题与语言切换         | 支持浅色/深色主题，中/英文界面 / Light/Dark themes and multilingual UI |
| 📺 自定义分辨率与码率     | 设置分辨率与 Mbps（码率） / Custom resolution and bitrate |
| 🔲 最大化窗口启动         | scrcpy 启动时自动最大化 / Start scrcpy in maximized window |
| 🎥 录像录制支持           | 支持视频录制，输出到指定路径 / Record screen with optional encoder |
| 📷 独立截图保存           | 支持每个设备截图 / Per-device screenshot capture |
| 🌙 关闭设备屏幕           | 启动时关闭手机屏幕省电 / Turn off device screen when mirroring |
| 📁 双向文件/文件夹传输    | 支持电脑⇄手机之间互传文件或文件夹 / Transfer files & folders both ways |
| 🔤 组合键使用说明目录     | 内建 scrcpy 常用组合键图示 / Built-in key shortcut reference |
| 📱 多设备并行连接         | 同时控制多台设备 / Control multiple devices concurrently |
| 💾 设置保存与自动加载     | 记录用户配置 / Save & load user presets automatically |

---

## 📁 文件传输功能 / File Transfer (New!)

- ✅ 支持 `adb push`（电脑 → 手机）
- ✅ 支持 `adb pull`（手机 → 电脑）
- ✅ 支持文件与整个文件夹的操作
- ✅ 内建自定义路径浏览器（无需外部依赖）

---

## 🎮 快捷键说明 / Scrcpy Shortcut Directory

内建一个快捷键速查页，方便新手快速掌握操作（支持语言切换）  
Includes a dedicated shortcut panel for scrcpy hotkeys with language toggle

示例：
- `Ctrl + F`: 全屏 / Fullscreen
- `Ctrl + S`: 截屏 / Screenshot
- `Ctrl + R`: 录屏 / Start recording
- 更多快捷键请见内建目录…

---

## 🚀 使用方式 / How to Use

1. 下载 `.AppImage` 文件  
   Download the `Artocarpus-x86_64.AppImage`
2. 授予可执行权限  
   Make it executable:
   
```bash
chmod +x Artocarpus_scrcpy_gui-Vxx.AppImage
./Artocarpus_scrcpy_gui-Vxx.AppImage
```

无需安装，支持大多数基于 Debian 的 Linux 系统（如 Ubuntu、Peppermint 等）。  
No installation needed. Compatible with most Debian-based Linux distributions (Ubuntu, Peppermint, etc.)

## 🪟 Windows 支持说明 / Windows Support

🧊 除了 Linux AppImage，本项目现已支持 **Windows 平台的免安装版本**！

In addition to Linux AppImage, this project now supports a **portable Windows version (.exe)**.

### ✅ Windows 使用方法 / How to Run on Windows

1. 下载 `.zip` 压缩包并解压，或直接下载 `.exe` 文件  
   Download the `.zip` and extract, or get the `.exe` directly.

2. 双击运行 `Artocarpus.exe` 启动程序  
   Double-click `Artocarpus.exe` to launch the app.

3. 程序内已包含 `adb.exe` 和 `scrcpy.exe`，无需安装任何依赖  
   The app includes `adb.exe` and `scrcpy.exe`, no installation or setup required.

⚠️ 若出现权限问题，可尝试 **右键 → 以管理员身份运行**  
If permission issues occur, try **Right click → Run as administrator**
---

## 🛠 技术栈 / Tech Stack

- 🐍 Python 3
- 🖼 Tkinter
- 📱 ADB + scrcpy
- 🤖 Gemini + ChatGPT（AI 协作开发）

---

## 🧱 项目结构 / Project Structure

```
Artocarpus/
├── scrcpy_gui.py           # 主程序入口
├── config/                 # 配置文件夹
├── assets/                 # 图标、样式等资源
├── adb/, scrcpy/           # 内嵌的 ADB 与 scrcpy 可执行程序
├── locale/                 # 多语言文件（zh, en）
├── LICENSE                 # MIT 许可证
└── THIRD_PARTY_LICENSES.md # 第三方组件说明
```

---

## 📜 开源协议 / License

本项目基于 [MIT License](LICENSE) 开源，欢迎自由使用、修改与分发。  
This project is open-sourced under the [MIT License](LICENSE). Feel free to use, modify, and distribute it.

```
Copyright © 2025
Author: JTLIAW
```

---

## ☕ 支持与反馈 / Feedback & Support

如果你觉得本项目有帮助，欢迎点个 ⭐Star 或 Fork 支持我继续改进！  
If you find this project helpful, feel free to ⭐Star or Fork to support future development.

---

## 🪴 名称由来 / About the Name

Artocarpus 是面包树（Breadfruit Tree）的学名。  
如同面包树的果实丰富、用途多样，本项目也希望成为你控制 Android 的高效工具！🌳  
Just like the breadfruit tree (Artocarpus) provides abundant and useful fruits, this project hopes to offer versatile and rich functionality. 🌳

## License

This project is licensed under the [MIT License](./LICENSE) © 2025 JTLIAW.

It uses the following open-source components:

- [scrcpy](https://github.com/Genymobile/scrcpy) (Apache 2.0)
- [adb](https://android.googlesource.com/platform/system/core/+/master/adb/) (Apache 2.0)

See [THIRD_PARTY_LICENSES.md](./THIRD_PARTY_LICENSES.md) for details.
