import asyncio
import json
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

if not TOKEN or not ADMIN_ID:
    raise RuntimeError(
        "Set TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_ID environment variables before starting the bot."
    )

ADMIN_ID = int(ADMIN_ID)
START_IMAGE = os.path.join(os.path.dirname(__file__), "2.jpg")
PAYMENT_IMAGE = os.path.join(os.path.dirname(__file__), "3.jpg")
ACCESS_LINK = "https://t.me/+JpJId4AN4BEyZTAy"
WELCOME_TEXT = (
    "<b>Welcome to NexusLoad.</b>\n\n"
    "<blockquote>- Единственный рабочий чит без рут прав и без бана.\n"
    "- Огромное кол-во реально полезных функций.\n"
    "- Лучший скинченжер на рынке модификаций с сохранением в облаке.</blockquote>\n"
    "<b>@NexusLoad</b>"
)
MENU_BUTTON_TEXT = "💎 Меню"
REFERRAL_BUTTON_TEXT = "✅ Реферальная система"
TOP_REFERRALS_BUTTON_TEXT = "👥 Топ рефералов"
REFERRALS_FILE = os.path.join(os.path.dirname(__file__), "referrals.json")
PROMOTION_TEXT = """В акции вы можете получить наш нон-рут чит на неделю!

Что нужно делать?

1. Подписаться на канал: @NexusLoad

2. Отправить 100 комментариев в TikTok, например:

Лучший нон рут у @NexusLoad

Ахахахахха, @NexusLoad сносит, еще и нон рут

Парни, не кирпичьте телефон, лучше купите нон рут в @NexusLoad

В общем, нужно написать текст минимум 3 слова с рекламой нашего чита. В тексте ОБЯЗАТЕЛЬНО должен быть юзернейм нашего официального канала — @NexusLoad.

Важно!
- Нужно написать именно 100 комментариев, сделав скриншот каждого.
- Нельзя повторять один и тот же текст более 5 раз.
- Под одним видео можно писать только 1 комментарий.
- Обязательно нужно лайкнуть свой комментарий.
- Комментарий должен быть обязательно под видео с темой читов на Standoff.

После выполнения нажмите кнопку «Выполнил ✅»."""
SUPPORT_TEXT = (
    "💬 Поддержка\n\n"
    "Напишите сюда и отправьте все 100 скриншотов выполнения. "
    "Бот передаст каждое сообщение администратору."
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния для ожидания скриншота
class PaymentState(StatesGroup):
    waiting_for_screenshot = State()


class SupportState(StatesGroup):
    waiting_for_messages = State()


class WithdrawalState(StatesGroup):
    waiting_for_request = State()


def bottom_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_BUTTON_TEXT, style="success")],
            [KeyboardButton(text=REFERRAL_BUTTON_TEXT, style="primary")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def load_referrals():
    if not os.path.exists(REFERRALS_FILE):
        with open(REFERRALS_FILE, "w", encoding="utf-8") as file:
            json.dump({}, file, ensure_ascii=False)
        return {}

    with open(REFERRALS_FILE, encoding="utf-8") as file:
        return json.load(file)


def save_referrals(referrals):
    with open(REFERRALS_FILE, "w", encoding="utf-8") as file:
        json.dump(referrals, file, ensure_ascii=False, indent=2)


def display_username(username, full_name):
    return f"@{username}" if username else (full_name or "Пользователь")


def update_referrer_profile(user_id, username, full_name):
    referrals = load_referrals()
    entry = referrals.setdefault(
        str(user_id), {"username": username, "full_name": full_name, "invited": []}
    )
    entry["username"] = username
    entry["full_name"] = full_name
    save_referrals(referrals)


def register_referral(inviter_id, invited_id, inviter_name):
    if inviter_id == invited_id:
        return False

    referrals = load_referrals()
    inviter = referrals.setdefault(
        str(inviter_id), {"username": inviter_name, "invited": []}
    )
    inviter["username"] = inviter_name or inviter.get("username")

    if any(str(invited_id) in entry["invited"] for entry in referrals.values()):
        save_referrals(referrals)
        return False

    inviter["invited"].append(str(invited_id))
    save_referrals(referrals)
    return True


def get_referral_leaderboard():
    referrals = load_referrals()
    ranking = [
        (
            display_username(entry.get("username"), entry.get("full_name")),
            len(entry["invited"]),
        )
        for user_id, entry in referrals.items()
        if entry["invited"]
    ]
    return sorted(ranking, key=lambda item: (-item[1], item[0].lower()))


def referral_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw")],
        [InlineKeyboardButton(text=TOP_REFERRALS_BUTTON_TEXT, callback_data="top_referrals")],
    ])

# Главное меню
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить Чит", callback_data="buy_cheat"),
            InlineKeyboardButton(text="ℹ️ Информация", callback_data="info"),
        ],
        [InlineKeyboardButton(text="🥳 Неделя бесплатно!", callback_data="free_week")],
    ])


def free_week_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Выполнил ✅", callback_data="promotion_done")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    update_referrer_profile(user.id, user.username, user.full_name)

    command_parts = (message.text or "").split(maxsplit=1)
    if len(command_parts) == 2 and command_parts[1].startswith("ref_"):
        try:
            inviter_id = int(command_parts[1][4:])
        except ValueError:
            inviter_id = None
        if inviter_id:
            register_referral(inviter_id, user.id, None)

    await message.answer(
        text=WELCOME_TEXT,
        reply_markup=bottom_menu(),
        parse_mode="HTML",
    )


@dp.message(F.text == MENU_BUTTON_TEXT)
async def menu_button_callback(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer_photo(
        photo=FSInputFile(START_IMAGE),
        reply_markup=main_menu(),
    )


@dp.message(F.text == REFERRAL_BUTTON_TEXT)
async def referral_button_callback(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    update_referrer_profile(user.id, user.username, user.full_name)
    bot_info = await bot.get_me()
    referral_count = len(load_referrals().get(str(user.id), {}).get("invited", []))
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"
    await message.answer(
        "<b>Ваша партнёрская статистика</b>\n\n"
        f"Перешли по ссылке: {referral_count}\n"
        "Реферальный процент: 50 %\n\n"
        f"Ваша реферальная ссылка: {referral_link}",
        reply_markup=referral_menu(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "top_referrals")
async def top_referrals_callback(callback: types.CallbackQuery):
    leaderboard = get_referral_leaderboard()
    if not leaderboard:
        text = "<b>Топ рефералов</b>\n\nПока никто не пригласил рефералов."
    else:
        lines = [f"{index}. {username} - {count} рефералов" for index, (username, count) in enumerate(leaderboard, start=1)]
        text = "<b>Топ рефералов</b>\n\n" + "\n".join(lines)

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "withdraw")
async def withdraw_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(WithdrawalState.waiting_for_request)
    await callback.message.answer(
        "💸 Вывод средств\n\n"
        "Отправьте одним сообщением реквизиты для вывода и сумму. "
        "Заявка будет передана администрации.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")],
        ]),
    )
    await callback.answer()

# Нажатие на кнопку "Купить Чит"
@dp.callback_query(F.data == "buy_cheat")
async def buy_cheat_callback(callback: types.CallbackQuery):
    text = (
        "💳 Реквизиты для оплаты\n\n"
        "Сбербанк💸:\n"
        "2202208415420208\n\n"
        "💰 Сумма: 149₽\n"
        "📅 Длительность: 30 дней\n\n"
        "После оплаты сделайте скриншот перевода.\n"
        "Нажмите кнопку ниже и отправьте скриншот."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил (Отправить скриншот)", callback_data="send_proof")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=FSInputFile(PAYMENT_IMAGE),
        caption=text,
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()

@dp.callback_query(F.data == "info")
async def info_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "✅ Бот соответствует каналу @NexusLoad - Другие Фейки (не ведитесь)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
        ]),
    )
    await callback.answer()


@dp.callback_query(F.data == "free_week")
async def free_week_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(PROMOTION_TEXT, reply_markup=free_week_menu())
    await callback.answer()


@dp.callback_query(F.data == "promotion_done")
async def promotion_done_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SupportState.waiting_for_messages)
    await callback.message.edit_text(
        text=SUPPORT_TEXT,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
        ]),
    )
    await callback.answer()

# Нажатие на кнопку "Я оплатил"
@dp.callback_query(F.data == "send_proof")
async def send_proof_callback(callback: types.CallbackQuery, state: FSMContext):
    # Переводим пользователя в состояние ожидания скриншота
    await state.set_state(PaymentState.waiting_for_screenshot)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")]
    ])
    
    await callback.message.edit_caption(
        caption="📥 Пожалуйста, отправьте скриншот оплаты прямо в этот чат:",
        reply_markup=kb,
    )
    await callback.answer()

# Ловим скриншот (фотографию) от пользователя
@dp.message(PaymentState.waiting_for_screenshot, F.photo)
async def process_screenshot(message: types.Message, state: FSMContext):
    # Берем самое качественное фото из отправленных
    photo_id = message.photo[-1].file_id
    user = message.from_user
    
    # Уведомляем пользователя
    await message.answer("✨ Скриншот принят! Ожидайте проверки администратором. Вам придет уведомление.")
    
    # Сбрасываем состояние ожидания
    await state.clear()
    
    # Пересылаем скриншот администратору с кнопками подтверждения
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выдать чит", callback_data=f"confirm_{user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_{user.id}")
        ]
    ])
    
    admin_text = (
        f"🔔 Новая оплата!\n\n"
        f"👤 Пользователь: @{user.username or 'нет юзернейма'}\n"
        f"🆔 ID: {user.id}\n"
        f"🏷 Имя: {user.full_name}\n"
    )
    
    await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_text, reply_markup=admin_kb, parse_mode="Markdown")

# Если вместо фото пользователь отправил текст в режиме ожидания скриншота
@dp.message(PaymentState.waiting_for_screenshot)
async def process_not_photo(message: types.Message):
    await message.answer("⚠️ Пожалуйста, отправьте именно скриншот (фотографию) перевода.")


@dp.message(SupportState.waiting_for_messages)
async def process_support_message(message: types.Message):
    user = message.from_user
    admin_text = (
        "💬 Новое сообщение в поддержку по акции\n\n"
        f"👤 Пользователь: @{user.username or 'нет юзернейма'}\n"
        f"🆔 ID: {user.id}\n"
        f"🏷 Имя: {user.full_name}"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_text)
    await bot.copy_message(
        chat_id=ADMIN_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await message.answer("✅ Материал отправлен в поддержку. Можете прислать следующий скриншот.")


@dp.message(WithdrawalState.waiting_for_request)
async def process_withdrawal_request(message: types.Message, state: FSMContext):
    user = message.from_user
    admin_text = (
        "💸 Новая заявка на вывод средств\n\n"
        f"👤 Пользователь: @{user.username or 'нет юзернейма'}\n"
        f"🆔 ID: {user.id}\n"
        f"🏷 Имя: {user.full_name}"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_text)
    await bot.copy_message(
        chat_id=ADMIN_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await state.clear()
    await message.answer("✅ Заявка на вывод отправлена администрации.")


# Обработка решений админа (Выдать / Отклонить)
@dp.callback_query(F.data.startswith("confirm_"))
async def admin_confirm(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    try:
        # Здесь вы можете сгенерировать и отправить сам чит / ключ / ссылку
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 Ваша оплата подтверждена! Спасибо за покупку. "
                f"Вот ваша ссылка/ключ: {ACCESS_LINK}"
            ),
        )
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n🟢 Одобрено, чит выдан.")
    except Exception:
        await callback.answer("Не удалось отправить сообщение пользователю.", show_alert=True)

@dp.callback_query(F.data.startswith("decline_"))
async def admin_decline(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(chat_id=user_id, text="❌ Ваша оплата не была подтверждена администратором. Проверьте данные или обратитесь в поддержку.")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n🔴 Отклонено.")
    except Exception:
        await callback.answer("Не удалось отправить сообщение пользователю.", show_alert=True)

# Возврат в главное меню и сброс состояний
@dp.callback_query(F.data == "back_main")
async def back_main_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.message.photo:
        await callback.message.edit_caption(
            caption=None,
            reply_markup=main_menu(),
        )
    else:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=FSInputFile(START_IMAGE),
            reply_markup=main_menu(),
        )
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
