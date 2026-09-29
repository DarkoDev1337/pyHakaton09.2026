import asyncio
import logging
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import router

load_dotenv()

PROXY = os.getenv("TG_PROXY")


async def main():
    logging.basicConfig(level=logging.INFO)
    session = AiohttpSession(proxy=PROXY) if PROXY else None
    bot = Bot(
        token=os.getenv("BOT_TOKEN"),
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())