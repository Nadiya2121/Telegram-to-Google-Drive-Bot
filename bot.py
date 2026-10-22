import os
from pyrogram import Client, filters
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# টেলিগ্রাম ক্রেডেনশিয়াল (Koyeb থেকে আসবে)
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

# জিমেইলের রিফ্রেশ টোকেন (কোনো API Key লাগবে না)
REFRESH_TOKEN = os.getenv("DRIVE_REFRESH_TOKEN")

app = Client("drive_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def get_drive_service():
    # ওপেন-সোর্স পাবলিক ক্লায়েন্ট ক্রেডেনশিয়াল
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id="202264815644.apps.googleusercontent.com", # Rclone-এর পাবলিক ক্লায়েন্ট
        client_secret="rclone-secret"
    )
    return build('drive', 'v3', credentials=creds)

@app.on_message(filters.video | filters.document)
async def upload_to_drive(client, message):
    status = await message.reply("⏳ ফাইলটি প্রসেস হচ্ছে এবং ড্রাইভে আপলোড শুরু হচ্ছে...")
    
    file_name = message.video.file_name if message.video else message.document.file_name
    if not file_name:
        file_name = "video.mp4"

    # টেলিগ্রাম থেকে স্ট্রিম ডাউনলোড
    file_bytes = await message.download(in_memory=True)
    
    try:
        drive_service = get_drive_service()
        file_metadata = {'name': file_name}
        media = MediaIoBaseUpload(io.BytesIO(file_bytes.getvalue()), mimetype='video/mp4', resumable=True)
        
        # ড্রাইভে আপলোড
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')

        # ফাইল পাবলিক করা (যাতে সবাই দেখতে পারে)
        drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()

        # লিঙ্ক তৈরি
        stream_link = f"https://drive.google.com/file/d/{file_id}/preview"
        embed_code = f'<iframe src="{stream_link}" width="640" height="360" frameborder="0" allowfullscreen></iframe>'

        await status.edit_text(
            f"✅ **সফলভাবে আপলোড হয়েছে!**\n\n"
            f"🎬 **সরাসরি প্লে লিংক:**\n{stream_link}\n\n"
            f"🌐 **ওয়েবসাইটে ব্যবহারের এম্বেড কোড:**\n`{embed_code}`"
        )
    except Exception as e:
        await status.edit_text(f"❌ আপলোডে সমস্যা হয়েছে: {str(e)}")

app.run()
