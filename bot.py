"""
Quiz Bot — Telegram Mini App викторина
aiogram 3.x
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in .env or environment")
if not WEBAPP_URL:
    raise ValueError("WEBAPP_URL not set in .env or environment")


@dataclass
class QuizResult:
    score: int
    total: int
    percent: float


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


def _parse_quiz_data(data: str) -> QuizResult | None:
    """Parse JSON quiz result from Mini App."""
    try:
        payload = json.loads(data)
        return QuizResult(
            score=int(payload.get("score", 0)),
            total=int(payload.get("total", 0)),
            percent=float(payload.get("percent", 0)),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


# ── Commands ──────────────────────────────────────────────────────────────


@dp.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Welcome message with a button to launch the quiz."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 Запустить викторину",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )

    await message.answer(
        "🌟 <b>Добро пожаловать в Quiz Bot!</b>\n\n"
        "Проверь свои знания в викторине на разные темы:\n"
        "🧪 Наука  ·  📜 История  ·  🌍 География  ·  💻 Технологии\n\n"
        "Нажми кнопку ниже, чтобы начать!",
        reply_markup=keyboard,
    )


@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message) -> None:
    """Open the quiz Mini App directly."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 Открыть викторину",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )
    await message.answer("👇 Нажми, чтобы начать викторину!", reply_markup=keyboard)


# ── Web App Data handler ──────────────────────────────────────────────────


@dp.message(lambda msg: msg.web_app_data is not None)
async def handle_webapp_data(message: types.Message) -> None:
    """Receive quiz results from the Mini App."""
    result = _parse_quiz_data(message.web_app_data.data)
    if result is None:
        await message.answer("❌ Не удалось обработать результат. Попробуй ещё раз.")
        return

    emoji = "🏆" if result.percent >= 80 else "👍" if result.percent >= 50 else "💪"

    text = (
        f"{emoji} <b>Твой результат!</b>\n\n"
        f"✅ Правильных ответов: <b>{result.score}/{result.total}</b>\n"
        f"📊 Процент: <b>{result.percent:.1f}%</b>\n\n"
    )

    if result.percent == 100:
        text += "🌟 Идеально! Ты настоящий эрудит!"
    elif result.percent >= 80:
        text += "🎉 Отлично! Ты много знаешь!"
    elif result.percent >= 60:
        text += "😊 Хороший результат! Есть куда расти."
    elif result.percent >= 40:
        text += "📚 Неплохо! Попробуй ещё раз, чтобы улучшить."
    else:
        text += "🤔 Стоит подтянуть знания. Попробуй снова!"

    await message.answer(text)


# ── Main ──────────────────────────────────────────────────────────────────


async def main() -> None:
    logger.info("Starting quiz bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
