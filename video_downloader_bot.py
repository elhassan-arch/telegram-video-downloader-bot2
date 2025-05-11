import logging
import requests
import stripe
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import hashlib

# Your API Token (7990538594:AAHfpWypQ-CEzS4jmAx0-SNU8ZPfE52PRUg)
API_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Stripe keys (replace with your actual Stripe keys)
STRIPE_SECRET_KEY = 'sk_test_51RNcv3PsEYwohgvB0EMu3swK5WmFkVDeaCPGfLR961ebd5z6An6Xm4hcgLtHMbQwl5HgvSIZ6qSaz8Z9IHKtTDBh00zIFiidlv'
DONATION_LINK = 'https://buy.stripe.com/test_fZu28t8RmbgiaZe8xueQM00'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
stripe.api_key = STRIPE_SECRET_KEY

USERS = {}  # User data {user_id: {"is_premium": bool, "expiry": datetime}}
REFERRALS = {}  # Track referrals

# Function to download video from TikTok or Instagram
async def download_video(url, quality="1080p"):
    if "tiktok.com" in url:
        api_url = f"https://api.tiktokdownloader.com/?url={url}&quality={quality}"
    elif "instagram.com" in url:
        api_url = f"https://api.instagramdownloader.com/?url={url}&quality={quality}"
    else:
        return None

    response = requests.get(api_url)
    return response.content if response.status_code == 200 else None

# Start command handler
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    ref_id = hashlib.md5(str(message.from_user.id).encode()).hexdigest()
    REFERRALS[ref_id] = message.from_user.id
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Donate", url=DONATION_LINK),
                 InlineKeyboardButton("Subscribe ($2/month)", callback_data="subscribe"))
    await message.reply(f"Welcome to InstaTikPlusBot! Send a video link to download.\n\nRefer for 1-day premium: https://t.me/InstaTikPlusBot?start={ref_id}", reply_markup=keyboard)

# Subscription handler
@dp.callback_query_handler(lambda call: call.data == "subscribe")
async def subscribe_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    expiry = datetime.now() + timedelta(days=30)
    USERS[user_id] = {"is_premium": True, "expiry": expiry}
    await call.message.edit_text(f"You are now a premium user until {expiry.strftime('%Y-%m-%d %H:%M')}")

# Main handler for receiving messages (URL handling)
@dp.message_handler()
async def handle_message(message: types.Message):
    if message.text.startswith('/start '):
        ref_code = message.text.split('/start ')[1]
        if ref_code in REFERRALS:
            ref_user = REFERRALS[ref_code]
            if ref_user in USERS:
                USERS[ref_user]["expiry"] = datetime.now() + timedelta(days=1)
            else:
                USERS[ref_user] = {"is_premium": True, "expiry": datetime.now() + timedelta(days=1)}
            await message.reply("You earned 1 day of premium by referral!")
        return

    user_id = message.from_user.id
    url = message.text

    # Check if user has premium subscription
    if user_id in USERS:
        if datetime.now() > USERS[user_id]["expiry"]:
            USERS[user_id]["is_premium"] = False

    if user_id not in USERS or not USERS[user_id].get("is_premium", False):
        await message.reply("Free users have a daily limit. Subscribe for unlimited access.")
        return

    await message.reply("Choose video quality:", reply_markup=quality_buttons())

# Quality selection handler
@dp.callback_query_handler()
async def quality_selection(callback_query: types.CallbackQuery):
    quality = callback_query.data
    message = callback_query.message
    url = message.reply_to_message.text

    video = await download_video(url, quality)

    if video:
        await message.reply_video(video, caption="Download Complete!")
    else:
        await message.reply("Failed to download. Please try another link.")

# Function to create the quality selection buttons
def quality_buttons():
    keyboard = InlineKeyboardMarkup()
    qualities = ["360p", "720p", "1080p"]
    for q in qualities:
        keyboard.add(InlineKeyboardButton(q, callback_data=q))
    return keyboard

# Start the bot
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
