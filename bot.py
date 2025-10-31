"""Main Telegram bot implementation with Claude AI integration."""
import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode, ChatAction
import config
from database import Database
from claude_client import ClaudeClient

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database and Claude client
db = Database()
claude = ClaudeClient()

# Telegram message length limit
MAX_MESSAGE_LENGTH = 4096


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split long message into chunks that fit Telegram's limit."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by paragraphs first
    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        # If single paragraph is too long, split by sentences
        if len(paragraph) > max_length:
            sentences = paragraph.split('. ')
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 2 < max_length:
                    current_chunk += sentence + '. '
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + '. '
        else:
            # Try to add paragraph to current chunk
            if len(current_chunk) + len(paragraph) + 2 < max_length:
                current_chunk += paragraph + '\n\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + '\n\n'

    # Add remaining text
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text[:max_length]]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)

    if not db.is_authorized(user.id):
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            "❌ У вас пока нет доступа к боту.\n"
            f"Ваш ID: `{user.id}`\n\n"
            "Отправьте этот ID администратору для получения доступа.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот с интеграцией Claude AI. Вы можете:\n"
        "• Задавать любые вопросы\n"
        "• Отправлять картинки для анализа\n"
        "• Отправлять текстовые файлы\n\n"
        "Команды:\n"
        "/clear - Очистить историю разговора\n"
        "/help - Показать справку\n"
        "/stats - Показать вашу статистику использования",
        parse_mode=ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user_id = update.effective_user.id

    if not db.is_authorized(user_id):
        await update.message.reply_text("❌ У вас нет доступа к боту.")
        return

    help_text = (
        "🤖 *Справка по боту*\n\n"
        "*Основные команды:*\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/clear - Очистить историю разговора\n"
        "/stats - Показать статистику использования\n\n"
        "*Возможности:*\n"
        "• Отправьте текстовое сообщение - получите ответ от Claude\n"
        "• Отправьте картинку с подписью - Claude проанализирует её\n"
        "• Отправьте текстовый файл - Claude прочитает и ответит\n\n"
        "*Особенности:*\n"
        "• Бот помнит контекст разговора\n"
        "• Используется модель: " + config.CLAUDE_MODEL
    )

    if db.is_admin(user_id):
        help_text += (
            "\n\n*Команды администратора:*\n"
            "/admin - Панель администратора\n"
            "/authorize <user_id> - Добавить пользователя\n"
            "/deauthorize <user_id> - Удалить пользователя\n"
            "/users - Список всех пользователей\n"
            "/totalstats - Общая статистика"
        )

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command to clear conversation history."""
    user_id = update.effective_user.id

    if not db.is_authorized(user_id):
        await update.message.reply_text("❌ У вас нет доступа к боту.")
        return

    db.clear_conversation_history(user_id)
    await update.message.reply_text("🗑️ История разговора очищена.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command to show user statistics."""
    user_id = update.effective_user.id

    if not db.is_authorized(user_id):
        await update.message.reply_text("❌ У вас нет доступа к боту.")
        return

    usage = db.get_user_usage(user_id)

    stats_text = (
        "📊 *Ваша статистика*\n\n"
        f"Запросов: {usage['total_requests']}\n"
        f"Токенов ввода: {usage['total_input_tokens']:,}\n"
        f"Токенов вывода: {usage['total_output_tokens']:,}\n"
        f"Общая стоимость: ${usage['total_cost']:.4f}"
    )

    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    user_id = update.effective_user.id

    if not db.is_authorized(user_id):
        await update.message.reply_text(
            "❌ У вас нет доступа к боту.\n"
            f"Ваш ID: `{user_id}`\n"
            "Отправьте этот ID администратору.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Update last active
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name, is_authorized=True)

    # Show typing indicator
    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        # Get conversation history
        history = db.get_conversation_history(user_id, limit=10)

        # Add current message
        user_message = update.message.text
        history.append({"role": "user", "content": user_message})

        # Send to Claude
        response_text, input_tokens, output_tokens = claude.send_message(history)

        # Save to database
        db.add_message_to_history(user_id, "user", user_message)
        db.add_message_to_history(user_id, "assistant", response_text)

        # Log usage
        cost = db.log_usage(user_id, config.CLAUDE_MODEL, input_tokens, output_tokens)

        # Send response - split if too long, try with Markdown, fallback to plain text
        message_chunks = split_message(response_text)

        for i, chunk in enumerate(message_chunks):
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception as parse_error:
                # Markdown parsing or length error, send as plain text
                logger.warning(f"Message send error for user {user_id}: {parse_error}")
                try:
                    await update.message.reply_text(chunk)
                except Exception as e:
                    # If still fails, truncate
                    logger.error(f"Failed to send chunk {i+1}: {e}")
                    await update.message.reply_text(chunk[:MAX_MESSAGE_LENGTH])

        # Log for admin
        logger.info(f"User {user_id} - Tokens: {input_tokens}+{output_tokens}, Cost: ${cost:.4f}")

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке сообщения:\n{str(e)}"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages."""
    user_id = update.effective_user.id

    if not db.is_authorized(user_id):
        await update.message.reply_text("❌ У вас нет доступа к боту.")
        return

    # Update last active
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name, is_authorized=True)

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()

        # Download photo
        photo_bytes = await photo_file.download_as_bytearray()

        # Get caption or default question
        caption = update.message.caption or "Что изображено на этой картинке?"

        # Get conversation history
        history = db.get_conversation_history(user_id, limit=10)
        history.append({"role": "user", "content": caption})

        # Send to Claude with image
        response_text, input_tokens, output_tokens = claude.send_message_with_image(
            history, bytes(photo_bytes), "jpeg"
        )

        # Save to database
        db.add_message_to_history(user_id, "user", f"[Image] {caption}")
        db.add_message_to_history(user_id, "assistant", response_text)

        # Log usage
        cost = db.log_usage(user_id, config.CLAUDE_MODEL, input_tokens, output_tokens)

        # Send response - split if too long, try with Markdown, fallback to plain text
        message_chunks = split_message(response_text)

        for i, chunk in enumerate(message_chunks):
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception as parse_error:
                # Markdown parsing or length error, send as plain text
                logger.warning(f"Message send error for user {user_id} (image): {parse_error}")
                try:
                    await update.message.reply_text(chunk)
                except Exception as e:
                    logger.error(f"Failed to send chunk {i+1}: {e}")
                    await update.message.reply_text(chunk[:MAX_MESSAGE_LENGTH])

        logger.info(f"User {user_id} - Image - Tokens: {input_tokens}+{output_tokens}, Cost: ${cost:.4f}")

    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке изображения:\n{str(e)}"
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages."""
    user_id = update.effective_user.id

    if not db.is_authorized(user_id):
        await update.message.reply_text("❌ У вас нет доступа к боту.")
        return

    # Update last active
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name, is_authorized=True)

    await update.message.chat.send_action(ChatAction.TYPING)

    document = update.message.document

    # Check if it's a text file
    if not document.mime_type or not document.mime_type.startswith('text/'):
        await update.message.reply_text(
            "❌ Поддерживаются только текстовые файлы.\n"
            "Поддерживаемые форматы: .txt, .py, .js, .json, .md, и т.д."
        )
        return

    # Check file size (max 1MB)
    if document.file_size > 1_000_000:
        await update.message.reply_text("❌ Файл слишком большой. Максимум: 1 МБ")
        return

    try:
        # Download document
        doc_file = await document.get_file()
        doc_bytes = await doc_file.download_as_bytearray()

        # Decode text
        try:
            doc_text = bytes(doc_bytes).decode('utf-8')
        except UnicodeDecodeError:
            doc_text = bytes(doc_bytes).decode('latin-1')

        # Get caption or default question
        caption = update.message.caption or "Проанализируй этот документ"

        # Get conversation history
        history = db.get_conversation_history(user_id, limit=5)
        history.append({"role": "user", "content": caption})

        # Send to Claude with document
        response_text, input_tokens, output_tokens = claude.send_message_with_document(
            history, doc_text
        )

        # Save to database
        db.add_message_to_history(user_id, "user", f"[Document: {document.file_name}] {caption}")
        db.add_message_to_history(user_id, "assistant", response_text)

        # Log usage
        cost = db.log_usage(user_id, config.CLAUDE_MODEL, input_tokens, output_tokens)

        # Send response - split if too long, try with Markdown, fallback to plain text
        message_chunks = split_message(response_text)

        for i, chunk in enumerate(message_chunks):
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception as parse_error:
                # Markdown parsing or length error, send as plain text
                logger.warning(f"Message send error for user {user_id} (document): {parse_error}")
                try:
                    await update.message.reply_text(chunk)
                except Exception as e:
                    logger.error(f"Failed to send chunk {i+1}: {e}")
                    await update.message.reply_text(chunk[:MAX_MESSAGE_LENGTH])

        logger.info(f"User {user_id} - Document - Tokens: {input_tokens}+{output_tokens}, Cost: ${cost:.4f}")

    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке документа:\n{str(e)}"
        )


def main():
    """Start the bot."""
    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    # Create application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("stats", stats))

    # Import admin handlers
    from admin import register_admin_handlers
    register_admin_handlers(application)

    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Start bot
    logger.info("Bot started successfully")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
