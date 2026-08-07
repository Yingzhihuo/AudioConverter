# Audio Converter

一个基于 PySide6 和 FFmpeg 开发的桌面音频工具，提供批量格式转换和音频元数据编辑功能。

> 项目目前处于早期开发阶段，主要面向 Windows 桌面环境。

## 功能特性

- 批量添加并转换多个音频文件
- 支持输出为 MP3、AAC、FLAC、WAV、Opus 和 OGG Vorbis
- 实时显示 FFmpeg 转换日志和任务进度
- 读取与修改音频的常用元数据：
  - 标题
  - 艺术家
  - 专辑
  - 专辑艺术家
  - 流派
  - 年份
  - 音轨号
- 可在设置中指定 FFmpeg 路径和默认输出目录
- 转换任务在后台线程运行，避免界面卡死

## 界面预览

项目暂未提供界面截图。后续可将截图放入 `assets/` 目录，并在这里展示。

## 环境要求

- Python 3.10 或更高版本
- FFmpeg（同时需要 `ffmpeg` 和 `ffprobe`）
- Windows 10/11（当前主要测试平台）

FFmpeg 与 FFprobe 应位于同一目录。例如：

```text
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

可从 [FFmpeg 官网](https://ffmpeg.org/download.html) 获取 FFmpeg。

## 安装

克隆项目并进入项目目录：

```powershell
git clone <仓库地址>
cd AudioConverter
```

建议创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## 配置

首次运行时，程序会在项目根目录创建 `config.json`。也可以在程序的“设置”页面完成配置。

配置示例：

```json
{
  "ffmpeg_path": "C:\\ffmpeg\\bin\\ffmpeg.exe",
  "ffprobe_path": "C:\\ffmpeg\\bin\\ffprobe.exe",
  "default_output": "output"
}
```

其中：

| 配置项 | 说明 |
| --- | --- |
| `ffmpeg_path` | `ffmpeg.exe` 的路径 |
| `ffprobe_path` | `ffprobe.exe` 的路径，当前应与 FFmpeg 位于同一目录 |
| `default_output` | 转换后文件的默认输出目录 |

`config.json` 包含本机路径，已被 Git 忽略，不建议提交到仓库。

## 运行

在项目根目录执行：

```powershell
python main.py
```

基本使用流程：

1. 在“格式转换”页面选择一个或多个音频文件。
2. 选择目标编码格式。
3. 确认设置页面中的输出目录和 FFmpeg 路径。
4. 点击“开始转换”，在界面下方查看进度和日志。
5. 如需编辑标签，可在“修改信息”页面选择文件并保存元数据。

## 项目结构

```text
AudioConverter/
├── assets/                 # 图片等静态资源
├── src/
│   ├── config/             # 配置读写
│   ├── core/               # 转换与 FFmpeg 调用
│   ├── models/             # 数据模型
│   └── utils/              # 通用工具
├── ui/                     # PySide6 用户界面
├── main.py                 # 程序入口
├── requirements.txt        # Python 依赖
└── README.md
```

## 开发计划

- [ ] 自动发现本机 FFmpeg
- [ ] 增加码率、采样率和声道设置
- [ ] 支持拖放添加文件
- [ ] 增加任务取消和输出文件冲突处理
- [ ] 完善异常提示和运行日志
- [ ] 添加自动化测试和代码质量检查
- [ ] 打包为可直接安装的 Windows 应用

## 已知限制

- 当前需要用户自行安装并配置 FFmpeg。
- 配置文件保存在项目根目录，尚未迁移至系统用户配置目录。
- 尚未提供安装包，需要通过 Python 源码运行。
- 项目仍在早期阶段，暂未建立稳定版本兼容承诺。

## 参与开发

欢迎通过 Issue 提交问题或功能建议。提交代码前，请尽量保持改动范围清晰，并说明测试方式和结果。
