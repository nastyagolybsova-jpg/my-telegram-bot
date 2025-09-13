import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
import aiohttp
import json

BOT_TOKEN = "8253385719:AAEJuuHrGG1fRu0yy_1uPEwRUWbeDTmzM5Y"
GIGACHAT_API_KEY = "OGYwMGUzZTYtMGRiZi00NzU2LWEwZmQtN2FlMmMxZjUzMTkyOmIwMjA0ZGJkLWRlZmMtNDA2Zi1iODI0LTVhNzQ5Y2Y3NWE1MA=="

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

user_states = {}
user_requests = {}

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💡 Генерация идей")],
            [KeyboardButton(text="🎉 Генерация поздравлений")],
            [KeyboardButton(text="📄 Создание документов")],
            [KeyboardButton(text="📊 Создание отчетов")]
        ],
        resize_keyboard=True
    )

def rating_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отлично, подходит", callback_data="accept")],
            [InlineKeyboardButton(text="🔄 Переделать", callback_data="redo")],
            [InlineKeyboardButton(text="↩️ Назад в меню", callback_data="back_to_menu")]
        ]
    )

async def ask_gigachat(prompt, previous_response=None, feedback=None):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GIGACHAT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [{"role": "user", "content": prompt}]
    
    if previous_response and feedback:
        messages.extend([
            {"role": "assistant", "content": previous_response},
            {"role": "user", "content": f"Не понравилось: {feedback}. Переделай с учетом этих замечаний:"}
        ])
    
    data = {
        "model": "GigaChat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, ssl=False) as response:
                result = await response.json()
                return result['choices'][0]['message']['content']
    except Exception as e:
        return f"Ошибка при обращении к AI: {str(e)}"

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 Добро пожаловать в бизнес-ассистент!\n\nВыберите нужную функцию:",
        reply_markup=main_keyboard()
    )

@dp.message(F.text == "💡 Генерация идей")
async def ideas_handler(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = "waiting_idea_description"
    
    await message.answer(
        "💡 Опишите подробнее, какие идеи вы хотите сгенерировать?\n\nНапример:\n• Идеи для корпоративного мероприятия\n• Идеи для нового продукта\n• Идеи для мотивации сотрудников",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="↩️ Назад в меню")]],
            resize_keyboard=True
        )
    )

@dp.message(F.text != "↩️ Назад в меню")
async def process_idea_request(message: types.Message):
    user_id = message.from_user.id
    
    if user_states.get(user_id) == "waiting_idea_description":
        user_states[user_id] = "processing"
        
        processing_msg = await message.answer("🔄 Генерирую идеи...")
        
        prompt = f"Сгенерируй 3-5 бизнес-идей по запросу: {message.text}. Представь в виде нумерованного списка."
        ai_response = await ask_gigachat(prompt)
        
        user_requests[user_id] = {
            "original_request": message.text,
            "ai_response": ai_response
        }
        
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        
        await message.answer(
            f"💡 Вот предложенные идеи:\n\n{ai_response}\n\nОцените результат:",
            reply_markup=rating_keyboard()
        )

@dp.callback_query(F.data == "accept")
async def accept_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "✅ Отлично! Рад, что идеи подошли!\n\nЧем еще могу помочь?",
        reply_markup=None
    )
    await callback.answer()

@dp.callback_query(F.data == "redo")
async def redo_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = "waiting_feedback"
    
    await callback.message.edit_text(
        "🔄 Что именно не понравилось в предложенных идеях?\nОпишите подробнее, что нужно изменить:",
        reply_markup=None
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=None
    )
    await callback.message.answer(
        "Выберите функцию:",
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.message(F.text != "↩️ Назад в меню")
async def process_feedback(message: types.Message):
    user_id = message.from_user.id
    
    if user_states.get(user_id) == "waiting_feedback":
        user_data = user_requests.get(user_id, {})
        
        processing_msg = await message.answer("🔄 Переделываю с учетом ваших замечаний...")
        
        new_response = await ask_gigachat(
            user_data["original_request"],
            user_data["ai_response"],
            message.text
        )
        
        user_requests[user_id]["ai_response"] = new_response
        
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        
        await message.answer(
            f"🔄 Переработанные идеи:\n\n{new_response}\n\nТеперь подходит лучше?",
            reply_markup=rating_keyboard()
        )

@dp.message(F.text == "↩️ Назад в меню")
async def back_to_menu_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    
    await message.answer(
        "Главное меню:",
        reply_markup=main_keyboard()
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())