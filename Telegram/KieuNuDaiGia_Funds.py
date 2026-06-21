"""Telegram Channel Notification Module.

This module provides a lightweight utility to send formatted HTML messages
and user mentions to a specific Telegram channel using the python-telegram-bot 
library.

Attributes:
    TOKEN (str): The Telegram Bot API token generated via @BotFather.
    CHANNEL_ID (int): The unique identifier for the target Telegram channel.
    bot (Bot): The initialized Telegram Bot instance.
"""

import asyncio
from telegram import Bot
from telegram.constants import ParseMode

# --- CONFIGURATION ---
TOKEN = "8557593460:AAHI1Kz2PjNdRgpLdvwyow4YinAzy1D0mQY"
CHANNEL_ID = -1003846912643 # or -100123456789

# Initialize the bot once
bot = Bot(token=TOKEN)

async def send_to_channel(message):
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode=ParseMode.HTML
        )
        print("Message sent successfully!")
    except Exception as e:
        print(f"Error sending message: {e}")

# --- HOW TO USE IT ---
async def main():
    # 1. Simple text
    await send_to_channel("Hello everyone!")

    # 2. Mentioning a user (by ID)
    mention = '<a href="tg://user?id=12345678">NamTV99</a>'
    await send_to_channel(f"Alert! {mention} please check this.")

if __name__ == "__main__":
    asyncio.run(main())