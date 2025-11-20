# Быстрый деплой Paraphrase Engine на Render

## Шаг 1: Создайте новый Web Service на Render

1. Перейдите на https://dashboard.render.com/web/new
2. Подключите репозиторий: `https://github.com/kachowska/paraphrase_engine`
3. Нажмите "Connect"

## Шаг 2: Настройки сервиса

**Name:** `paraphrase-engine`
**Environment:** `Python`
**Build Command:** `pip install -r requirements.txt`
**Start Command:** `python main.py`

## Шаг 3: Переменные окружения (Environment Variables)

Добавьте следующие переменные:

### ОБЯЗАТЕЛЬНЫЕ:
```
TELEGRAM_BOT_TOKEN = 7648679762:AAHz_mnzP-ImJki6q-1-4QanpyqeMmiKHCE
SECRET_KEY = generate-random-32-char-string-here-xyz123
APP_ENV = production
LOG_LEVEL = INFO
```

### AI Провайдеры (минимум один):
Выберите и добавьте хотя бы один:

**Для OpenAI:**
```
OPENAI_API_KEY = sk-...ваш_ключ_openai
```

**Для Anthropic Claude:**
```
ANTHROPIC_API_KEY = sk-ant-...ваш_ключ_anthropic
```

**Для Google Gemini:**
```
GOOGLE_API_KEY = AIza...ваш_ключ_google
```

### Дополнительные настройки:
```
MAX_FILE_SIZE_MB = 10
FILE_RETENTION_HOURS = 24
AI_TEMPERATURE = 0.7
AI_MAX_TOKENS = 2000
```

## Шаг 4: Выберите план

- **Free** - для тестирования (спит после 15 минут неактивности)
- **Starter ($9/month)** - рекомендуется для production

## Шаг 5: Deploy

Нажмите "Create Web Service" и дождитесь деплоя.

## Проверка работы

После успешного деплоя:

1. Откройте Telegram
2. Найдите бота @ParaphraseKN_Bot
3. Отправьте `/start`
4. Бот должен ответить

## Важные заметки

⚠️ **Безопасность токена**: Токен бота уже указан в этом файле. После настройки удалите его из публичных файлов!

⚠️ **SECRET_KEY**: Обязательно сгенерируйте уникальный SECRET_KEY. Можно использовать:
```python
import secrets
print(secrets.token_urlsafe(32))
```

⚠️ **AI Ключи**: Без хотя бы одного AI провайдера бот не запустится!

## Мониторинг

- Логи: Render Dashboard → Logs
- Метрики: Render Dashboard → Metrics
- Ошибки будут видны в логах

## Устранение проблем

### Бот не запускается:
1. Проверьте логи на наличие ошибок
2. Убедитесь, что все обязательные переменные установлены
3. Проверьте, что хотя бы один AI провайдер настроен

### Бот не отвечает:
1. Проверьте правильность TELEGRAM_BOT_TOKEN
2. Убедитесь, что сервис запущен (зеленый статус)
3. Проверьте логи на наличие ошибок подключения
