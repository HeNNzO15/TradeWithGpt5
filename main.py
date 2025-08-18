import asyncio
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

# ==== ENV ====
BOT_TOKEN = os.getenv("BOT_TOKEN", "8273684666:AAHStkIEUBSsCFdhps_yMYfRGEOIP4Q8VHw")
USER_ID = int(os.getenv("USER_ID", "1370058711"))

# "HH:MM" formatda, UZT vaqtida
SCHEDULE_1 = os.getenv("SCHEDULE_1", "11:55")  # London oldidan
SCHEDULE_2 = os.getenv("SCHEDULE_2", "18:55")  # NY oldidan

TZ = ZoneInfo("Asia/Tashkent")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --------- SIGNAL MATNI (bu yerda har kuni yangilab generatsiya qilamiz) ---------
def build_daily_signal() -> str:
    # Siz keyin istasangiz men bilan birga bu joyni real tahlilga bog'laymiz
    return (
        "📊 *XAU/USD — Kundalik & Intraday Signal*\n"
        "— *Kundalik (Swing)*\n"
        "  • Buy: 3331–3334  | SL: 3324  | TP1: 3345  | TP2: 3360\n"
        "— *Intraday (5–15m)*\n"
        "  • Agar 3334 ustida mustahkam bo‘lsa: Buy 3335 | SL 3329 | TP 3342/3348\n"
        "  • Agar 3328 pastiga sinib ketsa: Sell 3327 | SL 3333 | TP 3320/3315\n"
        "📝 Eslatma: London/NY ochilishida volatilitet yuqori — SL shart."
    )

# --------- JO'NATISH FUNKSIYASI ---------
async def send_signal():
    text = build_daily_signal()
    await bot.send_message(USER_ID, text, parse_mode="Markdown")

# --------- SODDA SCHEDULER (asyncio bilan) ---------
async def scheduler():
    # Matnli HH:MM ni time() ga aylantiramiz
    h1, m1 = map(int, SCHEDULE_1.split(":"))
    h2, m2 = map(int, SCHEDULE_2.split(":"))
    t1 = time(h1, m1, tzinfo=TZ)
    t2 = time(h2, m2, tzinfo=TZ)

    while True:
        now = datetime.now(TZ)
        # keyingi triggerlardan eng yaqinini topamiz
        today_t1 = now.replace(hour=t1.hour, minute=t1.minute, second=0, microsecond=0)
        today_t2 = now.replace(hour=t2.hour, minute=t2.minute, second=0, microsecond=0)

        targets = [today_t1, today_t2]
        # agar o‘tib ketgan bo‘lsa, ertangi kunni olamiz
        targets = [dt if dt > now else dt.replace(day=now.day, hour=dt.hour, minute=dt.minute) for dt in targets]
        # «ertangi» holat uchun:
        targets = [dt if dt > now else (dt + timedelta(days=1)) for dt in targets]

        next_run = min(targets)
        await asyncio.sleep((next_run - now).total_seconds())
        try:
            await send_signal()
        except Exception as e:
            await bot.send_message(USER_ID, f"⚠️ Signal jo'natishda xatolik: {e}")
        # keyingi iteratsiya
        await asyncio.sleep(1)

@dp.message(Command("start"))
async def start_cmd(message: Message):
    if message.from_user.id == USER_ID:
        await message.answer(
            "✅ Signal bot ishga tushdi!\n"
            f"⏰ Avtomatik vaqtlar: {SCHEDULE_1} va {SCHEDULE_2} (UZT).\n"
            "👉 /now — hozir test signal yuborish"
        )
    else:
        await message.answer("❌ Sizga ruxsat yo‘q.")

@dp.message(Command("now"))
async def now_cmd(message: Message):
    if message.from_user.id == USER_ID:
        await send_signal()
    else:
        await message.answer("❌ Ruxsat yo‘q.")

async def main():
    loop = asyncio.get_event_loop()
    loop.create_task(scheduler())          # jadval ishga tushadi
    await dp.start_polling(bot)            # bot pollingda 24/7

if __name__ == "__main__":
    asyncio.run(main())
