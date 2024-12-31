import cloudscraper
import json
import uuid
import os
from datetime import datetime
from pyrogram.types import Message

config = {
    'name': 'genspark',
    'description': 'Search using Genspark AI and get results as JSON',
    'usage': '/genspark <query>',
    'role': 'user',
    'cooldowns': 10,
    'usePrefix': True,
    'aliases': ['gs', ''],
    'author': 'MICRON'
}

async def display_help_message(message: Message):
    help_text = (
        "🔍 **Genspark Search Help**\n\n"
        "Search using Genspark AI and get results as JSON file\n\n"
        "**Usage:**\n"
        "• `/genspark <query>` - Search anything\n"
        "• `/gs <query>` - Short command\n\n"
        "**Features:**\n"
        "• Returns results as JSON file\n"
        "• Detailed search results\n"
        "• Cloudflare protection bypass\n"
        "• SSE handling\n\n"
        "**Example:**\n"
        "`/genspark how to learn python`\n"
        "`/gs latest AI news`"
    )
    await message.reply(help_text)

async def search_genspark(query, logger):
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            },
            debug=True,
            interpreter='nodejs'
        )
        
        # Add cookies
        cookies = {
            'i18n_set': 'en-US',
            'agree_terms': '0',
            'ARRAffinity': 'd3f3fef388a6525a4ceae0a5626ec531f36e1022c532806c9fc149d4974f9a6b',
            'ARRAffinitySameSite': 'd3f3fef388a6525a4ceae0a5626ec531f36e1022c532806c9fc149d4974f9a6b',
            '_ga': 'GA1.1.1358630954.1735590527',
            'session_id': str(uuid.uuid4())
        }
        scraper.cookies.update(cookies)
        
        # Generate headers
        request_id = str(uuid.uuid4()).replace('-', '')
        trace_id = request_id[:32]
        span_id = request_id[32:48]
        
        headers = {
            'User-Agent': 'PostmanRuntime/7.43.0',
            'Accept': 'text/event-stream',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'request-id': f'|{trace_id}.{span_id}',
            'traceparent': f'00-{trace_id}-{span_id}-01'
        }

        base_url = "https://www.genspark.ai/api/search/stream"
        
        # Initial site visit
        init_response = scraper.get('https://www.genspark.ai/')
        logger(f"Initial visit status code: {init_response.status_code}")
        
        if init_response.status_code != 200:
            error_details = {
                'status_code': init_response.status_code,
                'headers': dict(init_response.headers),
                'body': init_response.text[:500],
                'cookies': dict(scraper.cookies)
            }
            raise Exception(f"Initial visit failed\n```json\n{json.dumps(error_details, indent=2)}\n```")

        # Make search request
        response = scraper.post(
            base_url,
            headers=headers,
            params={"query": query},
            timeout=30
        )
        logger(f"Search request status code: {response.status_code}")
        
        if response.status_code != 200:
            error_details = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response.text[:500],
                'request_headers': headers,
                'cookies': dict(scraper.cookies)
            }
            raise Exception(f"Search request failed\n```json\n{json.dumps(error_details, indent=2)}\n```")
        
        # Process results
        results = []
        for line in response.iter_lines():
            if line:
                try:
                    data = line.decode('utf-8')
                    if data.startswith('data: '):
                        data = data[6:]
                    parsed = json.loads(data)
                    results.append(parsed)
                except json.JSONDecodeError as je:
                    logger(f"Failed to parse line: {data[:100]}...")
                    continue
                except Exception as e:
                    logger(f"Error processing line: {str(e)}")
                    continue
        
        return results

    except Exception as e:
        logger(f"Error in search_genspark: {str(e)}")
        raise

async def run(client, message, args, history, logger):
    try:
        if not args or args[0].lower() == 'help':
            logger("Displaying help message")
            await display_help_message(message)
            return

        query = ' '.join(args)
        logger(f"Processing query: {query}")
        
        status_msg = await message.reply("🔍 Searching...", quote=True)
        logger("Status message sent")

        try:
            results = await search_genspark(query, logger)
            logger(f"Received {len(results)} results")
            
            # Create temp directory with better error handling
            try:
                temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                logger(f"Created temp directory: {temp_dir}")
            except Exception as e:
                raise Exception(f"Failed to create temp directory: {str(e)}\nPath: {temp_dir}")

            # Generate and verify filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(temp_dir, f'genspark_results_{timestamp}.json')
            logger(f"Generated filename: {filename}")
            
            if not os.access(os.path.dirname(filename), os.W_OK):
                raise Exception(f"No write permission for directory: {os.path.dirname(filename)}")

            # Save results with error capture
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger("Results saved successfully")
            except Exception as e:
                raise Exception(f"Failed to save results: {str(e)}\nPath: {filename}")

            # Send file with error details if needed
            try:
                await message.reply_document(
                    document=filename,
                    caption=f"🔍 Search results for: `{query}`\n\nTotal results: {len(results)}",
                    quote=True
                )
                logger("File sent successfully")
            except Exception as e:
                raise Exception(f"Failed to send file: {str(e)}")

            # Cleanup
            try:
                os.remove(filename)
                await status_msg.delete()
            except Exception as e:
                logger(f"Cleanup warning: {str(e)}")

        except Exception as e:
            raise Exception(f"Search process failed:\n{str(e)}")

    except Exception as e:
        error_msg = (
            "❌ **Error Details:**\n\n"
            f"Query: `{query}`\n"
            f"Error: ```\n{str(e)}\n```\n\n"
            "📝 **Debug Info:**\n"
            f"• Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"• Environment: `Render`\n"
            "• Status: `Failed`"
        )
        
        if hasattr(logger, 'error'):
            logger.error("Genspark search error", str(e))
        else:
            logger(f"Error in genspark command: {str(e)}")

        if 'status_msg' in locals():
            await status_msg.edit(error_msg)
        else:
            await message.reply(error_msg)

# No need for on_reply as this is a single-query command
