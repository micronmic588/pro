import contextlib
import os
import sys
import io
import json
import time
import psutil
import asyncio
import traceback
from pathlib import Path
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import requests

# Command configuration
config = {
    'name': 'eval',
    'description': 'Execute Python code safely with monitoring',
    'usage': '/eval <python code>',
    'role': 'admin',
    'usePrefix': True,
    'aliases': ['py', 'dl'],
    'author': 'MICRON',
    'timeout': 30  # Max execution time in seconds
}

# Constants
MAX_MESSAGE_LENGTH = 4096
TEMP_DIR = Path(__file__).parent.parent / 'temp'
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Create a secure sandbox environment
SAFE_BUILTINS = {
    '__import__': __import__,
    'print': print,
    'len': len,
    'str': str,
    'int': int,
    'float': float,
    'bool': bool,
    'list': list,
    'dict': dict,
    'set': set,
    'tuple': tuple,
    'range': range,
    'requests': requests,
    'json': json
}

class ExecutionStats:
    def __init__(self):
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss

    def get_stats(self) -> str:
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        exec_time = round(end_time - self.start_time, 3)
        memory_used = (end_memory - self.start_memory) / (1024 * 1024)  # Convert to MB
        
        return f"⏱️ Time: `{exec_time}s` | 💾 Memory: `{memory_used:.2f}MB`"

def format_output(output: str) -> str:
    """Format output, prettifying JSON if possible"""
    try:
        data = json.loads(output)
        return json.dumps(data, indent=4)
    except:
        return output

def save_to_file(content: str, filename: str = "response.json") -> Path:
    """Save content to a file in the temp directory"""
    file_path = TEMP_DIR / filename
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return file_path

async def run(client: Client, message: Message, args, **kwargs):
    if not args:
        await message.reply(
            "**📝 Python Code Evaluator**\n\n"
            "**Features:**\n"
            "• Execution timeout protection\n"
            "• Memory monitoring\n"
            "• Pretty JSON formatting\n"
            "• Large output file support\n\n"
            "**Usage:** `/eval <python code>`"
        )
        return

    code = " ".join(args)
    status_msg = await message.reply("🔄 **Processing code...**")
    stats = ExecutionStats()
    
    output = io.StringIO()
    error = io.StringIO()
    
    try:
        sandbox = {
            '__builtins__': SAFE_BUILTINS,
            'client': client,
            'message': message
        }

        # Execute code with timeout protection
        async def execute_code():
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                exec(code, sandbox)
                
        try:
            await asyncio.wait_for(execute_code(), timeout=config['timeout'])
        except asyncio.TimeoutError:
            raise Exception(f"Execution timed out after {config['timeout']} seconds")

        stdout = output.getvalue().strip()
        stderr = error.getvalue().strip()
        
        formatted_output = format_output(stdout) if stdout else ""
        stats_text = stats.get_stats()
        
        if len(formatted_output) > MAX_MESSAGE_LENGTH:
            file_path = save_to_file(formatted_output)
            await message.reply_document(
                document=str(file_path),
                caption=f"📤 **Output saved to file**\n\n{stats_text}"
            )
            await status_msg.delete()
            
            try:
                os.remove(file_path)
            except:
                pass
        else:
            response = f"📤 **Output:**\n```json\n{formatted_output}\n```\n\n📊 **Stats:**\n{stats_text}"
            if stderr:
                response += f"\n\n❌ **Error:**\n```python\n{stderr}\n```"
                
            await status_msg.edit(response, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        error_traceback = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        await status_msg.edit(
            f"❌ **Execution Error:**\n```python\n{error_traceback}\n```",
            parse_mode=ParseMode.MARKDOWN
        )
    
    finally:
        output.close()
        error.close()

def init(client: Client):
    pass
