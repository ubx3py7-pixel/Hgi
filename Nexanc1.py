#!/usr/bin/env python3
# Multi-bot GC / Slide / Swipe tool (updated TOKENS & OWNER)
# - Spawns one Application per token and registers command handlers on each.
# - Commands available (same as original): /gcnc, /ncemo, /stopgcnc, /stopall, /delay, /status,
#   /targetslide, /stopslide, /slidespam, /stopslidespam, /swipe, /stopswipe,
#   /addsudo, /delsudo, /listsudo, /myid, /ping, /help
#
# NOTE: These tokens are sensitive. If they are real, revoke/rotate them after testing.

import asyncio
import json
import os
import random
import time
import logging
from typing import Dict
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# ---------------------------
# CONFIG (UPDATED)
# ---------------------------
TOKENS = [
  "8320677399:AAEY9DbiaZlCqq6qEesWs5pGLhLlNwUXQcE",
"8272155257:AAElZnydU_i_S1HnS72JZ_sUCPNfEPm_xik",
"8199166304:AAFB4zwsjib3m0zm9V1bdw0bPucw50nHvq8",
"8511210915:AAEQFdWb-wePkU4z8Fz4_g-lRh-UZrP6syU",
"8275126499:AAGQSqngva9plgmXq4i80p_CkvlLlheIbCU",
]

# Owner / initial sudo (you provided "Chat id 8569174027")
OWNER_ID = 8569174027
SUDO_FILE = "sudo.json"

# ---------------------------
# RAID TEXTS & EMOJIS
# ---------------------------
RAID_TEXTS = [
    "×~🌷GAY🌷×~",
"~×🌼BITCH🌼×~",
"~×🌻LESBIAN🌻×~",
"~×🌺CHAPRI🌺×~",
"~×🌹TMKC🌹×~",
"~×🏵️TMR🏵×~️",
"~×🪷TMKB🪷×~",
"~×💮CHUS💮×~",
"~×🌸HAKLE🌸×~",
"~×🌷GAREEB🌷×~",
"~×🌼RANDY🌼×~",
"~×🌻POOR🌻×~",
"~×🌺TATTI🌺×~",
"~×🌹CHOR🌹×~",
"~×🏵️CHAMAR🏵️×~",
"~×🪷SPERM COLLECTOR🪷×~",
"~×💮CHUTI LULLI💮×~",
"~×🌸KALWA🌸×~",
"~×🌷CHUD🌷×~",
"~×🌼CHUTKHOR🌼×~",
"~×🌻BAUNA🌻×~",
"~×🌺MOTE🌺×~",
"~×🌹GHIN ARHA TUJHSE🌹×~",
"~×🏵️CHI POOR🏵×~️",
"~🪷PANTY CHOR🪷~",
"~×💮LAND CHUS💮×~",
"~×🌸MUH MAI LEGA🌸×~",
"~×🌷GAND MARE 🌷×~",
"~×🌼MOCHI WALE 🌼×~",
"~×🌻GANDMARE 🌻×~",
"~×🌺KIDDE 🌺×~",
"~×🌹LAMO 🌹×~",
"~×🏵️BIHARI 🏵×~️",
"~×🪷MULLE 🪷×~",
"~×💮NAJAYESH LADKE 💮×~",
"~×🌸GULAM 🌸×~",
"~×🌷CHAMCHA🌷×~",
"~×🌼EWW 🌼×~",
"~×🌻CHOTE TATTE 🌻×~",
"~×🌺SEX WORKER 🌺×~",
"~×🌹CHINNAR MA KE LADKE 🌹×~"
]

EMOSPAM_PATTERNS = [
    "[ any text ] C‌‌V‌‌R‌‌ K‌‌A‌‌R‌‌ H‌‌A‌‌K‌‌L‌‌E‌‌-//--🩷" * 40,
    "[ any text ] 🇹 🇪 🇷 🇮  🇲 🇦 🇰 🇦  🇧 🇭 🇴 🇸 🇩 🇦 --🦋" * 40,
    "[ any text ] 𝙏𝙀𝙍𝙄 𝙈𝘼 𝙃𝘼𝘾𝙇𝙄-//--💗" * 40,
    "[ any text ] Cʜᴜᴘ Rᴀɴᴅʏ - 🤍" * 40
]

emospam_tasks: Dict[int, asyncio.Task] = {}


# ---------------------------
# GLOBAL STATE
# ---------------------------
# load or initialize SUDO users
if os.path.exists(SUDO_FILE):
    try:
        with open(SUDO_FILE, "r", encoding="utf-8") as f:
            _loaded = json.load(f)
            SUDO_USERS = set(int(x) for x in _loaded)
    except Exception:
        SUDO_USERS = {OWNER_ID}
else:
    SUDO_USERS = {OWNER_ID}
with open(SUDO_FILE, "w", encoding="utf-8") as f:
    json.dump(list(SUDO_USERS), f)

def save_sudo():
    with open(SUDO_FILE, "w", encoding="utf-8") as f:
        json.dump(list(SUDO_USERS), f)

# Per-chat group tasks: chat_id -> dict[token_key -> task]
group_tasks: Dict[int, Dict[str, asyncio.Task]] = {}
spam_tasks: Dict[int, asyncio.Task] = {}
slide_targets = set()
slidespam_targets = set()
swipe_mode = {}
apps, bots = [], []
delay = 0.01

logging.basicConfig(level=logging.INFO)

# ---------------------------
# DECORATORS
# ---------------------------
def only_sudo(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        uid = update.effective_user.id
        if uid not in SUDO_USERS:
            return await update.message.reply_text("❌𝐒ᴏʀʀʏ 🇧 🇧 🇾  𝐀ᴘ 𝐆ᴀʀʀᴇʙ 𝐇ᴏ.")
        return await func(update, context)
    return wrapper

def only_owner(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        uid = update.effective_user.id
        if uid != OWNER_ID:
            return await update.message.reply_text("❌ DEVA KO ABBU BOL.")
        return await func(update, context)
    return wrapper

# ---------------------------
# BOT LOOP used by gcnc/ncemo
# ---------------------------
async def bot_loop(bot, chat_id, base, mode):
    i = 0
    while True:
        try:
            if mode == "raid":
                text = f"{base} {RAID_TEXTS[i % len(RAID_TEXTS)]}"
            else:
                text = f"{base} {NCEMO_EMOJIS[i % len(NCEMO_EMOJIS)]}"
            await bot.set_chat_title(chat_id, text)
            i += 1
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"[WARN] Bot error in chat {chat_id}: {e}")
            await asyncio.sleep(0.001)

async def spam_loop(update, text):
    chat_id = update.message.chat_id
    i = 0
    while True:
        try:
            spam_pattern = SPAM_PATTERNS[i % len(SPAM_PATTERNS)]
            spam_text = spam_pattern.replace("[ text ]", text).replace("[ Text ]", text).replace("[ any text ]", text)
            await update.message.reply_text(spam_text)
            i += 1
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"[WARN] Spam error in chat {chat_id}: {e}")
            await asyncio.sleep(0.001)

# ---------------------------
# COMMANDS
# ---------------------------
@only_owner
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💗 Welcome to DEVA Bot!\nUse /help to see all commands.")

@only_owner
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ DEVA  MENU ✨\n\n"
        "🎪 Group Decorations:\n"
        "/ncloop <text> - Cycling name decoration\n"
        "/ncemo <text> - Emoji name decoration\n"
        "/stopgcnc - Stop decoration\n"
        "/stopall - Stop all decorations\n"
        "/delay <sec> - Set decoration speed\n"
        "/status - Check active decorations\n\n"
        "💬 Message Decorators:\n"
        "/targetslide (reply) - Target message sliding\n"
        "/stopslide (reply) - Stop target slide\n"
        "/slidespam (reply) - Spam style sliding\n"
        "/stopslidespam (reply) - Stop spam slide\n\n"
        "✨ Special Effects:\n"
        "/swipe <name> - Swipe decoration mode\n"
        "/stopswipe - Stop swipe mode\n"
        "/spamloop <text> - Text pattern loop\n"
        "/stopspam - Stop text loop\n"
        "/emospam <text> - Emoji spam decorator\n"
        "/stopemospam - Stop emoji decorator\n\n"
        "👑 Admin:\n"
        "/addsudo (reply) - Add follower\n"
        "/delsudo (reply) - Remove follower\n"
        "/listsudo - List followers\n\n"
        "🛠 Info:\n/myid - Your ID\n/ping - Test speed"
    )

@only_owner
async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    end_time = time.time()
    latency = int((end_time - start_time) * 1000)
    await msg.edit_text(f"🏓 Pong! ✅ {latency} ms")

@only_owner
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Your ID: {update.effective_user.id}")

# --- GC Loops ---
@only_owner
async def gcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /gcnc <text>")
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = getattr(bot, "token", str(id(bot)))
        if key not in group_tasks[chat_id]:
            task = asyncio.create_task(bot_loop(bot, chat_id, base, "raid"))
            group_tasks[chat_id][key] = task
    await update.message.reply_text("🔄चुदाई suru hua.")

@only_owner
async def ncemo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("⚠️ Usage: /ncemo <text>")
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        key = getattr(bot, "token", str(id(bot)))
        if key not in group_tasks[chat_id]:
            task = asyncio.create_task(bot_loop(bot, chat_id, base, "emoji"))
            group_tasks[chat_id][key] = task
    await update.message.reply_text("🔄 Emoji loop started with all bots.")

@only_owner
async def stopgcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        for task in group_tasks[chat_id].values():
            task.cancel()
        group_tasks[chat_id] = {}
        await update.message.reply_text("⏹ Loop stopped in this GC.")

@only_owner
async def stopall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for chat_id in list(group_tasks.keys()):
        for task in group_tasks[chat_id].values():
            task.cancel()
        group_tasks[chat_id] = {}
    await update.message.reply_text("⏹ All loops stopped.")

@only_owner
async def delay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global delay
    if not context.args: return await update.message.reply_text(f"⏱ Current delay: {delay}s")
    try:
        delay = float(context.args[0])
        await update.message.reply_text(f"✅ Delay set to {delay}s")
    except: await update.message.reply_text("⚠️ Invalid number.")

@only_owner
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📊 Active Loops:\n"
    for chat_id, tasks in group_tasks.items():
        msg += f"Chat {chat_id}: {len(tasks)} bots running\n"
    await update.message.reply_text(msg)

# --- SUDO ---
@only_owner
async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
        SUDO_USERS.add(uid); save_sudo()
        await update.message.reply_text(f"✅ {uid} added as sudo.")

@only_owner
async def delsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
        if uid in SUDO_USERS:
            SUDO_USERS.remove(uid); save_sudo()
            await update.message.reply_text(f"🗑 {uid} removed from sudo.")

@only_owner
async def listsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 SUDO USERS:\n" + "\n".join(map(str, SUDO_USERS)))

# --- Slide / Spam / Swipe ---
@only_owner
async def targetslide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        slide_targets.add(update.message.reply_to_message.from_user.id)
        await update.message.reply_text("🎯 Target slide added.")

@only_owner
async def stopslide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
        slide_targets.discard(uid)
        await update.message.reply_text("🛑 Target slide stopped.")

@only_owner
async def slidespam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        slidespam_targets.add(update.message.reply_to_message.from_user.id)
        await update.message.reply_text("💥 Slide spam started.")

@only_owner
async def stopslidespam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        slidespam_targets.discard(update.message.reply_to_message.from_user.id)
        await update.message.reply_text("🛑 Slide spam stopped.")

@only_owner
async def swipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("⚠️ Usage: /swipe <name>")
    swipe_mode[update.message.chat_id] = " ".join(context.args)
    await update.message.reply_text(f"⚡ Swipe mode ON with name: {swipe_mode[update.message.chat_id]}")

@only_owner
async def stopswipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    swipe_mode.pop(update.message.chat_id, None)
    await update.message.reply_text("🛑 Swipe mode stopped.")

# --- Nonstop Spam ---
@only_owner
async def spamloop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /spamloop <text>")
    text = " ".join(context.args)
    chat_id = update.message.chat_id
    if chat_id in spam_tasks:
        spam_tasks[chat_id].cancel()
    task = asyncio.create_task(spam_loop(update, text))
    spam_tasks[chat_id] = task
    await update.message.reply_text("🔄 चुदाई suru hua spam loop.")

@only_owner
async def stopspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in spam_tasks:
        spam_tasks[chat_id].cancel()
        spam_tasks.pop(chat_id)
        await update.message.reply_text("🛑 Spam stopped.")
    else:
        await update.message.reply_text("❌ No spam running.")

async def emospam_loop(update, text):
    chat_id = update.message.chat_id
    i = 0
    while True:
        try:
            pattern = EMOSPAM_PATTERNS[i % len(EMOSPAM_PATTERNS)]
            emo_text = pattern.replace("[ any text ]", text).replace("[ text ]", text).replace("[ Text ]", text)
            await update.message.reply_text(emo_text)
            i += 1
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"[WARN] Emospam error in chat {chat_id}: {e}")
            await asyncio.sleep(0.001)

@only_owner
async def emospam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /emospam <text>")
    text = " ".join(context.args)
    chat_id = update.message.chat_id
    if chat_id in emospam_tasks:
        emospam_tasks[chat_id].cancel()
    task = asyncio.create_task(emospam_loop(update, text))
    emospam_tasks[chat_id] = task
    await update.message.reply_text("🎯 Emoji spam started!")

@only_owner
async def stopemospam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in emospam_tasks:
        emospam_tasks[chat_id].cancel()
        emospam_tasks.pop(chat_id)
        await update.message.reply_text("🛑 Emoji spam stopped.")
    else:
        await update.message.reply_text("❌ No emoji spam running.")

# --- Auto Replies ---
async def auto_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, chat_id = update.message.from_user.id, update.message.chat_id
    if uid in slide_targets:
        for text in RAID_TEXTS: await update.message.reply_text(text)
    if uid in slidespam_targets:
        for text in RAID_TEXTS: await update.message.reply_text(text)
    if chat_id in swipe_mode:
        for text in RAID_TEXTS: await update.message.reply_text(f"{swipe_mode[chat_id]} {text}")

# ---------------------------
# BUILD APP & RUN
# ---------------------------
def build_app(token):
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("ncloop", gcnc))
    app.add_handler(CommandHandler("ncemo", ncemo))
    app.add_handler(CommandHandler("stopgcnc", stopgcnc))
    app.add_handler(CommandHandler("stopall", stopall))
    app.add_handler(CommandHandler("delay", delay_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("addsudo", addsudo))
    app.add_handler(CommandHandler("delsudo", delsudo))
    app.add_handler(CommandHandler("listsudo", listsudo))
    app.add_handler(CommandHandler("targetslide", targetslide))
    app.add_handler(CommandHandler("stopslide", stopslide))
    app.add_handler(CommandHandler("slidespam", slidespam))
    app.add_handler(CommandHandler("stopslidespam", stopslidespam))
    app.add_handler(CommandHandler("swipe", swipe))
    app.add_handler(CommandHandler("stopswipe", stopswipe))
    app.add_handler(CommandHandler("spamloop", spamloop))
    app.add_handler(CommandHandler("stopspam", stopspam))
    app.add_handler(CommandHandler("emospam", emospam))
    app.add_handler(CommandHandler("stopemospam", stopemospam))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_replies))
    return app

async def run_all_bots():
    global apps, bots
    # deduplicate tokens while preserving order
    seen = set(); unique_tokens = []
    for t in TOKENS:
        if t and t not in seen:
            seen.add(t); unique_tokens.append(t)

    for token in unique_tokens:
        try:
            app = build_app(token)
            apps.append(app)
            # app.bot may not be fully initialized until app.start(); keep reference from app after start
            bots.append(app.bot)
        except Exception as e:
            print("Failed building app:", e)

    # initialize & start apps
    for app in apps:
        try:
            await app.initialize(); await app.start(); await app.updater.start_polling()
        except Exception as e:
            print("Failed starting app:", e)

    print("🚀 DEVA Bot is running (all bots started).")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_all_bots())