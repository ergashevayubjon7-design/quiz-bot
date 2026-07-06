"""
Quiz Bot — Telegram Mini App викторина
Платежи (Telegram Stars) · CAPTCHA · Призовой фонд · Призовая игра
aiogram 3.x + SQLite
"""

import asyncio
import json
import logging
import os
import random
import sqlite3
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, BaseFilter
from aiogram.types import (
    LabeledPrice,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    CallbackQuery,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
STAR_PRICE = int(os.getenv("STAR_PRICE", "50"))  # Stars за 1 попытку
RUB_PER_STAR = float(os.getenv("RUB_PER_STAR", "1.0"))  # 1 Star ≈ 1₽
DB_PATH = os.getenv("DB_PATH", "quiz_bot.db")
PRIZE_THRESHOLD = 1600.0  # ₽ — запуск призовой игры
PRIZE_1ST = 1000.0
PRIZE_2ND = 500.0
PRIZE_3RD = 100.0

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in .env or environment")
if not WEBAPP_URL:
    raise ValueError("WEBAPP_URL not set in .env or environment")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ── Database ──────────────────────────────────────────────────


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                attempts INTEGER DEFAULT 0,
                total_paid_stars INTEGER DEFAULT 0,
                total_paid_rub REAL DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                captcha_solved INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stars_amount INTEGER DEFAULT 0,
                rub_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'completed',
                payload TEXT,
                telegram_charge_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                score INTEGER DEFAULT 0,
                total INTEGER DEFAULT 12,
                quiz_type TEXT DEFAULT 'regular',
                prize_position INTEGER,
                prize_amount REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS prize_fund (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_rub REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS captcha_sessions (
                user_id INTEGER PRIMARY KEY,
                answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Гарантируем строку призового фонда
        row = conn.execute("SELECT COUNT(*) FROM prize_fund").fetchone()
        if row[0] == 0:
            conn.execute("INSERT INTO prize_fund (amount_rub) VALUES (0)")

        # Миграция: добавляем столбцы, если таблица users уже есть (без captcha_solved)
        try:
            conn.execute("ALTER TABLE users ADD COLUMN captcha_solved INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # колонка уже есть

    logger.info("Database initialized: %s", DB_PATH)


# ── Filters ───────────────────────────────────────────────────


class CaptchaSolved(BaseFilter):
    """Проверяет, прошёл ли пользователь капчу."""

    async def __call__(self, message: types.Message) -> bool:
        with get_db() as conn:
            row = conn.execute(
                "SELECT captcha_solved FROM users WHERE user_id = ?",
                (message.from_user.id,),
            ).fetchone()
        return row is not None and row["captcha_solved"] == 1


class CaptchaNotSolved(BaseFilter):
    """Проверяет, НЕ прошёл ли пользователь капчу."""

    async def __call__(self, message: types.Message) -> bool:
        with get_db() as conn:
            row = conn.execute(
                "SELECT captcha_solved FROM users WHERE user_id = ?",
                (message.from_user.id,),
            ).fetchone()
        return row is None or row["captcha_solved"] == 0


# ── Helpers ───────────────────────────────────────────────────


def register_or_update_user(message: types.Message) -> None:
    """Обновить/создать пользователя в БД."""
    u = message.from_user
    with get_db() as conn:
        conn.execute(
            """INSERT INTO users (user_id, username, first_name, last_active)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id) DO UPDATE SET
                   username = excluded.username,
                   first_name = excluded.first_name,
                   last_active = CURRENT_TIMESTAMP""",
            (u.id, u.username, u.first_name),
        )


def get_user(user_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def generate_captcha() -> tuple[str, str]:
    """Генерирует капчу (текст вопроса, правильный ответ)."""
    a = random.randint(3, 12)
    b = random.randint(1, 10)
    op = random.choice(["+", "−"])
    if op == "−" and a < b:
        a, b = b, a
    if op == "+":
        answer = str(a + b)
    else:
        answer = str(a - b)
    question = f"🧮 Реши пример: {a} {op} {b} = ?"
    return question, answer


def get_prize_fund() -> float:
    with get_db() as conn:
        row = conn.execute("SELECT amount_rub FROM prize_fund ORDER BY id DESC LIMIT 1").fetchone()
    return float(row["amount_rub"]) if row else 0.0


def add_to_prize_fund(amount_rub: float) -> None:
    """Добавляет 90% платежа в призовой фонд, 10% остаётся (не вычитается)."""
    with get_db() as conn:
        conn.execute(
            "UPDATE prize_fund SET amount_rub = amount_rub + ?, updated_at = CURRENT_TIMESTAMP",
            (amount_rub,),
        )


def get_prize_leaderboard() -> list[dict]:
    """Топ-3 призовой игры за всё время."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT user_id, score, total, created_at
               FROM quiz_attempts
               WHERE quiz_type = 'prize'
               ORDER BY score DESC, id ASC
               LIMIT 3"""
        ).fetchall()
    return [dict(r) for r in rows]


# ── CAPTCHA ───────────────────────────────────────────────────


async def send_captcha(message: types.Message) -> None:
    """Показать капчу пользователю."""
    question, answer = generate_captcha()
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO captcha_sessions (user_id, answer, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (message.from_user.id, answer),
        )
    await message.answer(
        f"🤖 <b>Проверка — ты человек?</b>\n\n{question}\n\n"
        f"<i>Напиши ответ цифрой.</i>"
    )


async def check_captcha(message: types.Message) -> bool:
    """Проверить ответ капчи. True если правильно."""
    user_id = message.from_user.id

    with get_db() as conn:
        row = conn.execute(
            "SELECT answer FROM captcha_sessions WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        await send_captcha(message)
        return False

    expected = row["answer"].strip()
    actual = message.text.strip()

    if actual == expected:
        with get_db() as conn:
            conn.execute(
                "DELETE FROM captcha_sessions WHERE user_id = ?", (user_id,)
            )
            conn.execute(
                "UPDATE users SET captcha_solved = 1 WHERE user_id = ?", (user_id,)
            )
        await message.answer("✅ <b>Проверка пройдена!</b> Добро пожаловать! 👋")
        return True
    else:
        await message.answer("❌ <b>Неправильный ответ.</b> Попробуй ещё раз.")
        # генерируем новую капчу
        await send_captcha(message)
        return False


# ── Prize game helpers ────────────────────────────────────────


def is_prize_game_available() -> bool:
    """Призовая игра доступна, если фонд >= PRIZE_THRESHOLD."""
    return get_prize_fund() >= PRIZE_THRESHOLD


async def award_prizes_if_due() -> None:
    """Автоматически выплачивает призы топ-3, если фонд позволяет."""
    fund = get_prize_fund()
    if fund < PRIZE_THRESHOLD:
        return

    leaderboard = get_prize_leaderboard()
    if not leaderboard or len(leaderboard) < 3:
        # Недостаточно участников — ждём
        return

    # Проверяем, не выплачены ли уже призы из этой "серии"
    with get_db() as conn:
        already_paid = conn.execute(
            "SELECT COUNT(*) FROM quiz_attempts WHERE quiz_type = 'prize' AND prize_amount > 0"
        ).fetchone()[0]
    if already_paid >= 3:
        return

    prizes = [
        (0, PRIZE_1ST),
        (1, PRIZE_2ND),
        (2, PRIZE_3RD),
    ]

    total_prize = PRIZE_1ST + PRIZE_2ND + PRIZE_3RD  # 1600₽
    stars_paid_total = 0

    for position, amount_rub in prizes:
        if position >= len(leaderboard):
            break

        entry = leaderboard[position]
        user_id = entry["user_id"]
        stars_amount = int(amount_rub / RUB_PER_STAR)

        if stars_amount < 1:
            continue

        try:
            await bot.send_stars(
                chat_id=user_id,
                amount=stars_amount,
                label=f"🏆 Приз #{position+1} — Quiz Bot",
            )

            with get_db() as conn:
                conn.execute(
                    "UPDATE quiz_attempts SET prize_position = ?, prize_amount = ? WHERE user_id = ? AND quiz_type = 'prize' AND prize_amount IS NULL",
                    (position + 1, amount_rub, user_id),
                )

            stars_paid_total += stars_amount

            # Отправляем уведомление
            try:
                await bot.send_message(
                    user_id,
                    f"🏆 <b>Поздравляем! Ты занял {position+1} место в призовой игре!</b>\n\n"
                    f"💰 Выплачено: <b>{stars_amount} ⭐</b> (~{amount_rub:.0f}₽)\n\n"
                    f"Спасибо за участие! 🎉",
                )
            except Exception:
                pass

        except Exception as e:
            logger.error("Failed to pay %s to user %d: %s", amount_rub, user_id, e)

    # Списываем призовой фонд
    with get_db() as conn:
        conn.execute(
            "UPDATE prize_fund SET amount_rub = MAX(0, amount_rub - ?), updated_at = CURRENT_TIMESTAMP",
            (total_prize,),
        )

    # Рассылаем всем участникам о завершении сезона
    with get_db() as conn:
        participants = conn.execute(
            "SELECT DISTINCT user_id FROM quiz_attempts WHERE quiz_type = 'prize'"
        ).fetchall()

    notification = (
        f"🎊 <b>Призовая игра завершена!</b>\n\n"
        f"🏆 1 место: {PRIZE_1ST:.0f}₽\n"
        f"🥈 2 место: {PRIZE_2ND:.0f}₽\n"
        f"🥉 3 место: {PRIZE_3RD:.0f}₽\n\n"
        f"Призовой фонд обнулён. Копите снова! 💪"
    )

    for p in participants:
        try:
            await bot.send_message(p["user_id"], notification)
        except Exception:
            pass

    # Отправляем админу отчёт
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"📊 <b>Призовая игра завершена</b>\n\n"
            f"Выплачено {stars_paid_total} ⭐ на {len(prizes)} призовых мест.\n"
            f"Призовой фонд обнулён.",
        )


# ── Handlers — CAPTCHA gate ───────────────────────────────────


@dp.message(CaptchaNotSolved(), F.text)
async def captcha_gate(message: types.Message) -> None:
    """Ловит все сообщения от пользователей, не прошедших капчу."""
    register_or_update_user(message)

    # Проверяем, не ответ ли это на капчу
    if await check_captcha(message):
        # Капча пройдена — показываем главное меню
        await show_main_menu(message)
    # Иначе капча уже отправила ошибку


@dp.message(CaptchaNotSolved())
async def captcha_gate_non_text(message: types.Message) -> None:
    """Ловит не-текстовые сообщения (стикеры, фото и т.д.) от непроверенных."""
    register_or_update_user(message)
    await send_captcha(message)


# ── Handlers — Main Menu ──────────────────────────────────────


async def show_main_menu(message: types.Message) -> None:
    """Главное меню после капчи."""
    user = get_user(message.from_user.id)
    attempts = user["attempts"] if user else 0

    prize_available = is_prize_game_available()
    fund = get_prize_fund()

    buttons = [
        [
            InlineKeyboardButton(
                text="🎮 Играть (викторина)",
                callback_data="play_quiz",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"💰 Купить попытку ({STAR_PRICE} ⭐)",
                callback_data="buy_attempt",
            )
        ],
    ]

    if prize_available:
        buttons.append([
            InlineKeyboardButton(
                text="🏆 Призовая игра!",
                callback_data="play_prize",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="📊 Мой профиль",
            callback_data="my_profile",
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    fund_bar = "▓" * min(int(fund / 100), 16) + "░" * max(16 - min(int(fund / 100), 16), 0)
    fund_text = f"💰 <b>{fund:.0f}₽</b>\n" if fund > 0 else "💰 <b>0₽</b>\n"

    text = (
        f"🌟 <b>Добро пожаловать в Quiz Bot!</b>\n\n"
        f"🧠 <b>Попыток:</b> {attempts}\n"
        f"{fund_text}"
        f"{fund_bar}\n"
        f"<i>Призовой фонд: {fund:.0f} / {PRIZE_THRESHOLD:.0f}₽</i>\n\n"
        f"Проверь свои знания и выигрывай призы! 🎉"
    )

    await message.answer(text, reply_markup=keyboard)


@dp.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Welcome / start."""
    register_or_update_user(message)

    # Проверяем капчу
    user = get_user(message.from_user.id)
    if user and user["captcha_solved"] == 1:
        await show_main_menu(message)
    else:
        await send_captcha(message)


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message) -> None:
    """Показать главное меню."""
    register_or_update_user(message)
    # Капча уже должна быть пройдена, если дошли сюда
    await show_main_menu(message)


# ── Callbacks ─────────────────────────────────────────────────


@dp.callback_query(lambda c: c.data == "play_quiz")
async def cb_play_quiz(callback: CallbackQuery) -> None:
    """Открыть обычную викторину."""
    user = get_user(callback.from_user.id)
    if not user or user["attempts"] < 1:
        # Предложить купить
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💰 Купить попытку ({STAR_PRICE} ⭐)",
                        callback_data="buy_attempt",
                    )
                ],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")],
            ]
        )
        await callback.message.edit_text(
            "❌ <b>У тебя нет попыток!</b>\n\n"
            f"Купи попытку за {STAR_PRICE} ⭐, чтобы играть.",
            reply_markup=kb,
        )
        await callback.answer()
        return

    # Уменьшаем попытку
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET attempts = attempts - 1 WHERE user_id = ?",
            (callback.from_user.id,),
        )

    await callback.message.edit_text(
        "🎮 <b>Запускаем викторину!</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎮 Открыть викторину",
                        web_app=WebAppInfo(url=f"{WEBAPP_URL}?mode=regular"),
                    )
                ],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")],
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "play_prize")
async def cb_play_prize(callback: CallbackQuery) -> None:
    """Открыть призовую игру."""
    if not is_prize_game_available():
        await callback.answer("❌ Призовая игра пока недоступна. Копим фонд!", show_alert=True)
        return

    await callback.message.edit_text(
        "🏆 <b>Призовая игра!</b>\n\n"
        "Тебя ждут 10 сложнейших вопросов. Ответь правильно на максимум и займи место в топе!\n\n"
        f"🥇 1 место — {PRIZE_1ST:.0f}₽\n"
        f"🥈 2 место — {PRIZE_2ND:.0f}₽\n"
        f"🥉 3 место — {PRIZE_3RD:.0f}₽",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏆 Начать призовую игру",
                        web_app=WebAppInfo(url=f"{WEBAPP_URL}?mode=prize"),
                    )
                ],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")],
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "buy_attempt")
async def cb_buy_attempt(callback: CallbackQuery) -> None:
    """Создать счёт на оплату Stars."""
    payload = str(uuid.uuid4())

    prices = [LabeledPrice(label="🎮 Попытка викторины", amount=STAR_PRICE)]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="🎮 Попытка викторины",
        description=f"Одна попытка сыграть в Quiz Bot.\n"
        f"Цена: {STAR_PRICE} ⭐ Telegram Stars.\n"
        f"90% платежа идёт в призовой фонд!",
        payload=payload,
        provider_token=None,  # XTR не требует provider_token
        currency="XTR",
        prices=prices,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")]
            ]
        ),
    )

    await callback.answer()


@dp.callback_query(lambda c: c.data == "my_profile")
async def cb_my_profile(callback: CallbackQuery) -> None:
    """Показать профиль пользователя."""
    user = get_user(callback.from_user.id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    # Статистика игр
    with get_db() as conn:
        games_played = conn.execute(
            "SELECT COUNT(*) FROM quiz_attempts WHERE user_id = ? AND quiz_type = 'regular'",
            (callback.from_user.id,),
        ).fetchone()[0]
        best_score = conn.execute(
            "SELECT MAX(score) FROM quiz_attempts WHERE user_id = ? AND quiz_type = 'regular'",
            (callback.from_user.id,),
        ).fetchone()[0] or 0
        prize_best = conn.execute(
            "SELECT MAX(score) FROM quiz_attempts WHERE user_id = ? AND quiz_type = 'prize'",
            (callback.from_user.id,),
        ).fetchone()[0] or 0

    text = (
        f"📊 <b>Твой профиль</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Имя: {user['first_name'] or '—'}\n"
        f"🎮 Попыток: <b>{user['attempts']}</b>\n"
        f"⭐ Всего потрачено: {user['total_paid_stars']}\n\n"
        f"📈 <b>Статистика игр:</b>\n"
        f"• Сыграно: {games_played}\n"
        f"• Лучший результат: {best_score}/12\n"
        f"• Лучший в призовой: {prize_best}/10\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")]
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "back_menu")
async def cb_back_menu(callback: CallbackQuery) -> None:
    """Вернуться в главное меню."""
    await callback.message.delete()
    await show_main_menu(callback.message)
    await callback.answer()


# ── Payments ──────────────────────────────────────────────────


@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery) -> None:
    """Подтверждаем платёж."""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def payment_success(message: types.Message) -> None:
    """Обработка успешного платежа."""
    payment = message.successful_payment
    user_id = message.from_user.id
    stars_amount = payment.total_amount
    rub_amount = stars_amount * RUB_PER_STAR

    # 90% в призовой фонд
    prize_portion = rub_amount * 0.9

    with get_db() as conn:
        # Сохраняем платёж
        conn.execute(
            """INSERT INTO payments (user_id, stars_amount, rub_amount, status, payload, telegram_charge_id)
               VALUES (?, ?, ?, 'completed', ?, ?)""",
            (user_id, stars_amount, rub_amount, payment.invoice_payload, payment.telegram_payment_charge_id),
        )
        # Добавляем попытку пользователю
        conn.execute(
            "UPDATE users SET attempts = attempts + 1, total_paid_stars = total_paid_stars + ?, total_paid_rub = total_paid_rub + ? WHERE user_id = ?",
            (stars_amount, rub_amount, user_id),
        )

    # Добавляем в призовой фонд
    add_to_prize_fund(prize_portion)

    new_fund = get_prize_fund()

    await message.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"⭐ Пополнено: {stars_amount} Stars\n"
        f"🎮 У тебя теперь <b>{get_user(user_id)['attempts']} попыток</b>!\n\n"
        f"💰 В призовой фонд добавлено: {prize_portion:.0f}₽\n"
        f"📊 Текущий фонд: {new_fund:.0f} / {PRIZE_THRESHOLD:.0f}₽",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎮 Играть",
                        callback_data="play_quiz",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Мой профиль",
                        callback_data="my_profile",
                    )
                ],
            ]
        ),
    )

    # Проверяем, не пора ли запустить призовую игру
    if new_fund >= PRIZE_THRESHOLD:
        await message.answer(
            "🎊 <b>Призовой фонд набран!</b>\n\n"
            f"Достигнута цель {PRIZE_THRESHOLD:.0f}₽! 🏆\n"
            "Теперь доступна <b>призовая игра</b>!\n"
            "Сыграй и выиграй до 1000₽!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🏆 Начать призовую игру!",
                            callback_data="play_prize",
                        )
                    ]
                ]
            ),
        )

        # Уведомляем админа
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"🎊 <b>Призовой фонд заполнен!</b>\n\n"
                f"Текущий фонд: {new_fund:.0f}₽\n"
                f"Призовая игра активна!",
            )


# ── Web App Data handler ──────────────────────────────────────


@dp.message(lambda msg: msg.web_app_data is not None)
async def handle_webapp_data(message: types.Message) -> None:
    """Receive quiz results from the Mini App."""
    data = message.web_app_data.data
    logger.info("WebApp data received: %s", data[:200])

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        await message.answer("❌ Не удалось обработать результат. Попробуй ещё раз.")
        return

    mode = payload.get("mode", "regular")
    score = int(payload.get("score", 0))
    total = int(payload.get("total", 0))
    percent = (score / total * 100) if total > 0 else 0

    # Сохраняем результат
    with get_db() as conn:
        conn.execute(
            "INSERT INTO quiz_attempts (user_id, score, total, quiz_type) VALUES (?, ?, ?, ?)",
            (message.from_user.id, score, total, mode),
        )

    if mode == "prize":
        # Призовая игра — показываем результат и топ
        leaderboard = get_prize_leaderboard()

        lb_text = "\n\n🏆 <b>Топ призовой игры:</b>\n"
        positions_text = ["🥇", "🥈", "🥉"]
        for i, entry in enumerate(leaderboard):
            if i >= 3:
                break
            lb_text += f"{positions_text[i]} {entry['score']}/{entry['total']}\n"

        emoji = "🏆" if percent >= 80 else "👍"
        text = (
            f"{emoji} <b>Призовая игра завершена!</b>\n\n"
            f"✅ Правильных ответов: <b>{score}/{total}</b>\n"
            f"📊 Результат: <b>{percent:.0f}%</b>"
            f"{lb_text}"
        )

        await message.answer(text)

        # Проверяем, не пора ли выплатить призы
        await award_prizes_if_due()

    else:
        # Обычная викторина
        emoji = "🏆" if percent >= 80 else "👍" if percent >= 50 else "💪"
        text = (
            f"{emoji} <b>Твой результат!</b>\n\n"
            f"✅ Правильных ответов: <b>{score}/{total}</b>\n"
            f"📊 Процент: <b>{percent:.1f}%</b>\n\n"
        )

        if percent == 100:
            text += "🌟 Идеально! Ты настоящий эрудит!"
        elif percent >= 80:
            text += "🎉 Отлично! Ты много знаешь!"
        elif percent >= 60:
            text += "😊 Хороший результат! Есть куда расти."
        elif percent >= 40:
            text += "📚 Неплохо! Попробуй ещё раз, чтобы улучшить."
        else:
            text += "🤔 Стоит подтянуть знания. Попробуй снова!"

        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🎮 Играть ещё",
                            callback_data="play_quiz",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="💰 Купить попытку",
                            callback_data="buy_attempt",
                        )
                    ],
                ]
            ),
        )


# ── Admin commands ────────────────────────────────────────────


@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def cmd_admin(message: types.Message) -> None:
    """Админ-панель."""
    fund = get_prize_fund()

    with get_db() as conn:
        users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_payments = conn.execute(
            "SELECT COALESCE(SUM(rub_amount), 0) FROM payments"
        ).fetchone()[0]
        attempts_count = conn.execute(
            "SELECT COUNT(*) FROM quiz_attempts"
        ).fetchone()[0]

    await message.answer(
        f"🔐 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"💰 Призовой фонд: {fund:.0f}₽\n"
        f"📦 Всего платежей: {total_payments:.0f}₽\n"
        f"🎮 Сыграно игр: {attempts_count}\n\n"
        f"<b>Команды:</b>\n"
        f"/add_attempts [id] [n] — добавить попытки\n"
        f"/reset_fund — сбросить призовой фонд\n"
        f"/stats — детальная статистика",
    )


@dp.message(Command("add_attempts"), F.from_user.id == ADMIN_ID)
async def cmd_add_attempts(message: types.Message) -> None:
    """Добавить попытки пользователю. /add_attempts user_id count"""
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ Использование: /add_attempts [user_id] [count]")
        return

    try:
        target_id = int(parts[1])
        count = int(parts[2])
    except ValueError:
        await message.answer("❌ Неверный формат ID или количества.")
        return

    with get_db() as conn:
        conn.execute(
            "UPDATE users SET attempts = attempts + ? WHERE user_id = ?",
            (count, target_id),
        )

    await message.answer(f"✅ Добавлено {count} попыток пользователю {target_id}.")


@dp.message(Command("reset_fund"), F.from_user.id == ADMIN_ID)
async def cmd_reset_fund(message: types.Message) -> None:
    """Сбросить призовой фонд."""
    with get_db() as conn:
        conn.execute("UPDATE prize_fund SET amount_rub = 0, updated_at = CURRENT_TIMESTAMP")
    await message.answer("✅ Призовой фонд сброшен.")


@dp.message(Command("stats"), F.from_user.id == ADMIN_ID)
async def cmd_stats(message: types.Message) -> None:
    """Детальная статистика."""
    with get_db() as conn:
        payments_by_user = conn.execute(
            """SELECT u.user_id, u.first_name, u.attempts,
                      COALESCE(SUM(p.rub_amount), 0) as total_spent
               FROM users u
               LEFT JOIN payments p ON u.user_id = p.user_id
               GROUP BY u.user_id
               ORDER BY total_spent DESC
               LIMIT 10"""
        ).fetchall()

        prize_leaders = conn.execute(
            """SELECT user_id, score, total, created_at
               FROM quiz_attempts
               WHERE quiz_type = 'prize'
               ORDER BY score DESC, id ASC
               LIMIT 5"""
        ).fetchall()

    text = "📊 <b>Детальная статистика</b>\n\n"

    text += "<b>Топ по платежам:</b>\n"
    for row in payments_by_user:
        name = row["first_name"] or f"ID {row['user_id']}"
        text += f"• {name}: {row['total_spent']:.0f}₽ (попыток: {row['attempts']})\n"

    text += "\n<b>Топ призовой игры:</b>\n"
    positions = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, row in enumerate(prize_leaders):
        text += f"{positions[i] if i < len(positions) else '•'} ID {row['user_id']}: {row['score']}/{row['total']}\n"

    await message.answer(text)


# ── Main ──────────────────────────────────────────────────────


async def main() -> None:
    init_db()
    logger.info("Starting quiz bot with payments, captcha & prize game...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
