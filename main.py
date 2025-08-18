#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from typing import List

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

# --- HTTP server (Render Web Service uchun portni band qilish) ---
from fastapi import FastAPI
import uvicorn

# ================== ENV ==================
BOT_TOKEN  = os.getenv("BOT_TOKEN", "8273684666:AAHStkIEUBSsCFdhps_yMYfRGEOIP4Q8VHw")  # BotFather token
USER_ID    = int(os.getenv("USER_ID", "1370058711"))  # Sizning Telegram ID
SCHEDULE_1 = os.getenv("SCHEDULE_1", "11:55")  # HH:MM (UZT)
SCHEDULE_2 = os.getenv("SCHEDULE_2", "18:55")  # HH:MM (UZT), ixtiyoriy
TZ_NAME    = os.getenv("TZ", "Asia/Tashkent")
PORT       = int(os.getenv("PORT", "8000"))  # Render Web Service uchun

TZ = ZoneInfo(TZ_NAME)

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN env o‘rnatilmagan")
if USER_ID == 0:
    raise SystemExit("❌ USER_ID env o‘rnatilmagan yoki 0")

# ================== TELEGRAM ==================
bot = Bot(BOT_TOKEN)
dp  = Dispatcher()

# ================== XABAR BLOKLARI ==================
def build_news_outlook() -> str:
    """
    Kutilayotgan yangiliklar (hozircha shablon).
    Keyin bu qismni webdan avtomatik yangilik olishga ham ulash mumkin.
    """
    return (
        "📢 *Bugungi muhim yangiliklar*\n"
        "• 17:30 UZT – AQSh CPI (inflyatsiya) ma’lumotlari\n"
        "• 22:00 UZT – FOMC bayonoti\n\n"
        "📝 Kutilayotgan ta’sir:\n"
        "  – Kuchli inflyatsiya → dollar kuchayishi → oltin pasayishi\n"
        "  – Yumshoq natija → oltin ko‘tarilishi mumkin"
    )

def build_trade_zones() -> str:
    return (
        "📊 *XAU/USD — Buy/Sell zonalar*\n\n"
        "— *Buy zona*: 3331–3334 (support ustida)\n"
        "   ⛔ SL: 3324 | 🎯 TP1: 3345 | 🎯 TP2: 3360\n\n"
        "— *Sell zona*: agar 3328 pastga tushsa\n"
        "   ⛔ SL: 3333 | 🎯 TP1: 3320 | 🎯 TP2: 3315"
    )

# --------- SIGNAL YUBORISH ---------
async def send_signal():
    try:
        await bot.send_message(USER_ID, build_news_outlook(), parse_mode="Markdown")
        await bot.send_message(USER_ID, build_trade_zones(), parse_mode="Markdown")
    except Exception as e:
        try:
            await bot.send_message(USER_ID, f"⚠️ Signal jo‘natishda xato: {e}")
        except Exception:
            pass

# ================== SCHEDULER ==================
def parse_hhmm(s: str) -> time:
    h, m = map(int, s.strip().split(":"))
    return time(h, m, tzinfo=TZ)

def next_run_for(t: time, now: datetime) -> datetime:
    candidate = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)

def current_schedule_times() -> List[time]:
    times = []
    if SCHEDULE_1:
        times.append(parse_hhmm(SCHEDULE_1))
    if SCHEDULE_2:
        try:
            if SCHEDULE_2.strip():
                times.append(parse_hhmm(SCHEDULE_2))
        except Exception:
            pass
    return times or [parse_hhmm("11:55")]

async def scheduler():
    """
    Oddiy asyncio scheduler: belgilangan UZT vaqtlarda signal yuboradi.
    """
    while True:
        now = datetime.now(TZ)
        times = current_schedule_times()
        next_run = min(next_run_for(t, now) for t in times)
        sleep_s = max(1, int((next_run - now).total_seconds()))
        print(f"[scheduler] now={now.astimezone(TZ)} next_run={next_run.astimezone(TZ)} sleep={sleep_s}s")
        await asyncio.sleep(sleep_s)
        await send_signal()
        await asyncio.sleep(1)

# ================== HANDLERS ==================
@dp.message(Command("start"))
async def start_cmd(message: Message):
    if message.from_user.id != USER_ID:
        return await message.answer("❌ Ruxsat yo‘q.")
    sched = ", ".join(t.strftime("%H:%M") for t in current_schedule_times())
    await message.answer(
        "✅ Signal bot ishga tushdi!\n"
        f"⏰ Jadval (UZT, {TZ_NAME}): {sched}\n"
        "👉 /now — hozir test signal yuborish"
    )

@dp.message(Command("now"))
async def now_cmd(message: Message):
    if message.from_user.id == USER_ID:
        await send_signal()
    else:
        await message.answer("❌ Ruxsat yo‘q.")

# ================== HTTP SERVER (Render uchun) ==================
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "service": "xau-signal-bot", "tz": TZ_NAME, "schedules": [SCHEDULE_1, SCHEDULE_2]}

@app.get("/healthz")
def healthz():
    return {"ok": True}

async def run_http():
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

# ================== ENTRYPOINT ==================
async def main():
    asyncio.create_task(run_http())
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
