import os
import subprocess
import logging
import psutil

logger = logging.getLogger(__name__)


def run_command(command: str, timeout: int = 35) -> tuple[bool, str]:
    """Execute a shell command with a timeout."""
    if not command or not command.strip():
        return False, "No command specified."

    try:
        proc = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        output = proc.stdout.strip()
        err = proc.stderr.strip()

        combined = []
        if output:
            combined.append(output)
        if err:
            combined.append(f"Stderr:\n{err}")

        result_text = "\n".join(combined) if combined else "Command executed with no output."
        return proc.returncode == 0, result_text
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout} seconds."
    except Exception as e:
        return False, f"Execution failed: {str(e)}"


class ServiceManager:
    """Manages systemd and custom script services."""

    @staticmethod
    def start(service: dict) -> tuple[bool, str]:
        svc_type = service.get("type", "custom")
        name = service.get("name", service.get("id"))

        if svc_type == "systemd":
            cmd = f"sudo systemctl start {service.get('service_name', name)}"
        else:
            cmd = service.get("start_cmd", "")

        if not cmd:
            return False, f"No start command configured for {name}."

        success, out = run_command(cmd)
        status_icon = "✅" if success else "❌"
        return success, f"{status_icon} *{name} Start:*\n`{out}`"

    @staticmethod
    def stop(service: dict) -> tuple[bool, str]:
        svc_type = service.get("type", "custom")
        name = service.get("name", service.get("id"))

        if svc_type == "systemd":
            cmd = f"sudo systemctl stop {service.get('service_name', name)}"
        else:
            cmd = service.get("stop_cmd", "")

        if not cmd:
            return False, f"No stop command configured for {name}."

        success, out = run_command(cmd)
        status_icon = "🛑" if success else "❌"
        return success, f"{status_icon} *{name} Stop:*\n`{out}`"

    @staticmethod
    def restart(service: dict) -> tuple[bool, str]:
        svc_type = service.get("type", "custom")
        name = service.get("name", service.get("id"))

        if svc_type == "systemd":
            cmd = f"sudo systemctl restart {service.get('service_name', name)}"
            success, out = run_command(cmd)
            status_icon = "🔄" if success else "❌"
            return success, f"{status_icon} *{name} Restart:*\n`{out}`"

        # Custom service: check if dedicated restart_cmd exists
        restart_cmd = service.get("restart_cmd")
        if restart_cmd and restart_cmd.strip():
            success, out = run_command(restart_cmd)
            status_icon = "🔄" if success else "❌"
            return success, f"{status_icon} *{name} Restart:*\n`{out}`"

        # Fallback for custom: run stop then start
        _, stop_out = ServiceManager.stop(service)
        start_ok, start_out = ServiceManager.start(service)
        combined = f"{stop_out}\n\n{start_out}"
        return start_ok, combined

    @staticmethod
    def get_status(service: dict) -> str:
        svc_type = service.get("type", "custom")
        name = service.get("name", service.get("id"))

        if svc_type == "systemd":
            svc_name = service.get("service_name", name)
            _, out = run_command(f"systemctl is-active {svc_name}")
            return out.strip()

        status_cmd = service.get("status_cmd")
        if status_cmd and status_cmd.strip():
            _, out = run_command(status_cmd)
            return out.strip()

        return "Configured (Script)"


class LogManager:
    """Handles reading (tailing), downloading, and cleaning log files."""

    @staticmethod
    def tail(file_path: str, max_lines: int = 50) -> str:
        if not file_path:
            return "No log file configured for this service."

        if not os.path.exists(file_path):
            return f"Log file not found: `{file_path}`"

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                # Read all lines efficiently if small, or seek from end
                lines = f.readlines()
                selected = lines[-max_lines:] if len(lines) > max_lines else lines

            content = "".join(selected).strip()
            if not content:
                return "Log file is currently empty."

            # Telegram max message length is 4096. Keep within 3500 to leave margin.
            if len(content) > 3500:
                content = "...[truncated]...\n" + content[-3400:]

            return f"```\n{content}\n```"
        except Exception as e:
            return f"Error reading log file: {e}"

    @staticmethod
    def get_file_for_send(file_path: str) -> str | None:
        """Verify the log file exists and is readable."""
        if file_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return file_path
        return None

    @staticmethod
    def post_send_cleanup(file_path: str, action: str) -> str:
        """Handle post-send log retention (none, truncate, or delete)."""
        if not file_path or not os.path.exists(file_path):
            return ""

        action = (action or "none").lower().strip()
        try:
            if action == "truncate":
                # Safest method: keeps file descriptor & permissions intact for active loggers
                with open(file_path, "w") as f:
                    f.truncate(0)
                return "🧹 Log file was cleared (truncated) to free space."
            elif action == "delete":
                os.remove(file_path)
                return "🗑️ Log file was deleted."
        except Exception as e:
            logger.error(f"Failed to perform post-send action '{action}' on {file_path}: {e}")
            return f"⚠️ Could not execute log cleanup: {e}"

        return ""


def get_java_processes(jps_path: str = "jps") -> str:
    """List active Java processes using jps."""
    success, out = run_command(f"{jps_path} -l")
    if not success or not out:
        return "☕ *Active Java Applications:*\n─────────────────────────\n• No active Java processes found (or `jps` not accessible).\n─────────────────────────"
    return f"☕ *Active Java Applications:*\n─────────────────────────\n```\n{out}\n```\n─────────────────────────"


def get_python_processes(exclude_self: bool = True) -> str:
    """List active Python processes running on the system."""
    current_pid = os.getpid()
    results = []

    for p in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
        try:
            info = p.info
            name = (info.get("name") or "").lower()
            cmdline = info.get("cmdline") or []

            # Check if process is Python
            is_py = "python" in name or any("python" in arg.lower() for arg in cmdline[:1])
            if not is_py:
                continue

            pid = info.get("pid")
            if exclude_self and pid == current_pid:
                continue

            # Format human-friendly script name
            # e.g., ["python3", "/path/to/my_script.py", "--flag"] -> "my_script.py --flag"
            if len(cmdline) > 1:
                clean_args = []
                for i, arg in enumerate(cmdline[1:4]):
                    if i == 0:
                        clean_args.append(os.path.basename(arg))
                    else:
                        clean_args.append(arg)
                display_cmd = " ".join(clean_args)
            elif cmdline:
                display_cmd = os.path.basename(cmdline[0])
            else:
                display_cmd = name

            mem_mb = round((info["memory_info"].rss / (1024 * 1024)), 1) if info.get("memory_info") else 0
            results.append({
                "pid": pid,
                "cmd": display_cmd[:60],
                "mem_mb": mem_mb,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if not results:
        return "🐍 *Active Python Applications:*\n─────────────────────────\n• No other active Python applications running.\n─────────────────────────"

    lines = [f"• *[PID {r['pid']}]* `{r['cmd']}` (RAM: `{r['mem_mb']} MB`)" for r in results]
    return (
        "🐍 *Active Python Applications:*\n"
        "─────────────────────────\n"
        + "\n".join(lines)
        + f"\n─────────────────────────\nTotal: *{len(results)}* running process(es)"
    )


def get_javascript_processes(check_pm2: bool = True) -> str:
    """List active Node.js / JavaScript processes and PM2 status."""
    results = []

    # 1. Inspect processes with psutil (covers node, nodejs, bun, deno)
    for p in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
        try:
            info = p.info
            name = (info.get("name") or "").lower()
            cmdline = info.get("cmdline") or []

            is_js = name in ("node", "nodejs", "deno", "bun") or any(r in name for r in ("node", "bun", "deno"))
            if not is_js and cmdline:
                first_arg = os.path.basename(cmdline[0]).lower()
                if first_arg in ("node", "nodejs", "bun", "deno"):
                    is_js = True

            if not is_js:
                continue

            pid = info.get("pid")
            if len(cmdline) > 1:
                clean_args = []
                for i, arg in enumerate(cmdline[1:4]):
                    if i == 0:
                        clean_args.append(os.path.basename(arg))
                    else:
                        clean_args.append(arg)
                display_cmd = " ".join(clean_args)
            elif cmdline:
                display_cmd = os.path.basename(cmdline[0])
            else:
                display_cmd = name

            mem_mb = round((info["memory_info"].rss / (1024 * 1024)), 1) if info.get("memory_info") else 0
            results.append({
                "pid": pid,
                "cmd": display_cmd[:60],
                "mem_mb": mem_mb,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # 2. Check PM2 if enabled
    pm2_table = ""
    if check_pm2:
        success, out = run_command("pm2 list --no-color 2>/dev/null", timeout=6)
        if success and out and ("App name" in out or "online" in out or "status" in out):
            pm2_table = out.strip()

    sections = []
    if pm2_table:
        sections.append(f"📦 *PM2 Managed Apps:*\n```\n{pm2_table[:1200]}\n```")

    if results:
        lines = [f"• *[PID {r['pid']}]* `{r['cmd']}` (RAM: `{r['mem_mb']} MB`)" for r in results]
        sections.append(
            "🟨 *Node.js Processes:*\n"
            + "\n".join(lines)
            + f"\nTotal: *{len(results)}* running process(es)"
        )
    elif not pm2_table:
        sections.append("• No active JavaScript (Node.js/Bun) applications running.")

    return (
        "🟨 *Active JavaScript Applications:*\n"
        "─────────────────────────\n"
        + "\n\n".join(sections)
        + "\n─────────────────────────"
    )


def get_all_apps_summary(
    java_enabled: bool = True,
    jps_path: str = "jps",
    python_enabled: bool = True,
    exclude_self: bool = True,
    js_enabled: bool = True,
    check_pm2: bool = True,
) -> str:
    """Consolidated overview of all running apps across Java, Python, and JavaScript."""
    reports = []
    if java_enabled:
        reports.append(get_java_processes(jps_path))
    if python_enabled:
        reports.append(get_python_processes(exclude_self))
    if js_enabled:
        reports.append(get_javascript_processes(check_pm2))

    if not reports:
        return "⚠️ No application inspectors are currently enabled in `config.yaml`."

    return "\n\n".join(reports)
