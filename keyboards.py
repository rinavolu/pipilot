from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard(
    java_enabled: bool = False,
    python_enabled: bool = False,
    js_enabled: bool = False,
) -> InlineKeyboardMarkup:
    """Generate the root control menu."""
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("📊 System Health", callback_data="nav:health"),
        InlineKeyboardButton("🌐 Network & IP", callback_data="nav:network"),
        InlineKeyboardButton("⚙️ Services", callback_data="nav:services"),
        InlineKeyboardButton("📜 View Logs", callback_data="nav:logs"),
    ]

    app_buttons = []
    if java_enabled:
        app_buttons.append(InlineKeyboardButton("☕ Java Apps", callback_data="nav:java"))
    if python_enabled:
        app_buttons.append(InlineKeyboardButton("🐍 Python Apps", callback_data="nav:python"))
    if js_enabled:
        app_buttons.append(InlineKeyboardButton("🟨 JS Apps", callback_data="nav:js"))

    markup.add(*buttons)
    if app_buttons:
        markup.add(*app_buttons)

    markup.add(InlineKeyboardButton("ℹ️ Help", callback_data="nav:help"))

    # Power controls on the bottom row
    markup.row(
        InlineKeyboardButton("🔄 Reboot Pi", callback_data="power:reboot"),
        InlineKeyboardButton("⏻ Shutdown Pi", callback_data="power:shutdown"),
    )
    return markup


def services_menu_keyboard(services: list) -> InlineKeyboardMarkup:
    """List all configured services."""
    markup = InlineKeyboardMarkup(row_width=1)
    for svc in services:
        name = svc.get("name", svc.get("id"))
        svc_id = svc.get("id")
        markup.add(InlineKeyboardButton(f"⚙️ {name}", callback_data=f"svc:view:{svc_id}"))

    markup.add(InlineKeyboardButton("« Back to Main Menu", callback_data="nav:main"))
    return markup


def service_detail_keyboard(service: dict) -> InlineKeyboardMarkup:
    """Control buttons for a specific service."""
    markup = InlineKeyboardMarkup(row_width=3)
    svc_id = service.get("id")

    markup.row(
        InlineKeyboardButton("▶ Start", callback_data=f"svc:start:{svc_id}"),
        InlineKeyboardButton("⏹ Stop", callback_data=f"svc:stop:{svc_id}"),
        InlineKeyboardButton("🔄 Restart", callback_data=f"svc:restart:{svc_id}"),
    )

    if service.get("log_file"):
        markup.row(
            InlineKeyboardButton("📄 View Logs", callback_data=f"log:tail:{svc_id}"),
            InlineKeyboardButton("📥 Download Log", callback_data=f"log:send:{svc_id}"),
        )

    markup.row(
        InlineKeyboardButton("« Services", callback_data="nav:services"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="nav:main"),
    )
    return markup


def logs_menu_keyboard(services: list) -> InlineKeyboardMarkup:
    """List services that have configured logs."""
    markup = InlineKeyboardMarkup(row_width=1)
    has_logs = False
    for svc in services:
        if svc.get("log_file"):
            has_logs = True
            name = svc.get("name", svc.get("id"))
            svc_id = svc.get("id")
            markup.add(InlineKeyboardButton(f"📄 {name} Log", callback_data=f"log:view:{svc_id}"))

    if not has_logs:
        markup.add(InlineKeyboardButton("No log files configured", callback_data="nav:none"))

    markup.add(InlineKeyboardButton("« Back to Main Menu", callback_data="nav:main"))
    return markup


def log_actions_keyboard(service_id: str) -> InlineKeyboardMarkup:
    """Actions for a specific log file (tail or send)."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton("📄 View Last 50 Lines", callback_data=f"log:tail:{service_id}"),
        InlineKeyboardButton("📥 Download File", callback_data=f"log:send:{service_id}"),
    )
    markup.row(
        InlineKeyboardButton("« Back to Logs", callback_data="nav:logs"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="nav:main"),
    )
    return markup


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard for dangerous actions like reboot/shutdown."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton("✅ Yes, Proceed", callback_data=f"confirm:yes:{action}"),
        InlineKeyboardButton("❌ Cancel", callback_data="confirm:no"),
    )
    return markup


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Simple back button to return to the main dashboard."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🏠 Main Menu", callback_data="nav:main"))
    return markup
