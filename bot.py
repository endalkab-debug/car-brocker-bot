import os
PORT = int(os.environ.get('PORT', 8000))
print(f"Bot running on port: {PORT}")
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite
from datetime import datetime
import json

# Configuration from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL = os.getenv("ADMIN_CHANNEL", "@CarBrokerEthiopia")
ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS", "[]"))

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Database setup
DB_PATH = "car_broker.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                make TEXT,
                model TEXT,
                engine TEXT,
                fuel TEXT,
                transmission TEXT,
                condition TEXT,
                year TEXT,
                plate_number TEXT,
                price TEXT,
                phone TEXT,
                commission TEXT,
                car_type TEXT,
                description TEXT,
                photos TEXT,  # JSON array of photo IDs
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ads_posted INTEGER DEFAULT 0
            )
        ''')
        await db.commit()

# State machine
class CarForm(StatesGroup):
    waiting_for_make = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_price = State()
    waiting_for_phone = State()
    waiting_for_photos = State()

# Start command
@dp.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Ã°ÂÂÂ Sell Car"), 
             types.KeyboardButton(text="Ã°ÂÂÂ¢ Rent Car")],
            [types.KeyboardButton(text="Ã°ÂÂÂ Contact"),
             types.KeyboardButton(text="Ã¢ÂÂ¹Ã¯Â¸Â Help")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Ã°ÂÂÂÃ¯Â¸Â *Car Broker Bot*\n\n"
        "I help post car ads professionally!\n\n"
        "Choose:\n"
        "Ã¢ÂÂ¢ Ã°ÂÂÂ Sell Car - Post for sale\n"
        "Ã¢ÂÂ¢ Ã°ÂÂÂ¢ Rent Car - Post for rental\n"
        "Ã¢ÂÂ¢ Ã°ÂÂÂ Contact - Get support\n\n"
        "Send /cancel anytime.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    # Register user
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (message.from_user.id, message.from_user.username, message.from_user.full_name)
        )
        await db.commit()

# Quick ad creation - Simple version for now
@dp.message(F.text.in_(["Ã°ÂÂÂ Sell Car", "Ã°ÂÂÂ¢ Rent Car"]))
async def start_ad_creation(message: types.Message, state: FSMContext):
    car_type = "sale" if "Sell" in message.text else "rental"
    
    await state.update_data(car_type=car_type)
    await message.answer(
        f"Ã°ÂÂÂ Creating {'Sale' if car_type == 'sale' else 'Rental'} Ad\n\n"
        "Enter car MAKE (brand):\nExample: Toyota, KIA",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(CarForm.waiting_for_make)

# Collect car make
@dp.message(CarForm.waiting_for_make)
async def get_make(message: types.Message, state: FSMContext):
    await state.update_data(make=message.text)
    await message.answer("Enter car MODEL:\nExample: Vitz, Stonic")
    await state.set_state(CarForm.waiting_for_model)

# Collect model
@dp.message(CarForm.waiting_for_model)
async def get_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Enter YEAR:\nExample: 2002, 2020")
    await state.set_state(CarForm.waiting_for_year)

# Collect year
@dp.message(CarForm.waiting_for_year)
async def get_year(message: types.Message, state: FSMContext):
    await state.update_data(year=message.text)
    data = await state.get_data()
    
    if data['car_type'] == 'sale':
        question = "Enter PRICE in Birr:\nExample: 1,800,000"
    else:
        question = "Enter DAILY RENTAL PRICE:\nExample: 2,500 Birr/day"
    
    await message.answer(question)
    await state.set_state(CarForm.waiting_for_price)

# Collect price
@dp.message(CarForm.waiting_for_price)
async def get_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Enter PHONE NUMBER for contact:\nExample: 0910618029")
    await state.set_state(CarForm.waiting_for_phone)

# Collect phone
@dp.message(CarForm.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer(
        "Ã°ÂÂÂ¸ Send up to 5 photos of the car\n"
        "Send /skip if no photos\n"
        "Send /done when finished"
    )
    await state.update_data(photos=[])
    await state.set_state(CarForm.waiting_for_photos)

# Handle photos
@dp.message(CarForm.waiting_for_photos, F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    
    if len(photos) < 5:
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)
        await message.answer(f"Ã¢ÂÂ Photo added ({len(photos)}/5)\nSend /done when finished")
    else:
        await message.answer("Maximum 5 photos reached. Send /done to proceed.")

# Finish photo collection
@dp.message(CarForm.waiting_for_photos, Command("done"))
async def finish_ad(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    
    # Format ad
    if data['car_type'] == 'sale':
        ad_text = f"""Ã°ÂÂÂ *FOR SALE*

*Make:* {data['make']}
*Model:* {data['model']}
*Year:* {data['year']}
*Price:* {data['price']} Birr

*Contact:* {data['phone']}

#{data['make']} #{data['model']} #CarSale #Ethiopia"""
    else:
        ad_text = f"""Ã°ÂÂÂ¢ *FOR RENT*

Ã¡ÂÂ¨Ã¡ÂÂÃ¡ÂÂ¨Ã¡ÂÂ«Ã¡ÂÂ­ {data['make']} {data['model']} {data['year']}
*Daily Price:* {data['price']}

*Contact:* {data['phone']}

#{data['make']} #{data['model']} #CarRental #Ã¡ÂÂªÃ¡ÂÂ«Ã¡ÂÂ­"""
    
    # Save to database
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            '''INSERT INTO cars 
            (user_id, make, model, year, price, phone, car_type, photos, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (message.from_user.id, data['make'], data['model'], data['year'], 
             data['price'], data['phone'], data['car_type'], 
             json.dumps(photos), 'approved')
        )
        await db.commit()
    
    # Post to channel
    try:
        if photos:
            media = []
            for i, photo_id in enumerate(photos):
                if i == 0:
                    media.append(types.InputMediaPhoto(
                        media=photo_id, 
                        caption=ad_text,
                        parse_mode="Markdown"
                    ))
                else:
                    media.append(types.InputMediaPhoto(media=photo_id))
            await bot.send_media_group(chat_id=ADMIN_CHANNEL, media=media)
        else:
            await bot.send_message(
                chat_id=ADMIN_CHANNEL,
                text=ad_text,
                parse_mode="Markdown"
            )
        
        await message.answer(
            "Ã¢ÂÂ *Ad posted successfully!*\n"
            f"Check: {ADMIN_CHANNEL}",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="/start")]],
                resize_keyboard=True
            )
        )
    except Exception as e:
        await message.answer(f"Error posting: {str(e)}")
    
    await state.clear()

# Skip photos
@dp.message(CarForm.waiting_for_photos, Command("skip"))
async def skip_photos(message: types.Message, state: FSMContext):
    await finish_ad(message, state)

# Cancel command
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.", reply_markup=types.ReplyKeyboardRemove())

# Stats command for admin
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    if str(message.from_user.id) in ADMIN_IDS:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM cars")
            total = await cursor.fetchone()
            
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            users = await cursor.fetchone()
        
        await message.answer(
            f"Ã°ÂÂÂ *Statistics*\n\n"
            f"Ã¢ÂÂ¢ Total Ads: {total[0]}\n"
            f"Ã¢ÂÂ¢ Total Users: {users[0]}\n"
            f"Ã¢ÂÂ¢ Channel: {ADMIN_CHANNEL}",
            parse_mode="Markdown"
        )

# Broadcast command (admin only)
@dp.message(Command("broadcast"))
async def broadcast_command(message: types.Message):
    if str(message.from_user.id) in ADMIN_IDS:
        text = message.text.replace("/broadcast ", "")
        if text:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("SELECT user_id FROM users")
                users = await cursor.fetchall()
            
            for user in users:
                try:
                    await bot.send_message(user[0], f"Ã°ÂÂÂ¢ Announcement:\n\n{text}")
                    await asyncio.sleep(0.1)  # Rate limiting
                except:
                    pass
            
            await message.answer(f"Broadcast sent to {len(users)} users")

# Help command
@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = """Ã°ÂÂÂ§ *Help Guide*

*Commands:*
/start - Start the bot
/cancel - Cancel current operation
/help - Show this message

*How to Post:*
1. Click "Ã°ÂÂÂ Sell Car" or "Ã°ÂÂÂ¢ Rent Car"
2. Follow the steps
3. Add photos (optional)
4. Auto-post to channel

*Contact Support:* @YourSupportUsername
*Channel:* {ADMIN_CHANNEL}

Commission: 2-10% as agreed.""".format(ADMIN_CHANNEL=ADMIN_CHANNEL)
    
    await message.answer(help_text, parse_mode="Markdown")

# Main function
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
