# Настройка GitHub для проекта

✅ Репозиторий уже создан: https://github.com/rudeduns/tb-px

## ~~Шаг 1: Создайте репозиторий на GitHub~~ (ВЫПОЛНЕНО)

✅ Репозиторий создан
✅ Название: tb-px
✅ Пользователь: rudeduns

## ~~Шаг 2: Обновите URL в файлах~~ (ВЫПОЛНЕНО)

✅ Все URL обновлены на:
- Repository: https://github.com/rudeduns/tb-px
- Raw files: https://raw.githubusercontent.com/rudeduns/tb-px/main/

## Шаг 3: Загрузите файлы на GitHub

```bash
cd telegram-bot

# Инициализировать git репозиторий
git init

# Добавить все файлы
git add .

# Создать первый коммит
git commit -m "Initial commit: Telegram bot with Claude AI"

# Переименовать ветку в main
git branch -M main

# Добавить удаленный репозиторий
git remote add origin https://github.com/rudeduns/tb-px.git

# Загрузить на GitHub
git push -u origin main
```

## Шаг 4: Проверьте работу

После загрузки проверьте, что файлы доступны по raw URL:

```bash
curl -I https://raw.githubusercontent.com/rudeduns/tb-px/main/proxmox-deploy.sh
```

Должен вернуться HTTP 200 OK.

## Шаг 5: Готово!

Теперь можно использовать одну команду для установки:

```bash
curl -sSL https://raw.githubusercontent.com/rudeduns/tb-px/main/proxmox-deploy.sh | bash
```

## Альтернатива: Использование без GitHub

Если вы не хотите публиковать код на GitHub, можно:

1. Скопировать все файлы на Proxmox хост
2. Запустить `install.sh` вручную
3. Настроить `.env` файл
4. Запустить бота

Или модифицировать `proxmox-deploy.sh`, убрав секцию загрузки с GitHub и используя локальные файлы.

## Примечание о безопасности

Если репозиторий будет публичным:
- ✅ Никогда не коммитьте `.env` файл (уже в .gitignore)
- ✅ Не храните API ключи в коде
- ✅ Не коммитьте `bot_data.db`
- ✅ Используйте GitHub Secrets для CI/CD если нужно

Файл `.gitignore` уже настроен правильно и исключает все чувствительные данные.
