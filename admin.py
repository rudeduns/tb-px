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
        [InlineKeyboardButton("🔧 Управление пользователями", callback_data="admin_manage_users")],
        [InlineKeyboardButton("💬 Системный промпт", callback_data="admin_prompt_menu")],
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

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(users_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

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

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

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

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(pricing_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    elif query.data == "admin_manage_users":
        users = db.get_all_users()
        unauthorized_users = [u for u in users if not u['is_authorized']]
        authorized_users = [u for u in users if u['is_authorized'] and not u['is_admin']]

        manage_text = "🔧 <b>Управление пользователями</b>\n\n"

        keyboard = []

        if unauthorized_users:
            manage_text += "<b>Ожидают авторизации:</b>\n"
            for user in unauthorized_users:
                name = user['first_name'] or "Unknown"
                username = f"@{user['username']}" if user['username'] else ""
                manage_text += f"• {name} {username}\n  ID: <code>{user['user_id']}</code>\n"
                keyboard.append([InlineKeyboardButton(
                    f"✅ Авторизовать {name}",
                    callback_data=f"admin_auth_{user['user_id']}"
                )])
            manage_text += "\n"
        else:
            manage_text += "Нет пользователей, ожидающих авторизации.\n\n"

        if authorized_users:
            manage_text += "<b>Авторизованные пользователи:</b>\n"
            for user in authorized_users:
                name = user['first_name'] or "Unknown"
                username = f"@{user['username']}" if user['username'] else ""
                manage_text += f"• {name} {username}\n  ID: <code>{user['user_id']}</code>\n"
                keyboard.append([InlineKeyboardButton(
                    f"❌ Деавторизовать {name}",
                    callback_data=f"admin_deauth_{user['user_id']}"
                )])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(manage_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    elif query.data.startswith("admin_auth_"):
        target_user_id = int(query.data.replace("admin_auth_", ""))
        db.authorize_user(target_user_id)
        await query.answer(f"✅ Пользователь {target_user_id} авторизован!", show_alert=True)
        # Refresh the management menu
        await admin_callback(update, context)

    elif query.data.startswith("admin_deauth_"):
        target_user_id = int(query.data.replace("admin_deauth_", ""))
        if target_user_id == config.ADMIN_USER_ID:
            await query.answer("❌ Нельзя деавторизовать главного администратора!", show_alert=True)
            return
        db.deauthorize_user(target_user_id)
        await query.answer(f"✅ Пользователь {target_user_id} деавторизован!", show_alert=True)
        # Refresh the management menu
        await admin_callback(update, context)

    elif query.data == "admin_prompt_menu":
        current_prompt = db.get_setting('system_prompt')

        prompt_text = "💬 <b>Управление системным промптом</b>\n\n"

        if current_prompt:
            prompt_text += f"<b>Текущий промпт:</b>\n<code>{current_prompt[:200]}</code>"
            if len(current_prompt) > 200:
                prompt_text += "..."
        else:
            prompt_text += "Системный промпт не установлен."

        keyboard = [
            [InlineKeyboardButton("📋 Показать полностью", callback_data="admin_prompt_show")],
            [InlineKeyboardButton("🗑️ Очистить промпт", callback_data="admin_prompt_clear")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(prompt_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    elif query.data == "admin_prompt_show":
        current_prompt = db.get_setting('system_prompt')

        if current_prompt:
            prompt_text = f"📋 <b>Системный промпт:</b>\n\n<code>{current_prompt}</code>"
        else:
            prompt_text = "ℹ️ Системный промпт не установлен."

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_prompt_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(prompt_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    elif query.data == "admin_prompt_clear":
        db.set_setting('system_prompt', '')
        await query.answer("✅ Системный промпт очищен!", show_alert=True)
        # Return to prompt menu
        query.data = "admin_prompt_menu"
        await admin_callback(update, context)

    elif query.data == "admin_back":
        # Return to main admin menu
        keyboard = [
            [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
            [InlineKeyboardButton("📊 Общая статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 Стоимость токенов", callback_data="admin_pricing")],
            [InlineKeyboardButton("🔧 Управление пользователями", callback_data="admin_manage_users")],
            [InlineKeyboardButton("💬 Системный промпт", callback_data="admin_prompt_menu")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "⚙️ <b>Панель администратора</b>\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )


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


async def set_prompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set system prompt for all conversations."""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    # Check if prompt text was provided
    if not context.args:
        await update.message.reply_text(
            "❌ Использование: <code>/setprompt текст промпта</code>\n\n"
            "Пример:\n"
            "<code>/setprompt Ты - дружелюбный помощник. Отвечай кратко и по делу.</code>\n\n"
            "Чтобы удалить промпт:\n"
            "<code>/setprompt clear</code>",
            parse_mode=ParseMode.HTML
        )
        return

    # Get full prompt text from args
    prompt_text = " ".join(context.args)

    if prompt_text.lower() == "clear":
        # Clear system prompt
        db.set_setting('system_prompt', '')
        await update.message.reply_text("✅ Системный промпт удален.")
    else:
        # Set new system prompt
        db.set_setting('system_prompt', prompt_text)
        await update.message.reply_text(
            f"✅ Системный промпт установлен:\n\n<code>{prompt_text}</code>",
            parse_mode=ParseMode.HTML
        )


async def show_prompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current system prompt."""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    current_prompt = db.get_setting('system_prompt')

    if current_prompt:
        await update.message.reply_text(
            f"📋 <b>Текущий системный промпт:</b>\n\n<code>{current_prompt}</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("ℹ️ Системный промпт не установлен.")


def register_admin_handlers(application: Application):
    """Register all admin command handlers."""
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("authorize", authorize_user_command))
    application.add_handler(CommandHandler("deauthorize", deauthorize_user_command))
    application.add_handler(CommandHandler("users", list_users_command))
    application.add_handler(CommandHandler("totalstats", total_stats_command))
    application.add_handler(CommandHandler("setprompt", set_prompt_command))
    application.add_handler(CommandHandler("showprompt", show_prompt_command))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
