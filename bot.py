import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import yt_dlp
import firebase_config as fb

# --- تنظیمات اولیه ---
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- شناسایی پلتفرم ---
def get_platform(url):
    url = url.lower()
    if 'twitter.com' in url or 'x.com' in url: return 'twitter'
    if 'linkedin.com' in url: return 'linkedin'
    if 'instagram.com' in url: return 'instagram'
    if 'tiktok.com' in url: return 'tiktok'
    return 'other'

# --- بررسی دسترسی ---
def check_permission(user_id, url):
    user = fb.get_user(user_id)
    if not user:
        # Create user if not exists (username for admin visibility)
        # Note: aiogram message object has user details
        user = fb.create_user(user_id) 
    
    tier = user.get('tier', 'free')
    platform = get_platform(url)
    
    # 1. Platform Check
    allowed = False
    if tier == 'free':
        if platform == 'twitter': allowed = True
    elif tier == 'premium':
        if platform in ['twitter', 'linkedin']: allowed = True
    elif tier == 'super':
        allowed = True # All allowed
    
    if not allowed:
        return False, f"⚠️ شما در سطح **{tier}** هستید و امکان دانلود از **{platform}** را ندارید.\nبرای ارتقا با پشتیبانی تماس بگیرید."

    # 2. Rate Limit Check
    is_allowed, count, limit = fb.check_rate_limit(user_id, tier)
    if not is_allowed:
        return False, f"⛔️ شما به سقف دانلود روزانه ({limit} عدد) رسیده‌اید.\nفردا دوباره تلاش کنید یا اکانت خود را ارتقا دهید."
    
    return True, None

# --- استخراج لینک ---
def get_video_info(url):
    ydl_opts = {
        'format': 'best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "link": info.get('url'),
                "title": info.get('title', 'بدون عنوان')
            }
    except Exception as e:
        logging.error(f"Error extracting video info: {e}")
        return None

# --- دستور /start ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    # Ensure user exists on start
    fb.get_user(message.from_user.id) or fb.create_user(message.from_user.id, message.from_user.username)
    
    await message.reply(
        "سلام! 👋\nمن ربات «قیچی» هستم. ✂️\n\n"
        "📊 **سطوح اشتراک:**\n"
        "1️⃣ **رایگان**: روزانه ۳ ویدیو (فقط توییتر/X)\n"
        "2️⃣ **پریمیوم**: روزانه ۵ ویدیو (توییتر + لینکدین)\n"
        "3️⃣ **سوپر**: روزانه ۲۰ ویدیو (همه پلتفرم‌ها)\n\n"
        "لینک رو بفرست تا شروع کنیم!"
    )

# --- مدیریت لینک‌ها ---
@dp.message()
async def handle_link(message: types.Message):
    user_url = message.text
    user_id = message.from_user.id
    username = message.from_user.username

    if "http" in user_url:
        # Check Permissions
        allowed, error_msg = check_permission(user_id, user_url)
        if not allowed:
            await message.reply(error_msg)
            fb.log_request(user_id, user_url, get_platform(user_url), 'blocked')
            return

        processing_message = await message.reply("لطفاً صبر کن، دارم ویدیو رو قیچی می‌کنم... ✂️")
        
        video_info = get_video_info(user_url)
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)

        if video_info and video_info["link"]:
            caption = f"✅ **{video_info['title']}**\n\n@GheycheeBot"
            try:
                await message.reply_video(video_info["link"], caption=caption)
                fb.log_request(user_id, user_url, get_platform(user_url), 'success')
            except Exception as e:
                logging.error(f"Failed to send video: {e}")
                await message.reply("❌ خطا در ارسال ویدیو. ممکن است حجم فایل زیاد باشد.")
                fb.log_request(user_id, user_url, get_platform(user_url), 'failed_upload')
        else:
            await message.reply("❌ متاسفانه نتونستم ویدیویی پیدا کنم.")
            fb.log_request(user_id, user_url, get_platform(user_url), 'failed_extract')
    else:
        await message.reply("لطفاً یک لینک معتبر بفرست.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    print("ربات قیچی روشن شد...")
    asyncio.run(main())