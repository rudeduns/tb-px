# Быстрый старт для Proxmox

## Одна команда для полной установки

Подключитесь к вашему Proxmox серверу по SSH и выполните:

```bash
curl -sSL https://raw.githubusercontent.com/rudeduns/tb-px/main/proxmox-deploy.sh | bash
```

Или с wget:

```bash
wget -qO- https://raw.githubusercontent.com/rudeduns/tb-px/main/proxmox-deploy.sh | bash
```

## Что произойдет?

Скрипт спросит у вас:

### 1. Параметры контейнера:
- **Container ID** (по умолчанию: 200)
- **Hostname** (по умолчанию: telegram-bot)
- **Root Password** (по умолчанию: telegram123)
- **CPU Cores** (по умолчанию: 2)
- **RAM** (по умолчанию: 2048 MB)
- **Disk Size** (по умолчанию: 8 GB)
- **Storage** (по умолчанию: local-lvm)

### 2. Настройки бота:
- **Telegram Bot Token** - получите у [@BotFather](https://t.me/BotFather)
- **Claude API Key** - с [console.anthropic.com](https://console.anthropic.com/)
- **Admin Telegram User ID** - узнайте у [@userinfobot](https://t.me/userinfobot)
- **Claude Model** (по умолчанию: claude-3-5-sonnet-20241022)

### 3. Автоматически выполнится:
- ✅ Создание LXC контейнера Debian 12
- ✅ Установка Python 3 и зависимостей
- ✅ Загрузка кода бота
- ✅ Создание виртуального окружения Python
- ✅ Установка Python пакетов
- ✅ Настройка .env файла с вашими данными
- ✅ Создание systemd сервиса
- ✅ Запуск бота

## После установки

Бот сразу начнет работать! Откройте Telegram и напишите `/start` вашему боту.

### Полезные команды:

```bash
# Войти в контейнер
pct enter 200

# Посмотреть логи бота
pct exec 200 -- journalctl -u telegram-bot -f

# Перезапустить бота
pct exec 200 -- systemctl restart telegram-bot

# Остановить бота
pct exec 200 -- systemctl stop telegram-bot

# Проверить статус
pct exec 200 -- systemctl status telegram-bot
```

### Изменить настройки:

```bash
# Войти в контейнер
pct enter 200

# Отредактировать конфигурацию
nano /opt/telegram-bot/.env

# Перезапустить бота
systemctl restart telegram-bot
```

## Получение учетных данных

### Telegram Bot Token:

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям (имя бота, username)
4. Скопируйте полученный токен (выглядит как `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Claude API Key:

1. Зарегистрируйтесь на [console.anthropic.com](https://console.anthropic.com/)
2. Перейдите в "API Keys"
3. Нажмите "Create Key"
4. Скопируйте ключ (начинается с `sk-ant-`)
5. **Важно**: Пополните баланс в разделе "Billing"

### Admin Telegram User ID:

1. Откройте [@userinfobot](https://t.me/userinfobot) в Telegram
2. Нажмите "Start"
3. Бот пришлет вам ваш ID (например, `123456789`)

## Решение проблем

### Бот не отвечает в Telegram:

```bash
# Проверьте статус
pct exec 200 -- systemctl status telegram-bot

# Посмотрите ошибки в логах
pct exec 200 -- journalctl -u telegram-bot -n 50
```

Частые ошибки:
- Неверный Telegram Bot Token
- Недостаточно средств на Claude API
- Проблемы с сетью в контейнере

### Проверить конфигурацию:

```bash
pct exec 200 -- cat /opt/telegram-bot/.env
```

### Пересоздать контейнер:

Если что-то пошло не так, можно удалить контейнер и запустить скрипт заново:

```bash
pct stop 200
pct destroy 200
# Запустите скрипт установки снова
```

## Обновление бота

```bash
# Войдите в контейнер
pct enter 200

# Перейдите в директорию бота
cd /opt/telegram-bot

# Сохраните .env файл
cp .env .env.backup

# Обновите код (если используете git)
git pull

# Или скачайте файлы вручную
# curl -O https://raw.githubusercontent.com/YOUR_USERNAME/telegram-bot/main/bot.py
# И так далее для других файлов

# Обновите зависимости
venv/bin/pip install -r requirements.txt --upgrade

# Перезапустите бота
systemctl restart telegram-bot
```

## Безопасность

- **Смените пароль root** после установки: `pct exec 200 -- passwd`
- **Не делитесь** .env файлом - там ваши секретные ключи
- **Регулярно обновляйте** систему: `pct exec 200 -- apt-get update && apt-get upgrade -y`
- **Делайте бэкапы** контейнера через Proxmox UI

## Мониторинг расходов

В Telegram напишите боту `/totalstats` (если вы админ) чтобы увидеть расход токенов и стоимость.

Регулярно проверяйте баланс на [console.anthropic.com](https://console.anthropic.com/)
