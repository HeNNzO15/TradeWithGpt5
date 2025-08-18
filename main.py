#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from datetime import datetime, timedelta, time as dtime
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

# ================== ENV + DEFAULT ==================
# ❗ Siz xohlaganidek token va ID kod ichida default sifatida bor.
#    Agar Render’da ENV berilsa, ENV qiymatlari ustun bo‘ladi.
BOT_TOKEN  = os.getenv("BOT_TOKEN", "8273684666:AAHStkIEUBSsCFdhps_yMYfRGEOIP4Q8VHw")
USER_ID    = int(os.getenv("USER_ID", "1370058711"))
SCHEDULE_1 = os.getenv("SCHEDULE_1", "11:55")   # UZT (London oldidan)
SCHEDULE_2 = os.getenv("SCHEDULE_2", "18:55")   # UZT (NY oldidan)
TZ_NAME    = os.getenv("TZ", "Asia/Tashkent")
PORT       = int(os.getenv("PORT", "8000"))

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN env o‘rnatilmagan va default ham berilmagan")
if USER_ID == 0:
    raise SystemExit("❌ USER_ID env o‘rnatilmagan yoki 0")

TZ = ZoneInfo(TZ_NAME)

# ================== TELEGRAM ==================
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

# ================== SAQLAGICH ==================
# Oddiy RAM xotira (istasa DB ga oson ko‘chadi)
PREFS: Dict[int, Dict[str, str]] = {}  # {user_id: {"lang": "..", "tf": "..", "asset": ".."}}

# ================== LOKALIZATSIYA ==================
L = {
    "uz": {
        "greet": "Salom! Tilni tanlang:",
        "choose_tf": "Qaysi <b>timeframe</b>da savdo qilmoqchisiz?",
        "choose_asset": "Qaysi <b>aktiv</b> uchun signal kerak?",
        "signal_title": "📊 {asset} — <b>{tf}</b> signal",
        "buy_head": "🟢 <b>BUY ssenariy</b>",
        "sell_head": "🔴 <b>SELL ssenariy</b>",
        "sl": "⛔ SL: {sl}",
        "tp": "🎯 TP: {tps}",
        "risk": "⚖️ <b>Risk boshqaruvi</b>: bitim boshiga depozitning 0.5–1.0% dan ko‘p emas. Yangiliklar vaqtida SL shart.",
        "news_title": "📢 Savdoga ta’sir qiladigan yangiliklar",
        "news_body": (
            "• <b>Yuqori ta’sir</b>: CPI, NFP, FOMC, AQSh obligatsiya rentabelligi, DXY\n"
            "• <b>Effekt</b>: kuchli USD → oltin/BTC pasayishi; yumshoq ma’lumotlar → o‘sishi\n"
        ),
        "links": "🔗 Havolalar:\n{links}",
        "saved": "✅ Tanlov saqlandi: til: {lang_code}, timeframe: {tf}, aktiv: {asset}\n👉 /signal — shu profil bo‘yicha signal",
        "only_you": "❌ Bu bot faqat sizga ruxsat etilgan.",
        "start_ok": "✅ Bot ishga tushdi. Avval tilni tanlang.",
        "sched_head": "⏰ Avtomatik jadval (UZT): {sched}",
    },
    "ru": {
        "greet": "Здравствуйте! Выберите язык:",
        "choose_tf": "Какой <b>таймфрейм</b> хотите торговать?",
        "choose_asset": "Для какого <b>актива</b> нужен сигнал?",
        "signal_title": "📊 {asset} — <b>{tf}</b> сигнал",
        "buy_head": "🟢 <b>BUY сценарий</b>",
        "sell_head": "🔴 <b>SELL сценарий</b>",
        "sl": "⛔ SL: {sl}",
        "tp": "🎯 TP: {tps}",
        "risk": "⚖️ <b>Риск-менеджмент</b>: риск 0.5–1.0% на сделку. Во время новостей SL обязателен.",
        "news_title": "📢 Новости, влияющие на торговлю",
        "news_body": (
            "• <b>Высокое влияние</b>: CPI, NFP, FOMC, доходности UST, DXY\n"
            "• <b>Эффект</b>: сильный USD → золото/BTC вниз; мягкие данные → рост\n"
        ),
        "links": "🔗 Ссылки:\n{links}",
        "saved": "✅ Сохранено: язык: {lang_code}, таймфрейм: {tf}, актив: {asset}\n👉 /signal — сигнал по профилю",
        "only_you": "❌ Этот бот доступен только вам.",
        "start_ok": "✅ Бот запущен. Сначала выберите язык.",
        "sched_head": "⏰ Автографик (UZT): {sched}",
    },
    "en": {
        "greet": "Hi! Choose your language:",
        "choose_tf": "Which <b>timeframe</b> do you trade?",
        "choose_asset": "Which <b>asset</b> do you want a signal for?",
        "signal_title": "📊 {asset} — <b>{tf}</b> signal",
        "buy_head": "🟢 <b>BUY scenario</b>",
        "sell_head": "🔴 <b>SELL scenario</b>",
        "sl": "⛔ SL: {sl}",
        "tp": "🎯 TP: {tps}",
        "risk": "⚖️ <b>Risk management</b>: risk 0.5–1.0% per trade. SL is mandatory around news.",
        "news_title": "📢 Market-moving news",
        "news_body": (
            "• <b>High-impact</b>: CPI, NFP, FOMC, UST yields, DXY\n"
            "• <b>Effect</b>: strong USD → Gold/BTC down; soft data → up\n"
        ),
        "links": "🔗 Links:\n{links}",
        "saved": "✅ Saved: lang: {lang_code}, timeframe: {tf}, asset: {asset}\n👉 /signal — get signal with this profile",
        "only_you": "❌ This bot is restricted to you.",
        "start_ok": "✅ Bot is running. Please choose a language.",
        "sched_head": "⏰ Auto schedule (UZT): {sched}",
    },
}

LANG_BTNS = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🇺🇿 Uzbek",  callback_data="lang:uz"),
     InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
     InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")]
])

TF_LIST = ["1m", "5m", "15m", "1h", "4h", "1d"]
def tf_kb(lang: str) -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, tf in enumerate(TF_LIST, 1):
        row.append(InlineKeyboardButton(text=tf, callback_data=f"tf:{tf}"))
        if i % 3 == 0:
            rows.append(row); row = []
    if row: rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

ASSETS = {
    "XAUUSD": {"name": {"uz": "Gold (XAU/USD)", "ru": "Золото (XAU/USD)", "en": "Gold (XAU/USD)"}},
    "EURUSD": {"name": {"uz": "USD (EUR/USD)",  "ru": "USD (EUR/USD)",   "en": "USD (EUR/USD)"}},
    "BTCUSD": {"name": {"uz": "BTC (BTC/USD)",  "ru": "BTC (BTC/USD)",   "en": "BTC (BTC/USD)"}},
}
def asset_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ASSETS["XAUUSD"]["name"][lang], callback_data="asset:XAUUSD")],
        [InlineKeyboardButton(text=ASSETS["EURUSD"]["name"][lang], callback_data="asset:EURUSD")],
        [InlineKeyboardButton(text=ASSETS["BTCUSD"]["name"][lang], callback_data="asset:BTCUSD")],
    ])

def t(lang: str, key: str, **kw) -> str:
    return L.get(lang, L["en"]).get(key, "").format(**kw)

# ================== PROFESSIONAL SIGNALLAR ==================
# Har bir aktiv uchun alohida BUY/SELL, mustaqil SL va bir nechta TP.
def pro_signal_blocks(asset: str, tf: str, lang: str) -> Tuple[str, str]:
    # TF ga qarab minor o‘zgartirishlar kiritamiz (scalping vs swing)
    is_swing = tf in ("1d", "4h", "1h")

    if asset == "XAUUSD":  # GOLD
        if is_swing:
            buy_entry = "3356–3360 (D1/H4 yopilish ustida)"
            buy_sl    = "3338"
            buy_tps   = ["3385", "3410", "3440"]

            sell_entry= "3305 aniq buzilganda"
            sell_sl   = "3320"
            sell_tps  = ["3295", "3275"]
        else:
            buy_entry = "3340–3342 ustida M15/H1 yopilish"
            buy_sl    = "3332"
            buy_tps   = ["3348", "3356", "3368"]

            sell_entry= "3325 pastida M15/H1 yopilish"
            sell_sl   = "3332"
            sell_tps  = ["3315", "3305", "3295"]

    elif asset == "BTCUSD":
        if is_swing:
            buy_entry = "116000–117000"
            buy_sl    = "114000"
            buy_tps   = ["118500", "121000"]

            sell_entry= "115000 ostida mustahkamlanish"
            sell_sl   = "116100"
            sell_tps  = ["113800", "112500"]
        else:
            buy_entry = "116300–116800"
            buy_sl    = "115200"
            buy_tps   = ["117600", "118800"]

            sell_entry= "115500 ostida M15 yopilish"
            sell_sl   = "116100"
            sell_tps  = ["114600", "113800"]

    else:  # EURUSD (USD yo'nalishi)
        if is_swing:
            buy_entry = "1.1000–1.1020"
            buy_sl    = "1.0945"
            buy_tps   = ["1.1060", "1.1100"]

            sell_entry= "1.0985 pastida H1/H4 yopilish"
            sell_sl   = "1.1000"
            sell_tps  = ["1.0965", "1.0945"]
        else:
            buy_entry = "1.1005–1.1015"
            buy_sl    = "1.0990"
            buy_tps   = ["1.1030", "1.1050"]

            sell_entry= "1.0985 ostida M15/H1 yopilish"
            sell_sl   = "1.1000"
            sell_tps  = ["1.0965", "1.0945"]

    buy_block  = f"{t(lang,'buy_head')}\n• Entry: {buy_entry}\n{t(lang,'sl', sl=buy_sl)}\n{t(lang,'tp', tps='/'.join(buy_tps))}"
    sell_block = f"{t(lang,'sell_head')}\n• Entry: {sell_entry}\n{t(lang,'sl', sl=sell_sl)}\n{t(lang,'tp', tps='/'.join(sell_tps))}"
    return buy_block, sell_block

def news_links(asset: str) -> str:
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
    else:
        extras = [
            ("Bitcoin News (CoinDesk)", "https://www.coindesk.com/"),
            ("Crypto Calendar (CoinMarketCal)", "https://coinmarketcal.com/en/"),
        ]
    items = calendars + extras
    return "\n".join([f"• <a href='{u}'>{n}</a>" for (n, u) in items])

def build_news_outlook(lang: str) -> str:
    if lang == "ru":
        return (
            "📢 <b>Сегодняшние ключевые факторы</b>\n"
            "• CPI / NFP / FOMC: импульс USD\n"
            "• DXY и доходности UST → давление на золото и EUR; мягкие данные поддержат рост\n"
        )
    if lang == "en":
        return (
            "📢 <b>Today’s market drivers</b>\n"
            "• CPI / NFP / FOMC: USD impulse\n"
            "• DXY & UST yields → pressure on Gold/EUR; soft data supports upside\n"
        )
    return (
        "📢 <b>Bugungi asosiy drayverlar</b>\n"
        "• CPI / NFP / FOMC: USD impuls beradi\n"
        "• DXY va AQSh rentabelliklari → Oltin/EUR bosim ostida; yumshoq ma’lumotlar o‘sishni qo‘llaydi\n"
    )

async def send_composed_signal(chat_id: int, lang: str, asset: str, tf: str):
    title = t(lang, "signal_title", asset=ASSETS[asset]["name"][lang], tf=tf)
    buy_block, sell_block = pro_signal_blocks(asset, tf, lang)
    risk = t(lang, "risk")
    news_title = t(lang, "news_title")
    news_body  = t(lang, "news_body")
    links      = t(lang, "links", links=news_links(asset))

    await bot.send_message(chat_id, f"{title}\n\n{buy_block}\n\n{sell_block}\n\n{risk}")
    await bot.send_message(chat_id, f"{news_title}\n{news_body}\n{links}")

# ================== SCHEDULER (ixtiyoriy — avtomatik jo‘natish) ==================
def parse_hhmm(s: str) -> dtime:
    h, m = map(int, s.strip().split(":"))
    return dtime(h, m, tzinfo=TZ)

def next_run_for(ti: dtime, now: datetime) -> datetime:
    candidate = now.replace(hour=ti.hour, minute=ti.minute, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)

def current_schedule_times() -> List[dtime]:
    times: List[dtime] = []
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
        # default profil (agar hali tanlanmagan bo'lsa)
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
    await c.message.answer(t(lang, "saved", lang_code=lang.upper(), tf=tf, asset=pretty))
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
    # Web Service bo'lsa port talabini bajarish uchun HTTP serverni ishga tushiramiz
    asyncio.create_task(run_http())
    # Ixtiyoriy: kuniga 2 marta avtomatik signal (SCHEDULE_1/2 asosida)
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
