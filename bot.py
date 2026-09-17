
import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InputMediaPhoto
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Users waiting to send a new image
pending_replacements = {}


def extract_post_link(text):
    if not text:
        return None

    match = re.search(
        r"https?://t\.me/(?:c/)?[\w\d_+/.-]+",
        text
    )

    return match.group(0) if match else None


def extract_chat_id_and_message_id(link):
    if not link:
        return None, None

    # Private channel link:
    # https://t.me/c/1234567890/456
    match = re.search(
        r"t\.me/c/(\d+)/(\d+)",
        link
    )

    if match:
        channel_id = int("-100" + match.group(1))
        message_id = int(match.group(2))

        return channel_id, message_id

    # Public channel link:
    # https://t.me/channelname/456
    match = re.search(
        r"t\.me/([A-Za-z0-9_]+)/(\d+)",
        link
    )

    if match:
        username = "@" + match.group(1)
        message_id = int(match.group(2))

        return username, message_id

    return None, None


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

    post_link = extract_post_link(args[1].strip())

    if not post_link:
        await message.answer("❌ Invalid channel post link.")
        return

    chat_id, message_id = extract_chat_id_and_message_id(
        post_link
    )

    if chat_id is None or message_id is None:
        await message.answer("❌ Invalid channel post link.")
        return

    # If command is sent as a reply to an image
    if message.reply_to_message:

        replied = message.reply_to_message

        if replied.photo:

            await replace_image(
                message,
                chat_id,
                message_id,
                replied.photo[-1].file_id
            )

            return

        await message.answer(
            "❌ Reply message must contain an image."
        )

        return

    # Without reply: wait for new image
    pending_replacements[message.from_user.id] = {
        "chat_id": chat_id,
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
        data["chat_id"],
        data["message_id"],
        message.photo[-1].file_id
    )


async def replace_image(
    message: Message,
    chat_id,
    message_id: int,
    new_file_id: str
):
    try:

        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(
                media=new_file_id
            )
        )

        await message.answer(
            "✅ Image replaced successfully!"
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
