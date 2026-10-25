#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云雀 AI 屏幕翻译 —— 框选屏幕 -> 截图发给云端 AI -> 显示译文
只依赖: python3-tk, python3-pil, python3-pil.imagetk, (可选) mss
服务商可随意切换: OpenAI 兼容接口 / Gemini / Claude
"""
import base64, hashlib, io, json, os, queue, re, subprocess, sys, tempfile, threading, time, webbrowser
import urllib.parse
import urllib.request, urllib.error
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageChops, ImageOps, ImageTk

try:
    import mss
except ImportError:
    mss = None

PYNPUT_ERR = ""
try:  # 可选：全局鼠标触发（左键点击翻译区域 / 右键双击 / 中键）。X11 下可用
    from pynput import mouse as pmouse
except Exception as _e1:
    pmouse, PYNPUT_ERR = None, str(_e1)
    # 在虚拟环境(venv)里运行时看不到系统用 apt 装的包：借用系统自带的 python3-pynput 再试一次
    for _d in ("/usr/lib/python3/dist-packages", "/usr/local/lib/python3/dist-packages"):
        if not os.path.isdir(_d) or _d in sys.path:
            continue
        sys.path.append(_d)  # 放在最后，不会盖掉虚拟环境里自己的包
        try:
            from pynput import mouse as pmouse
            PYNPUT_ERR = ""
            break
        except Exception as _e2:
            pmouse, PYNPUT_ERR = None, str(_e2)
        finally:
            try:
                sys.path.remove(_d)
            except ValueError:
                pass

OCR_ENV = dict(os.environ, OMP_THREAD_LIMIT="1")  # Tesseract 自带多线程，几个任务一起跑时会互相抢 CPU，反而更慢
CONF_DIR = os.path.expanduser("~/.skylark_ai")
CONF = os.path.join(CONF_DIR, "config.json")
SHOT_DIR = os.path.expanduser("~/SkylarkTranslator")  # 网页模式的截图只放这一个文件夹，且只保留最新一张

DEFAULT = {
    "active": "OpenAI",
    "source": "自动识别 / Auto detect",
    "region": None,        # 固定区域，重启后保留
    "trigger": "off",      # off / right2(右键双击) / middle(中键单击)
    "font_size": 20,
    "click_delay": 0.8,   # 左键点击翻译区域后，等多少秒再翻译（等游戏文字显示完）
    "skip_ruby": True,    # 日文：忽略汉字上方的小字（振假名）
    "inset": 6,           # 框选区域往里缩几个像素再识别，避开对话框的边线
    "theme": "black",     # 译文窗口配色：black / gray / white
    "alpha": 0.9,         # 译文窗口透明度（需要系统有窗口合成效果才生效）
    "fallback": "",       # OCR 没把握时，自动改用哪个 AI 服务商看图翻译（空 = 不使用）
    "ui_lang": "auto",    # 界面语言：auto（跟随）/ zh / en
    "ocr_speed": "normal",  # 识别速度档位：fast / normal / best
    "backup2": "",        # 备用 2、备用 3：留空 = 不设
    "backup3": "",
    "backup": "__auto__",  # AI 额度用完 / 请求太频繁时自动改用的免费 OCR 服务商（__auto__ = Google 翻译；空 = 不使用）
    "conf_gate": 85,      # OCR 可信度低于这个百分数：译文上方加警告；设了备用 AI 的话改用 AI 看图
    "float": True,         # 译文窗口悬浮不抢游戏焦点
    "target": "简体中文 / Simplified Chinese",
    "extra": "",
    "max_side": 1600,
    "providers": {
        "OpenAI": {"type": "openai", "base_url": "https://api.openai.com/v1",
                   "api_key": "", "model": "gpt-4o-mini",
                   "signup_url": "https://platform.openai.com/api-keys", "note": "付费（按用量计费）"},
        "Gemini": {"type": "gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta",
                   "api_key": "", "model": "gemini-flash-lite-latest",
                   "signup_url": "https://aistudio.google.com/app/apikey",
                   "note": "有免费额度，但每天次数不多（Flash 约几十次，Flash-Lite 多一些），以官网为准"},
        "Claude": {"type": "claude", "base_url": "https://api.anthropic.com/v1",
                   "api_key": "", "model": "claude-haiku-5-5",
                   "signup_url": "https://console.anthropic.com/settings/keys", "note": "付费（按用量计费）"},
        "通义千问 / Qwen": {"type": "openai", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 "api_key": "", "model": "qwen-vl-plus",
                 "signup_url": "https://bailian.console.aliyun.com/", "note": "新用户可能有免费额度，以官网为准"},
        "Google翻译 / Google Translate (free+OCR)": {"type": "ocr_google", "base_url": "", "api_key": "", "model": "",
                          "signup_url": "",
                          "note": "完全免费，不用注册和密钥。非官方接口，太频繁可能被临时限制。需先装 tesseract"},
        "MyMemory (free+OCR) / 免费+OCR": {"type": "ocr_mymemory", "base_url": "", "api_key": "", "model": "",
                             "signup_url": "",
                             "note": "免费不用注册。匿名约每天5000字；把邮箱填到“API密钥”栏可提高到约每天50000字"},
        "Gemini网页版 / Gemini web": {"type": "web", "base_url": "https://gemini.google.com/app", "api_key": "", "model": "",
                     "signup_url": "https://gemini.google.com/app",
                     "note": "不用API密钥：用你已登入的谷歌账号，截图自动复制，到网页粘贴"},
        "ChatGPT网页版 / ChatGPT web": {"type": "web", "base_url": "https://chatgpt.com/", "api_key": "", "model": "",
                      "signup_url": "https://chatgpt.com/",
                      "note": "不用API密钥：用你已登入的ChatGPT账号，截图自动复制，到网页粘贴"},
        "智谱GLM / Zhipu GLM": {"type": "openai", "base_url": "https://open.bigmodel.cn/api/paas/v4",
                  "api_key": "", "model": "glm-4v-flash",
                  "signup_url": "https://open.bigmodel.cn/usercenter/apikeys",
                  "note": "glm-4v-flash 通常可免费调用，以官网为准"},
    },
}


_L = [("简体中文", "Simplified Chinese"), ("繁体中文", "Traditional Chinese"), ("英语", "English"),
      ("日语", "Japanese"), ("韩语", "Korean"), ("法语", "French"), ("德语", "German"),
      ("西班牙语", "Spanish"), ("葡萄牙语", "Portuguese"), ("意大利语", "Italian"), ("俄语", "Russian"),
      ("阿拉伯语", "Arabic"), ("印地语", "Hindi"), ("泰语", "Thai"), ("越南语", "Vietnamese"),
      ("印尼语", "Indonesian"), ("马来语", "Malay"), ("菲律宾语", "Filipino"), ("土耳其语", "Turkish"),
      ("荷兰语", "Dutch"), ("波兰语", "Polish"), ("乌克兰语", "Ukrainian"), ("捷克语", "Czech"),
      ("瑞典语", "Swedish"), ("丹麦语", "Danish"), ("挪威语", "Norwegian"), ("芬兰语", "Finnish"),
      ("希腊语", "Greek"), ("希伯来语", "Hebrew"), ("匈牙利语", "Hungarian"), ("罗马尼亚语", "Romanian"),
      ("保加利亚语", "Bulgarian"), ("波斯语", "Persian"), ("孟加拉语", "Bengali"), ("乌尔都语", "Urdu"),
      ("缅甸语", "Burmese"), ("高棉语", "Khmer"), ("老挝语", "Lao"), ("蒙古语", "Mongolian"),
      ("拉丁语", "Latin")]
LANGS = ["%s / %s" % t for t in _L]
AUTO = "自动识别 / Auto detect"
_TRIG_BASE = {"不触发（关闭）": "off", "左键点击翻译区域（推荐，不会误触手机的返回/主页）": "click", "右键双击（和旧版云雀一样）": "right2", "中键单击（滚轮按下，较不易和游戏冲突）": "middle"}
THEMES = {
    "black": {"label": "黑底白字（推荐，不显眼）", "bg": "#101010", "fg": "#f0f0f0", "dim": "#8a8a8a",
              "bar": "#262626", "barfg": "#cfcfcf", "sel": "#444444"},
    "gray": {"label": "深灰底浅字", "bg": "#2e2e2e", "fg": "#ececec", "dim": "#9a9a9a",
             "bar": "#444444", "barfg": "#e0e0e0", "sel": "#5a5a5a"},
    "white": {"label": "白底黑字", "bg": "#ffffff", "fg": "#111111", "dim": "#777777",
              "bar": "#444444", "barfg": "#ffffff", "sel": "#cce0ff"},
}
_THEME_BASE = {k: v["label"] for k, v in THEMES.items()}
ALPHAS = ["100%", "90%", "80%", "70%", "60%"]
_SPEEDS_BASE = {"fast": "快速（最快，复杂画面可能漏字）", "normal": "标准（推荐）", "best": "精细（最慢，最全）"}
_FB_NONE_BASE = "不使用（只用 OCR）"
_RUBY_BASE = ("忽略（推荐，只翻大字）", "保留（连小字一起识别）")
_FLOAT_BASE = ("悬浮（不抢游戏焦点，用右键或按钮关闭）", "普通窗口（可拖动）")


# ---------------------------------------------------------------- 界面语言（中文 / English）
LANG = "zh"
EN = {
    '请求被拒绝（400）：模型可能不支持看图，或模型名称写错。': 'Request rejected (400): the model may not support images, or the model name is wrong.',
    '密钥无效（401）：请检查 API 密钥是否填对，有没有多余空格。': 'Invalid key (401): check that the API key is correct and has no extra spaces.',
    '没有权限（403）：密钥权限不足，或该地区/账号不能使用此模型。': "No permission (403): the key lacks permission, or this region/account can't use this model.",
    '找不到（404）：请检查模型名称和接口地址是否正确。': 'Not found (404): check that the model name and API address are correct.',
    '请求太频繁或额度用完（429）：稍后再试，或检查账户余额。': 'Too many requests or quota used up (429): try again later, or check your account balance.',
    '错误：%s\n\n详细信息：%s': 'Error: %s\n\nDetails: %s',
    '错误：找不到这个模型（404）。模型名可能已经下线，请点设置里的“获取模型列表”，从里面选一个。\n\n详细信息：%s': "Error: this model wasn't found (404). It may have been retired - click “Get model list” in Settings and pick one.\n\nDetails: %s",
    '错误：没有找到 tesseract 文字识别程序。请先安装：\nsudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn tesseract-ocr-chi-sim': 'Error: the tesseract OCR program was not found. Please install it first:\nsudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn tesseract-ocr-chi-sim',
    '错误：无法连接服务器，请检查网络和接口地址。\n%s': "Error: can't connect to the server. Check your network and the API address.\n%s",
    '错误：服务商返回的格式不对，请确认“接口类型”选对了（openai / gemini / claude）。': 'Error: the provider returned an unexpected format. Make sure the “API type” is correct (openai / gemini / claude).',
    '错误：%s': 'Error: %s',
    'OCR 失败：%s': 'OCR failed: %s',
    '没有安装文字识别语言包：%s\n请在终端运行：\nsudo apt install %s': 'OCR language pack not installed: %s\nRun in a terminal:\nsudo apt install %s',
    '剪切': 'Cut',
    '复制': 'Copy',
    '粘贴': 'Paste',
    '全选': 'Select all',
    '目前的区域': 'Current area',
    '拖拽框选新的区域（蓝框 = 目前的区域）    右键取消': 'Drag to select a new area (blue box = current area)    Right-click to cancel',
    '设置': 'Settings',
    '关闭': 'Close',
    '服务商': 'Provider',
    'API 密钥': 'API key',
    '接口地址': 'API address',
    '接口类型': 'API type',
    '原文语言': 'Source language',
    '模型名称': 'Model name',
    '目标语言': 'Target language',
    '额外提示': 'Extra hint',
    '译文字号': 'Result font size',
    '译文窗口': 'Result window',
    '鼠标快捷触发': 'Mouse trigger',
    '日文小字（振假名）': 'Japanese small text (furigana)',
    '点击后等待（秒）': 'Wait after click (sec)',
    '译文透明度': 'Result opacity',
    '译文配色': 'Result theme',
    'OCR没把握时改用AI看图': 'Use AI vision when OCR is unsure',
    '框选内缩（像素，避开边线）': 'Selection inset (px, avoids borders)',
    '识别速度': 'Recognition speed',
    '可信度门槛（%）': 'Confidence threshold (%)',
    'openai = 所有 OpenAI 兼容接口   web = 网页版   ocr_* = 本地OCR+在线翻译': 'openai = any OpenAI-compatible API   web = web version   ocr_* = local OCR + online translation',
    '获取密钥（注册/登入）': 'Get key (sign up / sign in)',
    '粘贴密钥': 'Paste key',
    '显示密钥': 'Show key',
    '获取模型列表': 'Get model list',
    '测试连接': 'Test connection',
    '新增服务商': 'Add provider',
    '删除当前': 'Delete current',
    '保存并使用': 'Save and use',
    '名称：': 'Name:',
    '剪贴板里没有内容。请先在网页上选中密钥并复制。': 'The clipboard is empty. Select and copy the key on the web page first.',
    '已粘贴密钥（共 %d 个字符），请点“测试连接”。': 'Key pasted (%d characters). Click “Test connection”.',
    '这个接口类型没有模型列表。': 'This API type has no model list.',
    '请先填入 API 密钥。': 'Please enter the API key first.',
    '正在获取模型列表……': 'Getting the model list...',
    '[失败] ': '[Failed] ',
    '错误：': 'Error: ',
    '没有取到模型。': 'No models returned.',
    '[成功] 共 %d 个可用模型。原来的“%s”不可用，已换成“%s”。点“保存并使用”生效。': '[OK] %d models available. The old “%s” is unavailable; switched to “%s”. Click “Save and use” to apply.',
    '[成功] 共 %d 个可用模型，已放进“模型名称”的下拉里，可以选择。': "[OK] %d models available; they're now in the “Model name” drop-down.",
    '提示': 'Info',
    '这个服务商没有预设注册链接，请到它的官网申请 API 密钥。': 'This provider has no preset sign-up link. Please get an API key from its website.',
    '网页模式不需要密钥，无需测试。先在浏览器里登入对应网站即可。': 'Web mode needs no key and nothing to test. Just sign in to the website in your browser.',
    '[失败] 这个目标语言暂不支持在线翻译，请换一个。': "[Failed] This target language isn't supported by online translation. Please choose another.",
    '测试中……': 'Testing...',
    '[成功] 翻译接口可用：Hello -> ': '[OK] Translation service works: Hello -> ',
    '请先填入 API 密钥（点“获取密钥”去申请）。': 'Please enter the API key first (click “Get key” to apply for one).',
    '[成功] 连接成功，密钥可用，模型支持看图。': '[OK] Connected. The key works and the model supports images.',
    '[成功] 原来的模型“%s”已下线（404），已自动换成“%s”，连接成功。请点“保存并使用”。': '[OK] The old model “%s” is retired (404); switched automatically to “%s” and connected. Click “Save and use”.',
    '云雀AI翻译': 'Skylark AI Translator',
    '从（原文）：': 'From (source):',
    '互换语言': 'Swap languages',
    '到（译文）：': 'To (translation):',
    '框选区域并翻译（设定固定区域）': 'Select area and translate (sets the fixed area)',
    '翻译固定区域': 'Translate fixed area',
    '显示悬浮条（全屏时用）': 'Show floating bar (for fullscreen)',
    '收起成小条': 'Collapse to mini bar',
    '关闭此面板': 'Close this panel',
    '就绪': 'Ready',
    '框选': 'Select',
    '翻译': 'Translate',
    '展开': 'Expand',
    '自动识别': 'Auto detect',
    '原文语言现在是“自动识别”，没法互换。\n请先在设置里选好具体的原文语言。': "The source language is “Auto detect”, so it can't be swapped.\nPlease choose a specific source language in Settings first.",
    '语言方向已改为：%s\n（再按一次“互换”会换回来）': 'Language direction changed to: %s\n(Press “Swap” again to switch back)',
    ' 移动 ': ' Move ',
    '收起': 'Collapse',
    '互换': 'Swap',
    '看区域': 'Show area',
    '译文': 'Result',
    ' 翻译 ': ' Translate ',
    '还没有选择区域。请先点“框选”。': 'No area selected yet. Click “Select” first.',
    '请先点“框选”，选好对话框的位置。': 'Click “Select” first and choose the dialog box position.',
    '还没有填写 API 密钥。\n请点主窗口的“设置”，填入当前服务商的密钥后保存。': 'No API key entered yet.\nClick “Settings” in the main window, enter the key for the current provider, and save.',
    '翻译中……': 'Translating...',
    '请求中…': 'Requesting...',
    '鼠标触发需要 pynput': 'Mouse trigger needs pynput',
    '需要安装 pynput': 'pynput required',
    '鼠标触发需要 pynput（仅支持 X11）。\n\n程序现在用的 Python 是：\n%s\n\n请在终端运行这一条（装到程序自己用的 Python 里）：\n%s -m pip install pynput\n\n装完重新启动程序。\n\n导入失败的原因：%s': "The mouse trigger needs pynput (X11 only).\n\nThe Python used by the program is:\n%s\n\nRun this in a terminal (installs into the program's own Python):\n%s -m pip install pynput\n\nRestart the program afterwards.\n\nWhy the import failed: %s",
    '未知': 'unknown',
    '识别并翻译中……': 'Recognizing and translating...',
    '这个目标语言暂不支持在线翻译，请换一个。': "This target language isn't supported by online translation. Please choose another.",
    '（文字识别没把握，已自动改用 AI 看图：%s）\n\n%s': '(Text recognition was unsure; switched to AI vision automatically: %s)\n\n%s',
    '\n\n（备用的 AI 看图也失败了：%s）': '\n\n(The backup AI vision also failed: %s)',
    '\n\n提示：还没装日文识别包。日文游戏请运行 sudo apt install tesseract-ocr-jpn，并在设置里把“原文语言”选成日语。': "\n\nTip: the Japanese OCR language pack isn't installed. For Japanese games run sudo apt install tesseract-ocr-jpn, then set “Source language” to Japanese in Settings.",
    '（未识别到文字）': '(No text recognized)',
    '翻译 %.1f 秒': 'translation %.1f s',
    '翻译用了记忆，没重新请求': 'translation reused from memory (no new request)',
    '识别 %.1f 秒，%s': 'recognition %.1f s, %s',
    '\n\n（自动识别判断为：%s。不准的话，请在设置里直接指定原文语言）': "\n\n(Auto detect judged the language as: %s. If that's wrong, set the source language directly in Settings.)",
    '\n\n注意：这次识别的可信度很低（%d%%），译文很可能不准。请点“看区域”确认只框住了文字，或改用能直接看图的 AI 服务商。': '\n\nWarning: OCR confidence this time is very low (%d%%), so the translation is probably inaccurate. Click “Show area” to check that only the text is selected, or switch to an AI provider that reads the image directly.',
    '\n\n—— 原文（OCR 识别结果，可信度 %d%%；%s）——\n': '\n\n—— Original text (OCR result, confidence %d%%; %s) ——\n',
    '请识别图片中的文字，并翻译成【%s】，只输出译文。': 'Please recognize the text in the image and translate it into [%s]. Output only the translation.',
    '图片中的文字是【%s】。': 'The text in the image is [%s]. ',
    '[成功] 截图已复制到剪贴板。\n\n先点一下网页聊天框，再按 Ctrl+V 粘贴。\n粘贴不了就点聊天框的 + 号，再选“上传文件”，选 主文件夹/SkylarkTranslator/last.png。\n\n然后发送这句话：\n\n': "[OK] Screenshot copied to the clipboard.\n\nClick the chat box on the web page, then press Ctrl+V to paste.\nIf pasting doesn't work, click the + button in the chat box, choose “Upload file”, and pick home folder/SkylarkTranslator/last.png.\n\nThen send this sentence:\n\n",
    '截图已保存到：\n%s\n\n（自动复制到剪贴板没有成功，直接上传这个文件即可）\n到网页里点上传图片，选这个文件，然后发送：\n\n%s': "Screenshot saved to:\n%s\n\n(Copying to the clipboard didn't work; just upload this file.)\nOn the web page, click upload image, pick this file, then send:\n\n%s",
    '%s    按住这里拖动': '%s    Drag here to move',
    '—— 原文': '—— Original text',
    ' 按住这里拖动': ' Drag here to move',
    '重翻': 'Retry',
    '复位位置': 'Reset position',
    '换配色': 'Theme',
    '拖这里缩放': 'Drag here to resize',
    '付费（按用量计费）': 'Paid (pay per use)',
    '有免费额度：用谷歌账号登入即可免费申请密钥': 'Has a free quota: sign in with a Google account to get a free key',
    '新用户可能有免费额度，以官网为准': 'New users may get a free quota; check the official site',
    '完全免费，不用注册和密钥。非官方接口，太频繁可能被临时限制。需先装 tesseract': 'Completely free, no sign-up or key. Unofficial endpoint; too many requests may be throttled. Requires tesseract to be installed first',
    '免费不用注册。匿名约每天5000字；把邮箱填到“API密钥”栏可提高到约每天50000字': 'Free, no sign-up. About 5,000 characters/day anonymously; enter your email in the “API key” box to raise it to about 50,000/day',
    '不用API密钥：用你已登入的谷歌账号，截图自动复制，到网页粘贴': "No API key: uses the Google account you're signed in with; the screenshot is copied for you to paste into the web page",
    '不用API密钥：用你已登入的ChatGPT账号，截图自动复制，到网页粘贴': "No API key: uses the ChatGPT account you're signed in with; the screenshot is copied for you to paste into the web page",
    'glm-4v-flash 通常可免费调用，以官网为准': 'glm-4v-flash is usually free to call; check the official site',
    '左键点击翻译区域（推荐，不会误触手机的返回/主页）': "Left-click in the translate area (recommended; won't trigger the phone's Back/Home)",
    '右键双击（和旧版云雀一样）': 'Right double-click (like the old Skylark)',
    '中键单击（滚轮按下，较不易和游戏冲突）': 'Middle click (wheel press; less likely to clash with the game)',
    '黑底白字（推荐，不显眼）': 'White on black (recommended, unobtrusive)',
    '深灰底浅字': 'Light on dark gray',
    '白底黑字': 'Black on white',
    '快速（最快，复杂画面可能漏字）': 'Fast (fastest; may miss text in busy scenes)',
    '标准（推荐）': 'Standard (recommended)',
    '精细（最慢，最全）': 'Thorough (slowest, most complete)',
    '不使用（只用 OCR）': "Don't use (OCR only)",
    '忽略（推荐，只翻大字）': 'Ignore (recommended; translate only the large text)',
    '保留（连小字一起识别）': 'Keep (recognize the small text too)',
    '悬浮（不抢游戏焦点，用右键或按钮关闭）': "Floating (doesn't steal the game's focus; close with right-click or the button)",
    '普通窗口（可拖动）': 'Normal window (draggable)',
    '不触发（关闭）': 'Off',
    '界面语言 / Language': '界面语言 / Language',
    '（来自记忆：同一画面，没有重新请求）': '(From memory: same picture, no new request)',
}
UI_LANGS = {"自动 / Auto": "auto", "中文": "zh", "English": "en"}


EN.update({
    "AI额度用完时改用": "When the AI quota runs out, use",
    "不使用（直接显示错误）": "None (just show the error)",
    "（%s 额度用完或请求太频繁，已自动改用 %s。%s）": "(%s quota used up or too many requests; switched automatically to %s. %s)",
    "大约 %d 分钟后会再试 AI。": "The AI will be tried again in about %d min.",
    "大约 %d 秒后会再试 AI。": "The AI will be tried again in about %d s.",
    "（%s：今天已翻译 %d 次）": "(%s: %d requests today)",
    "备用 1（额度用完时改用）": "Backup 1 (used when the quota runs out)",
    "备用 2": "Backup 2",
    "备用 3": "Backup 3",
    "（不设）": "(not set)",
    "额度用完了，也没有可用的备用服务商。请在设置里选一个备用，或稍后再试。":
        "The quota is used up and there is no usable backup provider. Pick one in Settings, or try again later.",
    "有免费额度，但每天次数不多（Flash 约几十次，Flash-Lite 多一些），以官网为准":
        "Has a free quota, but the daily count is small (tens per day for Flash, more for Flash-Lite); check the official site",
})


def T(s):
    """界面文字：当前是英文界面就返回英文，没有对应英文的原样返回"""
    return EN.get(s, s) if LANG == "en" else s


def lang_label(s):
    """语言名在界面上怎么显示：中文界面显示中文名，英文界面显示英文名"""
    if s == AUTO:
        return T("自动识别")
    zh_, _, en_ = s.partition(" / ")
    return en_ if (LANG == "en" and en_) else zh_


def refresh_labels():
    """下拉选项的文字随界面语言变化；程序里其余地方用到时，读到的就是当前语言的文字"""
    global TRIG, SPEEDS, SPEED_KEYS, FB_NONE, RUBY_ON, RUBY_OFF, FLOAT_ON, FLOAT_OFF, THEME_LABELS
    TRIG = {T(k): v for k, v in _TRIG_BASE.items()}
    SPEEDS = {k: T(v) for k, v in _SPEEDS_BASE.items()}
    SPEED_KEYS = {v: k for k, v in SPEEDS.items()}
    FB_NONE = T(_FB_NONE_BASE)
    RUBY_ON, RUBY_OFF = T(_RUBY_BASE[0]), T(_RUBY_BASE[1])
    FLOAT_ON, FLOAT_OFF = T(_FLOAT_BASE[0]), T(_FLOAT_BASE[1])
    for k, v in THEMES.items():
        v["label"] = T(_THEME_BASE[k])
    THEME_LABELS = {v["label"]: k for k, v in THEMES.items()}


def resolve_lang(cfg, hint=None):
    """设置里选了中文/English 就用它；选“自动”就跟随宿主程序（Artocarpus）的语言，没有宿主就看系统语言"""
    v = cfg.get("ui_lang", "auto")
    if v in ("zh", "en"):
        return v
    if hint in ("zh", "en"):
        return hint
    try:
        import locale
        loc = (locale.getdefaultlocale()[0] or "").lower()
    except Exception:
        loc = ""
    if loc in ("", "c", "posix") or loc.startswith("zh"):  # 看不出系统语言时保持中文（本程序原来就是中文界面）
        return "zh"
    return "en"


def set_lang(code):
    global LANG
    LANG = code if code in ("zh", "en") else "zh"
    refresh_labels()


refresh_labels()


def lang_values(cfg):
    v = list(LANGS)
    if cfg["target"] not in v:
        v.insert(0, cfg["target"])
    return v


def friendly(e):
    s = str(e)
    tips = {"HTTP 400": T("请求被拒绝（400）：模型可能不支持看图，或模型名称写错。"),
            "HTTP 401": T("密钥无效（401）：请检查 API 密钥是否填对，有没有多余空格。"),
            "HTTP 403": T("没有权限（403）：密钥权限不足，或该地区/账号不能使用此模型。"),
            "HTTP 404": T("找不到（404）：请检查模型名称和接口地址是否正确。"),
            "HTTP 429": T("请求太频繁或额度用完（429）：稍后再试，或检查账户余额。")}
    for k, v in tips.items():
        if s.startswith(k):
            return T("错误：%s\n\n详细信息：%s") % (v, s[:300])
    if s.startswith("HTTP 404") and "models" in s.lower():
        return T("错误：找不到这个模型（404）。模型名可能已经下线，请点设置里的“获取模型列表”，从里面选一个。\n\n详细信息：%s") % s[:200]
    if isinstance(e, FileNotFoundError):
        return (T("错误：没有找到 tesseract 文字识别程序。请先安装：\n"
                "sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn tesseract-ocr-chi-sim"))
    if isinstance(e, OSError):
        return T("错误：无法连接服务器，请检查网络和接口地址。\n%s") % e
    if isinstance(e, (KeyError, IndexError, TypeError)):
        return T("错误：服务商返回的格式不对，请确认“接口类型”选对了（openai / gemini / claude）。")
    return T("错误：%s") % s


PROVIDER_RENAMES = {'通义千问': '通义千问 / Qwen', '智谱GLM': '智谱GLM / Zhipu GLM', 'Google翻译（免费+OCR）': 'Google翻译 / Google Translate (free+OCR)', 'MyMemory（免费+OCR）': 'MyMemory (free+OCR) / 免费+OCR', 'Gemini网页版': 'Gemini网页版 / Gemini web', 'ChatGPT网页版': 'ChatGPT网页版 / ChatGPT web'}


def load_cfg():
    cfg = json.loads(json.dumps(DEFAULT))
    try:
        with open(CONF, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    cfg["providers"] = {PROVIDER_RENAMES.get(k, k): v for k, v in cfg["providers"].items()}  # 旧名字换成中英双语名字
    cfg["active"] = PROVIDER_RENAMES.get(cfg["active"], cfg["active"])
    cfg["fallback"] = PROVIDER_RENAMES.get(cfg.get("fallback", ""), cfg.get("fallback", ""))
    for pv in cfg["providers"].values():  # 旧版默认的 gemini-2.x 已停用（2026-10-16 关停），自动换成永远指向最新 Flash 的别名
        if pv.get("type") == "gemini" and (re.match(r"gemini-[12]\.", pv.get("model", "")) or pv.get("model") == "gemini-flash-latest"):
            pv["model"] = "gemini-flash-lite-latest"  # Flash-Lite 免费次数更多，实测看图翻译日文游戏对话够用
    if cfg["active"] not in cfg["providers"]:
        cfg["active"] = list(cfg["providers"])[0]
    for name, d in DEFAULT["providers"].items():
        if d["type"] == "web" or d["type"].startswith("ocr_"):
            cfg["providers"].setdefault(name, dict(d))
        if name in cfg["providers"]:
            for k in ("signup_url", "note"):
                cfg["providers"][name].setdefault(k, d[k])
            cfg["providers"][name]["note"] = d["note"]
    if cfg["target"] not in LANGS:  # 旧配置里手写的“简体中文”等，换成列表里的写法
        for l in LANGS:
            if l.split(" / ")[0] == cfg["target"].strip():
                cfg["target"] = l
                break
    return cfg


def save_cfg(cfg):
    os.makedirs(CONF_DIR, exist_ok=True)
    with open(CONF, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONF, 0o600)
    except Exception:
        pass


# ---------------------------------------------------------------- 截图
def grab_screen():
    if mss:
        with mss.mss() as s:
            raw = s.grab(s.monitors[1])  # 主显示器
            return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    from PIL import ImageGrab
    return ImageGrab.grab().convert("RGB")


def grab_region(box):
    """只截固定区域（box 是截图像素坐标），不用隐藏任何窗口，速度快、不闪烁"""
    x0, y0, x1, y1 = [int(v) for v in box]
    if mss:
        with mss.mss() as sct:
            m = sct.monitors[1]
            raw = sct.grab({"left": m["left"] + x0, "top": m["top"] + y0, "width": x1 - x0, "height": y1 - y0})
            return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    from PIL import ImageGrab
    return ImageGrab.grab(bbox=(x0, y0, x1, y1)).convert("RGB")


# ---------------------------------------------------------------- AI 接口
def http_json(url, headers, body, timeout=90):
    headers = dict(headers)
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, json.dumps(body).encode("utf-8"), headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:400]))


ASK = "请翻译图片中的文字。"


def ask_openai(p, system, b64):
    body = {"model": p["model"], "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": [
            {"type": "text", "text": ASK},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}]}]}
    r = http_json(p["base_url"].rstrip("/") + "/chat/completions",
                  {"Authorization": "Bearer " + p["api_key"]}, body)
    return r["choices"][0]["message"]["content"]


def ask_gemini(p, system, b64):
    body = {"system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": ASK},
                                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}],
            "generationConfig": {"temperature": 0.2}}
    mr = str(p.get("media_res", "low")).lower()   # low / medium / high；在配置里给 Gemini 加 "media_res" 可改，写 "off" 则不设置
    if mr in ("low", "medium", "high"):
        body["generationConfig"]["mediaResolution"] = "MEDIA_RESOLUTION_" + mr.upper()
    url = "%s/models/%s:generateContent" % (p["base_url"].rstrip("/"), p["model"])
    r = http_json(url, {"x-goog-api-key": p["api_key"]}, body)
    return "".join(x.get("text", "") for x in r["candidates"][0]["content"]["parts"])


def ask_claude(p, system, b64):
    body = {"model": p["model"], "max_tokens": 2000, "system": system,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": ASK}]}]}
    r = http_json(p["base_url"].rstrip("/") + "/messages",
                  {"x-api-key": p["api_key"], "anthropic-version": "2023-06-01"}, body)
    return "".join(x.get("text", "") for x in r["content"] if x.get("type") == "text")


BACKENDS = {"openai": ask_openai, "gemini": ask_gemini, "claude": ask_claude}


def build_system(cfg):
    src = cfg.get("source", AUTO)
    if src == AUTO:
        head = ("原文语言不固定，可能是日文、英文或其他语言，也可能混合出现，请自动识别。"
                "请把图片中的所有文字翻译成【%s】。" % cfg["target"])
    else:
        head = "图片中的文字主要是【%s】，请把所有文字翻译成【%s】。" % (src, cfg["target"])
    s = ("你是屏幕翻译工具。图片是游戏或软件界面的一部分。" + head +
         "忽略对话框的边框、装饰线条、图标，以及汉字上方的小字注音（振假名），只翻译正文大字。"
         "日语常省略主语：请根据说话人和场景判断是谁在对谁说，不要把说话人和听话人弄反；假名同音词请结合上下文选词。"
         "人名、地名、店名、商品名拿不准时，保留原文或只音译，不要按字面意译。"
         "严格按下面两行格式输出，不要解释：\n原文：<你读到的正文，保持换行>\n译文：<译文，保持换行；已经是目标语言的部分原样保留>\n"
         "若图中没有文字，输出：原文：无\n译文：（未识别到文字）")
    if cfg.get("extra"):
        s += "\n补充说明：" + cfg["extra"]
    g = load_glossary()
    if g:
        s += "\n专有名词对照表（遇到必须按此翻译）：\n" + g
    return s


GLOSSARY = os.path.join(CONF_DIR, "glossary.txt")
KANA_RE = re.compile(r"[\u3040-\u30ff]")


def load_glossary():
    """术语表：~/.skylark_ai/glossary.txt，每行一条“原文=译文”，# 开头是注释。人名地名前后翻译一致全靠它"""
    try:
        with open(GLOSSARY, "r", encoding="utf-8") as f:
            return "\n".join(l.strip() for l in f if "=" in l and not l.lstrip().startswith("#"))
    except Exception:
        return ""


def split_reply(text, target=""):
    """AI 按“原文：…/译文：…”回复时只取译文。返回 (译文, 是否可信)；
    译文里假名太多（目标不是日语）说明模型把原文当译文抄回来了，判为不可信，调用方会重试一次"""
    t = text.strip()
    zh = t.split("译文：", 1)[1].strip() if "译文：" in t else t
    if zh in ("无", ""):
        zh = T("（未识别到文字）")
    if "日" in target:
        return zh, True
    kana = len(KANA_RE.findall(zh))
    return zh, kana / max(len(zh), 1) < 0.2


# ---------------------------------------------------------------- 本地 OCR + 免费在线翻译
GCODE = {"简体中文": "zh-CN", "繁体中文": "zh-TW", "英语": "en", "日语": "ja", "韩语": "ko", "法语": "fr",
         "德语": "de", "西班牙语": "es", "葡萄牙语": "pt", "意大利语": "it", "俄语": "ru", "阿拉伯语": "ar",
         "印地语": "hi", "泰语": "th", "越南语": "vi", "印尼语": "id", "马来语": "ms", "菲律宾语": "tl",
         "土耳其语": "tr", "荷兰语": "nl", "波兰语": "pl", "乌克兰语": "uk", "捷克语": "cs", "瑞典语": "sv",
         "丹麦语": "da", "挪威语": "no", "芬兰语": "fi", "希腊语": "el", "希伯来语": "iw", "匈牙利语": "hu",
         "罗马尼亚语": "ro", "保加利亚语": "bg", "波斯语": "fa", "孟加拉语": "bn", "乌尔都语": "ur",
         "缅甸语": "my", "高棉语": "km", "老挝语": "lo", "蒙古语": "mn", "拉丁语": "la"}
TESS = {"简体中文": "chi_sim", "繁体中文": "chi_tra", "英语": "eng", "日语": "jpn", "韩语": "kor", "法语": "fra",
        "德语": "deu", "西班牙语": "spa", "葡萄牙语": "por", "意大利语": "ita", "俄语": "rus", "阿拉伯语": "ara",
        "印地语": "hin", "泰语": "tha", "越南语": "vie", "印尼语": "ind", "马来语": "msa", "菲律宾语": "fil",
        "土耳其语": "tur", "荷兰语": "nld", "波兰语": "pol", "乌克兰语": "ukr", "捷克语": "ces", "瑞典语": "swe",
        "丹麦语": "dan", "挪威语": "nor", "芬兰语": "fin", "希腊语": "ell", "希伯来语": "heb", "匈牙利语": "hun",
        "罗马尼亚语": "ron", "保加利亚语": "bul", "波斯语": "fas", "孟加拉语": "ben", "乌尔都语": "urd",
        "缅甸语": "mya", "高棉语": "khm", "老挝语": "lao", "蒙古语": "mon", "拉丁语": "lat"}
CJK = "\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af"


def lang_name(s):
    return s.split(" / ")[0].strip()


def lcode(s):
    return "auto" if s == AUTO else GCODE.get(lang_name(s))


def _runs(flags):
    runs, start = [], None
    for i, f in enumerate(list(flags) + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            runs.append((start, i))
            start = None
    return runs


def remove_lines(g, tol=12, spread=22):
    """去掉对话框的边框线、笔记本式的横线：又细又长、颜色整条均匀、和背景不同的线。
    文字所在的行/列颜色变化大，不会被当成线"""
    W, H = g.size
    if W < 60 or H < 40:
        return g
    out = g.copy()
    for horizontal in (True, False):
        n = H if horizontal else W
        small = g.resize((min(W, 160), H) if horizontal else (W, min(H, 160)), Image.BOX)
        sw, sh = small.size
        data = list(small.getdata())
        if horizontal:
            lines = [data[y * sw:(y + 1) * sw] for y in range(sh)]
        else:
            lines = [data[x::sw] for x in range(sw)]
        means = [sum(l) / float(len(l)) for l in lines]
        uniform = [(max(l) - min(l)) <= spread for l in lines]
        ref = sorted(m for m, u in zip(means, uniform) if u)
        if not ref:
            continue
        bg = ref[len(ref) // 2]  # 背景色：均匀的行/列里最常见的那个
        flags = [u and abs(m - bg) > tol for m, u in zip(means, uniform)]
        limit = max(4, int(n * 0.05))  # 只处理细线，粗的色块不动
        for a, b in _runs(flags):
            if b - a > limit:
                continue
            src = a - 1 if a > 0 else b  # 用紧挨着的干净一行/列盖住
            if src >= n:
                continue
            if horizontal:
                out.paste(out.crop((0, src, W, src + 1)).resize((W, b - a)), (0, a))
            else:
                out.paste(out.crop((src, 0, src + 1, H)).resize((b - a, H)), (a, 0))
    return out


def _otsu(h):
    tot, tsum = sum(h), sum(i * v for i, v in enumerate(h))
    sb = wb = 0
    best = (0, 128)
    for t in range(256):
        wb += h[t]
        wf = tot - wb
        if not wb or not wf:
            continue
        sb += t * h[t]
        var = wb * wf * (sb / float(wb) - (tsum - sb) / float(wf)) ** 2
        if var > best[0]:
            best = (var, t)
    return best[1]


def erase_ruby(g):
    """日文的振假名（汉字上方的小字）会让识别程序把行高算错、甚至丢掉整行。
    识别前，先在图片上把它们涂掉：按“每一行有多少字的像素”找出文字带，
    比下面那一带明显矮、紧贴在它上方的窄带，就是注音。"""
    W, H = g.size
    if H < 36 or W < 36:
        return g
    hist = g.histogram()
    t = _otsu(hist)
    light = sum(hist[t + 1:]) < sum(hist[:t + 1])  # 白字深底
    bw = g.point(lambda p: 255 if (p > t) == light else 0)  # 字 = 255
    prof = list(bw.resize((1, H), Image.BOX).getdata())
    on = [v > 255 * 0.006 for v in prof]
    bands, y = [], 0
    while y < H:
        if on[y]:
            y0 = y
            while y < H and (on[y] or any(on[y + 1:y + 3])):  # 允许 2 行以内的小缺口
                y += 1
            if y - y0 >= 3:
                bands.append((y0, y, max(prof[y0:y])))
        else:
            y += 1
    out = g.copy()
    for i in range(len(bands) - 1):
        (a0, a1, ap), (b0, b1, bp) = bands[i], bands[i + 1]
        ha, hb, gap = a1 - a0, b1 - b0, b0 - a1
        if ha <= 0.62 * hb and gap <= max(3, 0.8 * hb) and ap <= 0.8 * bp:
            ry = min(H - 1, a1 + max(0, gap // 2))  # 取两带之间的一行背景，铺满注音所在的位置
            row = out.crop((0, ry, W, ry + 1))
            for yy in range(max(0, a0 - 1), min(H, a1 + 1)):
                out.paste(row, (0, yy))
    return out


def prepare_ocr_image(img, inset=6, ruby=False):
    """截图 -> 适合 OCR 的灰度图：往里缩一圈避开边框 -> 灰度 -> 拉开对比度 -> 去线 -> 放大"""
    w, h = img.size
    if inset and min(w, h) > inset * 8:
        img = img.crop((inset, inset, w - inset, h - inset))
    g = remove_lines(ImageOps.autocontrast(img.convert("L")))
    if ruby:
        g = erase_ruby(g)
    big = max(g.size)
    k = 3 if big < 600 else (2 if big < 1400 else 1)
    if k > 1:
        g = g.resize((g.width * k, g.height * k), Image.LANCZOS)
    return g


def tidy_text(text):
    """去掉识别出来的边线残渣（行首行尾的 | / _ 等），空行和纯符号行直接丢掉"""
    out = []
    for line in text.splitlines():
        line = re.sub(r"^[|｜/\\_\-—\s]+|[|｜/\\_\-—\s]+$", "", line)
        if not re.sub(r"[ー一―－—_~〜・\-\s]", "", line):  # 整行只有横线类符号 = 边框/横线的残渣
            continue
        if re.search("[A-Za-z0-9\u00c0-\u024f\u0370-\u03ff\u0400-\u04ff\u0590-\u06ff\u0900-\u0dff\u0e00-\u0eff\u1000-\u109f\u1780-\u17ff\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]", line):
            out.append(line)
    return "\n".join(out)


def tess_langs():
    r = subprocess.run(["tesseract", "--list-langs"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)
    return [l.strip() for l in r.stdout.decode("utf-8", "ignore").splitlines()
            if l.strip() and not l.startswith("List of")]


def ocr_text(path, langs, psm="6", min_conf=20, skip_small=False):
    """识别一张图，返回 (文字, 平均置信度)。置信度太低的词（多半是乱码）直接丢掉。
    skip_small=True：整行字明显比别的行小（日文的振假名）就整行忽略，只保留大字"""
    r = subprocess.run(["tesseract", path, "stdout", "-l", langs, "--psm", psm, "tsv"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90, env=OCR_ENV)
    if r.returncode != 0:
        raise RuntimeError(T("OCR 失败：%s") % r.stderr.decode("utf-8", "ignore")[:200])
    rows, order = {}, []
    for line in r.stdout.decode("utf-8", "ignore").splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or not f[11].strip():
            continue
        try:
            conf, h = float(f[10]), int(f[9])
        except ValueError:
            continue
        if conf < 0 or re.fullmatch(r"[|｜/\\_\-—~·.,'`]+", f[11].strip()):
            continue
        key = (f[2], f[3], f[4])
        if key not in rows:
            rows[key] = []
            order.append(key)
        rows[key].append((f[11].strip(), conf, h))
    if skip_small and rows:
        info = {}
        for k in order:
            ws = rows[k]
            hs = sorted(h for _, _, h in ws)
            # 行高取 75% 分位数而不是中位数：假名比汉字矮，一行里假名多时中位数会偏小，把正常的行误当成注音
            info[k] = (hs[min(len(hs) - 1, int(len(hs) * 0.75))], sum(c for _, c, _ in ws) / len(ws))
        ref = max([m for m, c in info.values() if c >= 50] or [m for m, c in info.values()])
        small = set()
        for i, k in enumerate(order[:-1]):  # 注音一定在大字的上面，所以最后一行永远不会是注音
            nxt = info[order[i + 1]][0]
            if info[k][0] < 0.65 * ref and nxt >= info[k][0] / 0.65:  # 明显比自己下面那行小
                small.add(k)
        order = [k for k in order if k not in small]
    kept = {k: [(t, c) for t, c, h in rows[k] if c >= min_conf] for k in order}
    order = [k for k in order if kept[k]]
    words = [w for k in order for w in kept[k]]
    if not words:
        return "", 0.0
    score = sum(c * len(t) for t, c in words) / float(sum(len(t) for t, c in words))
    return "\n".join(" ".join(t for t, c in kept[k]) for k in order), score

def alt_variant(path):
    """备选版本：裁掉四周同色的空白边，再补一圈背景色。Tesseract 的版面判断对这个很敏感，
    原图没读全时，这个版本常常能读出来"""
    g = Image.open(path).convert("L")
    bg = g.getpixel((0, 0))
    box = ImageChops.difference(g, Image.new("L", g.size, bg)).point(lambda p: 255 if p > 18 else 0).getbbox()
    if box:
        g = g.crop(box)
    n = 30
    out = Image.new("L", (g.width + 2 * n, g.height + 2 * n), bg)
    out.paste(g, (n, n))
    return out


def light_text(path):
    """白字深底 = True。亮的像素是少数，说明字是亮色的"""
    g = Image.open(path).convert("L")
    g.thumbnail((240, 240))
    h = g.histogram()
    tot, tsum = sum(h), sum(i * v for i, v in enumerate(h))
    sb = wb = 0
    best = (0, 128)
    for t in range(256):
        wb += h[t]
        wf = tot - wb
        if not wb or not wf:
            continue
        sb += t * h[t]
        var = wb * wf * (sb / float(wb) - (tsum - sb) / float(wf)) ** 2
        if var > best[0]:
            best = (var, t)
    t = best[1]
    return sum(h[t + 1:]) < sum(h[:t + 1])


_LAST_LANG = None  # 自动识别时，记住上次认出来的语言，下次先只试它


def ocr_quality(text, score):
    """综合“认出多少字”和“有多可信”：认得多又准的更好"""
    return score * score * len(re.sub(r"\s", "", text))


LOW_CONF = 65  # 识别可信度低于这个值，就认为没把握（会提醒，或改用备用 AI）
AUTO_ORDER = ["eng", "jpn", "chi_sim", "kor"]  # 自动识别时依次尝试的语言（只试已安装的）


def run_ocr(path, source, skip_ruby=True, mode="normal"):
    """返回 (识别出的文字, 采用的语言包, 已安装的语言包列表, 可信度)。
    mode：fast = 只试一种底色（猜不准或没把握才补试）；normal = 正反两种底色都试；best = 再加备选版本
    自动识别时先只试上次认出来的语言，没把握才把所有候选语言都试一遍"""
    global _LAST_LANG
    installed = tess_langs()
    code = TESS.get(lang_name(source))
    if code:
        if code not in installed:
            raise RuntimeError(T("没有安装文字识别语言包：%s\n请在终端运行：\nsudo apt install %s") % (
                code, "tesseract-ocr-" + code.replace("_", "-")))
        full = cands = [code]
    else:
        full = [l for l in AUTO_ORDER if l in installed] or [n for n in installed if n != "osd"][:1] or ["eng"]
        cands = [_LAST_LANG] if (mode != "best" and _LAST_LANG in full) else full
    inv = path[:-4] + "_inv.png"
    alt, alt_inv = path[:-4] + "_alt.png", path[:-4] + "_alt_inv.png"
    best, bscore, bq, blang = "", 0.0, -1.0, cands[0]
    from concurrent.futures import ThreadPoolExecutor

    def run_jobs(jobs):
        nonlocal best, bscore, bq, blang
        if not jobs:
            return
        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(lambda j: ocr_text(j[0], j[1], skip_small=False), jobs))
        for (v, l), (txt, sc) in zip(jobs, results):
            q = ocr_quality(txt, sc)
            if txt and q > bq:
                best, bscore, bq, blang = txt, sc, q, l

    try:
        ImageOps.invert(Image.open(path).convert("L")).save(inv)
        order = [inv, path] if light_text(path) else [path, inv]  # 猜得更可能对的那种底色排前面
        first = order[:1] if mode == "fast" else order
        run_jobs([(v, l) for l in cands for v in first])
        if mode == "fast" and bscore < LOW_CONF:  # 没把握：另一种底色也试试
            run_jobs([(order[1], l) for l in cands])
        if len(cands) < len(full) and bscore < LOW_CONF:  # 只试了上次的语言又没把握：其余语言也试
            run_jobs([(v, l) for l in full if l not in cands for v in first])
        if bscore < (85 if mode == "best" else LOW_CONF):  # 仍没把握：用“裁边补白”的备选版本再试
            a_img = alt_variant(path)
            a_img.save(alt)
            ImageOps.invert(a_img).save(alt_inv)
            run_jobs([(alt, blang), (alt_inv, blang)])
    finally:
        for f in (inv, alt, alt_inv):
            try:
                os.remove(f)
            except OSError:
                pass
    if not code and best:
        _LAST_LANG = blang
    text = re.sub("(?<=[%s])[ \\t]+(?=[%s])" % (CJK, CJK), "", best)  # 去掉中日韩文字之间多余的空格
    return tidy_text(text.strip()), blang, installed, max(bscore, 0.0)


def chunks(text, limit, merge=True):
    out, cur = [], ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        step = max(1, limit // 4)
        for i in range(0, len(line), step):
            part = line[i:i + step]
            if merge and cur and len((cur + "\n" + part).encode("utf-8")) <= limit:
                cur += "\n" + part
            else:
                if cur:
                    out.append(cur)
                cur = part
            if not merge:
                out.append(cur)
                cur = ""
    if cur:
        out.append(cur)
    return out


def http_get(url, timeout=30, headers=None):
    hdr = {"User-Agent": "Mozilla/5.0"}
    hdr.update(headers or {})
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:200]))


def quota_secs(e):
    """是额度用完/请求太频繁（429）的错误吗？是的话，返回建议多少秒后再试 AI；不是返回 None"""
    s = str(e)
    if not (s.startswith("HTTP 429") or "RESOURCE_EXHAUSTED" in s or "quota" in s.lower()):
        return None
    daily = bool(re.search(r"PerDay|per day|daily|每日", s, re.I))
    m_ = re.search(r"retry[^0-9]{0,30}(\d+(?:\.\d+)?)\s*s", s, re.I)
    secs = int(float(m_.group(1))) + 2 if m_ else 90
    return max(secs, 3 * 3600) if daily else secs


def final_ocr(cfg):
    """备用链的最后一级：免费的 OCR + Google 翻译（没有额度限制）"""
    for n, pv in cfg["providers"].items():
        if pv.get("type") == "ocr_google":
            return n, dict(pv)
    return None


def backup_chain(cfg):
    """依次要试的备用服务商 [(名字, 配置)…]：备用1 → 备用2 → 备用3，最后一级永远是免费 OCR。
    备用1 明确选了“不使用”且 2、3 也没设，就返回空（= 额度用完直接显示错误）"""
    chain, provs = [], cfg["providers"]
    for key in ("backup", "backup2", "backup3"):
        v = cfg.get(key, "__auto__" if key == "backup" else "")
        pv = provs.get(v) if v and v != "__auto__" else None
        if pv and pv.get("type") != "web" and v not in [n for n, _ in chain]:
            chain.append((v, dict(pv)))
    explicit_none = cfg.get("backup", "__auto__") == "" and not chain
    fo = final_ocr(cfg)
    if not explicit_none and fo and fo[0] not in [n for n, _ in chain]:
        chain.append(fo)
    return chain


def backup_provider(cfg):
    """设置里选的备用服务商：(名字, 配置) 或 None（None = 用户明确选了“不使用”）"""
    v, provs = cfg.get("backup", "__auto__"), cfg["providers"]
    if v == "":
        return None
    pv = provs.get(v)
    if v != "__auto__" and pv and pv.get("type") != "web":
        return v, dict(pv)
    return final_ocr(cfg)


def list_models(p):
    """向服务商询问：这个密钥现在能用哪些模型（模型名过期、写错时用）"""
    t, base, key = p.get("type"), p["base_url"].rstrip("/"), p.get("api_key", "")
    if t == "gemini":
        d = http_get(base + "/models?pageSize=200", headers={"x-goog-api-key": key})
        return sorted(m_["name"].split("/", 1)[-1] for m_ in d.get("models", [])
                      if "generateContent" in m_.get("supportedGenerationMethods", []))
    if t == "openai":
        d = http_get(base + "/models", headers={"Authorization": "Bearer " + key})
        return sorted(x["id"] for x in d.get("data", []))
    if t == "claude":
        d = http_get(base + "/models", headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
        return [x["id"] for x in d.get("data", [])]
    return []


def pick_gemini(names):
    """从模型列表里挑一个：优先永远指向最新 Flash 的别名，其次版本最高的正式版 Flash"""
    for pref in ("gemini-flash-lite-latest", "gemini-flash-latest"):
        if pref in names:
            return pref

    def ver(n):
        return tuple(int(x) for x in re.findall(r"\d+", n))
    stable = [n for n in names if re.fullmatch(r"gemini-\d+(\.\d+)?-flash", n)]
    if stable:
        return max(stable, key=ver)
    flash = [n for n in names if "flash" in n and not any(w in n for w in ("tts", "image", "live", "audio", "embedding", "exp"))]
    return max(flash, key=ver) if flash else (names[0] if names else None)


def add_context_menu(w):
    """给输入框加右键菜单（剪切/复制/粘贴/全选）"""
    menu = tk.Menu(w, tearoff=0)
    for label, ev in ((T("剪切"), "<<Cut>>"), (T("复制"), "<<Copy>>"), (T("粘贴"), "<<Paste>>")):
        menu.add_command(label=label, command=lambda ev=ev: w.event_generate(ev))
    menu.add_separator()
    menu.add_command(label=T("全选"), command=lambda: (w.focus_set(), w.selection_range(0, "end")))

    def pop(e):
        w.focus_set()
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()
    w.bind("<Button-3>", pop)


def tr_google(p, text, sl, tl):
    out = []
    for c in chunks(text, 800, True):
        q = urllib.parse.urlencode({"client": "gtx", "sl": sl, "tl": tl, "dt": "t", "q": c})
        d = http_get("https://translate.googleapis.com/translate_a/single?" + q)
        out.append("".join(seg[0] for seg in d[0] if seg and seg[0]).strip())
    return "\n".join(out)


def tr_mymemory(p, text, sl, tl):
    email = (p.get("api_key") or "").strip()  # “API密钥”栏填邮箱，可提高每日额度
    pair = "%s|%s" % ("Autodetect" if sl == "auto" else sl.replace("iw", "he"), tl.replace("iw", "he"))
    out = []
    for c in chunks(text, 450, False):
        params = {"q": c, "langpair": pair}
        if email:
            params["de"] = email
        d = http_get("https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(params))
        if str(d.get("responseStatus")) != "200":
            raise RuntimeError("HTTP %s: %s" % (d.get("responseStatus"), d.get("responseDetails", "")))
        out.append(d["responseData"]["translatedText"])
    return "\n".join(out)


TRANSLATORS = {"ocr_google": tr_google, "ocr_mymemory": tr_mymemory}


# ---------------------------------------------------------------- 框选
class Selector:
    def __init__(self, root, shot, cb, old=None):
        self.cb, self.shot = cb, shot
        t = self.top = tk.Toplevel(root)
        sw, sh = t.winfo_screenwidth(), t.winfo_screenheight()
        t.overrideredirect(True)
        t.geometry("%dx%d+0+0" % (sw, sh))
        t.attributes("-topmost", True)
        self.kx, self.ky = shot.width / float(sw), shot.height / float(sh)
        bg = shot if shot.size == (sw, sh) else shot.resize((sw, sh))
        self.img = ImageTk.PhotoImage(bg)
        c = self.c = tk.Canvas(t, width=sw, height=sh, highlightthickness=0, cursor="crosshair")
        c.pack()
        c.create_image(0, 0, anchor="nw", image=self.img)
        if old:  # 目前的区域用蓝色虚线框显示，重新框选时能对着它调整
            c.create_rectangle(*old, outline="#3399ff", width=3, dash=(8, 4))
            c.create_text(old[0] + 6, old[1] + 4, anchor="nw", text=T("目前的区域"), fill="#3399ff",
                          font=("sans-serif", 14, "bold"))
        c.create_text(sw // 2, 30, text=T("拖拽框选新的区域（蓝框 = 目前的区域）    右键取消"),
                      fill="red", font=("sans-serif", 18, "bold"))
        t.lift()
        self.rect = None
        c.bind("<ButtonPress-1>", self.down)
        c.bind("<B1-Motion>", self.move)
        c.bind("<ButtonRelease-1>", self.up)
        c.bind("<Button-3>", lambda e: self.finish(None))
        t.bind("<Escape>", lambda e: self.finish(None))
        t.focus_force()

    def down(self, e):
        self.x0, self.y0 = e.x, e.y
        self.rect = self.c.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

    def move(self, e):
        if self.rect:
            self.c.coords(self.rect, self.x0, self.y0, e.x, e.y)

    def up(self, e):
        x0, x1 = sorted((self.x0, e.x))
        y0, y1 = sorted((self.y0, e.y))
        if x1 - x0 < 10 or y1 - y0 < 10:
            return self.finish(None)
        sb = (int(x0 * self.kx), int(y0 * self.ky), int(x1 * self.kx), int(y1 * self.ky))
        self.finish(((x0, y0, x1, y1), sb, self.shot.crop(sb)))

    def finish(self, result):
        self.top.destroy()
        self.cb(result)


# ---------------------------------------------------------------- 设置窗口
class Settings:
    def __init__(self, app):
        self.app, cfg = app, app.cfg
        w = self.w = tk.Toplevel(app.host)
        w.title(T("设置"))
        w.attributes("-topmost", True)
        sw_, sh_ = w.winfo_screenwidth(), w.winfo_screenheight()
        top = ttk.Frame(w, padding=(10, 8, 10, 0))  # 顶部：服务商（始终可见）
        top.pack(side="top", fill="x")
        bottom = ttk.Frame(w, padding=(10, 4, 10, 8))  # 底部：提示和按钮（始终可见）
        bottom.pack(side="bottom", fill="x")
        outer = ttk.Frame(w)
        outer.pack(side="top", fill="both", expand=True)
        canvas = self.canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        f = ttk.Frame(canvas, padding=10)  # 中间：所有选项，放在可滚动的画布里
        canvas.create_window((0, 0), window=f, anchor="nw")
        f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.cur = cfg["active"]
        self.sel = tk.StringVar(value=self.cur)
        self.v = {k: tk.StringVar() for k in ("type", "base_url", "api_key", "model", "source", "target", "extra", "trigger", "font_size", "float", "skip_ruby", "click_delay", "theme", "alpha", "inset", "fallback", "ocr_speed", "conf_gate", "ui_lang", "backup", "backup2", "backup3")}
        self.v["source"].set(cfg.get("source", AUTO))
        self.v["target"].set(cfg["target"])
        inv = {v: k for k, v in TRIG.items()}
        self.v["trigger"].set(inv.get(cfg.get("trigger", "off"), T("关闭")))
        self.v["font_size"].set(str(cfg.get("font_size", 20)))
        self.v["float"].set(FLOAT_ON if cfg.get("float", True) else FLOAT_OFF)
        self.v["skip_ruby"].set(RUBY_ON if cfg.get("skip_ruby", True) else RUBY_OFF)
        self.v["click_delay"].set(str(cfg.get("click_delay", 0.8)))
        self.v["inset"].set(str(cfg.get("inset", 6)))
        self.v["theme"].set(THEMES.get(cfg.get("theme", "black"), THEMES["black"])["label"])
        self.v["alpha"].set("%d%%" % round(float(cfg.get("alpha", 0.9)) * 100))
        self.v["fallback"].set(cfg.get("fallback") or FB_NONE)
        self.v["ocr_speed"].set(SPEEDS.get(cfg.get("ocr_speed", "normal"), SPEEDS["normal"]))
        self.v["conf_gate"].set(str(cfg.get("conf_gate", 85)))
        self.bk_none = T("不使用（直接显示错误）")
        self.bk_empty = T("（不设）")
        _bk = backup_provider(cfg)
        self.v["backup"].set(_bk[0] if _bk else self.bk_none)
        for _k in ("backup2", "backup3"):
            self.v[_k].set(cfg.get(_k) if cfg.get(_k) in cfg["providers"] else self.bk_empty)
        self.v["ui_lang"].set({v: k for k, v in UI_LANGS.items()}.get(cfg.get("ui_lang", "auto"), "自动 / Auto"))
        self.note = tk.StringVar()
        self.msg = tk.StringVar()
        self.v["extra"].set(cfg.get("extra", ""))

        ttk.Label(top, text=T("服务商")).pack(side="left", padx=(0, 8))
        self.cb = ttk.Combobox(top, textvariable=self.sel, values=list(cfg["providers"]),
                               state="readonly", width=38)
        self.cb.pack(side="left")
        self.cb.bind("<<ComboboxSelected>>", self.switch)

        rows = [("界面语言 / Language", "ui_lang"), (T("接口类型"), "type"), (T("接口地址"), "base_url"), (T("API 密钥"), "api_key"),
                (T("模型名称"), "model"), (T("原文语言"), "source"), (T("目标语言"), "target"), (T("额外提示"), "extra"),
                (T("鼠标快捷触发"), "trigger"), (T("译文字号"), "font_size"), (T("译文窗口"), "float"),
                (T("日文小字（振假名）"), "skip_ruby"), (T("点击后等待（秒）"), "click_delay"),
                (T("译文配色"), "theme"), (T("译文透明度"), "alpha"),
                (T("框选内缩（像素，避开边线）"), "inset"), (T("OCR没把握时改用AI看图"), "fallback"), (T("识别速度"), "ocr_speed"),
                (T("可信度门槛（%）"), "conf_gate"), (T("备用 1（额度用完时改用）"), "backup"), (T("备用 2"), "backup2"), (T("备用 3"), "backup3")]
        for i, (label, key) in enumerate(rows, 1):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky="e")
            if key == "trigger":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=list(TRIG), state="readonly", width=38)
            elif key == "font_size":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=["14", "18", "22", "28", "36", "48"],
                                  state="readonly", width=38)
            elif key == "click_delay":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=["0.3", "0.5", "0.8", "1.2", "2", "3"],
                                  state="readonly", width=38)
            elif key == "inset":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=["0", "4", "6", "10", "16"],
                                  state="readonly", width=38)
            elif key == "theme":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=[t["label"] for t in THEMES.values()],
                                  state="readonly", width=38)
            elif key == "alpha":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=ALPHAS, state="readonly", width=38)
            elif key == "skip_ruby":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=[RUBY_ON, RUBY_OFF],
                                  state="readonly", width=38)
            elif key == "ui_lang":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=list(UI_LANGS), state="readonly", width=38)
            elif key == "ocr_speed":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=list(SPEEDS.values()),
                                  state="readonly", width=38)
            elif key in ("backup", "backup2", "backup3"):
                bk_names = [n for n, pv in cfg["providers"].items() if pv.get("type") != "web"]
                wd = ttk.Combobox(f, textvariable=self.v[key], values=[self.bk_none if key == "backup" else self.bk_empty] + bk_names,
                                  state="readonly", width=38)
            elif key == "fallback":
                ai_names = [n for n, pv in cfg["providers"].items() if pv.get("type") in ("openai", "gemini", "claude")]
                wd = ttk.Combobox(f, textvariable=self.v[key], values=[FB_NONE] + ai_names,
                                  state="readonly", width=38)
            elif key == "float":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=[FLOAT_ON, FLOAT_OFF],
                                  state="readonly", width=38)
            elif key == "source":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=[AUTO] + LANGS,
                                  state="readonly", width=38)
            elif key == "target":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=lang_values(cfg),
                                  state="readonly", width=38)
            elif key == "type":
                wd = ttk.Combobox(f, textvariable=self.v[key], values=["openai", "gemini", "claude", "web", "ocr_google", "ocr_mymemory"],
                                  state="readonly", width=38)
            elif key == "model":
                wd = self.model_cb = ttk.Combobox(f, textvariable=self.v[key], values=[], width=38)  # 可手动输入，也可从下拉选
            else:
                wd = ttk.Entry(f, textvariable=self.v[key], width=40, show="*" if key == "api_key" else "")
                if key == "api_key":
                    self.key_entry = wd
            wd.grid(row=i, column=1, pady=2)
        ttk.Label(f, text=T("openai = 所有 OpenAI 兼容接口   web = 网页版   ocr_* = 本地OCR+在线翻译"),
                  foreground="gray").grid(row=23, column=1, sticky="w")
        ttk.Label(f, textvariable=self.note, foreground="#0a7").grid(row=24, column=1, sticky="w")
        acc = ttk.Frame(f)
        acc.grid(row=25, column=0, columnspan=2, pady=4)
        ttk.Button(acc, text=T("获取密钥（注册/登入）"), command=self.signup).pack(side="left", padx=4)
        ttk.Button(acc, text=T("粘贴密钥"), command=self.paste_key).pack(side="left", padx=4)
        self.showkey = tk.BooleanVar(value=False)
        ttk.Checkbutton(acc, text=T("显示密钥"), variable=self.showkey, command=self.toggle_key).pack(side="left", padx=4)
        acc2 = ttk.Frame(f)
        acc2.grid(row=26, column=0, columnspan=2, pady=2)
        ttk.Button(acc2, text=T("获取模型列表"), command=self.fetch_models).pack(side="left", padx=4)
        ttk.Button(acc2, text=T("测试连接"), command=self.test).pack(side="left", padx=4)
        for wd_ in f.winfo_children():  # 所有可输入的框都加上右键菜单
            if isinstance(wd_, ttk.Entry) and str(wd_.cget("state")) != "readonly":
                add_context_menu(wd_)
        ttk.Label(bottom, textvariable=self.msg, wraplength=440, foreground="gray").pack(fill="x")
        bar = ttk.Frame(bottom)
        bar.pack(pady=4)
        ttk.Button(bar, text=T("新增服务商"), command=self.add).pack(side="left", padx=4)
        ttk.Button(bar, text=T("删除当前"), command=self.delete).pack(side="left", padx=4)
        ttk.Button(bar, text=T("保存并使用"), command=self.save).pack(side="left", padx=4)
        self.load()
        f.update_idletasks()  # 窗口高度不超过屏幕；放不下的部分用滚动条
        canvas.configure(width=f.winfo_reqwidth(), height=min(f.winfo_reqheight(), max(220, int(sh_ * 0.62))))
        w.minsize(420, 300)
        w.update_idletasks()
        w.geometry("+%d+%d" % (max(0, (sw_ - w.winfo_reqwidth()) // 2), 20))
        self.bind_wheel(w)

    def bind_wheel(self, widget):
        """鼠标滚轮滚动设置页。下拉框自己也会响应滚轮（会误改选项），所以统一拦下来改成滚动页面"""
        def wheel(e):
            up = getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0
            self.canvas.yview_scroll(-3 if up else 3, "units")
            return "break"

        def rec(wd):
            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                wd.bind(ev, wheel)
            for c in wd.winfo_children():
                rec(c)
        rec(widget)

    def load(self):
        p = self.app.cfg["providers"][self.cur]
        for k in ("type", "base_url", "api_key", "model"):
            self.v[k].set(p.get(k, ""))
        self.note.set(T(p.get("note", "")))
        self.msg.set("")

    def commit(self):
        p = self.app.cfg["providers"].setdefault(self.cur, {})
        for k in ("type", "base_url", "api_key", "model"):
            p[k] = self.v[k].get().strip()
        p["api_key"] = "".join(p["api_key"].split()).strip("\"'")  # 密钥里不会有空格/换行，复制时多带的一并去掉
        self.app.cfg["source"] = self.v["source"].get().strip() or AUTO
        self.app.cfg["target"] = self.v["target"].get().strip() or LANGS[0]
        self.app.cfg["extra"] = self.v["extra"].get().strip()
        self.app.cfg["trigger"] = TRIG.get(self.v["trigger"].get(), "off")
        try:
            self.app.cfg["font_size"] = int(self.v["font_size"].get())
        except ValueError:
            pass
        self.app.cfg["float"] = self.v["float"].get() == FLOAT_ON
        self.app.cfg["skip_ruby"] = self.v["skip_ruby"].get() == RUBY_ON
        self.app.cfg["theme"] = THEME_LABELS.get(self.v["theme"].get(), "black")
        fb = self.v["fallback"].get()
        self.app.cfg["fallback"] = "" if fb == FB_NONE else fb
        bk = self.v["backup"].get()
        self.app.cfg["backup"] = "" if bk == self.bk_none else bk
        for _k in ("backup2", "backup3"):
            _v = self.v[_k].get()
            self.app.cfg[_k] = "" if _v == self.bk_empty else _v
        self.app.cfg["ui_lang"] = UI_LANGS.get(self.v["ui_lang"].get(), "auto")
        self.app.cfg["ocr_speed"] = SPEED_KEYS.get(self.v["ocr_speed"].get(), "normal")
        try:
            self.app.cfg["conf_gate"] = min(98, max(40, int(float(self.v["conf_gate"].get()))))
        except ValueError:
            pass
        try:
            self.app.cfg["alpha"] = min(1.0, max(0.4, int(self.v["alpha"].get().strip("% ")) / 100.0))
        except ValueError:
            pass
        try:
            self.app.cfg["inset"] = int(self.v["inset"].get())
        except ValueError:
            pass
        try:
            self.app.cfg["click_delay"] = float(self.v["click_delay"].get())
        except ValueError:
            pass

    def switch(self, _=None):
        self.commit()
        self.cur = self.sel.get()
        self.load()

    def add(self):
        name = simpledialog.askstring(T("新增服务商"), T("名称："), parent=self.w)
        if not name or name in self.app.cfg["providers"]:
            return
        self.commit()
        self.app.cfg["providers"][name] = dict(self.app.cfg["providers"][self.cur])
        self.cur = name
        self.sel.set(name)
        self.cb.configure(values=list(self.app.cfg["providers"]))
        self.load()

    def delete(self):
        provs = self.app.cfg["providers"]
        if len(provs) <= 1:
            return
        del provs[self.cur]
        self.cur = list(provs)[0]
        self.sel.set(self.cur)
        self.cb.configure(values=list(provs))
        self.load()

    def toggle_key(self):
        self.key_entry.config(show="" if self.showkey.get() else "*")

    def paste_key(self):
        txt = ""
        for getter in (lambda: self.w.clipboard_get(), lambda: self.w.selection_get(selection="PRIMARY")):
            try:  # 先试普通剪贴板（Ctrl+C），再试 Linux 的“选中即复制”（中键粘贴用的那个）
                txt = getter()
            except tk.TclError:
                txt = ""
            if txt.strip():
                break
        key = "".join(txt.split()).strip("\"'")
        if not key:
            self.msg.set(T("剪贴板里没有内容。请先在网页上选中密钥并复制。"))
            return
        self.v["api_key"].set(key)
        self.msg.set(T("已粘贴密钥（共 %d 个字符），请点“测试连接”。") % len(key))

    def fetch_models(self):
        self.commit()
        p = dict(self.app.cfg["providers"][self.cur])
        if p["type"] not in ("openai", "gemini", "claude"):
            self.msg.set(T("这个接口类型没有模型列表。"))
            return
        if not p["api_key"]:
            self.msg.set(T("请先填入 API 密钥。"))
            return
        self.msg.set(T("正在获取模型列表……"))
        box = []

        def run():
            try:
                names = list_models(p)
                box.append(("ok", names))
            except Exception as e:
                box.append(("err", friendly(e)))
        threading.Thread(target=run, daemon=True).start()
        self.w.after(300, self.fetched, box, p)

    def fetched(self, box, p):
        if not self.w.winfo_exists():
            return
        if not box:
            self.w.after(300, self.fetched, box, p)
            return
        kind, data = box[0]
        if kind == "err":
            self.msg.set(T("[失败] ") + data.replace(T("错误："), "")[:160])
            return
        self.model_cb.config(values=data)
        if not data:
            self.msg.set(T("没有取到模型。"))
            return
        cur = self.v["model"].get().strip()
        if p["type"] == "gemini" and cur not in data:
            new = pick_gemini(data)
            self.v["model"].set(new)
            self.msg.set(T("[成功] 共 %d 个可用模型。原来的“%s”不可用，已换成“%s”。点“保存并使用”生效。") % (len(data), cur, new))
        else:
            self.msg.set(T("[成功] 共 %d 个可用模型，已放进“模型名称”的下拉里，可以选择。") % len(data))

    def signup(self):
        url = self.app.cfg["providers"][self.cur].get("signup_url")
        if url:
            webbrowser.open(url)
        else:
            messagebox.showinfo(T("提示"), T("这个服务商没有预设注册链接，请到它的官网申请 API 密钥。"), parent=self.w)

    def test(self):
        self.commit()
        p = dict(self.app.cfg["providers"][self.cur])
        if p["type"] == "web":
            self.msg.set(T("网页模式不需要密钥，无需测试。先在浏览器里登入对应网站即可。"))
            return
        if p["type"].startswith("ocr_"):
            tl = lcode(self.app.cfg["target"])
            if not tl or tl == "auto":
                self.msg.set(T("[失败] 这个目标语言暂不支持在线翻译，请换一个。"))
                return
            self.msg.set(T("测试中……"))
            box = []

            def run2():
                try:
                    box.append(T("[成功] 翻译接口可用：Hello -> ") + TRANSLATORS[p["type"]](p, "Hello", "en", tl))
                except Exception as e:
                    box.append(T("[失败] ") + friendly(e))
            threading.Thread(target=run2, daemon=True).start()
            self.w.after(300, self.check, box)
            return
        local = "localhost" in p["base_url"] or "127.0.0.1" in p["base_url"]
        if not p["api_key"] and not local:
            self.msg.set(T("请先填入 API 密钥（点“获取密钥”去申请）。"))
            return
        img = Image.new("RGB", (64, 64), "white")
        buf = io.BytesIO()
        img.save(buf, "JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        self.msg.set(T("测试中……"))
        box = []

        def run():
            try:
                BACKENDS.get(p["type"], ask_openai)(p, "Reply with OK.", b64)
                box.append(T("[成功] 连接成功，密钥可用，模型支持看图。"))
            except Exception as e:
                if p["type"] == "gemini" and str(e).startswith("HTTP 404"):
                    try:  # 404 多半是模型名已下线：列出当前能用的模型，自动挑一个再试
                        names = list_models(p)
                        new = pick_gemini(names)
                        if new and new != p["model"]:
                            BACKENDS["gemini"](dict(p, model=new), "Reply with OK.", b64)
                            self.pending_model = (new, names)
                            box.append(T("[成功] 原来的模型“%s”已下线（404），已自动换成“%s”，连接成功。请点“保存并使用”。") % (p["model"], new))
                            return
                    except Exception:
                        pass
                box.append(T("[失败] ") + friendly(e))
        threading.Thread(target=run, daemon=True).start()
        self.w.after(300, self.check, box)

    def check(self, box):
        if not self.w.winfo_exists():
            return
        if box:
            self.msg.set(box[0])
            pm = getattr(self, "pending_model", None)
            if pm:  # 自动换了模型：把新模型填进框里，并放进下拉列表
                self.v["model"].set(pm[0])
                self.model_cb.config(values=pm[1])
                self.pending_model = None
        else:
            self.w.after(300, self.check, box)

    def save(self):
        self.commit()
        self.app.cfg["active"] = self.cur
        save_cfg(self.app.cfg)
        self.app.apply_lang()
        self.app.refresh()
        self.app.apply_settings()
        self.w.destroy()


# ---------------------------------------------------------------- 主程序
class App:
    def __init__(self, master=None, lang=None):
        """master=None：独立运行；master=某个 Tk 窗口：嵌入到别的程序（如 Artocarpus）里使用；
        lang：宿主程序当前的界面语言（"zh"/"en"），设置里选“自动”时跟随它"""
        self.cfg = load_cfg()
        self.host_lang = lang
        set_lang(resolve_lang(self.cfg, lang))
        self.master = master
        self.embedded = master is not None
        r = self.root = tk.Toplevel(master) if self.embedded else tk.Tk()
        self.host = master if self.embedded else r  # 悬浮窗口、弹窗的父窗口
        self.build_panel()
        self.win = None
        self.last_screen = self.last_shot = None
        self.last_hash = self.last_text = None
        self.busy = False
        self.tq = queue.Queue()
        self.listener = None
        reg = self.cfg.get("region")  # 载入上次保存的固定区域
        if reg:
            self.last_screen, self.last_shot = tuple(reg["screen"]), tuple(reg["shot"])
        self.q = queue.Queue()
        self.bar = None
        self.ai_block = {}  # 某个 AI 服务商被限额后，到什么时间之前先不要再请求它
        self.note_next = None
        self._last_img = None
        self._last_b64 = None
        self.imem = {}  # 画面记忆：同一个画面（比如村民重复的台词）直接用上次的译文，不再请求、不再花免费额度
        self.tmem = {}  # 翻译记忆
        self.hidden = []
        if self.embedded:
            r.protocol("WM_DELETE_WINDOW", self.hide_panel)
            r.withdraw()  # 嵌入时默认不显示面板，需要时再打开
        r.after(100, self.poll)
        r.after(300, self.place_corner)
        r.after(500, self.apply_trigger)

    def build_panel(self):
        r = self.root
        r.title(T("云雀AI翻译"))
        r.attributes("-topmost", True)
        r.resizable(False, False)
        f = self.full = ttk.Frame(r, padding=8)
        f.pack()
        self.prov = tk.StringVar(value=self.cfg["active"])
        self.cb = ttk.Combobox(f, textvariable=self.prov, values=list(self.cfg["providers"]),
                               state="readonly", width=18)
        self.cb.pack(fill="x", pady=2)
        self.cb.bind("<<ComboboxSelected>>", self.on_prov)
        ttk.Label(f, text=T("从（原文）：")).pack(anchor="w")
        self.src = tk.StringVar(value=self.cfg["source"])
        self.scb = ttk.Combobox(f, textvariable=self.src, values=[AUTO] + LANGS,
                                state="readonly", width=26)
        self.scb.pack(fill="x", pady=2)
        self.scb.bind("<<ComboboxSelected>>", self.on_source)
        ttk.Button(f, text=T("互换语言"), command=self.swap).pack(fill="x", pady=2)
        ttk.Label(f, text=T("到（译文）：")).pack(anchor="w")
        self.tgt = tk.StringVar(value=self.cfg["target"])
        self.tcb = ttk.Combobox(f, textvariable=self.tgt, values=lang_values(self.cfg),
                                state="readonly", width=26)
        self.tcb.pack(fill="x", pady=2)
        self.tcb.bind("<<ComboboxSelected>>", self.on_target)
        ttk.Button(f, text=T("框选区域并翻译（设定固定区域）"), command=self.select).pack(fill="x", pady=2)
        ttk.Button(f, text=T("翻译固定区域"), command=self.repeat).pack(fill="x", pady=2)
        ttk.Button(f, text=T("设置"), command=lambda: Settings(self)).pack(fill="x", pady=2)
        ttk.Button(f, text=T("显示悬浮条（全屏时用）"), command=self.show_bar).pack(fill="x", pady=2)
        ttk.Button(f, text=T("收起成小条"), command=self.collapse).pack(fill="x", pady=2)
        if self.embedded:
            ttk.Button(f, text=T("关闭此面板"), command=self.hide_panel).pack(fill="x", pady=2)
        self.status = ttk.Label(f, text=T("就绪"), foreground="gray")
        self.status.pack()
        m = self.mini = ttk.Frame(r, padding=3)  # 收起后的小条
        ttk.Button(m, text=T("框选"), width=5, command=self.select).pack(side="left")
        ttk.Button(m, text=T("翻译"), width=5, command=self.repeat).pack(side="left")
        ttk.Button(m, text=T("展开"), width=5, command=self.expand).pack(side="left")

    def apply_lang(self):
        """界面语言改变后：重建主面板、悬浮条和译文窗口，让它们立刻换成新语言"""
        old = LANG
        set_lang(resolve_lang(self.cfg, self.host_lang))
        if LANG == old:
            return
        was_bar = self.bar is not None and self.bar.winfo_exists() and self.bar.winfo_viewable()
        for c in list(self.root.winfo_children()):  # 只删面板上的控件，不删弹出的窗口
            if not isinstance(c, tk.Toplevel):
                c.destroy()
        self.build_panel()
        if not self.embedded:
            self.place_corner()
        for attr in ("bar", "win"):
            w = getattr(self, attr, None)
            if w is not None and w.winfo_exists():
                w.destroy()
            setattr(self, attr, None)
        if was_bar:
            self.show_bar()

    def set_host_lang(self, code):
        """宿主程序（Artocarpus）切换了界面语言时调用"""
        self.host_lang = code
        if self.cfg.get("ui_lang", "auto") == "auto":
            self.apply_lang()

    def place_corner(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        self.root.geometry("+%d+%d" % (max(0, self.root.winfo_screenwidth() - w - 10), 10))

    def collapse(self):
        self.full.pack_forget()
        self.mini.pack()
        self.place_corner()

    def expand(self):
        self.mini.pack_forget()
        self.full.pack()
        self.place_corner()

    def pair_text(self):
        return "%s \u2192 %s" % (lang_label(self.cfg.get("source", AUTO)), lang_label(self.cfg["target"]))

    def update_pair(self):
        if getattr(self, "bar_pair", None) is not None:
            self.bar_pair.set(self.pair_text())

    def refresh(self):
        self.update_pair()
        self.cb.configure(values=list(self.cfg["providers"]))
        self.prov.set(self.cfg["active"])
        self.tcb.configure(values=lang_values(self.cfg))
        self.tgt.set(self.cfg["target"])
        self.src.set(self.cfg["source"])

    def on_source(self, _=None):
        self.cfg["source"] = self.src.get()
        save_cfg(self.cfg)

    def swap(self):
        s_, t_ = self.cfg["source"], self.cfg["target"]
        if s_ == AUTO:
            return self.show(T("原文语言现在是“自动识别”，没法互换。\n请先在设置里选好具体的原文语言。"))
        self.cfg["source"], self.cfg["target"] = t_, s_
        save_cfg(self.cfg)
        self.refresh()
        self.show(T("语言方向已改为：%s\n（再按一次“互换”会换回来）") % self.pair_text())

    def on_target(self, _=None):
        self.cfg["target"] = self.tgt.get()
        save_cfg(self.cfg)

    def on_prov(self, _=None):
        self.cfg["active"] = self.prov.get()
        save_cfg(self.cfg)

    # ---- 面板 / 悬浮条（全屏时用）
    def show_panel(self):
        self.root.deiconify()
        self.root.lift()
        self.expand()

    def hide_panel(self):
        self.root.withdraw()

    def on_scrcpy_end(self):
        """宿主程序（Artocarpus）的 scrcpy 结束时调用：收起悬浮条和译文窗口"""
        if self.bar is not None and self.bar.winfo_exists():
            self.bar.withdraw()
        if self.win and self.win.winfo_exists():
            self.win.withdraw()

    def show_bar(self, expand=False):
        """悬浮条是唯一的控制窗口：展开时是一整条按钮，收起后只剩一个“翻译”小格子（点一下展开，按住可拖动）"""
        if self.bar is not None and self.bar.winfo_exists():
            self.bar.deiconify()
            self.bar.lift()
            if expand and self.cfg.get("bar_collapsed"):
                self.bar_set_collapsed(False)
            return
        b = self.bar = tk.Toplevel(self.host)
        b.overrideredirect(True)  # 无边框、不被窗口管理器接管，全屏时也能盖在上面
        b.attributes("-topmost", True)
        bg, fs = "#202020", ("sans-serif", 13, "bold")
        full = self.bar_full = tk.Frame(b, bg=bg, highlightbackground="#888", highlightthickness=1)
        grip = tk.Label(full, text=T(" 移动 "), bg=bg, fg="#bbb", font=fs, cursor="fleur")
        grip.pack(side="left")
        tk.Button(full, text=T("收起"), command=lambda: self.bar_set_collapsed(True), font=fs, bg="#333",
                  fg="white", relief="flat", padx=6).pack(side="left", padx=1, pady=2)
        for txt, cmd in ((T("框选"), self.select), (T("翻译"), self.repeat)):
            tk.Button(full, text=txt, command=cmd, font=fs, bg="#2d6a2d", fg="white", relief="flat",
                      padx=8).pack(side="left", padx=1, pady=2)
        for txt, cmd in ((T("译文"), self.show_last), (T("看区域"), self.flash_region), (T("互换"), self.swap),
                         (T("设置"), lambda: Settings(self))):
            tk.Button(full, text=txt, command=cmd, font=fs, bg="#333", fg="white", relief="flat",
                      padx=8).pack(side="left", padx=1, pady=2)
        self.bar_pair = tk.StringVar(value=self.pair_text())
        tk.Label(full, textvariable=self.bar_pair, bg=bg, fg="#7fdc7f", font=fs, padx=8).pack(side="left")
        cell = self.bar_cell = tk.Label(b, text=T(" 翻译 "), font=fs, bg="#2d4f8a", fg="white", padx=10, pady=5,
                                        cursor="fleur", highlightbackground="#888", highlightthickness=1)

        def start(e):
            self._bdx, self._bdy = e.x_root - b.winfo_x(), e.y_root - b.winfo_y()
            self._bx, self._by, self._bmoved = e.x_root, e.y_root, False

        def move(e):
            if abs(e.x_root - self._bx) + abs(e.y_root - self._by) > 5:
                self._bmoved = True
            if self._bmoved:
                b.geometry("+%d+%d" % (e.x_root - self._bdx, e.y_root - self._bdy))

        def end(e):
            if self._bmoved:
                self.cfg["bar_pos"] = [b.winfo_x(), b.winfo_y()]
                save_cfg(self.cfg)
            elif e.widget is cell:  # 在小格子上点一下（没拖动）= 展开
                self.bar_set_collapsed(False)
        for w in (grip, cell):
            w.bind("<ButtonPress-1>", start)
            w.bind("<B1-Motion>", move)
            w.bind("<ButtonRelease-1>", end)
        collapsed = self.cfg.get("bar_collapsed", False) and not expand
        (cell if collapsed else full).pack()
        b.update_idletasks()
        sw = b.winfo_screenwidth()
        pos = self.cfg.get("bar_pos") or [max(0, sw // 2 - b.winfo_reqwidth() // 2), 10]
        b.geometry("+%d+%d" % (min(max(0, pos[0]), sw - 60), max(0, pos[1])))
        self.cfg["bar_collapsed"] = collapsed

    def bar_set_collapsed(self, collapsed):
        b = self.bar
        if collapsed:
            self.bar_full.pack_forget()
            self.bar_cell.pack()
        else:
            self.bar_cell.pack_forget()
            self.bar_full.pack()
        b.update_idletasks()
        sw = b.winfo_screenwidth()
        x = max(0, min(b.winfo_x(), sw - b.winfo_reqwidth()))  # 展开后别超出屏幕右边
        b.geometry("+%d+%d" % (x, b.winfo_y()))
        self.cfg["bar_collapsed"] = collapsed
        self.cfg["bar_pos"] = [x, b.winfo_y()]
        save_cfg(self.cfg)

    def show_last(self):
        if self.win and self.win.winfo_exists():
            self.win.deiconify()
            self.win.lift()
        elif self.last_text:
            self.show(self.last_text)

    def flash_region(self, ms=2000):
        """用红色边框在屏幕上圈出目前的翻译区域，方便确认选得准不准（边框画在区域外面，不会被识别到）"""
        if not self.last_screen:
            return self.show(T("还没有选择区域。请先点“框选”。"))
        x0, y0, x1, y1 = [int(v) for v in self.last_screen]
        t = 4
        parts = [(x0 - t, y0 - t, x1 - x0 + 2 * t, t), (x0 - t, y1, x1 - x0 + 2 * t, t),
                 (x0 - t, y0, t, y1 - y0), (x1, y0, t, y1 - y0)]
        wins = []
        for x, y, w, h in parts:
            tw = tk.Toplevel(self.host)
            tw.overrideredirect(True)
            tw.attributes("-topmost", True)
            tw.configure(bg="red")
            tw.geometry("%dx%d+%d+%d" % (w, h, x, y))
            wins.append(tw)

        def done():
            for w in wins:
                try:
                    w.destroy()
                except Exception:
                    pass
        self.root.after(ms, done)

    def capture(self):
        """截全屏前先把自己的窗口都藏起来，截完由 restore() 恢复"""
        self.hidden = []
        for w in (self.root, self.win, self.bar):
            try:
                if w is not None and w.winfo_exists() and w.winfo_viewable():
                    w.withdraw()
                    self.hidden.append(w)
            except Exception:
                pass
        self.root.update()
        time.sleep(0.25)
        return grab_screen()

    def restore(self):
        for w in self.hidden:
            try:
                if w.winfo_exists():
                    w.deiconify()
                    w.lift()
            except Exception:
                pass
        self.hidden = []

    def select(self):
        shot = self.capture()
        Selector(self.host, shot, self.on_selected, old=self.last_screen)

    def on_selected(self, res):
        self.restore()
        if not res:
            return
        self.last_screen, self.last_shot, crop = res
        self.cfg["region"] = {"screen": list(self.last_screen), "shot": list(self.last_shot)}
        save_cfg(self.cfg)
        self.flash_region()
        self.translate(crop)

    def repeat(self):
        if not self.last_shot:
            return self.show(T("请先点“框选”，选好对话框的位置。"))
        if self.busy:
            return
        try:
            img = grab_region(self.last_shot)
        except Exception as e:
            return self.show(friendly(e))
        self.translate(img)

    def translate(self, img):
        m = int(self.cfg.get("max_side", 1600))
        if max(img.size) > m:
            img.thumbnail((m, m), Image.LANCZOS)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=88)
        data = buf.getvalue()
        self._last_b64 = base64.b64encode(data).decode("ascii")  # 备用的 AI 看图也要用这张图
        model = str(self.cfg["providers"].get(self.cfg["active"], {}).get("model", ""))
        h = hashlib.md5(data).hexdigest() + self.cfg["active"] + model + self.cfg["target"] + self.cfg["source"]
        if h in self.imem:  # 同一个画面：直接用记忆里的译文
            return self.show(self.imem[h] + "\n\n" + T("（来自记忆：同一画面，没有重新请求）"))
        p = dict(self.cfg["providers"][self.cfg["active"]])
        if p["type"] == "web":
            return self.web_mode(img, p)
        if p["type"].startswith("ocr_"):
            return self.ocr_mode(img, p, h)
        self._last_img = img
        until = self.ai_block.get(self.cfg["active"], 0)
        if time.time() < until and self.pick_backup(self.cfg["active"]):  # 刚被限额：先不碰它，直接用备用，免得白等
            return self.run_backup(h, until - time.time())
        p["_name"] = self.cfg["active"]
        local = "localhost" in p["base_url"] or "127.0.0.1" in p["base_url"]
        if not p.get("api_key") and not local:
            return self.show(T("还没有填写 API 密钥。\n请点主窗口的“设置”，填入当前服务商的密钥后保存。"))
        self.busy = True
        self.show(T("翻译中……"))
        system = build_system(self.cfg)
        b64 = base64.b64encode(data).decode("ascii")
        self.status.configure(text=T("请求中…"))
        threading.Thread(target=self.work, args=(p, system, b64, h), daemon=True).start()

    def apply_trigger(self):
        if self.cfg.get("trigger", "off") == "off" or self.listener:
            return
        if not pmouse:
            self.status.configure(text=T("鼠标触发需要 pynput"))
            if not getattr(self, "pynput_warned", False):  # 只提醒一次，不要每次都弹
                self.pynput_warned = True
                messagebox.showinfo(T("需要安装 pynput"), (
                    T("鼠标触发需要 pynput（仅支持 X11）。\n\n"
                    "程序现在用的 Python 是：\n%s\n\n"
                    "请在终端运行这一条（装到程序自己用的 Python 里）：\n"
                    "%s -m pip install pynput\n\n"
                    "装完重新启动程序。\n\n导入失败的原因：%s") % (sys.executable, sys.executable, PYNPUT_ERR or T("未知"))))
            return
        state = {"t": 0.0}

        def on_click(x, y, button, pressed):
            mode = self.cfg.get("trigger", "off")
            if mode == "click":  # 左键在翻译区域内点一下（这一下照常传给游戏，不会被拦截）
                r = self.last_screen
                if (not pressed) and button == pmouse.Button.left and r and r[0] <= x <= r[2] and r[1] <= y <= r[3]:
                    self.tq.put(2)
                return
            if not pressed:
                return
            if mode == "middle" and button == pmouse.Button.middle:
                self.tq.put(1)
            elif mode == "right2" and button == pmouse.Button.right:
                now = time.time()
                if now - state["t"] < 0.45:
                    state["t"] = 0.0
                    self.tq.put(1)
                else:
                    state["t"] = now
        self.listener = pmouse.Listener(on_click=on_click)
        self.listener.daemon = True
        self.listener.start()

    def apply_settings(self):
        if self.win and self.win.winfo_exists():  # 字号、窗口样式改了，需要重建译文窗口
            self.win.destroy()
        self.win = None
        self.apply_trigger()

    def ocr_mode(self, img, p, h):
        g = prepare_ocr_image(img, int(self.cfg.get("inset", 6)),
                              ruby=bool(self.cfg.get("skip_ruby", True)) and lang_name(self.cfg.get("source", AUTO)) in ("日语", T("自动识别")))  # 内缩避开边框 + 去线 + 放大
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        g.save(path)
        try:  # 留一张“OCR 实际看到的图”方便排查（只保留最新一张，放在 SkylarkTranslator 文件夹里）
            os.makedirs(SHOT_DIR, exist_ok=True)
            g.save(os.path.join(SHOT_DIR, "ocr_last.png"))
        except OSError:
            pass
        b64 = None
        if self.cfg.get("fallback"):
            im2 = img.convert("RGB")
            m = int(self.cfg.get("max_side", 1600))
            if max(im2.size) > m:
                im2.thumbnail((m, m), Image.LANCZOS)
            buf = io.BytesIO()
            im2.save(buf, "JPEG", quality=88)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        self.busy = True
        self.show(T("识别并翻译中……"))
        self.status.configure(text=T("请求中…"))
        threading.Thread(target=self.work_ocr, args=(p, path, h, b64), daemon=True).start()

    def work_ocr(self, p, path, h, b64=None):
        try:
            tl = lcode(self.cfg["target"])
            if not tl or tl == "auto":
                raise RuntimeError(T("这个目标语言暂不支持在线翻译，请换一个。"))
            sl = lcode(self.cfg.get("source", AUTO)) or "auto"
            t0 = time.time()
            text, lang, installed, score = run_ocr(path, self.cfg.get("source", AUTO), self.cfg.get("skip_ruby", True),
                                                   self.cfg.get("ocr_speed", "normal"))
            t_ocr = time.time() - t0
            gate = int(self.cfg.get("conf_gate", 85))
            fb = self.cfg.get("fallback", "")
            fp = self.cfg["providers"].get(fb) if fb else None
            ai_err = ""
            if fp and b64 and (score < gate or not text) and fp.get("type") in BACKENDS and fp.get("api_key"):
                try:  # OCR 没把握：直接把截图交给 AI 看图翻译，不再硬翻一堆可能是乱码的文字
                    ai = split_reply(BACKENDS[fp["type"]](dict(fp), build_system(self.cfg), b64), str(self.cfg.get("target", "")))[0]
                    self.q.put((T("（文字识别没把握，已自动改用 AI 看图：%s）\n\n%s") % (fb, ai), h, True))
                    return
                except Exception as e:
                    ai_err = T("\n\n（备用的 AI 看图也失败了：%s）") % friendly(e).replace(T("错误："), "")[:150]
            auto = self.cfg.get("source", AUTO) == AUTO
            tip = ""
            if auto and "jpn" not in installed:
                tip = T("\n\n提示：还没装日文识别包。日文游戏请运行 sudo apt install tesseract-ocr-jpn，并在设置里把“原文语言”选成日语。")
            if not text:
                self.q.put((T("（未识别到文字）") + tip + ai_err, h, False))
                return
            key = (p["type"], sl, tl, text)  # 翻译记忆：同一句话（比如村民重复的台词）直接用上次的译文
            t1 = time.time()
            if key in self.tmem:
                out, t_tr = self.tmem[key], None
            else:
                out = TRANSLATORS[p["type"]](p, text, sl, tl)
                t_tr = time.time() - t1
                if len(self.tmem) >= 400:
                    self.tmem.pop(next(iter(self.tmem)))
                self.tmem[key] = out
            timing = T("识别 %.1f 秒，%s") % (t_ocr, T("翻译用了记忆，没重新请求") if t_tr is None else T("翻译 %.1f 秒") % t_tr)
            if auto:
                tip += T("\n\n（自动识别判断为：%s。不准的话，请在设置里直接指定原文语言）") % lang
            if score < gate:
                tip += (T("\n\n注意：这次识别的可信度很低（%d%%），译文很可能不准。请点“看区域”确认只框住了文字，"
                        "或改用能直接看图的 AI 服务商。") % score)
            tip += ai_err
            self.q.put((out + tip + T("\n\n—— 原文（OCR 识别结果，可信度 %d%%；%s）——\n") % (score, timing) + text, h, True))
        except Exception as e:
            self.q.put((friendly(e), h, False))
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def web_mode(self, img, p):
        os.makedirs(SHOT_DIR, exist_ok=True)
        path = os.path.join(SHOT_DIR, "last.png")  # 每次覆盖同一个文件，不会越积越多
        for old in (os.path.expanduser("~/skylark_last.png"),):  # 清掉旧版本留在主文件夹的文件
            try:
                os.remove(old)
            except OSError:
                pass
        img.convert("RGB").save(path, "PNG")
        copied = False
        try:
            subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-i", path],
                           timeout=5, check=True)
            time.sleep(0.3)  # 回读确认剪贴板里真的有图片，不假装成功
            r = subprocess.run(["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            copied = b"image/png" in r.stdout
        except Exception:
            pass
        url = p.get("base_url") or ""
        if not hasattr(self, "opened"):
            self.opened = set()
        if url and url not in self.opened:  # 同一个网页只自动打开一次，之后复用已开的标签页
            webbrowser.open(url)
            self.opened.add(url)
        src = self.cfg.get("source", AUTO)
        ask = T("请识别图片中的文字，并翻译成【%s】，只输出译文。") % self.cfg["target"]
        if src != AUTO:
            ask = T("图片中的文字是【%s】。") % src + ask
        if copied:
            msg = T("[成功] 截图已复制到剪贴板。\n\n先点一下网页聊天框，再按 Ctrl+V 粘贴。\n粘贴不了就点聊天框的 + 号，再选“上传文件”，选 主文件夹/SkylarkTranslator/last.png。\n\n然后发送这句话：\n\n") + ask
        else:
            msg = (T("截图已保存到：\n%s\n\n（自动复制到剪贴板没有成功，直接上传这个文件即可）\n"
                   "到网页里点上传图片，选这个文件，然后发送：\n\n%s") % (path, ask))
        self.show(msg, corner=True)
        self.collapse()

    def count_use(self, name):
        """记下今天用了某个 AI 服务商多少次（只算成功的），让你心里有数"""
        today = time.strftime("%Y-%m-%d")
        u = self.cfg.setdefault("usage", {})
        if u.get("date") != today:
            u.clear()
            u["date"], u["counts"] = today, {}
        u["counts"][name] = u["counts"].get(name, 0) + 1
        save_cfg(self.cfg)
        return u["counts"][name]

    def pick_backup(self, exhausted):
        """按顺序找第一个可用的备用：跳过刚用完额度的、正在冷却的、没填密钥的；免费 OCR 永远可用"""
        now = time.time()
        for name, pv in backup_chain(self.cfg):
            if name == exhausted:
                continue
            if str(pv.get("type", "")).startswith("ocr_"):
                return name, pv
            local = "localhost" in pv.get("base_url", "") or "127.0.0.1" in pv.get("base_url", "")
            if self.ai_block.get(name, 0) > now or (not pv.get("api_key") and not local):
                continue
            return name, pv
        return None

    def run_backup(self, h, secs, exhausted=None):
        exhausted = exhausted or self.cfg["active"]
        bk = self.pick_backup(exhausted)
        if not bk:
            self.busy = False
            return self.show(T("额度用完了，也没有可用的备用服务商。请在设置里选一个备用，或稍后再试。"))
        name, pv = bk
        when = T("大约 %d 分钟后会再试 AI。") % max(1, int(round(secs / 60.0))) if secs >= 90 \
            else T("大约 %d 秒后会再试 AI。") % max(1, int(secs))
        self.note_next = T("（%s 额度用完或请求太频繁，已自动改用 %s。%s）") % (exhausted, name, when)
        hb = h + "|backup"
        if str(pv.get("type", "")).startswith("ocr_"):
            return self.ocr_mode(self._last_img, pv, hb)
        p = dict(pv, _name=name)  # 备用的也是 AI 看图：它自己再被限额的话，会接着往下一级走
        self.busy = True
        self.show(T("翻译中……"))
        threading.Thread(target=self.work, args=(p, build_system(self.cfg), self._last_b64, hb), daemon=True).start()

    def work(self, p, system, b64, h):
        try:
            fn = BACKENDS.get(p["type"], ask_openai)
            tgt = str(self.cfg.get("target", ""))
            text, ok = split_reply(fn(p, system, b64), tgt)
            if not ok:  # 模型把原文抄回来了：加强提示重试一次（多用 1 次请求）
                text2, ok2 = split_reply(fn(p, system + "\n注意：【译文】必须是翻译后的目标语言，不能照抄原文。", b64), tgt)
                text = text2 if (ok2 or text2) else text
            name = p.get("_name", "")
            n = self.count_use(name) if name else 0
            self.q.put((text, h, True, ("\n\n" + T("（%s：今天已翻译 %d 次）") % (name, n)) if n else ""))
        except Exception as e:
            secs = quota_secs(e)
            if secs and self._last_img is not None and self.pick_backup(p.get("_name", "")):
                self.q.put(("__quota__", h, False, secs, p.get("_name", "")))
            else:
                self.q.put((friendly(e), h, False))

    def poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                text, h, ok = item[:3]
                extra = item[3] if len(item) > 3 and isinstance(item[3], str) else ""
                self.busy = False
                if text == "__quota__":  # AI 被限额：记下冷却时间，这一次直接改用免费备用
                    self.ai_block[item[4] or self.cfg["active"]] = time.time() + item[3]
                    self.run_backup(h, item[3], item[4])
                    continue
                if ok:
                    self.last_hash, self.last_text = h, text
                    if len(self.imem) >= 300:
                        self.imem.pop(next(iter(self.imem)))
                    self.imem[h] = text
                self.status.configure(text=T("就绪"))
                disp = text + extra
                if self.note_next:
                    disp, self.note_next = self.note_next + "\n\n" + disp, None
                self.show(disp)
        except queue.Empty:
            pass
        try:
            while True:
                item = self.tq.get_nowait()
                if item == 2:  # 区域内点击：等游戏文字显示完再翻，连点只算最后一次
                    if getattr(self, "click_job", None):
                        self.root.after_cancel(self.click_job)
                    ms = int(float(self.cfg.get("click_delay", 0.8)) * 1000)
                    self.click_job = self.root.after(ms, self.click_fire)
                else:
                    self.repeat()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def click_fire(self):
        self.click_job = None
        if self.busy:  # 上一次还在翻译，稍等再来
            self.click_job = self.root.after(400, self.click_fire)
            return
        self.repeat()

    def show(self, text, corner=False):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x0, y0, x1, y1 = self.last_screen or (sw // 4, sh // 2, sw * 3 // 4, sh * 3 // 4)
        fs = int(self.cfg.get("font_size", 20))
        if not (self.win and self.win.winfo_exists()):
            self.build_win(fs)
        w = max(x1 - x0, fs * 20)
        cpl = max(8, int(w / (fs * 1.4)))
        lines = text.count("\n") + 1 + len(text) // cpl
        h = min(int(sh * 0.5), 100 + int(lines * fs * 1.9))
        y = y1 + 8 if y1 + 8 + h < sh else max(0, y0 - h - 8)
        x = max(0, min(x0, sw - w))
        geo = self.cfg.get("win_geo")  # 你拖动/缩放过的位置和大小，优先使用
        if geo and not corner:
            x, y, w, h = geo
        if corner:  # 网页模式：放右下角，避免挡住网页的上传按钮和输入框
            w = 380
            x, y = sw - w - 10, sh - h - 70
        if getattr(self, "hide_job", None):
            try:
                self.win.after_cancel(self.hide_job)
            except Exception:
                pass
            self.hide_job = None
        self.win.geometry("%dx%d+%d+%d" % (w, h, max(0, min(x, sw - 60)), max(0, min(y, sh - 40))))
        self.pair_txt.set(T("%s    按住这里拖动") % self.pair_text())
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", text)
        mark = self.txt.search(T("—— 原文"), "1.0", "end")  # 下面附的 OCR 原文调暗，译文更突出
        if mark:
            self.txt.tag_add("dim", mark, "end")
        self.win.deiconify()
        self.win.lift()
        if corner:
            self.hide_job = self.win.after(30000, self.win.withdraw)

    def build_win(self, fs):
        win = self.win = tk.Toplevel(self.host)
        win.title(T("译文"))
        win.attributes("-topmost", True)
        if self.cfg.get("float", True):
            win.overrideredirect(True)  # 不被窗口管理器接管，就不会抢走游戏的焦点
        th = THEMES.get(self.cfg.get("theme", "black"), THEMES["black"])
        bg = th["bar"]
        try:  # 半透明（系统没有窗口合成效果时此项不起作用，不影响使用）
            win.attributes("-alpha", float(self.cfg.get("alpha", 0.9)))
        except Exception:
            pass
        top = tk.Frame(win, bg=bg)
        top.pack(side="top", fill="x")
        self.pair_txt = tk.StringVar(value=T(" 按住这里拖动"))
        grip = tk.Label(top, textvariable=self.pair_txt, bg=bg, fg=th["barfg"], cursor="fleur", font=("sans-serif", 12))
        grip.pack(side="left", fill="x", expand=True)
        tk.Button(top, text=T("关闭"), command=win.withdraw, bg="#7a2a2a", fg="white", relief="flat",
                  font=("sans-serif", 12, "bold")).pack(side="right", padx=1, pady=1)
        tk.Button(top, text=T("重翻"), command=self.repeat, bg="#2f5d2f", fg="white", relief="flat",
                  font=("sans-serif", 12)).pack(side="right", padx=1, pady=1)
        bottom = tk.Frame(win, bg=bg)
        bottom.pack(side="bottom", fill="x")
        tk.Button(bottom, text=T("复位位置"), command=self.reset_geo, bg="#333", fg="white", relief="flat",
                  font=("sans-serif", 11)).pack(side="left", padx=2, pady=1)
        tk.Button(bottom, text=T("换配色"), command=self.cycle_theme, bg="#333", fg="white", relief="flat",
                  font=("sans-serif", 11)).pack(side="left", padx=2, pady=1)
        rz = tk.Label(bottom, text=T("拖这里缩放"), bg=bg, fg=th["barfg"], cursor="bottom_right_corner",
                      font=("sans-serif", 11))
        rz.pack(side="right")
        self.txt = tk.Text(win, wrap="word", font=("sans-serif", fs), padx=8, pady=6, bg=th["bg"], fg=th["fg"],
                           insertbackground=th["fg"], selectbackground=th["sel"], selectforeground=th["fg"],
                           relief="flat", highlightthickness=0, borderwidth=0)
        self.txt.tag_configure("dim", foreground=th["dim"], font=("sans-serif", max(10, int(fs * 0.7))))
        self.txt.pack(fill="both", expand=True)

        def gstart(e):
            self._wdx, self._wdy = e.x_root - win.winfo_x(), e.y_root - win.winfo_y()

        def gmove(e):
            win.geometry("+%d+%d" % (e.x_root - self._wdx, e.y_root - self._wdy))

        def rmove(e):
            win.geometry("%dx%d" % (max(260, e.x_root - win.winfo_x()), max(120, e.y_root - win.winfo_y())))
        grip.bind("<ButtonPress-1>", gstart)
        grip.bind("<B1-Motion>", gmove)
        grip.bind("<ButtonRelease-1>", lambda e: self.save_geo())
        rz.bind("<B1-Motion>", rmove)
        rz.bind("<ButtonRelease-1>", lambda e: self.save_geo())
        self.txt.bind("<Button-3>", lambda e: win.withdraw())
        win.bind("<Escape>", lambda e: win.withdraw())

    def cycle_theme(self):
        order = list(THEMES)
        cur = self.cfg.get("theme", "black")
        self.cfg["theme"] = order[(order.index(cur) + 1) % len(order)] if cur in order else order[0]
        save_cfg(self.cfg)
        text = self.txt.get("1.0", "end").strip()

        def redo():
            if self.win and self.win.winfo_exists():
                self.win.destroy()
            self.win = None
            self.show(text)
        self.root.after(10, redo)

    def save_geo(self):
        w = self.win
        self.cfg["win_geo"] = [w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height()]
        save_cfg(self.cfg)

    def reset_geo(self):
        self.cfg["win_geo"] = None
        save_cfg(self.cfg)
        self.show(self.txt.get("1.0", "end").strip())

if __name__ == "__main__":
    App().root.mainloop()
