import os
import time
import socket
import subprocess
from datetime import datetime, timedelta
import psutil


def get_cpu_temp() -> float | None:
    """Retrieve the Raspberry Pi CPU temperature in Celsius."""
    # 1. Direct sysfs thermal zone (standard Raspberry Pi OS kernel)
    thermal_path = "/sys/class/thermal/thermal_zone0/temp"
    if os.path.exists(thermal_path):
        try:
            with open(thermal_path, "r") as f:
                temp_raw = f.read().strip()
                return round(float(temp_raw) / 1000.0, 1)
        except Exception:
            pass

    # 2. vcgencmd utility (Raspberry Pi specific)
    try:
        res = subprocess.check_output(["vcgencmd", "measure_temp"], text=True, stderr=subprocess.DEVNULL)
        # Output format: temp=48.2'C
        if "temp=" in res:
            temp_str = res.split("=")[1].split("'")[0]
            return round(float(temp_str), 1)
    except Exception:
        pass

    # 3. psutil fallback for other Linux / platforms
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    return round(entries[0].current, 1)
    except Exception:
        pass

    return None


def get_uptime_str() -> str:
    """Get system uptime as a human-readable string."""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        delta = datetime.now() - boot_time

        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if not parts:
            parts.append(f"{seconds}s")

        return " ".join(parts)
    except Exception:
        return "Unknown"


def get_wifi_ssid() -> str:
    """Get the currently connected Wi-Fi SSID."""
    try:
        # Try iwgetid first (standard on Raspberry Pi OS)
        out = subprocess.check_output(["iwgetid", "-r"], text=True, stderr=subprocess.DEVNULL).strip()
        if out:
            return out
    except Exception:
        pass

    try:
        # Try nmcli fallback (NetworkManager on newer Debian/Bookworm)
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        for line in out.splitlines():
            if line.startswith("yes:"):
                return line.split(":", 1)[1]
    except Exception:
        pass

    return "Ethernet / Not connected"


def get_network_info(preferred_iface: str = "wlan0") -> dict:
    """Scan and return host network interfaces, IPs, and hostname."""
    hostname = socket.gethostname()
    interfaces = []

    try:
        addrs = psutil.net_if_addrs()
        for iface_name, addr_list in addrs.items():
            for addr in addr_list:
                # AF_INET = IPv4, skip loopback
                if addr.family == socket.AF_INET and addr.address != "127.0.0.1":
                    interfaces.append({"name": iface_name, "ip": addr.address})
    except Exception:
        pass

    # Sort so preferred interface (e.g. wlan0) appears first
    interfaces.sort(key=lambda x: (x["name"] != preferred_iface, x["name"]))

    primary_ip = interfaces[0]["ip"] if interfaces else "No IPv4 assigned"
    return {
        "hostname": hostname,
        "primary_ip": primary_ip,
        "interfaces": interfaces,
    }


def get_resource_stats() -> dict:
    """Collect overall CPU, RAM, and Disk metrics."""
    # CPU usage percentage (sampled over 0.2s)
    cpu_pct = psutil.cpu_percent(interval=0.2)

    # Memory
    mem = psutil.virtual_memory()
    ram_used_mb = round(mem.used / (1024 ** 2), 1)
    ram_total_mb = round(mem.total / (1024 ** 2), 1)
    ram_pct = mem.percent

    # Disk (root filesystem)
    disk = psutil.disk_usage("/")
    disk_free_gb = round(disk.free / (1024 ** 3), 1)
    disk_total_gb = round(disk.total / (1024 ** 3), 1)
    disk_pct = disk.percent

    temp = get_cpu_temp()

    return {
        "cpu_pct": cpu_pct,
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "ram_pct": ram_pct,
        "disk_free_gb": disk_free_gb,
        "disk_total_gb": disk_total_gb,
        "disk_pct": disk_pct,
        "temp": temp,
    }


def get_startup_summary(preferred_iface: str = "wlan0") -> str:
    """Format an informative startup alert for Telegram."""
    net = get_network_info(preferred_iface)
    wifi = get_wifi_ssid()
    temp = get_cpu_temp()
    temp_str = f"{temp}°C" if temp is not None else "N/A"

    msg = (
        "🚀 *Raspberry Pi is Online!* 🚀\n\n"
        f"🏷️ *Hostname:* `{net['hostname']}`\n"
        f"🌐 *Primary IP:* `{net['primary_ip']}`\n"
        f"📶 *Wi-Fi:* `{wifi}`\n"
        f"🌡️ *CPU Temp:* `{temp_str}`\n"
        f"⏱️ *Uptime:* `{get_uptime_str()}`\n\n"
        "Send /menu or /status to interact with the bot."
    )
    return msg


def get_system_summary(preferred_iface: str = "wlan0", title: str = "Raspberry Pi System Health") -> str:
    """Format full system health report for Telegram."""
    stats = get_resource_stats()
    net = get_network_info(preferred_iface)
    wifi = get_wifi_ssid()
    temp_str = f"{stats['temp']}°C" if stats['temp'] is not None else "N/A"

    iface_lines = "\n".join([f"  • `{i['name']}`: `{i['ip']}`" for i in net["interfaces"]])
    if not iface_lines:
        iface_lines = "  • No active network interfaces"

    msg = (
        f"📊 *{title}*\n"
        "─────────────────────────\n"
        f"🏷️ *Host:* `{net['hostname']}`\n"
        f"⏱️ *Uptime:* `{get_uptime_str()}`\n"
        f"🌡️ *CPU Temp:* `{temp_str}`\n"
        f"⚡ *CPU Usage:* `{stats['cpu_pct']}%`\n"
        f"🧠 *RAM:* `{stats['ram_used_mb']}MB / {stats['ram_total_mb']}MB ({stats['ram_pct']}%)`\n"
        f"💾 *Disk Free:* `{stats['disk_free_gb']}GB / {stats['disk_total_gb']}GB ({stats['disk_pct']}% used)`\n\n"
        f"📶 *Wi-Fi:* `{wifi}`\n"
        f"🌐 *Network Interfaces:*\n{iface_lines}\n"
        "─────────────────────────"
    )
    return msg
