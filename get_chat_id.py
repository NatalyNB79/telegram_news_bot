import asyncio
from telegram import Bot
from config import TELEGRAM_TOKEN

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    chat = await bot.get_chat("@my_news_temp_channel")  # замени на имя твоего канала
    print(f"Chat ID: {chat.id}")

if __name__ == "__main__":
    asyncio.run(main())
