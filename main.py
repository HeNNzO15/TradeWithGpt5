#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from typing import List, Dict, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# --- HTTP server (Render Web Service uchun portni band qilish) ---
from fastapi import FastAPI
import uvicorn

# ================== ENV + ICHKI DEFAULTLAR ==================
# ❗ Siz so‘raganidek token va ID kod ichida DEFAULT sifatida bor.
#    Agar Render’da ENV berilsa, ENV ustun bo‘ladi.
BOT_TOKEN  = os.getenv("BOT_TOKEN", "8273684666:AAHStkIEUBSsCFdhps_yMYfRGEOIP4Q8VHw")  # BotFather token (default ichida)
USER_ID    = int(os.getenv("USER_ID", "1370058711"))                                     # Sizning Telegram ID (default ichida)
SCHEDULE_1 = os.getenv("SCHEDULE_1", "11:55")   # HH:MM (UZT)
SCHEDULE_2 = os.getenv("SCHEDULE_2", "18:55")   # HH:MM (UZT), ixtiyoriy
TZ_NAME    = os.getenv("TZ", "Asia/Tashkent")
PORT       = int(os.getenv("PORT", "8000"))     # Render Web Service uchun

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN env o‘rnatilmagan va default ham berilmagan")
if USER_ID == 0:
    raise SystemExit("❌ USER_ID env o‘rnatilmagan yoki 0")

TZ = ZoneInfo(TZ_NAME)

# ================== TELEGRAM ==================
# aiogram 3.7+ uchun parse_mode shu tarzda beriladi:
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

# ================== KICHIK SAQLAGICH ==================
# Foydalanuvchi afzalliklari (oddiy xotira; kerak bo‘lsa DBga oson ko‘chadi)
PREFS: Dict[int, Dict[str, str]] = {}

# ================== LOKALIZATSIYA ==================
L = {
    "uz": {
        "greet": "Salom! Tilni tanlang:",
        "choose_tf": "Qaysi <b>timeframe</b>da savdo qilmoqchisiz?",
        "choose_asset": "Qaysi <b>aktiv</b> uchun signal kerak?",
        "signal_title": "📊 {asset} — <b>{tf}</b> signal",
        "zones": "— <b>Buy</b>: {buy}\n— <b>Sell</b>: {sell}\n⛔ SL: {sl}\n🎯 TP1: {tp1}\n🎯 TP2: {tp2}",
        "news_title": "📢 Savdoga ta’sir qiladigan yangiliklar",
        "news_body": (
            "• <b>Yuqori ta’sirli</b>: CPI, NFP, FOMC, AQSh obligatsiya rentabelligi, DXY\n"
            "• <b>Ta’sir mexanizmi</b>: kuchli USD → oltin/BTC pasayishi; yumshoq ma’lumotlar → oltin/BTC o‘sishi\n"
        ),
        "links": "🔗 Havolalar:\n{links}",
        "saved": "✅ Tanlov saqlandi: til: {lang}, timeframe: {tf}, aktiv: {asset}\n👉 /signal — istalgan payt shu profil bo‘yicha signal",
        "only_you": "❌ Bu bot faqat bitta foydalanuvchi uchun ruxsat etilgan.",
        "start_ok": "✅ Bot ishga tushdi. Avval tilni tanlang.",
        "sent": "✅ Signal yuborildi.",
        "sched_head": "⏰ Avtomatik jadval (UZT): {sched}",
    },
    "ru": {
        "greet": "Здравствуйте! Выберите язык:",
        "choose_tf": "Какой <b>таймфрейм</b> хотите торговать?",
        "choose_asset": "Для какого <b>актива</b> нужен сигнал?",
        "signal_title": "📊 {asset} — <b>{tf}</b> сигнал",
        "zones": "— <b>Buy</b>: {buy}\n— <b>Sell</b>: {sell}\n⛔ SL: {sl}\n🎯 TP1: {tp1}\n🎯 TP2: {tp2}",
        "news_title": "📢 Новости, влияющие на торговлю",
        "news_body": (
            "• <b>Высокое влияние</b>: CPI, NFP, FOMC, доходности UST, индекс DXY\n"
            "• <b>Эффект</b>: сильный доллар → золото/BTC вниз; слабые данные → вверх\n"
        ),
        "links": "🔗 Ссылки:\n{links}",
        "saved": "✅ Сохранено: язык: {lang}, таймфрейм: {tf}, актив: {asset}\n👉 /signal — получить сигнал по профилю",
        "only_you": "❌ Этот бот доступен только одному пользователю.",
        "start_ok": "✅ Бот запущен. Сначала выберите язык.",
        "sent": "✅ Сигнал отправлен.",
        "sched_head": "⏰ Автографик (UZT): {sched}",
    },
    "en": {
        "greet": "Hi! Choose your language:",
        "choose_tf": "Which <b>timeframe</b> do you trade?",
        "choose_asset": "Which <b>asset</b> do you want a signal for?",
        "signal_title": "📊 {asset} — <b>{tf}</b> signal",
        "zones": "— <b>Buy</b>: {buy}\n— <b>Sell</b>: {sell}\n⛔ SL: {sl}\n🎯 TP1: {tp1}\n🎯 TP2: {tp2}",
        "news_title": "📢 Market-moving news",
        "news_body": (
            "• <b>High-impact</b>: CPI, NFP, FOMC, UST yields, DXY\n"
            "• <b>Effect</b>: strong USD → Gold/BTC down; soft data → up\n"
        ),
        "links": "🔗 Links:\n{links}",
        "saved": "✅ Saved: lang: {lang}, timeframe: {tf}, asset: {asset}\n👉 /signal — get signal with this profile",
        "only_you": "❌ This bot is restricted to a single user.",
        "start_ok": "✅ Bot is running. Please choose a language.",
        "sent": "✅ Signal sent.",
        "sched_head": "⏰ Auto schedule (UZT): {sched}",
    },
}

LANG_BTNS = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🇺🇿 Uzbek", callback_data="lang:uz"),
     InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
     InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")]
])

TF_LIST = ["1m", "5m", "15m", "1h", "4h", "1d"]
def tf_kb(lang: str) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, tf in enumerate(TF_LIST, 1):
        row.append(InlineKeyboardButton(text=tf, callback_data=f"tf:{tf}"))
        if i % 3 == 0:
            rows.append(row); row = []
    if row: rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

ASSETS = {
    "XAUUSD": {"name": {"uz": "Gold (XAU/USD)", "ru": "Золото (XAU/USD)", "en": "Gold (XAU/USD)"}},
    "EURUSD": {"name": {"uz": "USD (EUR/USD)", "ru": "USD (EUR/USD)", "en": "USD (EUR/USD)"}},
    "BTCUSD": {"name": {"uz": "BTC (BTC/USD)", "ru": "BTC (BTC/USD)", "en": "BTC (BTC/USD)"}},
}
def asset_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ASSETS["XAUUSD"]["name"][lang], callback_data="asset:XAUUSD")],
        [InlineKeyboardButton(text=ASSETS["EURUSD"]["name"][lang], callback_data="asset:EURUSD")],
        [InlineKeyboardButton(text=ASSETS["BTCUSD"]["name"][lang], callback_data="asset:BTCUSD")],
    ])

def t(lang: str, key: str, **kw) -> str:
    return L.get(lang, L["en"]).get(key, "").format(**kw)

# ================== SIGNAL GENERATOR (shablon) ==================
def signal_levels(asset: str, tf: str) -> Tuple[str, str, str, str, str]:
    if asset == "XAUUSD":  # Gold
        if tf in ("1d", "4h", "1h"):
            return "3331–3334", "3328 pastida", "3324", "3345", "3360"
        else:
            return "3333–3335", "3328 pastida", "3329", "3342", "3348"
    if asset == "EURUSD":  # USD proxy (EURUSD)
        if tf in ("1d", "4h", "1h"):
            return "1.1000–1.1020", "1.0960 pastida", "1.0945", "1.1060", "1.1100"
        else:
            return "1.1005–1.1015", "1.0985 pastida", "1.0975", "1.1030", "1.1050"
    if asset == "BTCUSD":
        if tf in ("1d", "4h", "1h"):
            return "116000–117000", "114500 pastida", "114000", "118500", "121000"
        else:
            return "116300–116800", "115500 pastida", "115200", "117600", "118800"
    return "—", "—", "—", "—", "—"

def news_links(asset: str, lang: str) -> str:
    calendars = [
        ("ForexFactory Calendar", "https://www.forexfactory.com/calendar"),
        ("Investing.com Calendar", "https://www.investing.com/economic-calendar/"),
        ("TradingView Calendar", "https://www.tradingview.com/markets/economic-calendar/"),
    ]
    if asset == "XAUUSD":
        extras = [
            ("Gold News (Reuters)", "https://www.reuters.com/markets/commodities/gold/"),
            ("Bloomberg TV Live", "https://www.youtube.com/@BloombergTV/live"),
        ]
    elif asset == "EURUSD":
        extras = [
            ("USD News (Reuters)", "https://www.reuters.com/markets/us/"),
            ("FOMC Statements", "https://www.federalreserve.gov/monetarypolicy.htm"),
        ]
    else:  # BTCUSD
        extras = [
            ("Bitcoin News (CoinDesk)", "https://www.coindesk.com/"),
            ("Crypto Calendar (CoinMarketCal)", "https://coinmarketcal.com/en/"),
        ]
    items = calendars + extras
    return "\n".join([f"• <a href='{u}'>{n}</a>" for (n, u) in items])

async def send_composed_signal(chat_id: int, lang: str, asset: str, tf: str):
    title = t(lang, "signal_title", asset=ASSETS[asset]["name"][lang], tf=tf)
    buy, sell, sl, tp1, tp2 = signal_levels(asset, tf)
    zones = t(lang, "zones", buy=buy, sell=sell, sl=sl, tp1=tp1, tp2=tp2)
    await bot.send_message(chat_id, f"{title}\n{zones}")
    await bot.send_message(chat_id, f"{t(lang, 'news_title')}\n{t(lang,'news_body')}\n" +
                           t(lang, "links", links=news_links(asset, lang)))

# ================== SCHEDULER (ixtiyoriy — avtomatik jo‘natish) ==================
def parse_hhmm(s: str) -> time:
    h, m = map(int, s.strip().split(":"))
    return time(h, m, tzinfo=TZ)

def next_run_for(ti: time, now: datetime) -> datetime:
    candidate = now.replace(hour=ti.hour, minute=ti.minute, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)

def current_schedule_times() -> List[time]:
    times = []
    if SCHEDULE_1:
        times.append(parse_hhmm(SCHEDULE_1))
    if SCHEDULE_2 and SCHEDULE_2.strip():
        times.append(parse_hhmm(SCHEDULE_2))
    return times

async def scheduler():
    while True:
        now = datetime.now(TZ)
        times = current_schedule_times()
        if not times:
            await asyncio.sleep(60); continue
        next_run = min(next_run_for(ti, now) for ti in times)
        await asyncio.sleep(max(1, int((next_run - now).total_seconds())))
        lang = PREFS.get(USER_ID, {}).get("lang", "uz")
        tf   = PREFS.get(USER_ID, {}).get("tf", "1d")
        asset= PREFS.get(USER_ID, {}).get("asset", "XAUUSD")
        try:
            await send_composed_signal(USER_ID, lang, asset, tf)
        except Exception as e:
            try:
                await bot.send_message(USER_ID, f"⚠️ Auto-signal xato: {e}")
            except Exception:
                pass
        await asyncio.sleep(1)

# ================== HANDLERS ==================
@dp.message(Command("start"))
async def start_cmd(message: Message):
    if message.from_user.id != USER_ID:
        return await message.answer(t("uz","only_you"))
    PREFS.setdefault(USER_ID, {"lang": "uz", "tf": "1d", "asset": "XAUUSD"})
    sched = ", ".join(ti.strftime("%H:%M") for ti in current_schedule_times()) or "—"
    await message.answer(t("uz","start_ok") + "\n" + t("uz","sched_head", sched=sched))
    await message.answer(t("uz","greet"), reply_markup=LANG_BTNS)

@dp.callback_query(F.data.startswith("lang:"))
async def choose_lang(c: CallbackQuery):
    if c.from_user.id != USER_ID:
        return await c.message.answer(t("uz","only_you"))
    lang = c.data.split(":")[1]
    PREFS.setdefault(USER_ID, {})["lang"] = lang
    await c.message.answer(t(lang, "choose_tf"), reply_markup=tf_kb(lang))
    await c.answer()

@dp.callback_query(F.data.startswith("tf:"))
async def choose_tf(c: CallbackQuery):
    if c.from_user.id != USER_ID:
        return await c.message.answer(t("uz","only_you"))
    tf = c.data.split(":")[1]
    lang = PREFS.get(USER_ID, {}).get("lang", "uz")
    PREFS[USER_ID]["tf"] = tf
    await c.message.answer(t(lang, "choose_asset"), reply_markup=asset_kb(lang))
    await c.answer()

@dp.callback_query(F.data.startswith("asset:"))
async def choose_asset(c: CallbackQuery):
    if c.from_user.id != USER_ID:
        return await c.message.answer(t("uz","only_you"))
    asset = c.data.split(":")[1]
    lang = PREFS.get(USER_ID, {}).get("lang", "uz")
    tf   = PREFS.get(USER_ID, {}).get("tf", "1d")
    PREFS[USER_ID]["asset"] = asset
    pretty = ASSETS[asset]["name"][lang]
    await c.message.answer(t(lang, "saved", lang=lang.upper(), tf=tf, asset=pretty))
    await send_composed_signal(c.message.chat.id, lang, asset, tf)
    await c.answer()

@dp.message(Command("signal"))
async def manual_signal(message: Message):
    if message.from_user.id != USER_ID:
        return await message.answer(t("uz","only_you"))
    lang = PREFS.get(USER_ID, {}).get("lang", "uz")
    tf   = PREFS.get(USER_ID, {}).get("tf", "1d")
    asset= PREFS.get(USER_ID, {}).get("asset", "XAUUSD")
    await send_composed_signal(message.chat.id, lang, asset, tf)

@dp.message(Command("now"))
async def now_cmd(message: Message):
    if message.from_user.id != USER_ID:
        return await message.answer(t("uz","only_you"))
    lang = PREFS.get(USER_ID, {}).get("lang", "uz")
    tf   = PREFS.get(USER_ID, {}).get("tf", "1d")
    asset= PREFS.get(USER_ID, {}).get("asset", "XAUUSD")
    await send_composed_signal(message.chat.id, lang, asset, tf)

# ================== HTTP SERVER (Render uchun) ==================
app = FastAPI()

@app.get("/")
def root():
    prefs = PREFS.get(USER_ID, {"lang":"uz","tf":"1d","asset":"XAUUSD"})
    return {"ok": True, "tz": TZ_NAME, "schedules": [SCHEDULE_1, SCHEDULE_2], "prefs": prefs}

@app.get("/healthz")
def healthz():
    return {"ok": True}

async def run_http():
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

# ================== ENTRYPOINT ==================
async def main():
    asyncio.create_task(run_http())   # Web Service bo'lsa port band bo'ladi
    asyncio.create_task(scheduler())  # ixtiyoriy avtomatik signal
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
