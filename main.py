import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

# ====== Token va User ID ======
BOT_TOKEN = os.getenv("BOT_TOKEN", "8273684666:AAHStkIEUBSsCFdhps_yMYfRGEOIP4Q8VHw")
USER_ID = int(os.getenv("USER_ID", "1370058711"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# /start komandasi
@dp.message(Command("start"))
async def start_cmd(message: Message):
    if message.from_user.id == USER_ID:
        await message.answer("✅ Signal bot ishga tushdi! Siz endi push xabarlarni olasiz.")
    else:
        await message.answer("❌ Sizga ruxsat yo‘q.")

# Signal yuborish funksiyasi (manual yoki avtomatik)
async def send_signal():
    text = (
        "📊 *Bugungi XAU/USD signal*\n\n"
        "📈 Buy: 3332 – 3334\n"
        "⛔ Stop Loss: 3328\n"
        "🎯 TP1: 3340\n"
        "🎯 TP2: 3345\n\n"
        "📝 Izoh: Support ustida ushlab turibdi, qisqa muddatli o‘sish ehtimoli yuqori."
    )
    await bot.send_message(chat_id=USER_ID, text=text, parse_mode="Markdown")

async def main():
    # Botni polling orqali doimiy ishga tushiramiz
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
