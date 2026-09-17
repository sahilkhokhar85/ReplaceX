
import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Temporary storage for users waiting to send an image
pending_replacements = {}


def extract_post_link(text):
    if not text:
        return None

    match = re.search(
        r"https?://t\.me/(?:c/)?[\w\d_+/.-]+",
        text
    )

    return match.group(0) if match else None


def extract_message_id(link):
    if not link:
        return None

    match = re.search(r"/(\d+)$", link)

    return int(match.group(1)) if match else None


@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "👋 Welcome to Image Replace Bot!\n\n"
        "Use /replace postlink to replace an image."
    )


@dp.message(Command("replace"))
async def replace_command(message: Message):
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "❌ Please provide a channel post link.\n\n"
            "Example:\n"
            "/replace https://t.me/c/1234567890/456"
        )
        return

    post_link = args[1].strip()
    message_id = extract_message_id(post_link)

    if not message_id:
        await message.answer("❌ Invalid channel post link.")
        return

    # If command is a reply to an image
    if message.reply_to_message:
        replied = message.reply_to_message

        if replied.photo:
            await replace_image(
                message,
                message_id,
                replied.photo[-1].file_id
            )
            return

        await message.answer("❌ Reply message must contain an image.")
        return

    # Without reply: ask user to send image
    pending_replacements[message.from_user.id] = {
        "message_id": message_id
    }

    await message.answer(
        "📸 Please send the new image.\n\n"
        "Caption will remain unchanged."
    )


@dp.message(F.photo)
async def image_handler(message: Message):
    user_id = message.from_user.id

    if user_id not in pending_replacements:
        return

    data = pending_replacements.pop(user_id)

    await replace_image(
        message,
        data["message_id"],
        message.photo[-1].file_id
    )


async def replace_image(
    message: Message,
    message_id: int,
    new_file_id: str
):
    try:
        await bot.edit_message_media(
            chat_id=CHANNEL_ID,
            message_id=message_id,
            media={
                "type": "photo",
                "media": new_file_id
            }
        )

        await message.answer(
            "✅ Image replaced successfully!\n"
            "Caption preserved."
        )

    except Exception as e:
        logging.exception("Replacement failed")

        await message.answer(
            "❌ Failed to replace image.\n\n"
            f"Error: {e}"
        )


async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN missing")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
