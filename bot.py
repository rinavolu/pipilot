import os
import sys
import time
import threading
import logging
import telebot
from telebot import types

from config_loader import cfg
from system_metrics import (
    get_system_summary,
    get_startup_summary,
    get_network_info,
    get_wifi_ssid,
)
from service_manager import (
    ServiceManager,
    LogManager,
    get_java_processes,
    get_python_processes,
    get_javascript_processes,
    get_all_apps_summary,
    run_command,
)
import keyboards

# Setup Logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("PiPilot")

# Validate configuration
if not cfg.bot_token or cfg.bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    logger.error("Telegram bot token is not configured! Please update config.yaml or set TELEGRAM_BOT_TOKEN.")
    print("ERROR: Please set your Telegram bot token in config.yaml or in your environment variables.")
    sys.exit(1)

bot = telebot.TeleBot(cfg.bot_token, parse_mode="Markdown")


# ==============================================================================
# Security & Authorization Helper
# ==============================================================================

def is_authorized(chat_id: int) -> bool:
    """Check if chat_id belongs to an admin."""
    if not cfg.admin_chat_ids:
        # If no admin IDs are configured, warn and allow first user or block
        logger.warning(f"No admin_chat_ids configured in config.yaml! Blocked request from {chat_id}.")
        return False
    return cfg.is_admin(chat_id)


def auth_guard(handler_func):
    """Decorator to restrict command access to configured admins only."""
    def wrapper(message, *args, **kwargs):
        if not is_authorized(message.chat.id):
            logger.warning(f"Unauthorized access attempt by chat_id: {message.chat.id} ({message.from_user.username})")
            bot.send_message(message.chat.id, "⛔ *Access Denied*: You are not authorized to control this Raspberry Pi.")
            return
        return handler_func(message, *args, **kwargs)
    return wrapper


def get_main_menu_markup():
    """Generate main menu keyboard with active application inspectors."""
    return keyboards.main_menu_keyboard(
        java_enabled=cfg.java_settings.get("enabled", False),
        python_enabled=cfg.python_settings.get("enabled", False),
        js_enabled=cfg.javascript_settings.get("enabled", False),
    )


# ==============================================================================
# Command Handlers
# ==============================================================================

@bot.message_handler(commands=["start", "menu"])
@auth_guard
def cmd_menu(message):
    """Display the interactive dashboard menu."""
    markup = get_main_menu_markup()
    bot.send_message(
        message.chat.id,
        "🎮 *Raspberry Pi Control Dashboard*\n\nSelect an option below to monitor or manage your Pi:",
        reply_markup=markup
    )


@bot.message_handler(commands=["status", "health", "pi_resources"])
@auth_guard
def cmd_status(message):
    """Send system health and hardware resource statistics."""
    summary = get_system_summary(cfg.system_settings.get("preferred_interface", "wlan0"))
    bot.send_message(message.chat.id, summary, reply_markup=keyboards.back_to_main_keyboard())


@bot.message_handler(commands=["ip", "network", "wifi", "connected_wifi", "ipconfig", "ip_py"])
@auth_guard
def cmd_network(message):
    """Send network interfaces and Wi-Fi information."""
    pref = cfg.system_settings.get("preferred_interface", "wlan0")
    net = get_network_info(pref)
    wifi = get_wifi_ssid()
    lines = [f"• `{i['name']}`: `{i['ip']}`" for i in net["interfaces"]]
    net_str = "\n".join(lines) if lines else "• No active IPv4 addresses"

    text = (
        "🌐 *Network & Connectivity*\n"
        "─────────────────────────\n"
        f"🏷️ *Hostname:* `{net['hostname']}`\n"
        f"📶 *Wi-Fi SSID:* `{wifi}`\n\n"
        f"*Assigned IP Addresses:*\n{net_str}\n"
        "─────────────────────────"
    )
    bot.send_message(message.chat.id, text, reply_markup=keyboards.back_to_main_keyboard())


@bot.message_handler(commands=["services"])
@auth_guard
def cmd_services(message):
    """Display list of configured services."""
    services = cfg.services
    if not services:
        bot.send_message(message.chat.id, "⚠️ No services configured in `config.yaml`.", reply_markup=keyboards.back_to_main_keyboard())
        return

    markup = keyboards.services_menu_keyboard(services)
    bot.send_message(message.chat.id, "⚙️ *Managed Services:*\nSelect a service to control:", reply_markup=markup)


@bot.message_handler(commands=["logs", "send_all_logs"])
@auth_guard
def cmd_logs(message):
    """Display log viewer menu."""
    markup = keyboards.logs_menu_keyboard(cfg.services)
    bot.send_message(message.chat.id, "📜 *Log Viewer:*\nChoose a service to inspect its logs:", reply_markup=markup)


@bot.message_handler(commands=["jps", "java", "active_j_apps"])
@auth_guard
def cmd_java(message):
    """List active Java processes."""
    if not cfg.java_settings.get("enabled", False):
        bot.send_message(message.chat.id, "Java process inspector is disabled in `config.yaml`.", reply_markup=keyboards.back_to_main_keyboard())
        return
    jps_path = cfg.java_settings.get("jps_path", "jps")
    output = get_java_processes(jps_path)
    bot.send_message(message.chat.id, output, reply_markup=keyboards.back_to_main_keyboard())


@bot.message_handler(commands=["python", "py", "python_apps", "py_apps"])
@auth_guard
def cmd_python(message):
    """List active Python processes."""
    if not cfg.python_settings.get("enabled", False):
        bot.send_message(message.chat.id, "Python process inspector is disabled in `config.yaml`.", reply_markup=keyboards.back_to_main_keyboard())
        return
    exclude_self = cfg.python_settings.get("exclude_self", True)
    output = get_python_processes(exclude_self=exclude_self)
    bot.send_message(message.chat.id, output, reply_markup=keyboards.back_to_main_keyboard())


@bot.message_handler(commands=["js", "node", "javascript", "js_apps", "node_apps"])
@auth_guard
def cmd_js(message):
    """List active JavaScript / Node.js processes."""
    if not cfg.javascript_settings.get("enabled", False):
        bot.send_message(message.chat.id, "JavaScript process inspector is disabled in `config.yaml`.", reply_markup=keyboards.back_to_main_keyboard())
        return
    check_pm2 = cfg.javascript_settings.get("pm2_enabled", True)
    output = get_javascript_processes(check_pm2=check_pm2)
    bot.send_message(message.chat.id, output, reply_markup=keyboards.back_to_main_keyboard())


@bot.message_handler(commands=["apps", "active_apps"])
@auth_guard
def cmd_all_apps(message):
    """List all active applications across Java, Python, and JavaScript."""
    output = get_all_apps_summary(
        java_enabled=cfg.java_settings.get("enabled", False),
        jps_path=cfg.java_settings.get("jps_path", "jps"),
        python_enabled=cfg.python_settings.get("enabled", False),
        exclude_self=cfg.python_settings.get("exclude_self", True),
        js_enabled=cfg.javascript_settings.get("enabled", False),
        check_pm2=cfg.javascript_settings.get("pm2_enabled", True),
    )
    bot.send_message(message.chat.id, output, reply_markup=keyboards.back_to_main_keyboard())


@bot.message_handler(commands=["reboot", "pi_reboot"])
@auth_guard
def cmd_reboot(message):
    """Ask confirmation to reboot."""
    bot.send_message(
        message.chat.id,
        "⚠️ *Confirm Reboot*\nAre you sure you want to reboot the Raspberry Pi?",
        reply_markup=keyboards.confirm_keyboard("reboot")
    )


@bot.message_handler(commands=["shutdown", "pi_shutdown"])
@auth_guard
def cmd_shutdown(message):
    """Ask confirmation to shut down."""
    bot.send_message(
        message.chat.id,
        "🛑 *Confirm Shutdown*\nAre you sure you want to turn off the Raspberry Pi? You will lose remote access until it is manually powered on.",
        reply_markup=keyboards.confirm_keyboard("shutdown")
    )


@bot.message_handler(commands=["help", "all_commands"])
@auth_guard
def cmd_help(message):
    """Show help documentation."""
    help_text = (
        "🤖 *PiPilot Commands:*\n\n"
        "• /menu or /start - Open interactive dashboard\n"
        "• /status, /health or /pi_resources - Hardware resources & CPU temp\n"
        "• /network, /ip or /connected_wifi - IP addresses & Wi-Fi status\n"
        "• /services - Start, stop, or restart your apps\n"
        "• /logs - Inspect or download application logs\n"
        "• /apps - All active applications (Java, Python, JS)\n"
        "• /py or /python - List active Python processes\n"
        "• /js or /node - List active JavaScript / Node apps\n"
        "• /jps or /java - List active Java processes\n"
        "• /reboot or /pi_reboot - Reboot the Raspberry Pi safely\n"
        "• /shutdown or /pi_shutdown - Power off the Raspberry Pi\n"
        "• /help or /all_commands - Show this help message"
    )
    bot.send_message(message.chat.id, help_text, reply_markup=keyboards.back_to_main_keyboard())


# ==============================================================================
# Callback Query Handlers (Button clicks)
# ==============================================================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: types.CallbackQuery):
    if not is_authorized(call.message.chat.id):
        bot.answer_callback_query(call.id, "⛔ Unauthorized", show_alert=True)
        return

    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    # 1. Navigation callbacks
    if data == "nav:main":
        markup = get_main_menu_markup()
        bot.edit_message_text(
            "🎮 *Raspberry Pi Control Dashboard*\n\nSelect an option below to monitor or manage your Pi:",
            chat_id=chat_id,
            message_id=msg_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

    elif data == "nav:health":
        pref = cfg.system_settings.get("preferred_interface", "wlan0")
        summary = get_system_summary(pref)
        bot.edit_message_text(summary, chat_id=chat_id, message_id=msg_id, reply_markup=keyboards.back_to_main_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "nav:network":
        pref = cfg.system_settings.get("preferred_interface", "wlan0")
        net = get_network_info(pref)
        wifi = get_wifi_ssid()
        lines = [f"• `{i['name']}`: `{i['ip']}`" for i in net["interfaces"]]
        net_str = "\n".join(lines) if lines else "• No active IPv4 addresses"
        text = (
            "🌐 *Network & Connectivity*\n"
            "─────────────────────────\n"
            f"🏷️ *Hostname:* `{net['hostname']}`\n"
            f"📶 *Wi-Fi SSID:* `{wifi}`\n\n"
            f"*Assigned IP Addresses:*\n{net_str}\n"
            "─────────────────────────"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=keyboards.back_to_main_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "nav:services":
        services = cfg.services
        if not services:
            bot.answer_callback_query(call.id, "No services configured.", show_alert=True)
            return
        markup = keyboards.services_menu_keyboard(services)
        bot.edit_message_text("⚙️ *Managed Services:*\nSelect a service to control:", chat_id=chat_id, message_id=msg_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    elif data == "nav:logs":
        markup = keyboards.logs_menu_keyboard(cfg.services)
        bot.edit_message_text("📜 *Log Viewer:*\nChoose a service to inspect its logs:", chat_id=chat_id, message_id=msg_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    elif data == "nav:java":
        jps_path = cfg.java_settings.get("jps_path", "jps")
        output = get_java_processes(jps_path)
        bot.edit_message_text(output, chat_id=chat_id, message_id=msg_id, reply_markup=keyboards.back_to_main_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "nav:python":
        exclude_self = cfg.python_settings.get("exclude_self", True)
        output = get_python_processes(exclude_self=exclude_self)
        bot.edit_message_text(output, chat_id=chat_id, message_id=msg_id, reply_markup=keyboards.back_to_main_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "nav:js":
        check_pm2 = cfg.javascript_settings.get("pm2_enabled", True)
        output = get_javascript_processes(check_pm2=check_pm2)
        bot.edit_message_text(output, chat_id=chat_id, message_id=msg_id, reply_markup=keyboards.back_to_main_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "nav:help":
        cmd_help(call.message)
        bot.answer_callback_query(call.id)

    # 2. Service Management callbacks
    elif data.startswith("svc:view:"):
        svc_id = data.split(":", 2)[2]
        svc = cfg.get_service(svc_id)
        if not svc:
            bot.answer_callback_query(call.id, "Service not found.", show_alert=True)
            return

        status = ServiceManager.get_status(svc)
        text = (
            f"⚙️ *Service:* `{svc.get('name')}`\n"
            f"📦 *Type:* `{svc.get('type', 'custom')}`\n"
            f"📊 *Current Status:* `{status}`\n"
            f"📄 *Log File:* `{svc.get('log_file', 'None')}`\n\n"
            "Choose an action:"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=keyboards.service_detail_keyboard(svc))
        bot.answer_callback_query(call.id)

    elif data.startswith("svc:start:"):
        svc_id = data.split(":", 2)[2]
        svc = cfg.get_service(svc_id)
        bot.answer_callback_query(call.id, f"Starting {svc.get('name')}...")
        _, out = ServiceManager.start(svc)
        bot.send_message(chat_id, out, reply_markup=keyboards.service_detail_keyboard(svc))

    elif data.startswith("svc:stop:"):
        svc_id = data.split(":", 2)[2]
        svc = cfg.get_service(svc_id)
        bot.answer_callback_query(call.id, f"Stopping {svc.get('name')}...")
        _, out = ServiceManager.stop(svc)
        bot.send_message(chat_id, out, reply_markup=keyboards.service_detail_keyboard(svc))

    elif data.startswith("svc:restart:"):
        svc_id = data.split(":", 2)[2]
        svc = cfg.get_service(svc_id)
        bot.answer_callback_query(call.id, f"Restarting {svc.get('name')}...")
        _, out = ServiceManager.restart(svc)
        bot.send_message(chat_id, out, reply_markup=keyboards.service_detail_keyboard(svc))

    # 3. Log Viewing & Downloading
    elif data.startswith("log:view:"):
        svc_id = data.split(":", 2)[2]
        svc = cfg.get_service(svc_id)
        markup = keyboards.log_actions_keyboard(svc_id)
        bot.edit_message_text(
            f"📜 *Log Options for {svc.get('name')}:*\nFile: `{svc.get('log_file')}`",
            chat_id=chat_id,
            message_id=msg_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

    elif data.startswith("log:tail:"):
        svc_id = data.split(":", 2)[2]
        svc = cfg.get_service(svc_id)
        max_lines = cfg.log_settings.get("default_tail_lines", 50)
        bot.answer_callback_query(call.id, "Fetching logs...")
        tail_content = LogManager.tail(svc.get("log_file"), max_lines=max_lines)
        bot.send_message(
            chat_id,
            f"📄 *Last {max_lines} lines of {svc.get('name')}:*\n{tail_content}",
            reply_markup=keyboards.log_actions_keyboard(svc_id)
        )

    elif data.startswith("log:send:"):
        svc_id = data.split(":", 2)[2]
        svc = cfg.get_service(svc_id)
        log_file = svc.get("log_file")
        verified_path = LogManager.get_file_for_send(log_file)

        if not verified_path:
            bot.answer_callback_query(call.id, "Log file not found or empty.", show_alert=True)
            return

        bot.answer_callback_query(call.id, "Uploading log file...")
        try:
            with open(verified_path, "rb") as doc:
                bot.send_document(
                    chat_id,
                    doc,
                    caption=f"📦 Log file for *{svc.get('name')}*"
                )

            # Apply post-send action (none, truncate, or delete)
            action = cfg.log_settings.get("post_send_action", "none")
            cleanup_msg = LogManager.post_send_cleanup(verified_path, action)
            if cleanup_msg:
                bot.send_message(chat_id, cleanup_msg)

        except Exception as e:
            bot.send_message(chat_id, f"❌ Failed to send log document: {e}")

    # 4. Power Management & Confirmation
    elif data == "power:reboot":
        bot.edit_message_text(
            "⚠️ *Confirm Reboot*\nAre you sure you want to reboot the Raspberry Pi?",
            chat_id=chat_id,
            message_id=msg_id,
            reply_markup=keyboards.confirm_keyboard("reboot")
        )
        bot.answer_callback_query(call.id)

    elif data == "power:shutdown":
        bot.edit_message_text(
            "🛑 *Confirm Shutdown*\nAre you sure you want to turn off the Raspberry Pi?",
            chat_id=chat_id,
            message_id=msg_id,
            reply_markup=keyboards.confirm_keyboard("shutdown")
        )
        bot.answer_callback_query(call.id)

    elif data == "confirm:no":
        bot.answer_callback_query(call.id, "Action cancelled.")
        cmd_menu(call.message)

    elif data == "confirm:yes:reboot":
        bot.answer_callback_query(call.id, "Rebooting Raspberry Pi...")
        cmd = cfg.system_settings.get("reboot_cmd", "sudo reboot")
        logger.info(f"Initiating reboot with command: {cmd}")
        success, out = run_command(cmd)
        if not success:
            logger.error(f"Reboot command failed: {out}")
            bot.send_message(
                chat_id,
                f"❌ *Reboot Failed!*\n`{out}`\n\n"
                "💡 *Troubleshooting:*\n"
                "• Check if the user requires a sudo password.\n"
                "• Enable passwordless sudo: `echo \"$USER ALL=(ALL) NOPASSWD: ALL\" | sudo tee /etc/sudoers.d/010_nopasswd`"
            )
        else:
            bot.send_message(chat_id, "🔄 *Raspberry Pi is rebooting now.* Please wait a few moments for it to come back online.")

    elif data == "confirm:yes:shutdown":
        bot.answer_callback_query(call.id, "Shutting down Raspberry Pi...")
        cmd = cfg.system_settings.get("shutdown_cmd", "sudo shutdown now")
        logger.info(f"Initiating shutdown with command: {cmd}")
        success, out = run_command(cmd)
        if not success:
            logger.error(f"Shutdown command failed: {out}")
            bot.send_message(
                chat_id,
                f"❌ *Shutdown Failed!*\n`{out}`\n\n"
                "💡 *Troubleshooting:*\n"
                "• Check if the user requires a sudo password.\n"
                "• Enable passwordless sudo: `echo \"$USER ALL=(ALL) NOPASSWD: ALL\" | sudo tee /etc/sudoers.d/010_nopasswd`"
            )
        else:
            bot.send_message(chat_id, "🛑 *Raspberry Pi is shutting down now.* Power cycle will be required to turn it back on.")


# ==============================================================================
# Main Entry Point & Startup Alert
# ==============================================================================

def send_startup_alert():
    """Send startup notification to all configured admins upon boot."""
    if not cfg.send_startup_message:
        return

    pref = cfg.system_settings.get("preferred_interface", "wlan0")
    alert_text = get_startup_summary(pref)

    for admin_id in cfg.admin_chat_ids:
        try:
            bot.send_message(admin_id, alert_text, reply_markup=get_main_menu_markup())
            logger.info(f"Startup alert sent to admin chat ID: {admin_id}")
        except Exception as e:
            logger.warning(f"Failed to send startup alert to {admin_id}: {e}")


stop_event = threading.Event()


def periodic_status_worker():
    """Background worker thread that periodically broadcasts system health to admins."""
    settings = cfg.periodic_status_settings
    if not settings.get("enabled", False):
        logger.info("Periodic status reporting is disabled.")
        return

    interval_minutes = settings.get("interval_minutes", 180)
    try:
        interval_minutes = int(interval_minutes)
    except (ValueError, TypeError):
        interval_minutes = 180

    if interval_minutes < 1:
        logger.warning(f"Invalid interval_minutes ({interval_minutes}), defaulting to 180.")
        interval_minutes = 180

    interval_seconds = interval_minutes * 60
    logger.info(f"Periodic status reporting started: reports scheduled every {interval_minutes} minutes ({interval_seconds}s).")

    while not stop_event.is_set():
        # Sleep for configured interval (or wake up immediately if stop_event is signaled)
        interrupted = stop_event.wait(timeout=interval_seconds)
        if interrupted:
            break

        current_settings = cfg.periodic_status_settings
        if not current_settings.get("enabled", False):
            logger.info("Periodic status reporting has been disabled.")
            break

        # Adjust interval dynamically if it changed in config
        new_interval = current_settings.get("interval_minutes", interval_minutes)
        try:
            new_interval = int(new_interval)
            if new_interval >= 1:
                interval_minutes = new_interval
                interval_seconds = interval_minutes * 60
        except (ValueError, TypeError):
            pass

        try:
            pref = cfg.system_settings.get("preferred_interface", "wlan0")
            status_text = get_system_summary(pref, title="Raspberry Pi Periodic Health Report")

            for admin_id in cfg.admin_chat_ids:
                try:
                    bot.send_message(admin_id, status_text)
                    logger.info(f"Periodic status report sent to admin: {admin_id}")
                except Exception as e:
                    logger.warning(f"Failed to send periodic status report to {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Error generating or sending periodic status report: {e}", exc_info=True)


def main():
    logger.info("Starting PiPilot...")
    send_startup_alert()

    # Start periodic status monitoring thread
    status_thread = threading.Thread(
        target=periodic_status_worker,
        daemon=True,
        name="PeriodicStatusWorker"
    )
    status_thread.start()

    # Register bot commands menu with Telegram for auto-completion
    try:
        bot.set_my_commands([
            types.BotCommand("menu", "Open interactive control dashboard"),
            types.BotCommand("status", "System resources, CPU temp & uptime"),
            types.BotCommand("network", "Network interfaces & Wi-Fi"),
            types.BotCommand("services", "Control configured applications"),
            types.BotCommand("logs", "Inspect or download logs"),
            types.BotCommand("apps", "Active apps across Java, Python, JS"),
            types.BotCommand("py", "Active Python processes"),
            types.BotCommand("js", "Active Node.js / JavaScript apps"),
            types.BotCommand("reboot", "Reboot Raspberry Pi"),
            types.BotCommand("shutdown", "Shutdown Raspberry Pi"),
            types.BotCommand("help", "Command reference"),
        ])
    except Exception as e:
        logger.warning(f"Could not register Telegram bot commands: {e}")

    logger.info("Bot is active and polling for updates...")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=25)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down bot...")
        stop_event.set()


if __name__ == "__main__":
    main()
