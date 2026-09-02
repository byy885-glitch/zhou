# 笔记本信息采集工具

一个简单的跨平台笔记本硬件信息采集脚本，支持 Windows / Linux / macOS。

## 功能

采集以下信息并输出为 JSON 文件 + 控制台打印：

- ✅ 系统信息（OS、版本、主机名、架构）
- ✅ CPU 信息（型号、核心数、频率、使用率）
- ✅ 内存信息（总量、使用率、插槽详情）
- ✅ 磁盘信息（逻辑分区、物理磁盘型号）
- ✅ 显卡信息（型号、显存、驱动、温度、使用率）
- ✅ 网卡信息（名称、IP、MAC、状态、流量）
- ✅ 电池信息（电量、健康度、循环次数、充电状态）
- ✅ BIOS/主板信息（厂商、型号、序列号、版本）
- ✅ 显示器信息（分辨率、型号）

## 快速开始

### Windows 用户（最简单，推荐）

1. **安装依赖**（打开 cmd 或 PowerShell 执行一次）：
```cmd
py -m pip install psutil
```

2. **双击 `run.bat`** 即可运行，自动检测 Python 环境，运行完成后暂停显示结果。

### 命令行运行

```bash
# Windows（推荐用 py，python 可能是商店别名无反应）
py laptop_info.py

# Linux / macOS
python3 laptop_info.py
```

> **Linux 下建议用 sudo 运行**，可以获取更完整的内存插槽、BIOS 等信息：
> ```bash
> sudo python3 laptop_info.py
> ```

### 查看结果

运行后会在当前目录生成 JSON 文件：

```
laptop_info_主机名_时间戳.json
```

用记事本或 VSCode 打开即可查看全部硬件信息。

## 输出示例

```json
{
  "系统信息": {
    "操作系统": "Windows",
    "系统版本": "10.0.22631",
    "主机名": "MyLaptop",
    "采集时间": "2026-09-02 14:30:00"
  },
  "CPU信息": {
    "型号": "Intel(R) Core(TM) i7-13700H",
    "物理核心数": 14,
    "逻辑核心数": 20,
    "当前频率(MHz)": 2400.0
  }
}
```

## 平台支持说明

| 信息类型 | Windows | Linux | macOS |
|---|---|---|---|
| 系统信息 | ✅ | ✅ | ✅ |
| CPU | ✅ | ✅ | ✅ |
| 内存 | ✅ | ✅(需sudo) | ✅ |
| 磁盘 | ✅ | ✅ | ✅ |
| 显卡(NVIDIA) | ✅ | ✅ | ❌ |
| 显卡(核显) | ✅ | ✅ | ✅ |
| 网卡 | ✅ | ✅ | ✅ |
| 电池 | ✅ | ✅ | ✅ |
| BIOS/主板 | ✅ | ✅(需sudo) | ✅ |
| 显示器 | ✅ | ✅(需X) | ✅ |

## 常见问题

### Q: Windows 上运行 `python laptop_info.py` 没反应？

A: Windows 上 `python` 可能是 Microsoft Store 的占位别名，会静默失败。请用 `py laptop_info.py` 代替，或者直接双击 `run.bat`。

### Q: 运行报错 `ModuleNotFoundError: No module named 'psutil'`

A: 先安装依赖：
- Windows: `py -m pip install psutil`
- Linux/macOS: `pip3 install psutil`

### Q: Linux 下内存插槽/BIOS 信息显示"需要管理员权限"

A: 用 sudo 运行：`sudo python3 laptop_info.py`

### Q: 显卡信息显示"未检测到独立显卡"

A: 可能使用的是核显，或者 NVIDIA 驱动未安装。核显信息会通过系统命令获取。

### Q: 可以只采集某几项信息吗？

A: 可以修改脚本，注释掉 `main()` 函数中不需要的采集项。

## 项目结构

```
laptop-info-collector/
├── laptop_info.py      # 主脚本
├── run.bat             # Windows 双击运行（推荐）
├── requirements.txt    # Python 依赖
├── README.md           # 说明文档
└── .gitignore          # Git 忽略文件
```

## License

MIT
