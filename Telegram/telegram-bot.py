import asyncio
import telegram

# Replace with your actual token and chat ID
TOKEN = "8557593460:AAHI1Kz2PjNdRgpLdvwyow4YinAzy1D0mQY"
CHAT_ID = "974005939"
MESSAGE = "Hello from the python-telegram-bot library!"

async def send_message():
    bot = telegram.Bot(TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=MESSAGE)

if __name__ == '__main__':
    asyncio.run(send_message())