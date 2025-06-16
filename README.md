![artocarpus](https://github.com/user-attachments/assets/290bbf63-14cd-4c6b-92a7-b8d732462ecc)




                              
# 🌿 Artocarpus - 多设备 scrcpy 图形界面 (Multi-device GUI for scrcpy)

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux--AppImage-important)](#)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)](#)

> ✨ 由 Google Gemini 与 ChatGPT 协作打造，一款专注于多设备控制的现代图形界面工具。  
> ✨ A modern GUI for scrcpy built with the help of Google Gemini and ChatGPT, focused on multi-device control.

---

## 📦 简介 / Introduction

**Artocarpus** 是一个基于 Python 和 AI 协作开发的图形化工具，为 `scrcpy` 与 `ADB` 提供更友好的多设备控制界面。  
**Artocarpus** is a Python-based graphical tool for Android screen mirroring, offering a powerful and user-friendly interface for `scrcpy` and `ADB`.

无需安装，直接运行 `.AppImage` 即可使用。  
No installation needed – just run the `.AppImage` file directly.

---

## 🎯 功能特色 / Features

| 功能 / Feature         | 描述 / Description                                                   |
|------------------------|----------------------------------------------------------------------|
| ⚡ 自动连接             | 启动自动连接设备 / Auto-connect to device on launch                 |
| 🎨 主题切换             | 亮/暗主题支持 / Light & dark theme toggle                          |
| 📐 分辨率码率调节       | 自定义输出分辨率和码率 / Set scrcpy resolution and bitrate         |
| 📱 多设备支持           | 多设备同时连接控制 / Control multiple devices simultaneously        |
| 📷 独立截屏             | 每台设备独立截屏 / Independent screenshot for each device          |
| 📺 启动最大窗口         | 启动时全屏显示 / Start scrcpy in maximized window                  |
| 🌙 可关闭设备屏幕       | 节电与隐私模式 / Turn off device screen while mirroring             |
| 🎥 视频录制支持         | 可选择编码器录制画面 / Record screen with optional encoder          |

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

---

## 🛠 技术栈 / Tech Stack

- 🐍 Python 3
- 🖼 Tkinter
- 📱 ADB + scrcpy
- 🤖 Gemini + ChatGPT（AI 协作开发）

---

## 🧱 项目结构 / Project Structure

```
├── main.py              # 主程序入口 / Entry point
├── config/              # 用户设置与预设 / User configs
├── assets/              # 图标、样式 / Icons and themes
├── locale/              # 多语言支持 / Language files
├── scrcpy/              # scrcpy 模块封装 / scrcpy wrapper
└── ...
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
如同面包树的果实丰富、用途多样，本项目也希望成为你控制 Android 的高效工具！ 🌳

Just like the breadfruit tree (Artocarpus) provides abundant and useful fruits, this project hopes to offer versatile and rich functionality. 🌳
