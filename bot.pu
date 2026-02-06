import os
import asyncio
import logging
import re
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
    return """
    <html>
        <head>
            <title>🚗 Addis Car Hub</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    background: rgba(255, 255, 255, 0.95);
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    max-width: 600px;
                    width: 100%;
                }
                h1 {
                    color: #2c3e50;
                    margin-bottom: 10px;
                }
                .status {
                    color: #27ae60;
                    font-weight: bold;
                    font-size: 24px;
                    margin: 20px 0;
                }
                .links {
                    margin: 30px 0;
                }
                .btn {
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 8px;
                    margin: 10px;
                    transition: 0.3s;
                }
                .btn:hover {
                    background: #764ba2;
                    transform: translateY(-3px);
                }
                .info {
                    color: #333;
                    margin: 15px 0;
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚗 Addis Car Hub</h1>
                <p class="status">✅ Bot & Channel Active!</p>
                <p style="color: #666;">Professional Car Brokerage Service in Addis Ababa</p>
                
                <div class="links">
                    <a href="https://t.me/AddisCarHubBot" class="btn">🤖 Our Bot</a>
                    <a href="https://t.me/AddisCarHub" class="btn">📢 Our Channel</a>
                </div>
                
                <div class="info">
                    <p>📍 Post cars for sale or rent in 2 minutes</p>
                    <p>✅ Verified listings only</p>
                    <p>🤝 Broker service with 2-10% commission</p>
                    <p>📞 Contact: +251 XXX XXX XXX</p>
                </div>
                
                <p style="color: #888; font-size: 12px; margin-top: 30px;">
                    Time: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """<br>
                    Service: Car Broker Bot v2.0
                </p>
            </div>
        </body>
    </html>
    """

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
BROKER_PHONE = os.getenv("BROKER_PHONE", "+251912345678")  # Your broker phone
BROKER_NAME = os.getenv("BROKER_NAME", "Addis Car Hub")

print("="*60)
print("🚗 ADDIS CAR HUB - ENHANCED BROKER BOT")
print("="*60)
print(f"🤖 Bot: @AddisCarHubBot")
print(f"📢 Channel: {ADMIN_CHANNEL}")
print(f"📞 Broker: {BROKER_NAME} ({BROKER_PHONE})")
print("="*60)

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN missing!")
    exit(1)

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
                user_phone TEXT,
                make TEXT,
                model TEXT,
                year TEXT,
                color TEXT,
                plate_code TEXT,
                plate_partial TEXT,
                plate_full TEXT,
                plate_region TEXT,
                price TEXT,
                condition TEXT,
                car_type TEXT,
                photos TEXT,
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
    print("✅ Database initialized")

# State machine
class CarForm(StatesGroup):
    waiting_for_make = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_color = State()
    waiting_for_plate_code = State()
    waiting_for_plate_partial = State()
    waiting_for_plate_region = State()
    waiting_for_price = State()
    waiting_for_phone = State()
    waiting_for_condition = State()
    waiting_for_photos = State()

# Format plate number
def format_plate_number(partial):
    """Format plate: A12 → A12xxx, 546 → 54xxxx"""
    partial = partial.upper().strip()
    
    # Check if contains letter
    if any(c.isalpha() for c in partial):
        # Has letter: first 3 chars + xxx
        if len(partial) >= 3:
            return f"{partial[:3]}xxx"
        else:
            return f"{partial}xxx"
    else:
        # No letter: first 2 digits + xxxx
        digits = ''.join(filter(str.isdigit, partial))
        if len(digits) >= 2:
            return f"{digits[:2]}xxxx"
        else:
            return f"{digits}x"

# Start command
@dp.message(Command("start"))
async def start_command(message: types.Message):
    welcome_msg = """🏎️ *Welcome to Addis Car Hub!* 🤝

We're your trusted car broker in Addis Ababa! 

*Why choose us?*
✅ Verified listings only
✅ Safe broker service
✅ 2-10% commission (as agreed)
✅ We handle all communications

*Post your car in 2 minutes:*
1. Choose sale/rental
2. Fill details
3. Add photos
4. We'll post to @AddisCarHub

*Your privacy:* We protect your contact info. All inquiries come through us first.

Choose an option below:"""

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🚗 Sell Car"), 
             types.KeyboardButton(text="🏢 Rent Car")],
            [types.KeyboardButton(text="📊 My Stats"),
             types.KeyboardButton(text="ℹ️ How it Works")],
            [types.KeyboardButton(text="📞 Contact Broker")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(welcome_msg, parse_mode="Markdown", reply_markup=keyboard)

# How it works
@dp.message(F.text == "ℹ️ How it Works")
async def how_it_works(message: types.Message):
    msg = """*🤝 How Addis Car Hub Works*

1. *You post* car via this bot
2. *We verify* and post to @AddisCarHub
3. *Buyers/Renters* contact us (not you directly)
4. *We connect* you with serious buyers
5. *Deal completed* with our broker service

*Commission:*
• Sales: 2% of final price
• Rentals: 10% of rental value

*Benefits:*
✅ Privacy protected
✅ Verified buyers only
✅ Price negotiation help
✅ Paperwork assistance

Start with 🚗 Sell Car or 🏢 Rent Car"""
    
    await message.answer(msg, parse_mode="Markdown")

# Contact Broker
@dp.message(F.text == "📞 Contact Broker")
async def contact_broker(message: types.Message):
    msg = f"""*📞 Contact Our Broker*

{BROKER_NAME}
Phone: `{BROKER_PHONE}`
Telegram: @[YourUsername]

*Office Hours:* 9AM - 6PM
*Services:* Car brokerage, verification, negotiation

*For urgent matters:* Call directly

*Channel:* @AddisCarHub
*Bot:* @AddisCarHubBot"""
    
    await message.answer(msg, parse_mode="Markdown")

# Quick ad creation
@dp.message(F.text.in_(["🚗 Sell Car", "🏢 Rent Car"]))
async def start_ad_creation(message: types.Message, state: FSMContext):
    car_type = "sale" if "Sell" in message.text else "rental"
    
    await state.update_data(car_type=car_type)
    
    type_text = "Sale" if car_type == "sale" else "Rental"
    await message.answer(
        f"📝 *{type_text} Car Posting*\n\n"
        "We'll collect your car details. All fields are required.\n\n"
        "*Step 1:* Enter car MAKE (brand):\nExample: Toyota, KIA, Honda",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(CarForm.waiting_for_make)

# Collect car make
@dp.message(CarForm.waiting_for_make)
async def get_make(message: types.Message, state: FSMContext):
    await state.update_data(make=message.text)
    await message.answer("*Step 2:* Enter car MODEL:\nExample: Vitz, Stonic, Corolla", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_model)

# Collect model
@dp.message(CarForm.waiting_for_model)
async def get_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("*Step 3:* Enter MANUFACTURE YEAR:\nExample: 2002, 2020, 2015", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_year)

# Collect year
@dp.message(CarForm.waiting_for_year)
async def get_year(message: types.Message, state: FSMContext):
    await state.update_data(year=message.text)
    await message.answer("*Step 4:* Enter car COLOR:\nExample: White, Black, Silver, Blue", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_color)

# Collect color
@dp.message(CarForm.waiting_for_color)
async def get_color(message: types.Message, state: FSMContext):
    await state.update_data(color=message.text)
    
    await message.answer(
        "*Step 5:* Enter PLATE CODE NUMBER:\n"
        "• 1 - Private Vehicle\n"
        "• 2 - Commercial/For Hire\n"
        "• 3 - Government/Diplomatic\n"
        "Enter just the number (1, 2, or 3):",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_plate_code)

# Collect plate code
@dp.message(CarForm.waiting_for_plate_code)
async def get_plate_code(message: types.Message, state: FSMContext):
    if message.text not in ['1', '2', '3']:
        await message.answer("❌ Please enter only 1, 2, or 3")
        return
    
    await state.update_data(plate_code=message.text)
    
    await message.answer(
        "*Step 6:* Enter FIRST PART of plate number:\n\n"
        "*Examples:*\n"
        "• If plate is A123456 → Enter: A12\n"
        "• If plate is B345678 → Enter: B34\n"
        "• If plate is 546789 → Enter: 546\n"
        "• If plate is 123ABC → Enter: 123\n\n"
        "We'll format as: A12xxx / 54xxxx for privacy",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_plate_partial)

# Collect plate partial
@dp.message(CarForm.waiting_for_plate_partial)
async def get_plate_partial(message: types.Message, state: FSMContext):
    partial = message.text.upper().strip()
    if not re.match(r'^[A-Z0-9]{1,3}$', partial):
        await message.answer("❌ Enter 1-3 letters/numbers (e.g., A12, B34, 546)")
        return
    
    formatted = format_plate_number(partial)
    await state.update_data(plate_partial=partial, plate_full=formatted)
    
    await message.answer(
        f"✅ Plate will appear as: *{formatted}*\n\n"
        "*Step 7:* Enter PLATE REGION:\n"
        "Example: Addis Ababa, Oromia, Amhara, SNNPR",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_plate_region)

# Collect plate region
@dp.message(CarForm.waiting_for_plate_region)
async def get_plate_region(message: types.Message, state: FSMContext):
    await state.update_data(plate_region=message.text)
    
    data = await state.get_data()
    if data['car_type'] == 'sale':
        question = "*Step 8:* Enter SELLING PRICE in Birr:\nExample: 1,800,000, 950,000"
    else:
        question = "*Step 8:* Enter DAILY RENTAL PRICE:\nExample: 2,500 Birr/day, 3,000 Birr/day"
    
    await message.answer(question, parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_price)

# Collect price
@dp.message(CarForm.waiting_for_price)
async def get_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    
    await message.answer(
        "*Step 9:* Enter YOUR PHONE NUMBER:\n\n"
        "⚠️ *Important:* This number is for our broker only.\n"
        "It will NOT appear in the public ad.\n"
        "Buyers will contact us first.\n\n"
        "Example: 0910618029",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_phone)

# Collect phone
@dp.message(CarForm.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    if not re.match(r'^09\d{8}$', message.text):
        await message.answer("❌ Please enter valid Ethiopian phone (09XXXXXXXX)")
        return
    
    await state.update_data(user_phone=message.text)
    
    await message.answer(
        "*Step 10:* Describe CAR CONDITION in detail:\n\n"
        "Include:\n"
        "• Mileage (km)\n"
        "• Accident history\n"
        "• Service history\n"
        "• Interior/Exterior condition\n"
        "• Any issues or repairs needed\n\n"
        "*Example:* 'Used, 120,000 km, no accidents, regular service, excellent condition'",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_condition)

# Collect condition
@dp.message(CarForm.waiting_for_condition)
async def get_condition(message: types.Message, state: FSMContext):
    await state.update_data(condition=message.text)
    
    await message.answer(
        "*Step 11 (Optional):* Send PHOTOS of the car:\n\n"
        "• Front view\n"
        "• Side view\n"
        "• Interior\n"
        "• Odometer\n"
        "• Any special features\n\n"
        "Send up to 5 photos\n"
        "Send /skip to proceed without photos",
        parse_mode="Markdown"
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
        remaining = 5 - len(photos)
        await message.answer(f"✅ Photo added ({len(photos)}/5)\n{remaining} more can be added. Send /done when finished.")
    else:
        await message.answer("📸 Maximum 5 photos reached. Send /done to proceed.")

# Finish photo collection
@dp.message(CarForm.waiting_for_photos, Command("done"))
async def finish_ad(message: types.Message, state: FSMContext):
    await process_ad(message, state)

# Skip photos
@dp.message(CarForm.waiting_for_photos, Command("skip"))
async def skip_photos(message: types.Message, state: FSMContext):
    await process_ad(message, state)

# Process and post ad
async def process_ad(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    car_type = data['car_type']
    
    # Format plate display
    plate_display = f"{data['plate_code']} {data['plate_full']} {data['plate_region']}"
    
    # Format ad based on type
    if car_type == 'sale':
        ad_text = f"""🚗 *FOR SALE - {data['make']} {data['model']} {data['year']}*

📋 *Details:*
• Make: {data['make']}
• Model: {data['model']}
• Year: {data['year']}
• Color: {data['color']}
• Plate: {plate_display}
• Price: *{data['price']} Birr*

🔧 *Condition:*
{data['condition']}

🤝 *Broker Service:*
• Verified listing
• Private seller protection
• Price negotiation assistance
• Paperwork verification

📞 *Contact Our Broker:* {BROKER_PHONE}
*Telegram:* @AddisCarHubBot

⚠️ *Note:* All communications through broker only.

#{data['make'].replace(" ", "")} #{data['model'].replace(" ", "")} 
#CarSale #አውቶሞቢል #AddisCarHub

*Want to sell your car?* Post via @AddisCarHubBot"""
    else:
        ad_text = f"""🏢 *FOR RENT - {data['make']} {data['model']} {data['year']}*

📋 *Details:*
• Make: {data['make']}
• Model: {data['model']}
• Year: {data['year']}
• Color: {data['color']}
• Plate: {plate_display}
• Daily Price: *{data['price']} Birr/day*

🔧 *Condition:*
{data['condition']}

🤝 *Broker Service:*
• Verified rental
• Contract assistance
• Security deposit handling
• Maintenance coordination

📞 *Contact Our Broker:* {BROKER_PHONE}
*Telegram:* @AddisCarHubBot

⚠️ *Note:* All bookings through broker only.

#{data['make'].replace(" ", "")} #{data['model'].replace(" ", "")} 
#CarRental #ኪራይ #AddisCarHub

*Want to rent out your car?* Post via @AddisCarHubBot"""
    
    # Save to database
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            '''INSERT INTO cars 
            (user_id, user_phone, make, model, year, color, plate_code, plate_partial, plate_full, plate_region, 
             price, condition, car_type, photos) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (message.from_user.id, data['user_phone'], data['make'], data['model'], data['year'], 
             data['color'], data['plate_code'], data['plate_partial'], data['plate_full'], 
             data['plate_region'], data['price'], data['condition'], data['car_type'], 
             json.dumps(photos))
        )
        await db.commit()
    
    print(f"💾 Ad saved: {data['make']} {data['model']} by user {message.from_user.id}")
    
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
            print(f"📤 Posted ad with {len(photos)} photos")
        else:
            await bot.send_message(
                chat_id=ADMIN_CHANNEL,
                text=ad_text,
                parse_mode="Markdown"
            )
            print("📤 Posted text ad")
        
        # Send thank you message
        thank_you_msg = f"""🎉 *THANK YOU FOR USING ADDIS CAR HUB!* 🚗

✅ Your {data['make']} {data['model']} has been posted to @AddisCarHub

*What happens next?*
1. Our broker will verify your listing
2. Interested buyers/renters contact us
3. We'll connect you with serious inquiries
4. We assist with negotiations and paperwork

*Your privacy is protected:*
• Your phone number is confidential
• All communications go through us
• We verify all parties

*Commission:* { '2% of sale price' if car_type == 'sale' else '10% of rental value' }

*Share with friends & family:*
🤖 Bot: @AddisCarHubBot
📢 Channel: @AddisCarHub

*Need help?* Contact our broker: {BROKER_PHONE}

Thank you for trusting Addis Car Hub! 🙏"""
        
        await message.answer(
            thank_you_msg,
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="/start")]],
                resize_keyboard=True
            )
        )
        
    except Exception as e:
        error_msg = f"Error posting: {str(e)}"
        print(f"❌ {error_msg}")
        await message.answer(f"❌ Error: {str(e)}\n\nPlease try again or contact {BROKER_PHONE}")
    
    await state.clear()

# Stats command
@dp.message(F.text == "📊 My Stats")
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        # User's ads
        cursor = await db.execute(
            "SELECT COUNT(*) FROM cars WHERE user_id = ?",
            (message.from_user.id,)
        )
        user_ads = await cursor.fetchone()
        
        # Total ads
        cursor = await db.execute("SELECT COUNT(*) FROM cars")
        total_ads = await cursor.fetchone()
        
        # User info
        cursor = await db.execute(
            "SELECT registered_at FROM users WHERE user_id = ?",
            (message.from_user.id,)
        )
        user_info = await cursor.fetchone()
    
    if user_info:
        stats_msg = f"""📊 *Your Statistics*

• Your Ads Posted: {user_ads[0]}
• Total Ads in System: {total_ads[0]}
• Member Since: {user_info[0][:10] if user_info[0] else 'Today'}

*Broker Information:*
• Channel: {ADMIN_CHANNEL}
• Broker: {BROKER_NAME}
• Phone: {BROKER_PHONE}

Keep posting! Each ad increases your chances of sale/rental."""
    else:
        stats_msg = "You haven't posted any ads yet. Use 🚗 Sell Car or 🏢 Rent Car to start!"
    
    await message.answer(stats_msg, parse_mode="Markdown")

# Cancel command
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Operation cancelled.\n\n"
        "Start again with /start or choose an option below.",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="🚗 Sell Car"), 
                 types.KeyboardButton(text="🏢 Rent Car")],
                [types.KeyboardButton(text="📞 Contact Broker")]
            ],
            resize_keyboard=True
        )
    )

# Help command
@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = f"""🆘 *Help & Support*

*Commands:*
/start - Main menu
/stats - Your statistics
/cancel - Cancel current operation
/help - This message

*How to Post:*
1. Choose 🚗 Sell Car or 🏢 Rent Car
2. Follow the 11 steps
3. Add photos (optional)
4. We post to @AddisCarHub

*Broker Service:*
• {BROKER_NAME}
• Phone: {BROKER_PHONE}
• Channel: {ADMIN_CHANNEL}

*Commission:*
• Sales: 2% of final price
• Rentals: 10% of rental value

*Privacy:* Your contact info is never shared publicly."""
    
    await message.answer(help_text, parse_mode="Markdown")

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
    
    print("🤖 Bot starting polling...")
    print("✅ All systems ready!")
    await dp.start_polling(bot)

def main():
    # Start Flask in background thread
    print("🌐 Starting web server...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run bot
    asyncio.run(run_bot())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("="*60)
    print("🚗 ADDIS CAR HUB BOT - STARTING ENHANCED VERSION")
    print("="*60)
    main()
