import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import spotdl
from spotdl import Spotdl

# تنظیمات لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن ربات
TOKEN = "8091044377:AAFsFuE_Tx6U8leXjAJlvOvRfXMzuPgUCNk"

# تابع شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! من یه ربات دانلودرم. لینک ویدیویی یا آهنگ از یوتیوب، اینستاگرام، تیک‌تاک، ایکس یا اسپاتیفای بفرست تا برات دانلود کنم (تا 2 گیگابایت)!")

# تابع مدیریت خطاها
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f'Update {update} caused error {context.error}')
    await update.message.reply_text("یه مشکلی پیش اومد! دوباره امتحان کن.")

# تابع دانلود از اسپاتیفای با spotdl
async def download_spotify(url, update: Update):
    await update.message.reply_text("در حال پردازش لینک اسپاتیفای... لطفاً صبر کن.")

    try:
        # راه‌اندازی spotdl
        client = Spotdl()
        # دانلود آهنگ یا پلی‌لیست
        songs = client.search([url])
        if not songs:
            await update.message.reply_text("هیچ آهنگی پیدا نشد! مطمئن شو لینک درست باشه.")
            return None

        # دانلود اولین آهنگ (برای پلی‌لیست می‌تونی حلقه بزنی)
        song = songs[0]
        output_file = f"downloaded_spotify_{song.name}.mp3"
        client.download(song, output=output_file)

        return output_file

    except Exception as e:
        logger.error(f"Error downloading Spotify: {e}")
        await update.message.reply_text("خطا تو دانلود از اسپاتیفای! لینک رو چک کن یا دوباره امتحان کن.")
        return None

# تابع دانلود با yt-dlp (برای بقیه پلتفرم‌ها)
async def download_yt_dlp(url, update: Update):
    await update.message.reply_text("در حال پردازش لینک... لطفاً صبر کن، فایل‌های بزرگ ممکنه کمی طول بکشه.")

    # تنظیمات yt-dlp
    ydl_opts = {
        'outtmpl': 'downloaded_file.%(ext)s',  # اسم فایل خروجی
        'format': 'bestvideo+bestaudio/best',  # بهترین کیفیت
        'merge_output_format': 'mp4',          # فرمت خروجی mp4
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return filename
    except Exception as e:
        logger.error(f"Error downloading with yt-dlp: {e}")
        await update.message.reply_text("خطا تو دانلود! مطمئن شو لینک درست باشه یا دوباره امتحان کن.")
        return None

# تابع اصلی دانلود و ارسال فایل
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    # بررسی اینکه لینک اسپاتیفای هست یا نه
    if "open.spotify.com" in url:
        # دانلود از اسپاتیفای
        filename = await download_spotify(url, update)
    else:
        # دانلود از بقیه پلتفرم‌ها با yt-dlp
        filename = await download_yt_dlp(url, update)

    if not filename or not os.path.exists(filename):
        return

    # بررسی سایز فایل (تلگرام محدودیت 2GB داره)
    file_size = os.path.getsize(filename) / (1024 * 1024)  # تبدیل به مگابایت
    if file_size > 2000:
        await update.message.reply_text("فایل خیلی بزرگه (بیشتر از 2 گیگابایت). تلگرام این حجم رو پشتیبانی نمی‌کنه.")
        os.remove(filename)
        return

    # ارسال فایل به کاربر
    await update.message.reply_text("در حال آپلود فایل... صبور باش!")
    with open(filename, 'rb') as file:
        if file_size <= 50:
            # برای فایل‌های کوچک‌تر از 50MB، به صورت ویدیو یا آهنگ ارسال کن
            if filename.endswith('.mp3'):
                await update.message.reply_audio(audio=file, caption="آهنگ شما آماده‌ست!")
            else:
                await update.message.reply_video(video=file, caption="فایل شما آماده‌ست!")
        else:
            # برای فایل‌های بزرگ‌تر، به صورت داکیومنت ارسال کن
            await update.message.reply_document(document=file, caption="فایل شما آماده‌ست (ارسال به صورت داکیومنت چون حجمش بالاست)!")

    # حذف فایل بعد از ارسال
    os.remove(filename)
    await update.message.reply_text("فایل با موفقیت ارسال شد!")

def main():
    # ساخت اپلیکیشن ربات
    application = Application.builder().token(TOKEN).build()

    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    application.add_error_handler(error)

    # شروع ربات
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()