![artocarpus](https://github.com/user-attachments/assets/290bbf63-14cd-4c6b-92a7-b8d732462ecc)



    # 🌿 Artocarpus - 多设备 scrcpy 图形界面 (GUI)

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux--AppImage-important)](#)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)](#)

> ✨ 由 Google Gemini 与 ChatGPT 协作打造，一款专注于多设备控制的现代图形界面工具。

---

## 📦 简介

**Artocarpus** 是一款基于 Python 和 ChatGPT + Google Gemini 智能协作开发的 Linux 图形化工具，旨在简化 Android 设备的远程控制体验。它为 `scrcpy` 和 `ADB` 提供了一个强大、直观且美观的用户界面。

无需安装，直接运行 `.AppImage` 文件，即可快速启动并控制多部 Android 设备。

---

## 🎯 主要功能特色

| 功能               | 描述                                                                 |
|--------------------|----------------------------------------------------------------------|
| ⚡ 自动连接         | 启动时自动连接设备，无需输入命令                                     |
| 🎨 主题切换         | 支持亮/暗色主题，自由切换                                           |
| 📐 分辨率与码率设置 | 可调节 scrcpy 输出分辨率与 Mbps 码率                                 |
| 📱 多设备同时连接   | 支持多设备同时连接并分别控制                                         |
| 📷 自动截屏         | 每台设备独立截屏并自动保存                                           |
| 📺 最大化窗口启动   | 启动时窗口自动最大化，适合全屏操作                                   |
| 🌙 关闭手机屏幕     | 可关闭 Android 屏幕以节省电量或保护隐私                             |
| 🎥 视频录制         | 支持录像并选择编码器进行保存                                         |

---

## 🚀 使用方式

1. 下载 `Artocarpus-x86_64.AppImage`  
2. 给予执行权限  
3. 直接运行

```bash
chmod +x Artocarpus-x86_64.AppImage
./Artocarpus-x86_64.AppImage
```

无需安装，支持大多数基于 Debian 的 Linux 系统（如 Ubuntu、Peppermint 等）。

---

## 🛠 技术栈

- 🐍 Python 3
- 🖼 Tkinter
- 📱 ADB + scrcpy
- 🤖 Gemini + ChatGPT 协同开发辅助

---

## 🧱 项目结构（简略）

```
├── main.py              # 主程序入口
├── config/              # 用户设置与预设
├── assets/              # 图标、样式
├── locale/              # 多语言支持
├── scrcpy/              # scrcpy 参数集成模块
└── ...
```

---

## 📜 开源协议

本项目基于 [MIT License](LICENSE) 开源，欢迎自由使用、修改与分发，但请保留作者署名。

```
Copyright © 2025
Author: JTLIAW
```

---

## ☕ 感谢支持

如果你觉得这个项目对你有帮助，欢迎点个 ⭐Star 或 Fork 支持我继续改进！

---

## 📬 联系作者

如有建议或问题，欢迎在 GitHub 提 issue 或 PR。

---

## 🪴 项目名称由来

Artocarpus 是面包树（Breadfruit Tree）的学名。  
如同面包树的果实丰富、用途多样，本项目也希望成为你控制 Android 的高效工具 🌳                                
