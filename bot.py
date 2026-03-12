"""Main Telegram bot implementation with Claude AI integration."""
import logging
import io
import asyncio
import re
import httpx
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


def is_bot_mentioned(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if bot is mentioned in a group message (via @ or reply)."""
    # Always respond in private chats
    if update.effective_chat.type == 'private':
        return True

    message = update.message
    if not message:
        return False

    # Check if message is a reply to bot's message
    if message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
        return True

    # Check if bot is mentioned in message text
    if message.entities and message.text:
        for entity in message.entities:
            if entity.type in ('mention', 'text_mention'):
                if entity.type == 'mention':
                    mention_text = message.text[entity.offset:entity.offset + entity.length]
                    bot_username = context.bot.username
                    if mention_text == f'@{bot_username}' or mention_text.lower() == f'@{bot_username.lower()}':
                        return True
                elif entity.type == 'text_mention' and entity.user.id == context.bot.id:
                    return True

    # Check if bot is mentioned in caption (for photos)
    if message.caption and message.caption_entities:
        for entity in message.caption_entities:
            if entity.type in ('mention', 'text_mention'):
                if entity.type == 'mention':
                    mention_text = message.caption[entity.offset:entity.offset + entity.length]
                    bot_username = context.bot.username
                    if mention_text == f'@{bot_username}' or mention_text.lower() == f'@{bot_username.lower()}':
                        return True
                elif entity.type == 'text_mention' and entity.user.id == context.bot.id:
                    return True

    return False


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


async def keep_typing(chat, stop_event: asyncio.Event):
    """Keep sending typing action every 5 seconds until stopped."""
    try:
        while not stop_event.is_set():
            await chat.send_action(ChatAction.TYPING)
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"Error sending typing action: {e}")


def convert_markdown_to_html(text: str) -> str:
    """Convert Markdown formatting to Telegram HTML."""
    # Code blocks ``` (process first to avoid affecting ** inside)
    text = re.sub(r'```(.*?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)

    # Inline code `
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Bold text **
    text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', text)

    # Italic * (single asterisks, but not inside words)
    text = re.sub(r'(?<!\*)\*(?!\*)([^\*]+)\*(?!\*)', r'<i>\1</i>', text)

    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)

    if not db.is_authorized(user.id):
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            "❌ У вас пока нет доступа к боту.\n"
            f"Ваш ID: <code>{user.id}</code>\n\n"
            "Отправьте этот ID администратору для получения доступа.",
            parse_mode=ParseMode.HTML
        )
        return

    voice_line = "\n• Отправлять голосовые сообщения (распознавание речи)" if config.WHISPER_URL else ""
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот с интеграцией Claude AI. Вы можете:\n"
        "• Задавать любые вопросы\n"
        "• Отправлять картинки для анализа\n"
        "• Отправлять текстовые файлы"
        f"{voice_line}\n\n"
        "Команды:\n"
        "/clear - Очистить историю разговора\n"
        "/help - Показать справку\n"
        "/stats - Показать вашу статистику использования",
        parse_mode=ParseMode.HTML
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user_id = update.effective_user.id

    if not db.is_authorized(user_id):
        await update.message.reply_text("❌ У вас нет доступа к боту.")
        return

    help_text = (
        "🤖 <b>Справка по боту</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/clear - Очистить историю разговора\n"
        "/stats - Показать статистику использования\n\n"
        "<b>Возможности:</b>\n"
        "• Отправьте текстовое сообщение - получите ответ от Claude\n"
        "• Отправьте картинку с подписью - Claude проанализирует её\n"
        "• Отправьте текстовый файл - Claude прочитает и ответит\n"
        + ("• Отправьте голосовое сообщение - будет распознано и отправлено Claude\n" if config.WHISPER_URL else "")
        + "\n"
        "<b>Особенности:</b>\n"
        "• Бот помнит контекст разговора\n"
        "• Используется модель: " + config.CLAUDE_MODEL
    )

    if db.is_admin(user_id):
        help_text += (
            "\n\n<b>Команды администратора:</b>\n"
            "/admin - Панель администратора\n"
            "/authorize &lt;user_id&gt; - Добавить пользователя\n"
            "/deauthorize &lt;user_id&gt; - Удалить пользователя\n"
            "/users - Список всех пользователей\n"
            "/totalstats - Общая статистика\n"
            "/setprompt &lt;текст&gt; - Установить системный промпт\n"
            "/showprompt - Показать текущий промпт"
        )

    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command to clear conversation history."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not db.is_authorized(user_id):
        await update.message.reply_text("❌ У вас нет доступа к боту.")
        return

    db.clear_conversation_history(user_id, chat_id)
    await update.message.reply_text("🗑️ История разговора очищена в этом чате.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command to show user statistics."""
    user_id = update.effective_user.id

    if not db.is_authorized(user_id):
        await update.message.reply_text("❌ У вас нет доступа к боту.")
        return

    usage = db.get_user_usage(user_id)

    stats_text = (
        "📊 <b>Ваша статистика</b>\n\n"
        f"Запросов: {usage['total_requests']}\n"
        f"Токенов ввода: {usage['total_input_tokens']:,}\n"
        f"Токенов вывода: {usage['total_output_tokens']:,}\n"
        f"Общая стоимость: ${usage['total_cost']:.4f}"
    )

    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    user_id = update.effective_user.id

    # In groups, only respond if bot is mentioned
    if not is_bot_mentioned(update, context):
        return

    if not db.is_authorized(user_id):
        await update.message.reply_text(
            "❌ У вас нет доступа к боту.\n"
            f"Ваш ID: <code>{user_id}</code>\n"
            "Отправьте этот ID администратору.",
            parse_mode=ParseMode.HTML
        )
        return

    # Update last active
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name, is_authorized=True)

    # Send typing status immediately
    await update.message.chat.send_action(ChatAction.TYPING)

    # Start continuous typing indicator
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.message.chat, stop_typing))

    try:
        chat_id = update.effective_chat.id

        # Get conversation history for this specific chat
        history = db.get_conversation_history(user_id, chat_id, limit=10)

        # Add current message
        user_message = update.message.text
        history.append({"role": "user", "content": user_message})

        # Get system prompt from database
        system_prompt = db.get_setting('system_prompt')

        # Send to Claude with system prompt
        response_text, input_tokens, output_tokens = claude.send_message(history, system_prompt)

        # Convert Markdown to HTML formatting
        response_text = convert_markdown_to_html(response_text)

        # Save to database with chat_id
        db.add_message_to_history(user_id, chat_id, "user", user_message)
        db.add_message_to_history(user_id, chat_id, "assistant", response_text)

        # Log usage
        cost = db.log_usage(user_id, config.CLAUDE_MODEL, input_tokens, output_tokens)

        # Send response - split if too long, try with HTML, fallback to plain text
        message_chunks = split_message(response_text)

        for i, chunk in enumerate(message_chunks):
            # Small delay between chunks to look more natural
            if i > 0:
                await asyncio.sleep(0.5)

            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
            except Exception as parse_error:
                # HTML parsing or length error, send as plain text
                logger.warning(f"Message send error for user {user_id}: {parse_error}")
                try:
                    await update.message.reply_text(chunk)
                except Exception as e:
                    # If still fails, truncate
                    logger.error(f"Failed to send chunk {i+1}: {e}")
                    await update.message.reply_text(chunk[:MAX_MESSAGE_LENGTH])

        # Stop typing indicator after all messages sent
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

        # Log for admin
        logger.info(f"User {user_id} - Tokens: {input_tokens}+{output_tokens}, Cost: ${cost:.4f}")

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        # Stop typing on error
        stop_typing.set()
        typing_task.cancel()
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке сообщения:\n{str(e)}"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages."""
    user_id = update.effective_user.id

    # In groups, only respond if bot is mentioned
    if not is_bot_mentioned(update, context):
        return

    if not db.is_authorized(user_id):
        await update.message.reply_text("❌ У вас нет доступа к боту.")
        return

    # Update last active
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name, is_authorized=True)

    # Send typing status immediately
    await update.message.chat.send_action(ChatAction.TYPING)

    # Start continuous typing indicator
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.message.chat, stop_typing))

    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()

        # Download photo
        photo_bytes = await photo_file.download_as_bytearray()

        chat_id = update.effective_chat.id

        # Get caption or default question
        caption = update.message.caption or "Что изображено на этой картинке?"

        # Get conversation history for this specific chat
        history = db.get_conversation_history(user_id, chat_id, limit=10)
        history.append({"role": "user", "content": caption})

        # Get system prompt from database
        system_prompt = db.get_setting('system_prompt')

        # Send to Claude with image and system prompt
        response_text, input_tokens, output_tokens = claude.send_message_with_image(
            history, bytes(photo_bytes), "jpeg", system_prompt
        )

        # Convert Markdown to HTML formatting
        response_text = convert_markdown_to_html(response_text)

        # Save to database with chat_id
        db.add_message_to_history(user_id, chat_id, "user", f"[Image] {caption}")
        db.add_message_to_history(user_id, chat_id, "assistant", response_text)

        # Log usage
        cost = db.log_usage(user_id, config.CLAUDE_MODEL, input_tokens, output_tokens)

        # Send response - split if too long, try with HTML, fallback to plain text
        message_chunks = split_message(response_text)

        for i, chunk in enumerate(message_chunks):
            # Small delay between chunks to look more natural
            if i > 0:
                await asyncio.sleep(0.5)

            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
            except Exception as parse_error:
                # HTML parsing or length error, send as plain text
                logger.warning(f"Message send error for user {user_id} (image): {parse_error}")
                try:
                    await update.message.reply_text(chunk)
                except Exception as e:
                    logger.error(f"Failed to send chunk {i+1}: {e}")
                    await update.message.reply_text(chunk[:MAX_MESSAGE_LENGTH])

        # Stop typing indicator after all messages sent
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

        logger.info(f"User {user_id} - Image - Tokens: {input_tokens}+{output_tokens}, Cost: ${cost:.4f}")

    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        # Stop typing on error
        stop_typing.set()
        typing_task.cancel()
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке изображения:\n{str(e)}"
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice and audio messages via Whisper STT."""
    if not config.WHISPER_URL:
        return

    user_id = update.effective_user.id

    # In groups, only respond if bot is mentioned
    if not is_bot_mentioned(update, context):
        return

    if not db.is_authorized(user_id):
        await update.message.reply_text(
            "❌ У вас нет доступа к боту.\n"
            f"Ваш ID: <code>{user_id}</code>\n"
            "Отправьте этот ID администратору.",
            parse_mode=ParseMode.HTML
        )
        return

    # Send typing status immediately
    await update.message.chat.send_action(ChatAction.TYPING)

    # Start continuous typing indicator
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.message.chat, stop_typing))

    try:
        voice = update.message.voice or update.message.audio
        file = await context.bot.get_file(voice.file_id)
        ogg_bytes = await file.download_as_bytearray()

        # Send to Whisper for transcription
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{config.WHISPER_URL}/transcribe",
                files={"file": ("voice.ogg", bytes(ogg_bytes), "audio/ogg")},
                timeout=60,
            )
        r.raise_for_status()
        transcribed_text = r.json()["text"].strip()

        if not transcribed_text:
            stop_typing.set()
            typing_task.cancel()
            await update.message.reply_text("❌ Не удалось распознать речь.")
            return

        logger.info(f"User {user_id} - Voice transcribed: {transcribed_text[:100]}")

        # Process transcribed text through Claude as a regular message
        user_id = update.effective_user.id
        user = update.effective_user
        db.add_user(user.id, user.username, user.first_name, user.last_name, is_authorized=True)

        chat_id = update.effective_chat.id
        history = db.get_conversation_history(user_id, chat_id, limit=10)

        user_message = f"[Голосовое сообщение]: {transcribed_text}"
        history.append({"role": "user", "content": user_message})

        system_prompt = db.get_setting('system_prompt')
        response_text, input_tokens, output_tokens = claude.send_message(history, system_prompt)
        response_text = convert_markdown_to_html(response_text)

        db.add_message_to_history(user_id, chat_id, "user", user_message)
        db.add_message_to_history(user_id, chat_id, "assistant", response_text)
        cost = db.log_usage(user_id, config.CLAUDE_MODEL, input_tokens, output_tokens)

        # Send transcription note + response
        await update.message.reply_text(
            f"🎤 <i>{transcribed_text}</i>",
            parse_mode=ParseMode.HTML
        )

        message_chunks = split_message(response_text)
        for i, chunk in enumerate(message_chunks):
            if i > 0:
                await asyncio.sleep(0.5)
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
            except Exception as parse_error:
                logger.warning(f"Message send error for user {user_id} (voice): {parse_error}")
                try:
                    await update.message.reply_text(chunk)
                except Exception as e:
                    logger.error(f"Failed to send chunk {i+1}: {e}")
                    await update.message.reply_text(chunk[:MAX_MESSAGE_LENGTH])

        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

        logger.info(f"User {user_id} - Voice - Tokens: {input_tokens}+{output_tokens}, Cost: ${cost:.4f}")

    except httpx.HTTPError as e:
        logger.error(f"Whisper API error: {e}")
        stop_typing.set()
        typing_task.cancel()
        await update.message.reply_text("❌ Ошибка связи с Whisper сервером.")
    except Exception as e:
        logger.error(f"Error handling voice: {e}")
        stop_typing.set()
        typing_task.cancel()
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке голосового сообщения:\n{str(e)}"
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

    # Send typing status immediately
    await update.message.chat.send_action(ChatAction.TYPING)

    # Start continuous typing indicator
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.message.chat, stop_typing))

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

        chat_id = update.effective_chat.id

        # Get caption or default question
        caption = update.message.caption or "Проанализируй этот документ"

        # Get conversation history for this specific chat
        history = db.get_conversation_history(user_id, chat_id, limit=5)
        history.append({"role": "user", "content": caption})

        # Get system prompt from database
        system_prompt = db.get_setting('system_prompt')

        # Send to Claude with document and system prompt
        response_text, input_tokens, output_tokens = claude.send_message_with_document(
            history, doc_text, system_prompt
        )

        # Convert Markdown to HTML formatting
        response_text = convert_markdown_to_html(response_text)

        # Save to database with chat_id
        db.add_message_to_history(user_id, chat_id, "user", f"[Document: {document.file_name}] {caption}")
        db.add_message_to_history(user_id, chat_id, "assistant", response_text)

        # Log usage
        cost = db.log_usage(user_id, config.CLAUDE_MODEL, input_tokens, output_tokens)

        # Send response - split if too long, try with HTML, fallback to plain text
        message_chunks = split_message(response_text)

        for i, chunk in enumerate(message_chunks):
            # Small delay between chunks to look more natural
            if i > 0:
                await asyncio.sleep(0.5)

            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
            except Exception as parse_error:
                # HTML parsing or length error, send as plain text
                logger.warning(f"Message send error for user {user_id} (document): {parse_error}")
                try:
                    await update.message.reply_text(chunk)
                except Exception as e:
                    logger.error(f"Failed to send chunk {i+1}: {e}")
                    await update.message.reply_text(chunk[:MAX_MESSAGE_LENGTH])

        # Stop typing indicator after all messages sent
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

        logger.info(f"User {user_id} - Document - Tokens: {input_tokens}+{output_tokens}, Cost: ${cost:.4f}")

    except Exception as e:
        logger.error(f"Error handling document: {e}")
        # Stop typing on error
        stop_typing.set()
        typing_task.cancel()
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
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    # Start bot
    logger.info("Bot started successfully")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
