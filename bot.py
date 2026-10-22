import os
import io
import json
from pyrogram import Client, filters
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DB_FILE = "drives.json"

# গুগলের পাবলিক রেডিমেড কনফিগ (কোনো API বানাতে হবে না)
CLIENT_CONFIG = {
    "web": {
        "client_id": "202264815644.apps.googleusercontent.com",
        "client_secret": "rclone-secret",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}
SCOPES = ['https://www.googleapis.com/auth/drive']

app = Client("multi_drive_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def load_drives():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return []

def save_drives(drives):
    with open(DB_FILE, "w") as f:
        json.dump(drives, f)

# ১. সরাসরি লগইন লিংক পাওয়ার কমান্ড
@app.on_message(filters.command("login") & filters.user(ADMIN_ID))
async def generate_login_url(client, message):
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob")
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    
    await message.reply(
        "👇 **নিচের লিংকে ক্লিক করে জিমেইলে লগইন করুন:**\n\n"
        f"[👉 এখানে ক্লিক করুন 👈]({auth_url})\n\n"
        "লগইন করার পর গুগল আপনাকে একটি **Code** দেবে।\n"
        "সেই কোডটি কপি করে এনে আমাকে এভাবে পাঠান:\n"
        "`/code আপনার_পাওয়া_কোড`",
        disable_web_page_preview=True
    )

# ২. কোড দিয়ে ড্রাইভ সেভ করার কমান্ড
@app.on_message(filters.command("code") & filters.user(ADMIN_ID))
async def submit_code(client, message):
    if len(message.command) < 2:
        await message.reply("❌ ব্যবহারের নিয়ম: `/code আপনার_কোড`")
        return
        
    auth_code = message.command[1].strip()
    status = await message.reply("⏳ ভেরিফাই করা হচ্ছে...")
    
    try:
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob")
        flow.fetch_token(code=auth_code)
        creds = flow.credentials
        
        service = build('drive', 'v3', credentials=creds)
        about = service.about().get(fields="user, storageQuota").execute()
        email = about.get('user', {}).get('emailAddress', 'Google Drive')
        
        drives = load_drives()
        drives.append({"email": email, "token": creds.refresh_token})
        save_drives(drives)
        
        await status.edit_text(f"🎉 **অভিনন্দন!**\n📧 জিমেইল: `{email}` সফলভাবে যুক্ত হয়েছে!\nমোট ড্রাইভ: {len(drives)} টি।")
    except Exception as e:
        await status.edit_text(f"❌ ভুল হয়েছে! আবার চেষ্টা করুন।\nসমস্যা: {str(e)}")

# ৩. ড্রাইভগুলোর তথ্য দেখা
@app.on_message(filters.command("drives") & filters.user(ADMIN_ID))
async def list_drives(client, message):
    drives = load_drives()
    if not drives:
        await message.reply("এখনো কোনো ড্রাইভ যোগ করা হয়নি! লিখুন `/login`")
        return
    text = "📊 **কানেক্ট করা ড্রাইভ সমূহ:**\n\n"
    for idx, d in enumerate(drives):
        text += f"**{idx+1}. {d['email']}**\n"
    await message.reply(text)

# ৪. ভিডিও আপলোড হ্যান্ডলার
@app.on_message((filters.video | filters.document) & filters.user(ADMIN_ID))
async def upload_video(client, message):
    drives = load_drives()
    if not drives:
        await message.reply("❌ কোনো জিমেইল কানেক্ট করা নেই! আগে `/login` করুন।")
        return
        
    status = await message.reply("⏳ জিমেইলে আপলোড হচ্ছে...")
    file_obj = message.video or message.document
    file_name = file_obj.file_name or "video.mp4"

    # প্রথম ড্রাইভে আপলোড শুরু
    from google.oauth2.credentials import Credentials
    creds = Credentials(None, refresh_token=drives[0]["token"], token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_CONFIG["web"]["client_id"], client_secret=CLIENT_CONFIG["web"]["client_secret"])
    service = build('drive', 'v3', credentials=creds)

    file_bytes = await message.download(in_memory=True)
    media = MediaIoBaseUpload(io.BytesIO(file_bytes.getvalue()), mimetype='video/mp4', resumable=True)
    file = service.files().create(body={'name': file_name}, media_body=media, fields='id').execute()
    file_id = file.get('id')

    service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
    stream_link = f"https://drive.google.com/file/d/{file_id}/preview"

    await status.edit_text(f"✅ **আপলোড সম্পন্ন!**\n\n🎬 **প্লে লিংক:**\n{stream_link}")

app.run()
