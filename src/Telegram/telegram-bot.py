import asyncio
import os
import telegram

# Replace with your actual token and chat ID
TOKEN = os.getenv("TELE_CHERRYBOT_TOKEN", "")
CHAT_ID = os.getenv("TELE_CHERRYBOT_CHATID", "")
MESSAGE = "Hello from the python-telegram-bot library!"

async def send_message():
    bot = telegram.Bot(TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=MESSAGE)

if __name__ == '__main__':
    asyncio.run(send_message())