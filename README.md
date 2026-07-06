# 🧠 Quiz Bot

Telegram-бот с Mini App викториной на 12 вопросов по разным темам: наука, история, география, технологии.

## 📂 Структура

```
quiz-bot/
├── bot.py                 # Основной файл бота (aiogram 3.x)
├── requirements.txt       # Зависимости
├── .env.example           # Пример переменных окружения
├── webapp/
│   ├── index.html         # Mini App фронтенд
│   ├── style.css          # Стили (тёмная тема Telegram)
│   └── app.js             # Логика викторины
└── .github/workflows/
    └── deploy.yml         # GitHub Actions → GitHub Pages
```

## 🚀 Запуск бота

1. **Клонируй репозиторий:**
   ```bash
   git clone https://github.com/viqex/quiz-bot.git
   cd quiz-bot
   ```

2. **Создай и настрой `.env`:**
   ```bash
   cp .env.example .env
   ```
   Отредактируй `.env`, укажи:
   - `BOT_TOKEN` — токен бота от [@BotFather](https://t.me/BotFather)
   - `WEBAPP_URL` — URL задеплоенного Mini App

3. **Установи зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Запусти бота:**
   ```bash
   python bot.py
   ```

## 🌐 Развёртывание Mini App

### GitHub Pages (автоматически)

При пуше в ветку `main` GitHub Actions автоматически деплоит `webapp/` на GitHub Pages.
URL будет доступен в Settings → Pages репозитория.

### Вручную

Можно разместить файлы из папки `webapp/` на любом хостинге:
- GitHub Pages
- Surge.sh (`surge ./webapp`)
- Vercel / Netlify
- Cloudflare Pages

> ⚠️ После деплоя обязательно обнови `WEBAPP_URL` в `.env` бота!

## 🎮 Как использовать

1. Запусти бота командой `/start`
2. Нажми кнопку «Запустить викторину»
3. Ответь на 12 вопросов
4. Получи результат в боте
5. Поделись результатом с друзьями!

## 🤖 Команды

- `/start` — приветствие и кнопка запуска викторины
- `/quiz` — открыть Mini App викторины

## 🛠 Технологии

- **Python 3.10+** / **aiogram 3.x**
- **HTML / CSS / JS** (Telegram Mini App)
- **GitHub Actions** (CI/CD)
