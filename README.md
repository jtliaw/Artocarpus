![artocarpus](https://github.com/user-attachments/assets/290bbf63-14cd-4c6b-92a7-b8d732462ecc)



# 🌿 Artocarpus - A GUI for scrcpy with multi-device magic

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux--AppImage-important)](#)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)](#)

> ✨ 由 Google Gemini 与 ChatGPT 协作打造，一款专注于多设备控制的现代图形界面工具。

---

## 📦 简介

**Artocarpus** 是一个基于 Python + Tkinter 的图形化工具，旨在让你轻松通过 `scrcpy` 和 `ADB` 控制多个 Android 设备，支持自动连接、分辨率调节、视频录制与截屏等众多高级功能。

无需安装，一键运行 AppImage 文件，快速启动，直达目标。

---

## 🎯 核心功能

| 功能                 | 描述                                                                 |
|----------------------|----------------------------------------------------------------------|
| ⚡ 自动连接           | 启动时可自动连接上次设备，无需手动输入 IP                           |
| 🎨 主题切换           | 支持亮色 / 暗色 UI 风格，夜间更舒适                                 |
| 🖼 分辨率 / 码率调整  | 可视化调节 scrcpy 输出画质与 Mbps 带宽控制                          |
| 🖱 多设备连接         | 支持多台设备同时连接，并独立管理截屏与控制                         |
| 🔲 最大化窗口启动     | 可设置 App 启动时自动最大化窗口                                     |
| 📷 自动截屏           | 每个设备的截屏将分别保存并记录                                      |
| 🎥 视频录制           | 支持选择视频编码器录制手机屏幕                                     |
| 🌙 屏幕关闭模式       | 可在连接后自动关闭 Android 屏幕（节能 & 隐私）                      |

---

## 🚀 如何使用

只需下载 `.AppImage` 文件，赋予执行权限，双击运行即可：

```bash
chmod +x Artocarpus-x86_64.AppImage
./Artocarpus-x86_64.AppImage
