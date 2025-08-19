#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import json
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
from typing import Dict, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# --- HTTP (Render Web Service portini band qilish) ---
from fastapi import FastAPI
import uvicorn

# ================== ENV + DEFAULT ==================
BOT_TOKEN  = os.getenv("BOT_TOKEN", "8273684666:AAHStkIEUBSsCFdhps_yMYfRGEOIP4Q8VHw")
ADMIN_ID   = int(os.getenv("ADMIN_ID", "1370058711"))
TZ_NAME    = os.getenv("TZ", "Asia/Tashkent")
# "eng zo'r" default vaqtlari (UZT):
SCHEDULE_1 = os.getenv("SCHEDULE_1", "12:00")   # London open (UZT)
SCHEDULE_2 = os.getenv("SCHEDULE_2", "18:30")   # NY open (UZT)
PORT       = int(os.getenv("PORT", "8000"))

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN yo‘q (ENV yoki default)")
TZ = ZoneInfo(TZ_NAME)

# ================== TELEGRAM ==================
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

# ================== FAYLLAR ==================
USERS_FILE = "allowed_users.json"   # set of user_ids
LANG_FILE  = "user_lang.json"       # {uid: "uz/ru/en"}
PREFS_FILE = "user_prefs.json"      # {uid: {"asset": "...", "tf": "..."}}
SUBS_FILE  = "subs.json"            # {uid: true/false}

def load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path: str, data):
    with open(path, "w") as f:
        json.dump(data, f)

# Python set() JSONga moslash
ALLOWED_USERS = set(load_json(USERS_FILE, []))
USER_LANG: Dict[str, str]   = load_json(LANG_FILE, {})
USER_PREFS: Dict[str, Dict] = load_json(PREFS_FILE, {})
SUBS: Dict[str, bool]       = load_json(SUBS_FILE, {})

def is_allowed(uid: int) -> bool:
    return uid in ALLOWED_USERS or uid == ADMIN_ID

# ================== LOKALIZATSIYA ==================
TEXTS = {
    "uz": {
        "no_access": "⛔ Sizga hali ruxsat berilmagan. Admin bilan bog‘laning.",
        "welcome": "✅ Xush kelibsiz! Sizga ruxsat berilgan.",
        "lang_choose": "🇺🇿 Tilni tanlang:",
        "choose_asset": "📊 Qaysi aktiv uchun signal kerak?",
        "choose_tf": "⏱ Qaysi timeframe?",
        "saved": "✅ Saqlandi.",
        "sub_on": "✅ Avtomatik signalga yozildingiz.",
        "sub_off": "🛑 Avtomatik signaldan chiqdingiz.",
        "need_profile": "ℹ️ Avval /set orqali aktiv va timeframe tanlang.",
        "profile": "👤 Profil: til={lang}, aktiv={asset}, tf={tf}, obuna={sub}",
        "start_info": "✅ Bot ishga tushdi. /signal — qo‘lda, /set — profil, /subscribe — obuna, /unsubscribe — bekor qilish.",
        "best_times": "⏰ Avto-signal UZT bo‘yicha: {t1} va {t2}",
    },
    "ru": {
        "no_access": "⛔ Вам пока не выдан доступ. Свяжитесь с админом.",
        "welcome": "✅ Добро пожаловать! Доступ выдан.",
        "lang_choose": "🇷🇺 Выберите язык:",
        "choose_asset": "📊 Для какого актива нужен сигнал?",
        "choose_tf": "⏱ Какой таймфрейм?",
        "saved": "✅ Сохранено.",
        "sub_on": "✅ Вы подписались на авто-сигналы.",
        "sub_off": "🛑 Подписка отключена.",
        "need_profile": "ℹ️ Сначала задайте профиль через /set.",
        "profile": "👤 Профиль: lang={lang}, asset={asset}, tf={tf}, sub={sub}",
        "start_info": "✅ Бот запущен. /signal — вручную, /set — профиль, /subscribe — подписка, /unsubscribe — отмена.",
        "best_times": "⏰ Автосигналы по UZT: {t1} и {t2}",
    },
    "en": {
        "no_access": "⛔ You are not allowed yet. Contact admin.",
        "welcome": "✅ Welcome! Access granted.",
        "lang_choose": "🇬🇧 Choose language:",
        "choose_asset": "📊 Which asset do you want a signal for?",
        "choose_tf": "⏱ Which timeframe?",
        "saved": "✅ Saved.",
        "sub_on": "✅ Subscribed to auto-signals.",
        "sub_off": "🛑 Unsubscribed.",
        "need_profile": "ℹ️ Set your profile via /set first.",
        "profile": "👤 Profile: lang={lang}, asset={asset}, tf={tf}, sub={sub}",
        "start_info": "✅ Bot is running. /signal — manual, /set — profile, /subscribe — subscribe, /unsubscribe — cancel.",
        "best_times": "⏰ Auto-signal (UZT): {t1} and {t2}",
    },
}

def lang_of(uid: int) -> str:
    return USER_LANG.get(str(uid), "uz")

def t(uid: int, key: str, **kw) -> str:
    return TEXTS[lang_of(uid)][key].format(**kw)

# ================== SIGNAL BLOKLARI (professional) ==================
def pro_signal_blocks(asset: str, tf: str, lang: str) -> Tuple[str, str]:
    is_swing = tf in ("1d", "4h", "1h")

    if asset == "XAUUSD":  # GOLD
        if is_swing:
            buy_entry = "3356–3360 (H4/D1 yopilish ustida)"
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

    else:  # EURUSD
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

    def head(txt_uz, txt_ru, txt_en):
        return {
            "uz": txt_uz,
            "ru": txt_ru,
            "en": txt_en
        }[lang]

    buy_head  = head("🟢 <b>BUY ssenariy</b>", "🟢 <b>BUY сценарий</b>", "🟢 <b>BUY scenario</b>")
    sell_head = head("🔴 <b>SELL ssenariy</b>", "🔴 <b>SELL сценарий</b>", "🔴 <b>SELL scenario</b>")
    sl_lbl    = head("⛔ SL", "⛔ SL", "⛔ SL")
    tp_lbl    = head("🎯 TP", "🎯 TP", "🎯 TP")

    buy_block  = f"{buy_head}\n• Entry: {buy_entry}\n{sl_lbl}: {buy_sl}\n{tp_lbl}: {'/'.join(buy_tps)}"
    sell_block = f"{sell_head}\n• Entry: {sell_entry}\n{sl_lbl}: {sell_sl}\n{tp_lbl}: {'/'.join(sell_tps)}"
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
        return ("📢 <b>Сегодняшние драйверы</b>\n"
                "• CPI/NFP/FOMC: импульс USD\n"
                "• Индекс DXY и доходности UST → давление на Gold/EUR; мягкие данные поддержат рост\n")
    if lang == "en":
        return ("📢 <b>Today’s drivers</b>\n"
                "• CPI/NFP/FOMC: USD impulse\n"
                "• DXY & UST yields → pressure on Gold/EUR; soft data supports upside\n")
    return ("📢 <b>Bugungi drayverlar</b>\n"
            "• CPI/NFP/FOMC: USD impuls\n"
            "• DXY va AQSh rentabelliklari → Oltin/EUR bosim ostida; yumshoq ma’lumotlar o‘sishni qo‘llaydi\n")

async def send_signal_message(chat_id: int, lang: str, asset: str, tf: str):
    title = {
        "uz": "📊 {asset} — <b>{tf}</b> signal",
        "ru": "📊 {asset} — <b>{tf}</b> сигнал",
        "en": "📊 {asset} — <b>{tf}</b> signal",
    }[lang].format(asset={"XAUUSD":"Gold (XAU/USD)", "EURUSD":"USD (EUR/USD)", "BTCUSD":"BTC (BTC/USD)"}[asset], tf=tf)

    buy_block, sell_block = pro_signal_blocks(asset, tf, lang)
    risk = {
        "uz": "⚖️ <b>Risk boshqaruvi</b>: 0.5–1.0%/bitim; yangiliklarda SL shart.",
        "ru": "⚖️ <b>Риск-менеджмент</b>: 0.5–1.0%/сделку; SL обязателен на новостях.",
        "en": "⚖️ <b>Risk management</b>: 0.5–1.0%/trade; SL mandatory around news.",
    }[lang]
    news_title = {"uz":"📢 Savdoga ta’sir qiladigan yangiliklar","ru":"📢 Новости, влияющие на рынок","en":"📢 Market-moving news"}[lang]
    news_body  = build_news_outlook(lang)
    links      = news_links(asset)

    await bot.send_message(chat_id, f"{title}\n\n{buy_block}\n\n{sell_block}\n\n{risk}")
    await bot.send_message(chat_id, f"{news_title}\n{news_body}\n🔗 {links}")

# ================== SCHEDULER (SUBS uchun) ==================
def parse_hhmm(s: str) -> dtime:
    h, m = map(int, s.strip().split(":"))
    return dtime(h, m, tzinfo=TZ)

def next_run_for(ti: dtime, now: datetime) -> datetime:
    candidate = now.replace(hour=ti.hour, minute=ti.minute, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)

def schedule_times():
    times = []
    if SCHEDULE_1: times.append(parse_hhmm(SCHEDULE_1))
    if SCHEDULE_2 and SCHEDULE_2.strip(): times.append(parse_hhmm(SCHEDULE_2))
    return times

async def broadcast_auto_signals():
    # SUBS = {uid: True/False}
    for uid_str, on in list(SUBS.items()):
        if not on:
            continue
        uid = int(uid_str)
        # Profil bo‘lmasa — default
        prefs = USER_PREFS.get(uid_str, {"asset": "XAUUSD", "tf": "1h"})
        lang  = lang_of(uid)
        try:
            await send_signal_message(uid, lang, prefs["asset"], prefs["tf"])
            await asyncio.sleep(0.2)  # anti-spam
        except Exception as e:
            try:
                await bot.send_message(uid, f"⚠️ Auto-signal xato: {e}")
            except Exception:
                pass

async def scheduler():
    while True:
        now = datetime.now(TZ)
        times = schedule_times()
        if not times:
            await asyncio.sleep(60); continue
        next_run = min(next_run_for(ti, now) for ti in times)
        await asyncio.sleep(max(1, int((next_run - now).total_seconds())))
        await broadcast_auto_signals()
        await asyncio.sleep(1)

# ================== HANDLERS ==================
@dp.message(Command("start"))
async def start_cmd(message: Message):
    uid = message.from_user.id
    # Lang tugmalari
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uzbek", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
    ])
    USER_LANG.setdefault(str(uid), USER_LANG.get(str(uid), "uz"))
    save_json(LANG_FILE, USER_LANG)

    t1, t2 = SCHEDULE_1, SCHEDULE_2
    if is_allowed(uid):
        await message.answer(t(uid, "welcome"))
    else:
        await message.answer(t(uid, "no_access"))
    await message.answer(t(uid, "start_info"))
    await message.answer(t(uid, "best_times", t1=t1, t2=t2))
    await message.answer(t(uid, "lang_choose"), reply_markup=kb)

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(c: CallbackQuery):
    lang = c.data.split("_")[1]
    USER_LANG[str(c.from_user.id)] = lang
    save_json(LANG_FILE, USER_LANG)
    await c.message.answer(f"✅ Language set: {lang.upper()}")
    await c.answer()

# ---- Admin: allow/deny/list
@dp.message(Command("allow"))
async def allow_user(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid = message.text.split(maxsplit=1)
        uid = int(uid)
        ALLOWED_USERS.add(uid)
        save_json(USERS_FILE, list(ALLOWED_USERS))
        await message.answer(f"✅ User {uid} ga ruxsat berildi.")
        try:
            await bot.send_message(uid, "✅ Sizga ruxsat berildi! /set orqali profilni belgilang, so‘ng /subscribe bosing.")
        except:
            pass
    except:
        await message.answer("⚠️ Foydalanish: /allow user_id")

@dp.message(Command("deny"))
async def deny_user(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid = message.text.split(maxsplit=1)
        uid = int(uid)
        if uid in ALLOWED_USERS:
            ALLOWED_USERS.remove(uid)
            save_json(USERS_FILE, list(ALLOWED_USERS))
            SUBS.pop(str(uid), None); save_json(SUBS_FILE, SUBS)
            await message.answer(f"⛔ User {uid} bloklandi va obuna o‘chirildi.")
        else:
            await message.answer("❌ Bunday user ro‘yxatda yo‘q.")
    except:
        await message.answer("⚠️ Foydalanish: /deny user_id")

@dp.message(Command("list"))
async def list_users(message: Message):
    if message.from_user.id != ADMIN_ID: return
    if not ALLOWED_USERS:
        await message.answer("📂 Hali hech kimga ruxsat berilmagan.")
    else:
        users = "\n".join(str(u) for u in sorted(ALLOWED_USERS))
        await message.answer(f"📂 Ruxsat berilgan userlar:\n{users}")

# ---- /set: aktiv va timeframe tanlash
@dp.message(Command("set"))
async def set_profile(message: Message):
    uid = message.from_user.id
    if not is_allowed(uid): return await message.answer(t(uid, "no_access"))
    # Aktiv tanlash:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟡 GOLD", callback_data="set_asset_XAUUSD")],
        [InlineKeyboardButton(text="💵 USD (EUR/USD)", callback_data="set_asset_EURUSD")],
        [InlineKeyboardButton(text="₿ BTC", callback_data="set_asset_BTCUSD")],
    ])
    await message.answer(t(uid, "choose_asset"), reply_markup=kb)

@dp.callback_query(F.data.startswith("set_asset_"))
async def set_asset(c: CallbackQuery):
    uid = c.from_user.id
    if not is_allowed(uid): return await c.answer("⛔", show_alert=True)
    asset = c.data.split("_")[2]
    prefs = USER_PREFS.get(str(uid), {"asset":"XAUUSD", "tf":"1h"})
    prefs["asset"] = asset
    USER_PREFS[str(uid)] = prefs
    save_json(PREFS_FILE, USER_PREFS)

    # TF tanlash:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1m",  callback_data="set_tf_1m"),
         InlineKeyboardButton(text="5m",  callback_data="set_tf_5m"),
         InlineKeyboardButton(text="15m", callback_data="set_tf_15m")],
        [InlineKeyboardButton(text="1h",  callback_data="set_tf_1h"),
         InlineKeyboardButton(text="4h",  callback_data="set_tf_4h"),
         InlineKeyboardButton(text="1d",  callback_data="set_tf_1d")],
    ])
    await c.message.answer(t(uid, "choose_tf"), reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data.startswith("set_tf_"))
async def set_tf(c: CallbackQuery):
    uid = c.from_user.id
    if not is_allowed(uid): return await c.answer("⛔", show_alert=True)
    tf = c.data.split("_")[2]
    prefs = USER_PREFS.get(str(uid), {"asset":"XAUUSD", "tf":"1h"})
    prefs["tf"] = tf
    USER_PREFS[str(uid)] = prefs
    save_json(PREFS_FILE, USER_PREFS)
    await c.message.answer(t(uid, "saved"))
    await c.answer()

# ---- Subscribe / Unsubscribe / Profile
@dp.message(Command("subscribe"))
async def subscribe_cmd(message: Message):
    uid = message.from_user.id
    if not is_allowed(uid): return await message.answer(t(uid, "no_access"))
    SUBS[str(uid)] = True
    save_json(SUBS_FILE, SUBS)
    await message.answer(t(uid, "sub_on") + "\n" + t(uid, "best_times", t1=SCHEDULE_1, t2=SCHEDULE_2))

@dp.message(Command("unsubscribe")))
async def unsubscribe_cmd(message: Message):
    uid = message.from_user.id
    if not is_allowed(uid): return await message.answer(t(uid, "no_access"))
    SUBS[str(uid)] = False
    save_json(SUBS_FILE, SUBS)
    await message.answer(t(uid, "sub_off"))

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    uid = message.from_user.id
    if not is_allowed(uid): return await message.answer(t(uid, "no_access"))
    prefs = USER_PREFS.get(str(uid), {"asset":"XAUUSD", "tf":"1h"})
    sub = "on✅" if SUBS.get(str(uid)) else "off⛔️"
    await message.answer(t(uid, "profile", lang=lang_of(uid), asset=prefs["asset"], tf=prefs["tf"], sub=sub))

# ---- Manual signal
@dp.message(Command("signal")))
async def signal_cmd(message: Message):
    uid = message.from_user.id
    if not is_allowed(uid): return await message.answer(t(uid, "no_access"))
    prefs = USER_PREFS.get(str(uid))
    if not prefs:
        return await message.answer(t(uid, "need_profile"))
    await send_signal_message(uid, lang_of(uid), prefs["asset"], prefs["tf"])

@dp.message(Command("now")))
async def now_cmd(message: Message):
    uid = message.from_user.id
    if not is_allowed(uid): return await message.answer(t(uid, "no_access"))
    prefs = USER_PREFS.get(str(uid), {"asset":"XAUUSD", "tf":"1h"})
    await send_signal_message(uid, lang_of(uid), prefs["asset"], prefs["tf"])

# ================== HTTP (Render uchun) ==================
app = FastAPI()

@app.get("/")
def root():
    return {
        "ok": True,
        "tz": TZ_NAME,
        "schedules": [SCHEDULE_1, SCHEDULE_2],
        "allowed": len(ALLOWED_USERS),
        "subs_on": sum(1 for v in SUBS.values() if v),
    }

@app.get("/healthz")
def healthz():
    return {"ok": True}

async def run_http():
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

# ================== ENTRYPOINT ==================
async def main():
    # HTTP server (Render Web Service uchun)
    asyncio.create_task(run_http())
    # Avto-signal scheduler
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
