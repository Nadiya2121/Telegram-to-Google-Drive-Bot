import os
import io
import time
import json
import asyncio
import requests
import math

# Python 3.12+ এর জন্য ইভেন্ট লুপ ফিক্স
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from aiohttp import web
from pyrogram import Client, filters, idle
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# পরিবেশ ভেরিয়েবল
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PORT = int(os.getenv("PORT", 8080))

# আপনার আসল Koyeb ডোমেইন
BASE_URL = "https://quarrelsome-floris-chatgept-52ae575d.koyeb.app"

DB_FILE = "drives.json"

app = Client("pro_drive_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def humanbytes(size):
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}B"

def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "")
    return tmp[:-2] if tmp else "0s"

# ৫ সেকেন্ড পর পর লাইভ প্রগ্রেস বার আপডেট করার ফাংশন
async def progress_bar(current, total, status_msg, start_time):
    now = time.time()
    diff = now - start_time
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = time_formatter(elapsed_time)
        estimated_total_time = time_formatter(estimated_total_time)

        progress = "[{0}{1}] \n**অগ্রগতি:** {2}%\n".format(
            ''.join(["█" for i in range(math.floor(percentage / 10))]),
            ''.join(["░" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2))

        tmp = progress + "**আকার:** {0} / {1}\n**গতি:** {2}/s\n**বাকি সময়:** {3}\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await status_msg.edit_text(f"⏳ **গুগল ড্রাইভে আপলোড হচ্ছে...**\n\n{tmp}")
        except Exception:
            pass

def load_drives():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_drives(drives):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(drives, f)
    except Exception as e:
        print(f"Error saving drives: {e}")

def get_service(token):
    url = "https://developers.google.com/oauthplayground/refreshAccessToken"
    headers = {"Content-Type": "application/json"}
    payload = {
        "token_uri": "https://oauth2.googleapis.com/token",
        "refresh_token": token
    }
    res = requests.post(url, json=payload, headers=headers)
    data = res.json()
    access_token = data.get("access_token")
    if not access_token:
        raise Exception(f"টোকেন রিফ্রেশ ব্যর্থ: {data}")
    creds = Credentials(token=access_token)
    return build('drive', 'v3', credentials=creds)

# ----------------- বিশ্বমানের নেটফ্লিক্স স্টাইল কাস্টম প্লেয়ার -----------------
routes = web.RouteTableDef()

@routes.get("/")
async def home(request):
    return web.Response(text="🚀 Netflix Style Stream Server is Running!", content_type="text/plain")

@routes.get("/watch")
@routes.get("/watch/")
async def watch_player(request):
    file_id = request.query.get("id")
    if not file_id:
        return web.Response(text="ভিডিও ফাইল পাওয়া যায়নি!", status=400)

    # প্রিমিয়াম Plyr HTML5 প্লেয়ার (Netflix Red Theme + 0% Google UI)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>সিনেমা প্লেয়ার</title>
        <!-- Plyr CSS -->
        <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body, html {{ 
                width: 100%; 
                height: 100%; 
                background-color: #000; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                overflow: hidden;
            }}
            .video-container {{
                width: 100vw;
                height: 100vh;
                max-width: 100%;
                max-height: 100%;
                background: #000;
            }}
            /* নেটফ্লিক্স রেড কালার থিম */
            :root {{
                --plyr-color-main: #E50914;
                --plyr-video-background: #000;
                --plyr-menu-background: rgba(20, 20, 20, 0.95);
                --plyr-menu-color: #fff;
            }}
            .plyr {{
                height: 100%;
                width: 100%;
            }}
        </style>
    </head>
    <body oncontextmenu="return false;">
        <div class="video-container">
            <video id="player" playsinline controls crossorigin>
                <source src="https://drive.google.com/uc?export=download&id={file_id}" type="video/mp4" />
            </video>
        </div>

        <!-- Plyr JS -->
        <script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
        <script>
            const player = new Plyr('#player', {{
                controls: [
                    'play-large', 'play', 'progress', 'current-time', 
                    'duration', 'mute', 'volume', 'settings', 'pip', 'airplay', 'fullscreen'
                ],
                settings: ['speed', 'quality'],
                speed: {{ selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] }},
                seekTime: 10,
                keyboard: {{ focused: true, global: true }},
                tooltips: {{ controls: true, seek: true }}
            }});

            // কিবোর্ড শর্টকাট ও ইন্সপেক্ট বন্ধ করা
            document.onkeydown = function(e) {{
                if (e.keyCode == 123 || (e.ctrlKey && (e.keyCode == 85 || e.keyCode == 83 || e.keyCode == 67))) {{
                    return false;
                }}
            }};
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type="text/html")

# ----------------- টেলিগ্রাম বট হ্যান্ডলার -----------------
@app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(client, message):
    await message.reply(
        "👋 **নেটফ্লিক্স স্টাইল প্রো ক্লাউড বটে স্বাগতম!**\n\n"
        "➕ **জিমেইল যুক্ত করতে:** `/add টোকেন`\n"
        "📊 **ড্রাইভ দেখতে:** `/drives`\n\n"
        "🎬 ভিডিও পাঠালে আমি লাইভ প্রগ্রেস বারসহ ড্রাইভে আপলোড করে আধুনিক প্লেয়ার লিংক দেব!"
    )

@app.on_message(filters.command("add") & filters.user(ADMIN_ID))
async def add_drive(client, message):
    if len(message.command) < 2:
        await message.reply("❌ নিয়ম: `/add আপনার_টোকেন`")
        return
    token = message.command[1].strip()
    status = await message.reply("🔍 জিমেইল ভেরিফাই করা হচ্ছে...")
    try:
        service = get_service(token)
        about = service.about().get(fields="user").execute()
        email = about.get('user', {}).get('emailAddress', 'Google Drive')
        drives = load_drives()
        drives = [d for d in drives if d.get("email") != email]
        drives.append({"email": email, "token": token})
        save_drives(drives)
        await status.edit_text(f"🎉 **সফলভাবে যুক্ত হয়েছে!**\n📧 জিমেইল: `{email}`\nমোট ড্রাইভ: {len(drives)} টি।")
    except Exception as e:
        await status.edit_text(f"❌ সমস্যা: {str(e)}")

@app.on_message(filters.command("drives") & filters.user(ADMIN_ID))
async def list_drives(client, message):
    drives = load_drives()
    if not drives:
        await message.reply("কোনো ড্রাইভ যোগ করা নেই! `/add টোকেন` দিন।")
        return
    text = "📊 **কানেক্ট করা ড্রাইভ সমূহ:**\n\n"
    for idx, d in enumerate(drives):
        text += f"**{idx+1}. {d.get('email')}**\n"
    await message.reply(text)

@app.on_message((filters.video | filters.document) & filters.user(ADMIN_ID))
async def upload_video(client, message):
    drives = load_drives()
    if not drives:
        await message.reply("❌ আগে `/add` দিয়ে ড্রাইভ যোগ করুন!")
        return
        
    start_time = time.time()
    status = await message.reply("⏳ প্রসেসিং শুরু হচ্ছে...")
    file_obj = message.video or message.document
    file_name = file_obj.file_name or "video.mp4"

    try:
        # প্রগ্রেস বারসহ ফাইল ডাউনলোড
        file_path = await message.download(
            progress=progress_bar,
            progress_args=(status, start_time)
        )

        await status.edit_text("⚡ **টেলিগ্রাম থেকে নেওয়া সম্পন্ন! এবার গুগল ড্রাইভে পাঠানো হচ্ছে...**")

        service = get_service(drives[0]["token"])
        media = MediaIoBaseUpload(io.FileIO(file_path, 'rb'), mimetype='video/mp4', resumable=True)
        
        file = service.files().create(body={'name': file_name}, media_body=media, fields='id').execute()
        file_id = file.get('id')
        service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()

        # সার্ভারের লোকাল ফাইল রিমুভ (Koyeb স্টোরেজ ক্লিয়ার রাখা)
        if os.path.exists(file_path):
            os.remove(file_path)

        custom_play_link = f"{BASE_URL}/watch?id={file_id}"
        embed_code = f'<iframe src="{custom_play_link}" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>'

        await status.edit_text(
            f"✅ **ভিডিও সফলভাবে আপলোড সম্পন্ন হয়েছে!**\n\n"
            f"🎬 **১. নেটফ্লিক্স প্রিমিয়াম প্লে লিংক:**\n"
            f"{custom_play_link}\n\n"
            f"🌐 **২. ওয়েবসাইটে ব্যবহারের এম্বেড কোড:**\n"
            f"```{embed_code}```"
        )
    except Exception as e:
        await status.edit_text(f"❌ আপলোডে সমস্যা: {str(e)}")

# ----------------- মেইন রানার -----------------
async def main():
    await app.start()
    web_app = web.Application()
    web_app.add_routes(routes)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🚀 Netflix Stream Server started on port {PORT}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
