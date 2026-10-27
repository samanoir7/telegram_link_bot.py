"""
Telegram Link Formatter Bot (Uzbek, batched)
---------------------------------------------
Botga link(lar) yuborasiz (bitta yoki bir nechta xabar ichida, ketma-ket
tez yuborilsa ham), u 2 soniya kutadi — shu vaqt ichida kelgan BARCHA
linklarni bitta ro'yxatga yig'ib, keyin ularni "1-qism", "2-qism" ...
tartibida, har biri alohida paragraf va bosiladigan (clickable) link
qilib, bitta xabar sifatida qaytaradi.

Bu sizning avvalgi muammoingizni hal qiladi: ko'p link yuborilganda
Telegram xabarni ikkiga bo'lib yuborsa ham (yoki siz linklarni bir necha
marta ketma-ket joylashtirsangiz ham), bot ularni bitta davomli ro'yxat
sifatida ko'radi va raqamlashni 1 dan boshlamay, davom ettiradi.

O'RNATISH
1. Kutubxona:  pip install python-telegram-bot --upgrade
2. TOKEN qatoriga BotFather'dan olgan tokeningizni yozing
   (yoki TELEGRAM_BOT_TOKEN muhit o'zgaruvchisini o'rnating).
3. Ishga tushirish:  python telegram_link_bot.py
4. Telegram'da botga linklarni yuboring (bitta xabarda bir nechtasi,
   yoki ketma-ket bir necha xabar qilib) — 2 soniyadan keyin bot
   hammasini birlashtirib, raqamlab javob beradi.
"""

import os
import re
import html
import asyncio

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

# ── Sozlamalar ───────────────────────────────────────────────────
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8821098317:AAGjGMc_JtubhfXYqtb7t17dKinQz9XHb5A")

# Yangi link kelganda, shuncha soniya kutib turadi, shu vaqt ichida
# kelgan boshqa xabarlardagi linklarni ham shu ro'yxatga qo'shadi.
BATCH_DELAY_SECONDS = 2.0

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

# Har bir chat (foydalanuvchi) uchun: yig'ilayotgan linklar va
# navbatdagi "yuborish" vazifasi shu yerda saqlanadi.
# { chat_id: {"links": [...], "task": asyncio.Task | None} }
pending: dict[int, dict] = {}


def extract_links(text: str) -> list[str]:
    """Matndan (har qatordan bittadan) linklarni ajratib oladi."""
    links = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = URL_PATTERN.search(line)
        if match:
            links.append(match.group(0))
    return links


def build_message(links: list[str]) -> str:
    """Linklar ro'yxatidan HTML formatdagi, bosiladigan, paragraflarga
    bo'lingan '1-qism / 2-qism ...' xabarini yasaydi."""
    blocks = []
    for i, link in enumerate(links, start=1):
        safe_link = html.escape(link, quote=True)
        blocks.append(f'<a href="{safe_link}">{i}-qism</a>')
    # Har biri orasida bo'sh qator — alohida paragraf bo'lib ko'rinadi,
    # shunda ketma-ket linklarni bosganda adashib ketish qiyinroq bo'ladi.
    return "\n\n".join(blocks)


async def flush_after_delay(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """BATCH_DELAY_SECONDS kutadi; shu vaqtda yangi link kelmasa,
    yig'ilgan hamma linkni bitta xabar qilib yuboradi."""
    try:
        await asyncio.sleep(BATCH_DELAY_SECONDS)
    except asyncio.CancelledError:
        # Yangi link keldi va kutish vaqti qaytadan boshlandi — chiqib ketamiz.
        return

    state = pending.pop(chat_id, None)
    if not state or not state["links"]:
        return

    message = build_message(state["links"])
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    links = extract_links(text)

    if not links:
        await update.message.reply_text(
            "Linklarni topa olmadim. Har bir linkni alohida qatorga yozib yuboring."
        )
        return

    chat_id = update.effective_chat.id
    state = pending.setdefault(chat_id, {"links": [], "task": None})

    # Yangi kelgan linklarni mavjud ro'yxatga qo'shamiz.
    state["links"].extend(links)

    # Avvalgi kutish vazifasi bor bo'lsa, bekor qilamiz — vaqt qaytadan boshlanadi.
    if state["task"] is not None:
        state["task"].cancel()

    state["task"] = asyncio.create_task(flush_after_delay(chat_id, context))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Linklaringizni yuboring (bittadan yoki bir nechtasini ketma-ket) — "
        f"men {int(BATCH_DELAY_SECONDS)} soniya kutib, hammasini yig'ib, "
        "1-qism, 2-qism ... tartibida, bosiladigan qilib qaytaraman."
    )


def main() -> None:
    if TOKEN == "8821098317:AAGjGMc_JtubhfXYqtb7t17dKinQz9XHb5A":
        raise SystemExit(
            "Avval tokeningizni kiriting: shu faylda TOKEN qatorini tahrirlang, "
            "yoki TELEGRAM_BOT_TOKEN muhit o'zgaruvchisini o'rnating."
        )

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot ishlayapti. To'xtatish uchun Ctrl+C bosing.")
    app.run_polling()


if __name__ == "__main__":
    main()
