import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.database import Database
from bot.handlers import BotHandlers
from bot.antiflood import AntiFlood

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE = os.getenv("DATABASE", "chat_social.db")

MODE = os.getenv("MODE", "polling").strip().lower()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/telegram").strip() or "/telegram"
WEBHOOK_LISTEN = os.getenv("WEBHOOK_LISTEN", "0.0.0.0").strip()
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip() or None

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application):
    db = Database(DATABASE)
    await db.init()
    application.bot_data["db"] = db
    application.bot_data["flood"] = AntiFlood()


async def post_shutdown(application):
    db = application.bot_data.get("db")
    if db:
        await db.close()


def main():
    if not TOKEN or TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise SystemExit("BOT_TOKEN не настроен. Создайте .env из .env.example.")

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    h = BotHandlers()
    app.add_handler(CommandHandler(["start", "help"], h.start))
    app.add_handler(CommandHandler("profile", h.profile_command))
    app.add_handler(CommandHandler("stats", h.stats_command))
    app.add_handler(CommandHandler("achievements", h.achievements_command))
    app.add_handler(CommandHandler("mute", h.mute_command))
    app.add_handler(CommandHandler("unmute", h.unmute_command))
    app.add_handler(CommandHandler("warn", h.warn_command))
    app.add_handler(CommandHandler("unwarn", h.unwarn_command))
    app.add_handler(CommandHandler("ban", h.ban_command))
    app.add_handler(CommandHandler("kick", h.kick_command))
    app.add_handler(CommandHandler("addgroup", h.addgroup_command))
    app.add_handler(CommandHandler("removegroup", h.removegroup_command))
    app.add_handler(CommandHandler("groups", h.groups_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, h.text_message))

    if MODE == "webhook":
        if not WEBHOOK_URL:
            raise SystemExit(
                "MODE=webhook, но WEBHOOK_URL не задан.\n"
                "Пример: WEBHOOK_URL=https://your-domain.com/telegram"
            )
        logger.info(
            "Webhook mode: listen=%s:%s path=%s url=%s",
            WEBHOOK_LISTEN, WEBHOOK_PORT, WEBHOOK_PATH, WEBHOOK_URL,
        )
        app.run_webhook(
            listen=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            url_path=WEBHOOK_PATH.lstrip("/"),
            webhook_url=WEBHOOK_URL,
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
    else:
        logger.info("Polling mode")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
