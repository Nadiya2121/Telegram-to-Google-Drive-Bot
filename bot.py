import os
import io
import json
from pyrogram import Client, filters
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Koyeb পরিবেশ ভেরিয়েবল
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DB_FILE = "drives.json"

app = Client("multi_drive_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

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
    # গুগল ড্রাইভ সার্ভিস তৈরি
    creds = Credentials(
        token=None,
        refresh_token=token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id="407408718192.apps.googleusercontent.com",
        client_secret=""
    )
    return build('drive', 'v3', credentials=creds)

# ১. স্টার্ট কমান্ড
@app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(client, message):
    await message.reply(
        "👋 **স্বাগতম! বট প্রস্তুত আছে।**\n\n"
        "➕ **জিমেইল যুক্ত করতে লিখুন:**\n`/add আপনার_টোকেন`\n\n"
        "📊 **ড্রাইভ দেখতে লিখুন:**\n`/drives`\n\n"
        "🎬 যেকোনো ভিডিও পাঠালে স্বয়ংক্রিয়ভাবে ড্রাইভে আপলোড হয়ে যাবে!"
    )

# ২. ড্রাইভ যুক্ত করার স্মার্ট কমান্ড
@app.on_message(filters.command("add") & filters.user(ADMIN_ID))
async def add_drive(client, message):
    if len(message.command) < 2:
        await message.reply("❌ ব্যবহারের নিয়ম: `/add আপনার_টোকেন`")
        return
        
    token = message.command[1].strip()

    # যদি ইউজার ভুল করে 4/0 কোড দেয়
    if token.startswith("4/"):
        await message.reply(
            "⚠️ **এটি আসল রিফ্রেশ টোকেন নয়!**\n\n"
            "গুগলের পেজে ওই কোডটার ঠিক নিচে নীল রঙের একটি বাটন আছে:\n"
            "👉 **'Exchange authorization code for tokens'**\n\n"
            "ওই নীল বাটনে চাপ দিলে নিচে `1//...` দিয়ে শুরু হওয়া আসল টোকেনটি পাবেন। সেটি কপি করে আনুন!"
        )
        return

    status = await message.reply("🔍 জিমেইল ভেরিফাই করা হচ্ছে...")
    
    try:
        service = get_service(token)
        about = service.about().get(fields="user, storageQuota").execute()
        email = about.get('user', {}).get('emailAddress', 'Google Drive')
        
        drives = load_drives()
        # আগের টোকেন থাকলে আপডেট হবে, না থাকলে নতুন যোগ হবে
        drives = [d for d in drives if d.get("email") != email]
        drives.append({"email": email, "token": token})
        save_drives(drives)
        
        await status.edit_text(f"🎉 **সফলভাবে যুক্ত হয়েছে!**\n📧 জিমেইল: `{email}`\nমোট ড্রাইভ সংখ্যা: {len(drives)} টি।")
    except Exception as e:
        await status.edit_text(f"❌ কানেক্ট হতে পারেনি!\nসমস্যা: {str(e)}")

# ৩. ড্রাইভ লিস্ট দেখার কমান্ড
@app.on_message(filters.command("drives") & filters.user(ADMIN_ID))
async def list_drives(client, message):
    drives = load_drives()
    if not drives:
        await message.reply("এখনো কোনো ড্রাইভ যোগ করা হয়নি! লিখুন `/add টোকেন`")
        return
    text = "📊 **কানেক্ট করা ড্রাইভ সমূহ:**\n\n"
    for idx, d in enumerate(drives):
        text += f"**{idx+1}. {d.get('email')}**\n"
    await message.reply(text)

# ৪. ভিডিও আপলোড হ্যান্ডলার
@app.on_message((filters.video | filters.document) & filters.user(ADMIN_ID))
async def upload_video(client, message):
    drives = load_drives()
    if not drives:
        await message.reply("❌ কোনো জিমেইল কানেক্ট করা নেই! আগে `/add টোকেন` দিয়ে ড্রাইভ যোগ করুন।")
        return
        
    status = await message.reply("⏳ গুগল ড্রাইভে আপলোড হচ্ছে, দয়া করে অপেক্ষা করুন...")
    file_obj = message.video or message.document
    file_name = file_obj.file_name or "video.mp4"

    try:
        # প্রথম ড্রাইভে আপলোড
        service = get_service(drives[0]["token"])
        file_bytes = await message.download(in_memory=True)
        media = MediaIoBaseUpload(io.BytesIO(file_bytes.getvalue()), mimetype='video/mp4', resumable=True)
        
        file = service.files().create(body={'name': file_name}, media_body=media, fields='id').execute()
        file_id = file.get('id')

        # সবার দেখার অনুমতি (Public Viewer)
        service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
        stream_link = f"https://drive.google.com/file/d/{file_id}/preview"
        embed_code = f'<iframe src="{stream_link}" width="640" height="360" frameborder="0" allowfullscreen></iframe>'

        await status.edit_text(
            f"✅ **ভিডিও আপলোড সফল হয়েছে!**\n\n"
            f"🎬 **সরাসরি প্লে লিংক:**\n{stream_link}\n\n"
            f"🌐 **ওয়েবসাইটে ব্যবহারের এম্বেড কোড:**\n`{embed_code}`"
        )
    except Exception as e:
        await status.edit_text(f"❌ আপলোডে সমস্যা হয়েছে: {str(e)}")

app.run()
