"""Admin commands for managing bot users and viewing statistics."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Application
)
from telegram.constants import ParseMode
from database import Database
import config

db = Database()


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel with buttons."""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    keyboard = [
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Общая статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("💰 Стоимость токенов", callback_data="admin_pricing")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ <b>Панель администратора</b>\n\nВыберите действие:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel callbacks."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not db.is_admin(user_id):
        await query.edit_message_text("❌ У вас нет прав администратора.")
        return

    if query.data == "admin_users":
        users = db.get_all_users()

        users_text = "👥 <b>Список пользователей</b>\n\n"

        authorized_users = [u for u in users if u['is_authorized']]
        unauthorized_users = [u for u in users if not u['is_authorized']]

        if authorized_users:
            users_text += "<b>Авторизованные:</b>\n"
            for user in authorized_users:
                name = user['first_name'] or "Unknown"
                username = f"@{user['username']}" if user['username'] else ""
                admin_badge = " 👑" if user['is_admin'] else ""
                users_text += f"• {name} {username}{admin_badge}\n  ID: <code>{user['user_id']}</code>\n"
            users_text += "\n"

        if unauthorized_users:
            users_text += "<b>Ожидают авторизации:</b>\n"
            for user in unauthorized_users:
                name = user['first_name'] or "Unknown"
                username = f"@{user['username']}" if user['username'] else ""
                users_text += f"• {name} {username}\n  ID: <code>{user['user_id']}</code>\n"

        users_text += f"\n<b>Всего пользователей:</b> {len(users)}"

        await query.edit_message_text(users_text, parse_mode=ParseMode.HTML)

    elif query.data == "admin_stats":
        stats = db.get_total_usage()

        stats_text = (
            "📊 <b>Общая статистика использования</b>\n\n"
            f"Всего запросов: {stats['total_requests']:,}\n"
            f"Токенов ввода: {stats['total_input_tokens']:,}\n"
            f"Токенов вывода: {stats['total_output_tokens']:,}\n"
            f"Всего токенов: {stats['total_input_tokens'] + stats['total_output_tokens']:,}\n\n"
            f"💰 <b>Общая стоимость:</b> ${stats['total_cost']:.4f}\n\n"
            f"Используемая модель: <code>{config.CLAUDE_MODEL}</code>"
        )

        await query.edit_message_text(stats_text, parse_mode=ParseMode.HTML)

    elif query.data == "admin_pricing":
        pricing_text = "💰 <b>Стоимость токенов Claude</b>\n\n"

        for model, prices in config.CLAUDE_PRICING.items():
            pricing_text += f"<b>{model}</b>\n"
            pricing_text += f"  Ввод: ${prices['input']:.2f} / 1M токенов\n"
            pricing_text += f"  Вывод: ${prices['output']:.2f} / 1M токенов\n\n"

        current = config.CLAUDE_PRICING.get(config.CLAUDE_MODEL)
        if current:
            pricing_text += f"<b>Текущая модель:</b> <code>{config.CLAUDE_MODEL}</code>\n"
            pricing_text += f"Ввод: ${current['input']:.2f} / 1M\n"
            pricing_text += f"Вывод: ${current['output']:.2f} / 1M"

        await query.edit_message_text(pricing_text, parse_mode=ParseMode.HTML)


async def authorize_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Authorize a user by ID."""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Использование: <code>/authorize &lt;user_id&gt;</code>\n"
            "Пример: <code>/authorize 123456789</code>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Некорректный ID пользователя.")
        return

    # Check if user exists in database
    users = db.get_all_users()
    user_exists = any(u['user_id'] == target_user_id for u in users)

    if not user_exists:
        await update.message.reply_text(
            f"⚠️ Пользователь с ID <code>{target_user_id}</code> не найден в базе.\n"
            "Пользователь должен сначала написать боту команду /start",
            parse_mode=ParseMode.HTML
        )
        return

    db.authorize_user(target_user_id)
    await update.message.reply_text(
        f"✅ Пользователь <code>{target_user_id}</code> авторизован.",
        parse_mode=ParseMode.HTML
    )


async def deauthorize_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deauthorize a user by ID."""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Использование: <code>/deauthorize &lt;user_id&gt;</code>\n"
            "Пример: <code>/deauthorize 123456789</code>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Некорректный ID пользователя.")
        return

    if target_user_id == config.ADMIN_USER_ID:
        await update.message.reply_text("❌ Нельзя деавторизовать главного администратора.")
        return

    db.deauthorize_user(target_user_id)
    await update.message.reply_text(
        f"✅ Пользователь <code>{target_user_id}</code> деавторизован.",
        parse_mode=ParseMode.HTML
    )


async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all users."""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    users = db.get_all_users()

    users_text = "👥 <b>Список всех пользователей</b>\n\n"

    authorized_users = [u for u in users if u['is_authorized']]
    unauthorized_users = [u for u in users if not u['is_authorized']]

    if authorized_users:
        users_text += "<b>Авторизованные:</b>\n"
        for user in authorized_users:
            name = user['first_name'] or "Unknown"
            username = f"@{user['username']}" if user['username'] else ""
            admin_badge = " 👑" if user['is_admin'] else ""
            users_text += f"• {name} {username}{admin_badge}\n  ID: <code>{user['user_id']}</code>\n"
        users_text += "\n"

    if unauthorized_users:
        users_text += "<b>Ожидают авторизации:</b>\n"
        for user in unauthorized_users:
            name = user['first_name'] or "Unknown"
            username = f"@{user['username']}" if user['username'] else ""
            users_text += f"• {name} {username}\n  ID: <code>{user['user_id']}</code>\n"

    users_text += f"\n<b>Всего пользователей:</b> {len(users)}"

    await update.message.reply_text(users_text, parse_mode=ParseMode.HTML)


async def total_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show total usage statistics."""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    stats = db.get_total_usage()

    stats_text = (
        "📊 <b>Общая статистика использования</b>\n\n"
        f"Всего запросов: {stats['total_requests']:,}\n"
        f"Токенов ввода: {stats['total_input_tokens']:,}\n"
        f"Токенов вывода: {stats['total_output_tokens']:,}\n"
        f"Всего токенов: {stats['total_input_tokens'] + stats['total_output_tokens']:,}\n\n"
        f"💰 <b>Общая стоимость:</b> ${stats['total_cost']:.4f}\n\n"
        f"Используемая модель: <code>{config.CLAUDE_MODEL}</code>"
    )

    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)


def register_admin_handlers(application: Application):
    """Register all admin command handlers."""
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("authorize", authorize_user_command))
    application.add_handler(CommandHandler("deauthorize", deauthorize_user_command))
    application.add_handler(CommandHandler("users", list_users_command))
    application.add_handler(CommandHandler("totalstats", total_stats_command))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
