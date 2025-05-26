import json
import time
import urllib.parse
import os
from curl_cffi import requests
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import MessageTooLong

# Command configuration
config = {
    'name': 'bilivid',
    'description': 'Get video information or download links from Bilibili.tv',
    'usage': '/bilivid <bilibili_video_url>',
    'role': 'user',
    'cooldowns': 20,
    'usePrefix': True,
    'aliases': ['bili', 'bilibili'],
    'author': 'MICRON',
}

async def run(client: Client, message: Message, args, history, logger):
    # Check if URL is provided
    if not args:
        await message.reply(
            "📺 **Bilibili Video Downloader**\n\n"
            "Please provide a Bilibili video URL.\n"
            "**Usage:** `/bilivid <bilibili_video_url>`\n\n"
            "**Example:** `/bilivid https://www.bilibili.tv/en/video/1234567890`"
        )
        return
    
    # Get the video URL from arguments
    video_url = ' '.join(args)
    
    # Send a processing message
    processing_msg = await message.reply("🔄 Processing your Bilibili video request...")
    
    try:
        # Process the video URL and get response
        result = await process_bilibili_video(video_url, logger)
        
        if result["success"]:
            # Check if the response text is too long for a single message
            if len(result["data_text"]) > 4000:
                # Create a JSON file to send
                file_path = f"bilibili_{message.from_user.id}_{int(time.time())}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result["data"], f, indent=2, ensure_ascii=False)
                
                # Send the file
                await message.reply_document(
                    document=file_path,
                    caption=f"📁 Here's the video information for your Bilibili link.\n\nURL: `{video_url}`"
                )
                
                # Delete the file after sending
                try:
                    os.remove(file_path)
                except:
                    logger.error(f"Could not delete temporary file: {file_path}")
            else:
                # Send as text message
                await message.reply(
                    f"📺 **Bilibili Video Info**\n\n"
                    f"```json\n{result['data_text']}```"
                )
                
            # Include a direct message with video links if available
            if result["direct_links"]:
                links_text = "\n".join([f"• Quality: {link['quality']} - [Download]({link['url']})" for link in result["direct_links"]])
                await message.reply(
                    f"🎬 **Download Links**\n\n{links_text}\n\n"
                    f"Note: Links may expire after some time."
                )
        else:
            # If there was an error
            await message.reply(f"❌ **Error**: {result['error']}")
    
    except Exception as e:
        logger.error(f"Error in bilivid command: {str(e)}")
        await message.reply("An error occurred while processing your request. Please try again later.")
    
    finally:
        # Delete the processing message
        try:
            await processing_msg.delete()
        except:
            pass

async def process_bilibili_video(video_url, logger):
    """Process the Bilibili video URL and return the results"""
    try:
        # Encode the URL for the API request
        encoded_url = urllib.parse.quote(video_url)
        api_url = f"https://api.ryzumi.vip/api/downloader/bilibili?url={encoded_url}"
        
        # Set up headers that look like a real browser
        headers = {
            'Host': 'api.ryzumi.vip',
            'Referer': 'https://api.ryzumi.vip/all-features',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1'
        }
        
        # Using curl_cffi to bypass Cloudflare protection
        with requests.Session() as session:
            session.impersonate = "chrome110"
            
            logger.info(f"Attempting to fetch Bilibili video info: {api_url}")
            
            # First visit the main site to establish a session
            session.get('https://api.ryzumi.vip', impersonate="chrome110", timeout=30)
            time.sleep(1)
            
            # Then get the features page
            session.get('https://api.ryzumi.vip/all-features', impersonate="chrome110", timeout=30)
            time.sleep(1)
            
            # Now get the actual video data
            response = session.get(api_url, headers=headers, timeout=30, impersonate="chrome110")
            
            if response.status_code == 200:
                # Try to parse as JSON
                try:
                    data = response.json()
                    data_text = json.dumps(data, indent=2, ensure_ascii=False)
                    
                    # Extract direct video links if available
                    direct_links = []
                    if data.get("status") == True and "data" in data:
                        if "mediaList" in data["data"] and "videoList" in data["data"]["mediaList"]:
                            videos = data["data"]["mediaList"]["videoList"]
                            for video in videos:
                                if "url" in video:
                                    direct_links.append({
                                        "quality": video.get("quality", "Unknown"),
                                        "url": video["url"]
                                    })
                    
                    return {
                        "success": True,
                        "data": data,
                        "data_text": data_text,
                        "direct_links": direct_links
                    }
                except Exception as e:
                    logger.error(f"Error parsing JSON: {str(e)}")
                    return {
                        "success": True,
                        "data": {"raw_text": response.text},
                        "data_text": response.text[:4000] + "..." if len(response.text) > 4000 else response.text,
                        "direct_links": []
                    }
            else:
                return {
                    "success": False,
                    "error": f"API returned status code {response.status_code}",
                    "data": {"error": response.text[:1000]},
                    "data_text": "",
                    "direct_links": []
                }
                
    except Exception as e:
        logger.error(f"Error processing Bilibili video: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to process video: {str(e)}",
            "data": {},
            "data_text": "",
            "direct_links": []
        }
