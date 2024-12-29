from pyrogram.types import Message
from pyrogram.errors import RPCError
import asyncio
import re

# Initialize global variables
bot = None
user = None

config = {
    'name': 'info',
    'description': 'Get user information using SangMata bot',
    'usage': '/info <user_id/username> or reply to message',
    'role': 'user',
    'cooldowns': 30,
    'usePrefix': True,
    'aliases': ['userinfo'],
    'author': 'Micron'
}

def init(clients):
    global bot, user
    bot = clients['bot']
    user = clients['user']

async def find_response(user_client, chat_id: str, query_id: str, after_message_id: int, timeout: int = 20):
    end_time = asyncio.get_event_loop().time() + timeout
    
    while asyncio.get_event_loop().time() < end_time:
        try:
            async for message in user_client.get_chat_history(chat_id, limit=10):
                if message.id <= after_message_id:
                    continue
                    
                if message.text and "History for" in message.text and query_id in message.text:
                    return message.text
                    
        except Exception as e:
            print(f"Error in history search: {str(e)}")
            
        await asyncio.sleep(2)
    return None

async def get_user_id(client, message, args):
    try:
        # Case 1: Reply to a message
        if message.reply_to_message:
            return message.reply_to_message.from_user.id
            
        # Case 2: Command arguments provided
        if args:
            user_input = args[0]
            
            # If direct user ID
            if user_input.isdigit():
                return int(user_input)
                
            # If username (remove @ if present)
            if user_input.startswith('@'):
                user_input = user_input[1:]
            
            try:
                user = await client.get_users(user_input)
                return user.id
            except:
                return None
                
        return None
        
    except Exception as e:
        print(f"Error getting user ID: {e}")
        return None

async def process_user(user_client, user_id: int):
    try:
        chat_id = "SangMata_BOT"
        
        # Send query to SangMata bot
        sent_msg = await user_client.send_message(chat_id=chat_id, text=str(user_id))
        
        # Wait for response
        response = await find_response(
            user_client, 
            chat_id, 
            str(user_id), 
            sent_msg.id
        )
        
        if response:
            return response.strip()
        else:
            return f"❌ No information found for user ID: {user_id}"
            
    except Exception as e:
        print(f"Error processing user {user_id}: {e}")
        return f"❌ Error processing user ID {user_id}: {str(e)}"

async def run(client: Message, message: Message, args, **kwargs):
    global user, bot
    
    try:
        if not user:
            await message.reply("❌ User session is not configured.")
            return

        # Get user ID from various possible inputs
        user_id = await get_user_id(client, message, args)
        
        if not user_id:
            await message.reply(
                "ℹ️ Please send the user ID or username with command, or reply to a message/forwarded message."
            )
            return

        status_msg = await message.reply(f"🔍 Fetching information for user ID: {user_id}")

        try:
            result = await process_user(user, user_id)
            
            # Handle long responses
            if len(result) > 4000:
                chunks = [result[i:i+4000] for i in range(0, len(result), 4000)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await status_msg.edit(chunk)
                    else:
                        await message.reply(chunk)
            else:
                await status_msg.edit(result)

        except Exception as e:
            await status_msg.edit(f"❌ Error occurred: {str(e)}")
            print(f"SangMata error: {e}")

    except Exception as e:
        print(f"Critical error in info command: {e}")
        await message.reply(f"❌ An error occurred: {str(e)}")
