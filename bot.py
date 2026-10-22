import os
import io
import json
import asyncio
import requests
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
PORT = int(os.getenv("PORT", 5244))

# Koyeb-এর নিজস্ব ডোমেইন স্বয়ংক্রিয়ভাবে খুঁজে নেওয়া
BASE_URL = os.getenv("KOYEB_PUBLIC_DOMAIN")
if BASE_URL:
    BASE_URL = f"https://{BASE_URL}"
else:
    BASE_URL = os.getenv("BASE_URL", "https://national-harlie-chatgept-b2123952.koyeb.app/view/Telegram-to-Google-Drive-Bot")

DB_FILE = "drives.json"

app = Client("pro_drive_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

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
        raise Exception(f"গুগল টোকেন রিফ্রেশ ব্যর্থ: {data}")
    creds = Credentials(token=access_token)
    return build('drive', 'v3', credentials=creds)

# ----------------- কাস্টম প্লেয়ার ওয়েব সার্ভার (Aiohttp) -----------------
routes = web.RouteTableDef()

@routes.get("/")
async def home(request):
    return web.Response(text="🚀 Pro Stream Server is Running Smoothly!", content_type="text/plain")

@routes.get("/watch")
async def watch_player(request):
    file_id = request.query.get("id")
    if not file_id:
        return web.Response(text="ভিডিও ফাইল আইডি পাওয়া যায়নি!", status=400)

    # প্রিমিয়াম ডার্ক প্লেয়ার ডিজাইন (গুগল ড্রাইভের লোগো ও হেডার পুরোপুরি হাইড করা)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>প্রিমিয়াম ভিডিও প্লেয়ার</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body, html {{ width: 100%; height: 100%; overflow: hidden; background-color: #0b0e14; }}
            .player-wrapper {{
                position: relative;
                width: 100vw;
                height: 100vh;
                overflow: hidden;
            }}
            /* গুগল ড্রাইভের ওপরের টাইটেল বার এবং পপআউট আইকন ক্রপ করে বাদ দেওয়া */
            iframe {{
                position: absolute;
                top: -56px;
                left: 0;
                width: 100%;
                height: calc(100% + 56px);
                border: none;
            }}
        </style>
    </head>
    <body oncontextmenu="return false;">
        <div class="player-wrapper">
            <iframe src="https://drive.google.com/file/d/{file_id}/preview" allow="autoplay; fullscreen" allowfullscreen></iframe>
        </div>
        <script>
            // রাইট ক্লিক ও ইন্সপেক্ট বন্ধ করা
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
        "👋 **প্রো ক্লাউড বটে স্বাগতম!**\n\n"
        "➕ **জিমেইল যুক্ত করতে:** `/add টোকেন`\n"
        "📊 **ড্রাইভ লিস্ট:** `/drives`\n\n"
        "🎬 যেকোনো ভিডিও পাঠান, বট কাস্টম ব্র্যান্ডেড লিংক বানিয়ে দেবে!"
    )

@app.on_message(filters.command("add") & filters.user(ADMIN_ID))
async def add_drive(client, message):
    if len(message.command) < 2:
        await message.reply("❌ নিয়ম: `/add আপনার_টোকেন`")
        return
    token = message.command[1].strip()
    status = await message.reply("🔍 ভেরিফাই হচ্ছে...")
    try:
        service = get_service(token)
        about = service.about().get(fields="user").execute()
        email = about.get('user', {}).get('emailAddress', 'Google Drive')
        drives = load_drives()
        drives = [d for d in drives if d.get("email") != email]
        drives.append({"email": email, "token": token})
        save_drives(drives)
        await status.edit_text(f"🎉 **যুক্ত হয়েছে!**\n📧 জিমেইল: `{email}`\nমোট ড্রাইভ: {len(drives)} টি।")
    except Exception as e:
        await status.edit_text(f"❌ সমস্যা: {str(e)}")

@app.on_message(filters.command("drives") & filters.user(ADMIN_ID))
async def list_drives(client, message):
    drives = load_drives()
    if not drives:
        await message.reply("কোনো ড্রাইভ যোগ করা নেই!")
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
        
    status = await message.reply("⏳ গুগল ড্রাইভে আপলোড হচ্ছে...")
    file_obj = message.video or message.document
    file_name = file_obj.file_name or "video.mp4"

    try:
        service = get_service(drives[0]["token"])
        file_bytes = await message.download(in_memory=True)
        media = MediaIoBaseUpload(io.BytesIO(file_bytes.getvalue()), mimetype='video/mp4', resumable=True)
        
        file = service.files().create(body={'name': file_name}, media_body=media, fields='id').execute()
        file_id = file.get('id')
        service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()

        # আমাদের নতুন কাস্টম প্লেয়ার লিংক
        custom_play_link = f"{BASE_URL}/watch?id={file_id}"
        embed_code = f'<iframe src="{custom_play_link}" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>'

        await status.edit_text(
            f"✅ **ভিডিও সফলভাবে আপলোড হয়েছে!**\n\n"
            f"🎬 **আপনার নিজস্ব প্রিমিয়াম প্লে লিংক:**\n{custom_play_link}\n\n"
            f"🌐 **ওয়েবসাইটে ব্যবহারের এম্বেড কোড:**\n`{embed_code}`"
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
    print(f"🚀 Server started on port {PORT}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
