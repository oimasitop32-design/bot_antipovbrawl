import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_ID = int(os.environ["TELEGRAM_ADMIN_ID"])

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния для ожидания скриншота
class PaymentState(StatesGroup):
    waiting_for_screenshot = State()

# Главное меню
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить Чит", callback_data="buy_cheat")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info")]
    ])

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать! Выберите действие:", reply_markup=main_menu())

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
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# Нажатие на кнопку "Я оплатил"
@dp.callback_query(F.data == "send_proof")
async def send_proof_callback(callback: types.CallbackQuery, state: FSMContext):
    # Переводим пользователя в состояние ожидания скриншота
    await state.set_state(PaymentState.waiting_for_screenshot)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")]
    ])
    
    await callback.message.edit_text("📥 Пожалуйста, отправьте скриншот оплаты прямо в этот чат:", reply_markup=kb)

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
# Обработка решений админа (Выдать / Отклонить)
@dp.callback_query(F.data.startswith("confirm_"))
async def admin_confirm(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    try:
        # Здесь вы можете сгенерировать и отправить сам чит / ключ / ссылку
        await bot.send_message(chat_id=user_id, text="🎉 Ваша оплата подтверждена! Спасибо за покупку. Вот ваша ссылка/ключ: [ССЫЛКА]")
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
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())

async def main():
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
