# Paraphrase Engine - Render Deployment Guide

## Настройка на Render

### 1. Создание нового Web Service

1. Перейдите на [Render Dashboard](https://dashboard.render.com)
2. Нажмите "New +" → "Web Service"
3. Выберите репозиторий: `kachowska/paraphrase_engine`
4. Заполните настройки:
   - **Name**: `paraphrase-engine`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Starter ($9/month) или выше

### 2. Обязательные переменные окружения

В разделе "Environment Variables" добавьте:

#### Основные (ОБЯЗАТЕЛЬНЫЕ):
- `TELEGRAM_BOT_TOKEN` - токен вашего Telegram бота (получить у @BotFather)
- `SECRET_KEY` - случайная строка для безопасности (сгенерируйте длинную случайную строку)

#### AI провайдеры (минимум один ОБЯЗАТЕЛЕН):
- `OPENAI_API_KEY` - ключ OpenAI API
- `ANTHROPIC_API_KEY` - ключ Anthropic Claude API  
- `GOOGLE_API_KEY` - ключ Google Gemini API

#### Дополнительные настройки:
- `APP_ENV` = `production`
- `LOG_LEVEL` = `INFO`
- `MAX_FILE_SIZE_MB` = `10`
- `FILE_RETENTION_HOURS` = `24`
- `PORT` = `8000` (Render автоматически установит)

### 3. Google Sheets интеграция (опционально)

Если нужна интеграция с Google Sheets:

1. Создайте Service Account в Google Cloud Console
2. Скачайте JSON credentials
3. Добавьте переменные:
   - `GOOGLE_SHEETS_CREDENTIALS` - содержимое JSON файла credentials
   - `GOOGLE_SHEETS_SPREADSHEET_ID` - ID вашей таблицы

### 4. Redis для кеширования (опционально)

Для улучшения производительности можно подключить Redis:

1. Создайте Redis instance на Render
2. Добавьте переменную:
   - `REDIS_URL` - URL вашего Redis instance

### 5. База данных (опционально)

По умолчанию используется SQLite. Для production рекомендуется PostgreSQL:

1. Создайте PostgreSQL database на Render
2. Добавьте переменную:
   - `DATABASE_URL` - URL вашей базы данных

## Локальная разработка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/kachowska/paraphrase_engine.git
cd paraphrase_engine
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `.env.example`:
```bash
cp env.example .env
# Отредактируйте .env и добавьте ваши ключи
```

5. Запустите бота:
```bash
python main.py
```

## Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/process` - Обработать документ
- `/status` - Проверить статус обработки
- `/cancel` - Отменить текущую операцию

## Поддерживаемые форматы документов

- `.docx` - Microsoft Word документы
- `.txt` - Текстовые файлы
- `.pdf` - PDF документы (в разработке)

## Мониторинг и логи

- Логи доступны в Render Dashboard → Logs
- Метрики производительности в разделе Metrics
- Для детального мониторинга установите `LOG_LEVEL=DEBUG`

## Устранение неполадок

### Бот не отвечает
1. Проверьте правильность `TELEGRAM_BOT_TOKEN`
2. Убедитесь, что бот запущен (зеленый статус в Render)
3. Проверьте логи на наличие ошибок

### Ошибки AI провайдеров
1. Проверьте правильность API ключей
2. Убедитесь, что у вас есть кредиты/баланс
3. Проверьте лимиты rate limiting

### Проблемы с файлами
1. Проверьте размер файла (макс 10MB по умолчанию)
2. Убедитесь, что формат поддерживается
3. Проверьте права доступа к temp директории

## Поддержка

При возникновении проблем:
1. Проверьте логи в Render Dashboard
2. Создайте issue в GitHub репозитории
3. Свяжитесь с разработчиком
