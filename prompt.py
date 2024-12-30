# commands/prompt.py

import os
import aiohttp
import asyncio
import base64
import json
from pathlib import Path
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ParseMode

# Command configuration
config = {
    'name': 'prompt',
    'description': 'Generate a text prompt from an image.',
    'usage': '/prompt (reply to an image)',
    'role': 'user',
    'cooldowns': 20,
    'usePrefix': True,
    'aliases': [],
    'author': 'Micron',
}

# Directory for temporary files
TEMP_DIR = Path(__file__).parent.parent / 'tmp'
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Utility function to generate a random string
def generate_random_string(length):
    import random
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.choice(chars) for _ in range(length))

# Main function to run the command
async def run(client: Client, message: Message, args, **kwargs):
    # Check if the message is a reply to a photo or image document
    if message.reply_to_message and (
        message.reply_to_message.photo or 
        (message.reply_to_message.document and message.reply_to_message.document.mime_type.startswith("image/"))
    ):
        # Send a processing message to inform the user
        processing_message = await message.reply("__Processing your image to generate a prompt...__")

        # Extract the file ID from the replied message
        photo_data = message.reply_to_message.photo if message.reply_to_message.photo else message.reply_to_message.document

        # Download the image
        try:
            file_path = await download_image(client, photo_data)
        except Exception as error:
            print(f"Error downloading image: {error}")
            await message.reply("Failed to download the image. Please try again.")
            await processing_message.delete()
            return

        # Upload the image to Telegraph to get a public URL
        telegraph_url = await upload_image_to_telegraph(file_path)
        os.remove(file_path)

        if not telegraph_url:
            await message.reply("Failed to upload the image to Telegraph. Please try again later.")
            await processing_message.delete()
            return

        # Send the image URL to cococlip.ai to get the UID
        uid = await get_cococlip_uid(telegraph_url)

        if not uid:
            await message.reply("Failed to process the image with Cococlip.ai. Please try again later.")
            await processing_message.delete()
            return

        # Wait for 10 seconds to allow Cococlip.ai to process the image
        await asyncio.sleep(10)

        # Poll Cococlip.ai to get the generated prompt
        prompt = await get_cococlip_prompt(uid)

        if prompt:
            # Send the prompt back to the user
            await message.reply(f"`{prompt}`", parse_mode=ParseMode.MARKDOWN, reply_to_message_id=message.reply_to_message.id)
        else:
            await message.reply("Failed to retrieve the prompt from Cococlip.ai. Please try again later.")

        # Delete the processing message
        await processing_message.delete()

    else:
        # If the command is not a reply to an image, inform the user
        await message.reply("Please reply to an image with the /prompt command to generate a text prompt.")

# Helper function to download an image from Telegram
async def download_image(client, file_data):
    try:
        file_path = TEMP_DIR / f"{file_data.file_id}.jpg"
        downloaded_file = await client.download_media(file_data, file_name=file_path)
        return downloaded_file
    except Exception as e:
        print(f"Error downloading image: {e}")
        raise

# Helper function to upload an image to Telegraph
async def upload_image_to_telegraph(img_file):
    try:
        file_ext = Path(img_file).suffix
        filename = f"{generate_random_string(10)}{file_ext}"

        with open(img_file, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        payload = {
            "image": base64_image,
            "filename": filename
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://akaiapi.onrender.com/telegraph", json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data.get("url")

        return None

    except Exception as error:
        print(f"Error uploading image to Telegraph: {error}")
        return None

# Helper function to get UID from Cococlip.ai
async def get_cococlip_uid(image_url):
    try:
        api_url = f"https://cococlip.ai/api/v1/imagetoprompt/imageclip?image={image_url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data.get("id")

        return None

    except Exception as error:
        print(f"Error getting UID from Cococlip.ai: {error}")
        return None

# Helper function to poll Cococlip.ai for the prompt
async def get_cococlip_prompt(uid):
    try:
        poll_url = f"https://cococlip.ai/api/v1/imagetoprompt/imageclippoll?promptId={uid}"
        async with aiohttp.ClientSession() as session:
            async with session.get(poll_url) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data.get("prompt")

        return None

    except Exception as error:
        print(f"Error polling Cococlip.ai for prompt: {error}")
        return None
