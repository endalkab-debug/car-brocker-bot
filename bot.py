import os
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
from flask import Flask
import threading

# ====================
# FLASK WEB SERVER
# ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "🚗 Addis Car Hub Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)

# ====================
# TELEGRAM BOT
# ====================

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL = os.getenv("ADMIN_CHANNEL", "@AddisCarHub")
ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS", "[]"))

# Validate
print("="*50)
print("🚗 Addis Car Hub Bot")
print("="*50)

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN missing!")
    exit(1)

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Database
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
                photos TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        await db.commit()
    print("✅ Database ready")

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
            [types.KeyboardButton(text="🚗 Sell Car"), 
             types.KeyboardButton(text="🏢 Rent Car")],
            [types.KeyboardButton(text="ℹ️ Help")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "🏎️ *Car Broker Bot*\n\n"
        "Post car ads in 2 minutes!\n\n"
        "Choose:\n"
        "• 🚗 Sell Car\n"
        "• 🏢 Rent Car\n",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# Quick ad creation
@dp.message(F.text.in_(["🚗 Sell Car", "🏢 Rent Car"]))
async def start_ad_creation(message: types.Message, state: FSMContext):
    car_type = "sale" if "Sell" in message.text else "rental"
    
    await state.update_data(car_type=car_type)
    await message.answer("Enter car MAKE:\nExample: Toyota, KIA")
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
    await message.answer("Enter PHONE NUMBER:\nExample: 0910618029")
    await state.set_state(CarForm.waiting_for_phone)

# Collect phone
@dp.message(CarForm.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    
    data = await state.get_data()
    if data['car_type'] == 'sale':
        ad_text = f"""🚗 *FOR SALE*

*Make:* {data['make']}
*Model:* {data['model']}
*Year:* {data['year']}
*Price:* {data['price']} Birr

*Contact:* {data['phone']}

#{data['make']} #{data['model']} #CarSale"""
    else:
        ad_text = f"""🏢 *FOR RENT*

የሚከራይ {data['make']} {data['model']} {data['year']}
*Daily Price:* {data['price']}

*Contact:* {data['phone']}

#{data['make']} #{data['model']} #CarRental"""
    
    # Save to database (simplified)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cars (user_id, make, model, year, price, phone, car_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (message.from_user.id, data['make'], data['model'], data['year'], 
             data['price'], data['phone'], data['car_type'])
        )
        await db.commit()
    
    # Post to channel
    try:
        await bot.send_message(
            chat_id=ADMIN_CHANNEL,
            text=ad_text,
            parse_mode="Markdown"
        )
        await message.answer("✅ *Ad posted successfully!*", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")
    
    await state.clear()

# Cancel command
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.")

# Help command
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("Send /start to begin\nSend /cancel to stop")

# Ping command
@dp.message(Command("ping"))
async def ping_command(message: types.Message):
    await message.answer("🏓 Pong! Bot is running.")

# ====================
# START BOT
# ====================

async def run_bot():
    await init_db()
    
    # Remove any webhook
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    
    print("✅ Bot starting polling...")
    await dp.start_polling(bot)

def main():
    # Start Flask in background thread
    print("🌐 Starting Flask server...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run bot
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
