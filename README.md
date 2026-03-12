# Telegram Bot с Claude AI

Telegram бот с интеграцией Claude AI, поддерживающий текстовые сообщения, изображения и файлы. Включает систему управления пользователями и отслеживание стоимости токенов.

## Возможности

- 💬 **Общение с Claude AI** - поддержка контекста диалога
- 🖼️ **Анализ изображений** - отправка картинок для анализа
- 📄 **Обработка файлов** - анализ текстовых документов
- 🎤 **Голосовые сообщения** - распознавание речи через Whisper (опционально)
- 🤖 **Смена модели на лету** - админ выбирает модель Claude из актуального списка без перезапуска
- 👥 **Управление пользователями** - админ-панель для контроля доступа
- 💰 **Подсчет стоимости** - отслеживание расхода токенов и стоимости
- 🗄️ **История разговоров** - изолированный контекст для каждого чата
- ⏱️ **Автоматическая очистка** - контекст забывается через 10 минут
- 🔒 **Приватность контекста** - в каждой группе свой отдельный контекст
- 📊 **Статистика использования** - для админа и пользователей

## Быстрый старт

### Метод 1: Автоматическая установка на Proxmox (РЕКОМЕНДУЕТСЯ) 🚀

Подключитесь к Proxmox хосту по SSH и выполните:

```bash
curl -sSL https://raw.githubusercontent.com/rudeduns/tb-px/main/proxmox-deploy.sh -o proxmox-deploy.sh
chmod +x proxmox-deploy.sh
./proxmox-deploy.sh
```

Скрипт интерактивно спросит все необходимые параметры:
- Настройки контейнера (ID, CPU, RAM, диск)
- Telegram Bot Token (от @BotFather)
- Claude API Key (от console.anthropic.com)
- Admin Telegram User ID (от @userinfobot)

После этого бот будет полностью установлен, настроен и запущен!

📖 Подробная инструкция: [QUICKSTART.md](QUICKSTART.md)

### Метод 2: Ручная установка на Linux

```bash
# Клонируйте репозиторий
git clone <repo-url> telegram-bot
cd telegram-bot

# Запустите скрипт установки
chmod +x install.sh
sudo ./install.sh

# Настройте бота
sudo nano /opt/telegram-bot/.env

# Запустите бота
sudo systemctl start telegram-bot
```

### Метод 3: Локальная разработка

```bash
# Установите зависимости
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
pip install -r requirements.txt

# Создайте конфигурацию
cp .env.example .env
nano .env  # Добавьте свои ключи

# Запустите бота
python bot.py
```

## Настройка

Отредактируйте файл `.env` и укажите:

```env
# Telegram Bot Token от @BotFather
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Claude API Key от https://console.anthropic.com/
CLAUDE_API_KEY=your_claude_api_key_here

# Admin Telegram User ID (узнать можно у @userinfobot)
ADMIN_USER_ID=your_telegram_user_id_here

# Модель Claude (по умолчанию claude-3-5-sonnet-20241022)
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Максимум токенов на ответ
MAX_TOKENS=4096
```

### Получение учетных данных

1. **Telegram Bot Token**:
   - Напишите [@BotFather](https://t.me/BotFather) в Telegram
   - Отправьте `/newbot`
   - Следуйте инструкциям
   - Скопируйте полученный токен

2. **Claude API Key**:
   - Зарегистрируйтесь на [console.anthropic.com](https://console.anthropic.com/)
   - Перейдите в раздел API Keys
   - Создайте новый ключ
   - Пополните баланс

3. **Admin User ID**:
   - Напишите [@userinfobot](https://t.me/userinfobot) в Telegram
   - Скопируйте ваш ID

## Использование

### Работа в личных сообщениях

Просто напишите боту в личные сообщения - он будет отвечать на все ваши сообщения.

### Работа в группах и каналах

Бот можно добавить в группы. В группах бот отвечает **только когда его упоминают**:

- **Через @упоминание**: `@your_bot_username привет`
- **Через Reply**: Ответьте на сообщение бота

Если писать без упоминания - бот молчит.

**Изоляция контекста:**
- Каждый чат (личка, группа, канал) имеет свой отдельный контекст
- Бот не путает разговоры из разных групп
- Контекст автоматически забывается через 10 минут неактивности
- Команда `/clear` очищает контекст только в текущем чате

#### Настройка бота для групп:

1. Напишите [@BotFather](https://t.me/BotFather)
2. Отправьте `/mybots` → выберите своего бота
3. `Bot Settings` → `Group Privacy` → **Disable** (Turn off Privacy Mode)
4. Теперь можно добавить бота в группу как администратора или участника

### Команды для пользователей

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/clear` - Очистить историю разговора
- `/stats` - Показать статистику использования

### Команды для администратора

- `/admin` - Панель администратора
- `/model` - Сменить модель Claude (список тянется live из Anthropic API)
- `/authorize <user_id>` - Добавить пользователя
- `/deauthorize <user_id>` - Удалить пользователя
- `/users` - Список всех пользователей
- `/totalstats` - Общая статистика использования
- `/setprompt <текст>` - Установить системный промпт для всех диалогов
- `/showprompt` - Показать текущий системный промпт

### Настройка системного промпта

Системный промпт применяется ко **всем диалогам бота** и позволяет задать поведение Claude AI:

```
/setprompt Ты - опытный программист. Отвечай кратко и с примерами кода.
```

Примеры использования:
- Установить роль: `/setprompt Ты - дружелюбный помощник, который всегда отвечает на русском языке`
- Задать стиль: `/setprompt Отвечай максимально кратко, без лишних пояснений`
- Удалить промпт: `/setprompt clear`
- Посмотреть текущий: `/showprompt`

### Отправка контента

- **Текст**: Просто напишите сообщение
- **Изображение**: Отправьте картинку с вопросом в подписи
- **Файл**: Отправьте текстовый файл (до 1 МБ)

## Управление сервисом

```bash
# Запуск
sudo systemctl start telegram-bot

# Остановка
sudo systemctl stop telegram-bot

# Перезапуск
sudo systemctl restart telegram-bot

# Статус
sudo systemctl status telegram-bot

# Просмотр логов
sudo journalctl -u telegram-bot -f

# Просмотр последних ошибок
sudo journalctl -u telegram-bot -n 50 --no-pager
```

## Обновление бота

С хоста Proxmox одной командой (скачивает все файлы, обновляет зависимости, рестартует):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/rudeduns/tb-px/main/update.sh) ВАШ_CT_ID
```

Или без ID — скрипт спросит интерактивно:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/rudeduns/tb-px/main/update.sh)
```

## Структура проекта

```
telegram-bot/
├── bot.py                 # Основной файл бота
├── admin.py               # Команды администратора
├── config.py              # Конфигурация
├── database.py            # Работа с БД
├── claude_client.py       # Клиент Claude API
├── requirements.txt       # Зависимости Python
├── .env.example           # Пример конфигурации
├── install.sh             # Скрипт установки
├── proxmox-deploy.sh      # Автоматическая установка на Proxmox
├── update.sh              # Обновление бота в контейнере одной командой
├── set_admin.sh           # Скрипт установки прав администратора
├── README.md              # Документация
├── QUICKSTART.md          # Быстрый старт
└── CLAUDE.md              # Техническая документация
```

## База данных

Используется SQLite с тремя таблицами:

- **users** - информация о пользователях и права доступа
- **usage_stats** - статистика использования токенов
- **conversations** - история разговоров

База создается автоматически при первом запуске.

## Стоимость

Текущие цены Claude (за 1 млн токенов):

| Модель | Ввод | Вывод |
|--------|------|-------|
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude 3 Opus | $15.00 | $75.00 |
| Claude 3 Haiku | $0.25 | $1.25 |

Бот автоматически отслеживает расход токенов и считает стоимость.

## Решение проблем

### Бот не запускается

```bash
# Проверьте логи
sudo journalctl -u telegram-bot -n 100

# Проверьте конфигурацию
sudo nano /opt/telegram-bot/.env

# Проверьте права доступа
sudo chown -R telegram-bot:telegram-bot /opt/telegram-bot
```

### Ошибки API

- Проверьте валидность TELEGRAM_BOT_TOKEN
- Проверьте баланс Claude API
- Проверьте лимиты API

### Ошибки форматирования сообщений

Бот использует HTML форматирование Telegram вместо Markdown для лучшей стабильности. Если видите ошибки — обновите бота до последней версии (см. раздел "Обновление бота").

### База данных

```bash
# Пересоздать базу
sudo rm /opt/telegram-bot/bot_data.db
sudo systemctl restart telegram-bot
```

### Добавление администратора

Чтобы назначить пользователя администратором:

```bash
# На Proxmox хосте
pct exec CONTAINER_ID -- curl -sSL https://raw.githubusercontent.com/rudeduns/tb-px/main/set_admin.sh -o /tmp/set_admin.sh
pct exec CONTAINER_ID -- bash /tmp/set_admin.sh ВАШ_TELEGRAM_ID

# Или внутри контейнера
curl -sSL https://raw.githubusercontent.com/rudeduns/tb-px/main/set_admin.sh -o /tmp/set_admin.sh
bash /tmp/set_admin.sh ВАШ_TELEGRAM_ID
```

Скрипт обновит .env и базу данных с правами администратора.

## Требования

- Python 3.8+
- Debian/Ubuntu Linux (для автоматической установки)
- Proxmox 7.0+ (опционально, для LXC)

## Безопасность

- Бот хранит API ключи в `.env` файле (не в git)
- Используется система авторизации пользователей
- Админ-аккаунт настраивается при установке
- Логи не содержат чувствительных данных

## Лицензия

MIT

## Поддержка

При возникновении проблем:

1. Проверьте логи: `journalctl -u telegram-bot -f`
2. Убедитесь в правильности конфигурации `.env`
3. Проверьте баланс Claude API
4. Создайте issue в репозитории
