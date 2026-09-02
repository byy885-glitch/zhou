#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
笔记本信息采集脚本
跨平台支持 Windows / Linux / macOS
采集硬件和系统信息，输出 JSON 文件 + 控制台打印
"""

import json
import platform
import subprocess
import sys
import os
from datetime import datetime

try:
    import psutil
except ImportError:
    print("[错误] 缺少 psutil 库，请先运行: pip install psutil")
    sys.exit(1)


def run_cmd(cmd, timeout=10):
    """执行系统命令并返回输出"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_size(bytes_val, suffix="B"):
    """字节转换为可读格式"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes_val < factor:
            return f"{bytes_val:.2f} {unit}{suffix}"
        bytes_val /= factor
    return f"{bytes_val:.2f} P{suffix}"


def collect_system_info():
    """采集系统信息"""
    info = {
        "操作系统": platform.system(),
        "系统版本": platform.version(),
        "系统发行版": platform.release(),
        "架构": platform.machine(),
        "处理器架构": platform.processor() if platform.processor() else "未知",
        "主机名": platform.node(),
        "用户名": os.environ.get("USERNAME") or os.environ.get("USER", "未知"),
        "Python版本": platform.python_version(),
        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Windows 补充
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
            )
            info["Windows版本"] = winreg.QueryValueEx(key, "ProductName")[0]
            info["Windows内部版本"] = winreg.QueryValueEx(key, "CurrentBuild")[0]
            winreg.CloseKey(key)
        except Exception:
            pass

    # Linux 补充
    if platform.system() == "Linux":
        distro = run_cmd("cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'\"' -f2")
        if distro:
            info["Linux发行版"] = distro
        kernel = run_cmd("uname -r")
        if kernel:
            info["内核版本"] = kernel

    return info


def collect_cpu_info():
    """采集CPU信息"""
    cpu_freq = psutil.cpu_freq()
    info = {
        "物理核心数": psutil.cpu_count(logical=False),
        "逻辑核心数": psutil.cpu_count(logical=True),
        "当前频率(MHz)": round(cpu_freq.current, 1) if cpu_freq else "未知",
        "最大频率(MHz)": round(cpu_freq.max, 1) if cpu_freq and cpu_freq.max > 0 else "未知",
        "最小频率(MHz)": round(cpu_freq.min, 1) if cpu_freq and cpu_freq.min > 0 else "未知",
        "当前使用率(%)": psutil.cpu_percent(interval=1),
    }

    # CPU 型号
    if platform.system() == "Windows":
        model = run_cmd('wmic cpu get Name 2>nul | findstr /v "Name"')
        info["型号"] = model.strip() if model else "未知"
    elif platform.system() == "Linux":
        model = run_cmd("lscpu 2>/dev/null | grep 'Model name' | cut -d: -f2")
        info["型号"] = model.strip() if model else "未知"
        # 补充更多
        for line in run_cmd("lscpu 2>/dev/null").split("\n"):
            if "Architecture" in line:
                info["架构"] = line.split(":")[1].strip()
            if "Vendor ID" in line:
                info["厂商"] = line.split(":")[1].strip()
    elif platform.system() == "Darwin":
        model = run_cmd("sysctl -n machdep.cpu.brand_string 2>/dev/null")
        info["型号"] = model.strip() if model else "未知"

    return info


def collect_memory_info():
    """采集内存信息"""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    info = {
        "总内存": get_size(mem.total),
        "已用内存": get_size(mem.used),
        "可用内存": get_size(mem.available),
        "内存使用率(%)": mem.percent,
        "交换分区总量": get_size(swap.total),
        "交换分区已用": get_size(swap.used),
        "交换分区使用率(%)": swap.percent,
    }

    # 内存插槽详情
    slots = []
    if platform.system() == "Windows":
        output = run_cmd('wmic memorychip get DeviceLocator,Capacity,Speed,Manufacturer,PartNumber 2>nul')
        lines = [l for l in output.split("\n") if l.strip() and not l.startswith("DeviceLocator")]
        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                slots.append({
                    "插槽": parts[0],
                    "容量": get_size(int(parts[1])),
                    "频率(MHz)": parts[2],
                    "厂商": parts[3],
                    "型号": parts[4],
                })
    elif platform.system() == "Linux":
        output = run_cmd("sudo dmidecode -t memory 2>/dev/null | grep -A5 'Memory Device' | grep -E 'Size:|Locator:|Speed:|Manufacturer:|Part Number:'")
        if not output:
            output = run_cmd("lshw -class memory 2>/dev/null | grep -E 'size:|product:|vendor:|slot:'")
        # 简化解析
        current = {}
        for line in output.split("\n"):
            line = line.strip()
            if "Size:" in line and "GB" in line:
                if current:
                    slots.append(current)
                current = {"容量": line.split("Size:")[1].strip()}
            elif "Locator:" in line:
                current["插槽"] = line.split("Locator:")[1].strip()
            elif "Speed:" in line:
                current["频率(MHz)"] = line.split("Speed:")[1].strip().replace("MHz", "").strip()
            elif "Manufacturer:" in line:
                current["厂商"] = line.split("Manufacturer:")[1].strip()
            elif "Part Number:" in line:
                current["型号"] = line.split("Part Number:")[1].strip()
        if current:
            slots.append(current)

    if slots:
        info["内存插槽详情"] = slots
    else:
        info["内存插槽详情"] = "需要管理员权限获取详细插槽信息"

    return info


def collect_disk_info():
    """采集磁盘信息"""
    disks = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk = {
                "设备": partition.device,
                "挂载点": partition.mountpoint,
                "文件系统": partition.fstype,
                "总容量": get_size(usage.total),
                "已用": get_size(usage.used),
                "可用": get_size(usage.free),
                "使用率(%)": usage.percent,
            }
            disks.append(disk)
        except (PermissionError, OSError):
            continue

    # 物理磁盘型号
    physical_disks = []
    if platform.system() == "Windows":
        output = run_cmd('wmic diskdrive get Model,Size,MediaType,InterfaceType 2>nul')
        lines = [l for l in output.split("\n") if l.strip() and not l.startswith("InterfaceType")]
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                physical_disks.append({
                    "型号": " ".join(parts[:-3]),
                    "容量": get_size(int(parts[-3])),
                    "类型": parts[-2],
                    "接口": parts[-1],
                })
    elif platform.system() == "Linux":
        output = run_cmd("lsblk -d -o NAME,MODEL,SIZE,TYPE,TRAN 2>/dev/null | grep -v loop")
        for line in output.split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 4:
                physical_disks.append({
                    "设备": parts[0],
                    "型号": " ".join(parts[1:-3]) if len(parts) > 4 else "未知",
                    "容量": parts[-3],
                    "类型": parts[-2],
                    "接口": parts[-1],
                })
    elif platform.system() == "Darwin":
        output = run_cmd("diskutil list physical 2>/dev/null")
        physical_disks.append({"信息": output[:500] if output else "未知"})

    result = {
        "逻辑分区": disks,
        "物理磁盘": physical_disks if physical_disks else "需要管理员权限获取",
    }
    return result


def collect_gpu_info():
    """采集显卡信息"""
    gpus = []

    if platform.system() == "Windows":
        output = run_cmd('wmic path win32_VideoController get Name,AdapterRAM,DriverVersion,VideoProcessor 2>nul')
        lines = [l for l in output.split("\n") if l.strip() and not l.startswith("AdapterRAM")]
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    vram = get_size(int(parts[0]))
                except (ValueError, IndexError):
                    vram = "未知"
                gpus.append({
                    "型号": " ".join(parts[3:]) if len(parts) > 3 else " ".join(parts[1:]),
                    "显存": vram,
                    "驱动版本": parts[1] if len(parts) > 1 else "未知",
                })
        # NVIDIA GPU 补充
        nvidia = run_cmd('nvidia-smi --query-gpu=name,memory.total,driver_version,temperature.gpu,utilization.gpu --format=csv,noheader 2>nul')
        if nvidia:
            gpus = []
            for line in nvidia.split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append({
                        "型号": parts[0],
                        "显存": parts[1],
                        "驱动版本": parts[2],
                        "温度(℃)": parts[3],
                        "使用率(%)": parts[4],
                    })
    elif platform.system() == "Linux":
        # NVIDIA
        nvidia = run_cmd("nvidia-smi --query-gpu=name,memory.total,driver_version,temperature.gpu,utilization.gpu --format=csv,noheader 2>/dev/null")
        if nvidia:
            for line in nvidia.split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append({
                        "型号": parts[0],
                        "显存": parts[1],
                        "驱动版本": parts[2],
                        "温度(℃)": parts[3],
                        "使用率(%)": parts[4],
                    })
        # AMD / Intel
        if not gpus:
            output = run_cmd("lspci 2>/dev/null | grep -iE 'vga|3d|display'")
            for line in output.split("\n"):
                if line.strip():
                    gpus.append({"型号": line.split(":")[-1].strip()})
    elif platform.system() == "Darwin":
        output = run_cmd("system_profiler SPDisplaysDataType 2>/dev/null | grep -E 'Chipset Model:|VRAM:|Metal:|Resolution:'")
        current = {}
        for line in output.split("\n"):
            if "Chipset Model:" in line:
                if current:
                    gpus.append(current)
                current = {"型号": line.split("Chipset Model:")[1].strip()}
            elif "VRAM:" in line:
                current["显存"] = line.split("VRAM:")[1].strip()
            elif "Resolution:" in line:
                current["分辨率"] = line.split("Resolution:")[1].strip()
        if current:
            gpus.append(current)

    return gpus if gpus else [{"型号": "未检测到独立显卡，可能使用核显"}]


def collect_network_info():
    """采集网卡信息"""
    interfaces = []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    for name, addr_list in addrs.items():
        if name == "Loopback Pseudo-Interface 1" or name == "lo":
            continue
        info = {"网卡名称": name, "状态": "UP" if stats[name].isup else "DOWN"}
        for addr in addr_list:
            if addr.family.name == "AF_INET":
                info["IPv4"] = addr.address
                info["子网掩码"] = addr.netmask
            elif addr.family.name == "AF_INET6":
                info["IPv6"] = addr.address
            elif hasattr(addr, "address") and len(addr.address) == 17 and ":" in addr.address:
                info["MAC地址"] = addr.address
        interfaces.append(info)

    # 网络流量
    io = psutil.net_io_counters()
    traffic = {
        "总发送": get_size(io.bytes_sent),
        "总接收": get_size(io.bytes_recv),
        "发送包数": io.packets_sent,
        "接收包数": io.packets_recv,
    }

    return {"网卡列表": interfaces, "网络流量": traffic}


def collect_battery_info():
    """采集电池信息（笔记本特有）"""
    if not hasattr(psutil, "sensors_battery"):
        return {"状态": "不支持电池检测"}

    battery = psutil.sensors_battery()
    if battery is None:
        return {"状态": "未检测到电池（可能是台式机）"}

    info = {
        "电量(%)": battery.percent,
        "充电状态": "充电中" if battery.power_plugged else "使用电池",
        "预计剩余时间": f"{battery.secsleft // 60} 分钟" if battery.secsleft != psutil.POWER_TIME_UNLIMITED else "未知",
    }

    # 电池详细信息
    if platform.system() == "Windows":
        output = run_cmd('wmic path Win32_Battery get Name,DesignCapacity,FullChargeCapacity,EstimatedChargeRemaining,BatteryStatus 2>nul')
        lines = [l for l in output.split("\n") if l.strip() and not l.startswith("BatteryStatus")]
        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                try:
                    design = int(parts[-4])
                    full = int(parts[-3])
                    health = round(full / design * 100, 1) if design > 0 else 0
                    info["设计容量(mWh)"] = design
                    info["满充容量(mWh)"] = full
                    info["电池健康度(%)"] = health
                except (ValueError, IndexError):
                    pass
                info["电池型号"] = " ".join(parts[:-4]) if len(parts) > 4 else "未知"
    elif platform.system() == "Linux":
        output = run_cmd("upower -i $(upower -e 2>/dev/null | grep BAT) 2>/dev/null | grep -E 'energy-full:|energy-full-design:|capacity:|model:|vendor:|technology:'")
        for line in output.split("\n"):
            if "energy-full-design:" in line:
                info["设计容量"] = line.split(":")[1].strip()
            elif "energy-full:" in line:
                info["满充容量"] = line.split(":")[1].strip()
            elif "capacity:" in line:
                info["健康度(%)"] = line.split(":")[1].strip()
            elif "model:" in line:
                info["型号"] = line.split(":")[1].strip()
            elif "vendor:" in line:
                info["厂商"] = line.split(":")[1].strip()
    elif platform.system() == "Darwin":
        output = run_cmd("system_profiler SPPowerDataType 2>/dev/null | grep -E 'Cycle Count|Condition|Maximum Capacity|Serial Number'")
        for line in output.split("\n"):
            if "Cycle Count" in line:
                info["循环次数"] = line.split(":")[1].strip()
            elif "Condition" in line:
                info["状态"] = line.split(":")[1].strip()
            elif "Maximum Capacity" in line:
                info["最大容量(%)"] = line.split(":")[1].strip()

    return info


def collect_bios_info():
    """采集BIOS/主板信息"""
    info = {}

    if platform.system() == "Windows":
        output = run_cmd('wmic bios get Manufacturer,SMBIOSBIOSVersion,ReleaseDate,SerialNumber 2>nul')
        lines = [l for l in output.split("\n") if l.strip() and not l.startswith("Manufacturer")]
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                info["BIOS厂商"] = parts[0]
                info["BIOS版本"] = parts[1]
                info["发布日期"] = parts[2]
                info["序列号"] = parts[3]
        # 主板
        board = run_cmd('wmic baseboard get Manufacturer,Product,Version,SerialNumber 2>nul')
        lines = [l for l in board.split("\n") if l.strip() and not l.startswith("Manufacturer")]
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                info["主板厂商"] = parts[0]
                info["主板型号"] = parts[1]
                info["主板版本"] = parts[2]
                info["主板序列号"] = parts[3]
    elif platform.system() == "Linux":
        output = run_cmd("sudo dmidecode -t bios 2>/dev/null | grep -E 'Vendor:|Version:|Release Date:|Serial Number:'")
        for line in output.split("\n"):
            if "Vendor:" in line:
                info["BIOS厂商"] = line.split("Vendor:")[1].strip()
            elif "Version:" in line and "BIOS" not in info:
                info["BIOS版本"] = line.split("Version:")[1].strip()
            elif "Release Date:" in line:
                info["发布日期"] = line.split("Release Date:")[1].strip()
            elif "Serial Number:" in line:
                info["序列号"] = line.split("Serial Number:")[1].strip()
        # 主板
        board = run_cmd("sudo dmidecode -t baseboard 2>/dev/null | grep -E 'Manufacturer:|Product Name:|Version:|Serial Number:'")
        for line in board.split("\n"):
            if "Manufacturer:" in line:
                info["主板厂商"] = line.split("Manufacturer:")[1].strip()
            elif "Product Name:" in line:
                info["主板型号"] = line.split("Product Name:")[1].strip()
            elif "Version:" in line:
                info["主板版本"] = line.split("Version:")[1].strip()
            elif "Serial Number:" in line and "主板序列号" not in info:
                info["主板序列号"] = line.split("Serial Number:")[1].strip()
    elif platform.system() == "Darwin":
        output = run_cmd("system_profiler SPHardwareDataType 2>/dev/null | grep -E 'Model Name|Model Identifier|Chip|Serial Number|Hardware UUID'")
        for line in output.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                info[key.strip()] = val.strip()

    return info if info else {"状态": "需要管理员权限获取BIOS信息"}


def collect_display_info():
    """采集显示器信息"""
    displays = []

    if platform.system() == "Windows":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            screens = []
            for i in range(10):
                w = user32.GetSystemMetrics(78) if i == 0 else 0
                # 简化：使用 powershell 获取
                break
        except Exception:
            pass
        output = run_cmd('powershell -Command "Get-CimInstance -Namespace root\\\\wmi -ClassName WmiMonitorBasicDisplayParams | ForEach-Object { $_.InstanceName }" 2>nul')
        # 更简单的方式
        output2 = run_cmd('wmic desktopmonitor get ScreenHeight,ScreenWidth,Name 2>nul')
        lines = [l for l in output2.split("\n") if l.strip() and not l.startswith("Name")]
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                displays.append({
                    "名称": " ".join(parts[2:]),
                    "分辨率": f"{parts[1]}x{parts[0]}",
                })
    elif platform.system() == "Linux":
        output = run_cmd("xrandr 2>/dev/null | grep -E ' connected|\\*'")
        current = None
        for line in output.split("\n"):
            if " connected" in line:
                if current:
                    displays.append(current)
                current = {"接口": line.split(" connected")[0].strip()}
            elif "*" in line and current:
                res = line.strip().split()[0]
                current["当前分辨率"] = res
        if current:
            displays.append(current)
    elif platform.system() == "Darwin":
        output = run_cmd("system_profiler SPDisplaysDataType 2>/dev/null | grep -E 'Resolution:|Display Type:|Main Display:'")
        current = {}
        for line in output.split("\n"):
            if "Resolution:" in line:
                if current:
                    displays.append(current)
                current = {"分辨率": line.split("Resolution:")[1].strip()}
            elif "Display Type:" in line:
                current["类型"] = line.split("Display Type:")[1].strip()
        if current:
            displays.append(current)

    return displays if displays else [{"信息": "未检测到外接显示器，使用笔记本内置屏幕"}]


def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_dict(d, indent=0):
    """递归打印字典"""
    for key, value in d.items():
        prefix = "  " * indent
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_dict(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}:")
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    print(f"{prefix}  [{i + 1}]")
                    print_dict(item, indent + 2)
                else:
                    print(f"{prefix}  [{i + 1}] {item}")
        else:
            print(f"{prefix}{key}: {value}")


def main():
    print("=" * 60)
    print("  笔记本信息采集工具")
    print("=" * 60)
    print(f"系统: {platform.system()} {platform.release()}")
    print(f"主机: {platform.node()}")
    print("正在采集信息，请稍候...\n")

    # 采集所有信息
    data = {
        "系统信息": collect_system_info(),
        "CPU信息": collect_cpu_info(),
        "内存信息": collect_memory_info(),
        "磁盘信息": collect_disk_info(),
        "显卡信息": collect_gpu_info(),
        "网络信息": collect_network_info(),
        "电池信息": collect_battery_info(),
        "BIOS/主板信息": collect_bios_info(),
        "显示器信息": collect_display_info(),
    }

    # 控制台打印
    for section, content in data.items():
        print_section(section)
        if isinstance(content, list):
            for i, item in enumerate(content):
                print(f"  [{i + 1}]")
                print_dict(item, 2)
        else:
            print_dict(content, 1)

    # 保存 JSON
    hostname = platform.node()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"laptop_info_{hostname}_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"  采集完成！结果已保存到: {filename}")
    print("=" * 60)

    return filename


if __name__ == "__main__":
    main()
