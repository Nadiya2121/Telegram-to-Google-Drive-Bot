import os
import io
import json
from pyrogram import Client, filters
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Koyeb থেকে আসবে (একবারই সেট করবেন)
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # শুধু আপনি যেন বট নিয়ন্ত্রণ করতে পারেন

DB_FILE = "drives.json"

app = Client("multi_drive_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def load_drives():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return []

def save_drives(drives):
    with open(DB_FILE, "w") as f:
        json.dump(drives, f)

def get_service(token):
    creds = Credentials(
        None,
        refresh_token=token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id="202264815644.apps.googleusercontent.com",
        client_secret="rclone-secret"
    )
    return build('drive', 'v3', credentials=creds)

# ১. বট স্টার্ট কমান্ড
@app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(client, message):
    await message.reply(
        "👋 স্বাগতম!\n\n"
        "➕ **নতুন জিমেইল যোগ করতে লিখুন:**\n`/add আপনার_টোকেন`\n\n"
        "📊 **ড্রাইভগুলোর অবস্থা দেখতে লিখুন:**\n`/drives`\n\n"
        "🎬 ভিডিও পাঠালে আমি সরাসরি ড্রাইভগুলোতে আপলোড করে দেব!"
    )

# ২. জিমেইল টোকেন যুক্ত করার কমান্ড
@app.on_message(filters.command("add") & filters.user(ADMIN_ID))
async def add_drive(client, message):
    if len(message.command) < 2:
        await message.reply("❌ ব্যবহারের নিয়ম: `/add আপনার_টোকেন`")
        return
    
    token = message.command[1].strip()
    status = await message.reply("🔍 টোকেন ভেরিফাই করা হচ্ছে...")
    
    try:
        service = get_service(token)
        about = service.about().get(fields="user, storageQuota").execute()
        email = about.get('user', {}).get('emailAddress', 'অজানা ইমেইল')
        
        drives = load_drives()
        drives.append({"email": email, "token": token})
        save_drives(drives)
        
        await status.edit_text(f"✅ **সফলভাবে যুক্ত হয়েছে!**\n📧 জিমেইল: `{email}`\nমোট ড্রাইভ সংখ্যা: {len(drives)} টি।")
    except Exception as e:
        await status.edit_text(f"❌ টোকেনটি সঠিক নয়! ভুল: {str(e)}")

# ৩. সব ড্রাইভের স্টোরেজ দেখার কমান্ড
@app.on_message(filters.command("drives") & filters.user(ADMIN_ID))
async def list_drives(client, message):
    drives = load_drives()
    if not drives:
        await message.reply("এখনো কোনো জিমেইল যুক্ত করা হয়নি! `/add টোকেন` দিয়ে যুক্ত করুন।")
        return
    
    text = "📊 **আপনার কানেক্ট করা জিমেইল সমূহ:**\n\n"
    for idx, d in enumerate(drives):
        try:
            service = get_service(d["token"])
            about = service.about().get(fields="storageQuota").execute()
            quota = about.get('storageQuota', {})
            limit_gb = round(int(quota.get('limit', 0)) / (1024**3), 2)
            usage_gb = round(int(quota.get('usage', 0)) / (1024**3), 2)
            free_gb = round(limit_gb - usage_gb, 2)
            text += f"**{idx+1}. {d['email']}**\n   └ খালি আছে: {free_gb} GB / {limit_gb} GB\n\n"
        except:
            text += f"**{idx+1}. {d['email']}** (কানেকশন সমস্যা)\n\n"
            
    await message.reply(text)

# ৪. ভিডিও আপলোড হ্যান্ডলার
@app.on_message((filters.video | filters.document) & filters.user(ADMIN_ID))
async def upload_video(client, message):
    drives = load_drives()
    if not drives:
        await message.reply("❌ কোনো জিমেইল কানেক্ট করা নেই! আগে `/add টোকেন` দিয়ে জিমেইল যুক্ত করুন।")
        return
        
    status = await message.reply("🔍 খালি জিমেইল খোঁজা হচ্ছে...")
    
    file_obj = message.video or message.document
    file_name = file_obj.file_name or "video.mp4"
    file_size = file_obj.file_size

    # জায়গা আছে এমন ড্রাইভ নির্বাচন
    selected_service = None
    target_email = ""
    for d in drives:
        try:
            service = get_service(d["token"])
            about = service.about().get(fields="storageQuota").execute()
            quota = about.get('storageQuota', {})
            free_space = int(quota.get('limit', 0)) - int(quota.get('usage', 0))
            if free_space > file_size:
                selected_service = service
                target_email = d["email"]
                break
        except:
            continue

    if not selected_service:
        await status.edit_text("❌ সব ড্রাইভ ফুল হয়ে গেছে! দয়া করে নতুন একটি জিমেইল `/add` করুন।")
        return

    await status.edit_text(f"⏳ `{target_email}` এ আপলোড হচ্ছে...")

    file_bytes = await message.download(in_memory=True)
    
    try:
        file_metadata = {'name': file_name}
        media = MediaIoBaseUpload(io.BytesIO(file_bytes.getvalue()), mimetype='video/mp4', resumable=True)
        file = selected_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')

        # পাবলিক লিংক তৈরি
        selected_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()

        stream_link = f"https://drive.google.com/file/d/{file_id}/preview"
        embed_code = f'<iframe src="{stream_link}" width="640" height="360" frameborder="0" allowfullscreen></iframe>'

        await status.edit_text(
            f"✅ **ভিডিও আপলোড সম্পন্ন!**\n📧 আপলোড হয়েছে: `{target_email}`\n\n"
            f"🎬 **সরাসরি প্লে লিংক:**\n{stream_link}\n\n"
            f"🌐 **ওয়েবসাইটে ব্যবহারের এম্বেড কোড:**\n`{embed_code}`"
        )
    except Exception as e:
        await status.edit_text(f"❌ সমস্যা হয়েছে: {str(e)}")

app.run()
