# Audio Converter

一款基于 PySide6 与 FFmpeg 开发的 Windows 桌面音频工具，支持批量格式转换和常用音频元数据编辑。

> 当前版本：v0.1.0（早期测试版）

## 主要功能

- 批量添加和转换多个音频文件
- 支持以下输出格式：
  - MP3
  - AAC（M4A）
  - FLAC
  - WAV
  - Opus
  - OGG Vorbis
- 实时显示转换进度和 FFmpeg 日志
- 在后台线程中执行转换，避免界面卡死
- 读取和修改常用音频信息：
  - 标题
  - 艺术家
  - 专辑
  - 专辑艺术家
  - 流派
  - 年份
  - 音轨号
- 支持设置默认输出目录和自定义 FFmpeg 路径
- Windows 发布版内置 FFmpeg，无需用户单独安装

## 下载与使用

普通用户可以前往项目的 [Releases 页面](https://github.com/Yingzhihuo/AudioConverter/releases) 下载最新 Windows 压缩包。

使用步骤：

1. 下载 `AudioConverter-版本号-windows-x64.zip`。
2. 将压缩包完整解压到本地目录。
3. 双击 `AudioConverter.exe`。
4. 选择音频文件和输出编码，然后点击“开始转换”。

请勿只复制 `AudioConverter.exe`。程序运行还需要压缩包内的 `_internal` 目录。

发布版已经包含 `ffmpeg.exe` 和 `ffprobe.exe`。程序会优先使用设置中有效的 FFmpeg 路径；如果没有配置，则自动使用随程序打包的版本。

## 从源码运行

### 环境要求

- Windows 10/11
- Python 3.10 或更高版本
- FFmpeg 和 FFprobe

克隆仓库：

```powershell
git clone https://github.com/Yingzhihuo/AudioConverter.git
cd AudioConverter
```

创建并激活虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 禁止执行激活脚本，也可以在后续命令中直接使用 `.venv\Scripts\python.exe`。

安装依赖：

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

将 FFmpeg 文件放入以下位置：

```text
tools/
├── ffmpeg.exe
└── ffprobe.exe
```

`ffplay.exe` 不是本项目的运行依赖。`tools/` 中的第三方二进制文件不会提交到 Git 仓库。

启动程序：

```powershell
python main.py
```

也可以在程序右上角的“设置”页面选择其他 `ffmpeg.exe`。`ffprobe.exe` 需要与其位于同一目录。

## 配置说明

程序首次运行时会在当前工作目录创建 `config.json`：

```json
{
  "ffmpeg_path": "",
  "ffprobe_path": "",
  "default_output": "output"
}
```

| 配置项 | 说明 |
| --- | --- |
| `ffmpeg_path` | 用户指定的 `ffmpeg.exe` 路径；无有效配置时使用内置版本 |
| `ffprobe_path` | 预留的 FFprobe 路径配置；当前程序从 FFmpeg 所在目录查找 FFprobe |
| `default_output` | 转换文件的默认输出目录 |

`config.json` 通常包含本机路径，因此已被 Git 忽略。

## 构建 Windows 发布版

项目使用 PyInstaller 的 `onedir` 模式构建。打包前确认以下文件存在：

```text
tools/ffmpeg.exe
tools/ffprobe.exe
```

安装 PyInstaller：

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
```

根据项目内的 `AudioConverter.spec` 构建：

```powershell
.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  AudioConverter.spec
```

构建结果位于：

```text
dist/AudioConverter/
├── AudioConverter.exe
└── _internal/
    └── tools/
        ├── ffmpeg.exe
        └── ffprobe.exe
```

发布时应压缩整个 `dist/AudioConverter` 目录，并将压缩包上传到 GitHub Releases；不要把 `dist/`、ZIP 或 RAR 发布文件提交进 Git 仓库。

## 项目结构

```text
AudioConverter/
├── src/
│   ├── config/             # 配置读写
│   ├── core/               # 音频转换和 FFmpeg 调用
│   ├── models/             # 转换任务等数据模型
│   └── utils/              # 通用工具
├── tools/                  # 本地 FFmpeg 文件（Git 忽略）
├── ui/                     # PySide6 用户界面
├── AudioConverter.spec     # PyInstaller 构建配置
├── main.py                 # 程序入口
├── requirements.txt        # Python 运行依赖
└── README.md
```

## 已知限制

- 当前主要面向 Windows 10/11，尚未测试 macOS 和 Linux。
- 配置文件仍保存在当前工作目录，尚未迁移到系统用户配置目录。
- 输出文件重名时默认由 FFmpeg 覆盖，暂未提供冲突处理选项。
- 暂不支持取消正在执行的转换任务。
- 尚未建立自动化测试和持续集成流程。

## 后续计划

- [ ] 支持码率、采样率和声道设置
- [ ] 支持拖放添加文件
- [ ] 增加任务取消功能
- [ ] 增加输出文件重名处理
- [ ] 改进异常提示和日志展示
- [ ] 将配置保存到 Windows 用户配置目录
- [ ] 添加自动化测试和代码质量检查
- [ ] 增加程序图标与安装程序

## 反馈与贡献

如果遇到问题或有功能建议，欢迎通过 [GitHub Issues](https://github.com/Yingzhihuo/AudioConverter/issues) 提交反馈。

提交代码时，请尽量说明改动内容、测试方式和测试结果。
