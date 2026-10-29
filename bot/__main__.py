import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .ai import Consultant
from .catalog import Catalog
from .config import load_config
from .db import Database
from .handlers import setup_routers


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config = load_config()
    catalog = Catalog()
    db = Database(config.db_path)
    await db.init()
    ai = Consultant(config.anthropic_api_key, config.claude_model, catalog)
    if not ai.enabled:
        logging.warning("ANTHROPIC_API_KEY не задан — ИИ-ответы выключены, работают только кнопки")

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(config=config, catalog=catalog, db=db, ai=ai)
    dp.include_router(setup_routers())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
