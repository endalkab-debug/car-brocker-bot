import os
import asyncio
import logging
import re
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite
from datetime import datetime
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
                <p class="status">✅ Bot and Channel are operational!</p>
                <p style="color: #666;">Reliable car sales and rental brokerage service in Addis Ababa</p>
                
                <div class="links">
                    <a href="https://t.me/AddisCarHubBot" class="btn">🤖 Our Bot</a>
                    <a href="https://t.me/AddisCarHub" class="btn">📢 Our Channel</a>
                </div>
                
                <div class="info">
                    <p>📍 Post your car for sale or rental in 2 minutes via this bot</p>
                    <p>✅ Verified and accurate car details only</p>
                    <p>🤝 Brokerage service with 2-10% commission</p>
                    <p>📞 Contact: +251 XXX XXX XXX</p>
                </div>
                
                <p style="color: #888; font-size: 12px; margin-top: 30px;">
                    Time: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """<br>
                    Service: Car Brokerage Bot v2.0
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

# Configuration with safer JSON parsing
def get_env_list(env_name, default):
    """Safely get JSON list from environment variable"""
    env_value = os.getenv(env_name)
    if env_value:
        try:
            return json.loads(env_value)
        except json.JSONDecodeError:
            print(f"⚠️ Warning: {env_name} has invalid JSON format, using default")
            return default
    return default

def get_env_value(env_name, default):
    """Safely get value from environment variable"""
    return os.getenv(env_name, default)

BOT_TOKEN = get_env_value("BOT_TOKEN", "")
ADMIN_CHANNEL = get_env_value("ADMIN_CHANNEL", "@AddisCarHub")
ADMIN_IDS = get_env_list("ADMIN_IDS", [])
BROKER_PHONES = get_env_list("BROKER_PHONES", ["+251912345678", "+251911223344", "+251922334455", "+251933445566"])
BROKER_NAME = get_env_value("BROKER_NAME", "Addis Car Hub")

# Check for required BOT_TOKEN
if not BOT_TOKEN:
    print("❌ Critical Error: BOT_TOKEN environment variable is not set!")
    print("Please set the BOT_TOKEN environment variable in Railway.")
    exit(1)

print("="*60)
print("🚗 ADDIS CAR HUB - Car Sales & Rental Brokerage Bot")
print("="*60)
print(f"🤖 Bot Token: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
print(f"🤖 Bot: @AddisCarHubBot")
print(f"📢 Channel: {ADMIN_CHANNEL}")
print(f"👥 Brokers: {len(BROKER_PHONES)} people")
print(f"📞 Contact: {', '.join(BROKER_PHONES[:2])}...")
print("="*60)

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
                user_name TEXT,
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
                rental_advanced TEXT,
                rental_warranty TEXT,
                rental_purpose TEXT,
                rental_region TEXT,
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
    print("✅ Database setup completed")

# ====================
# ADMIN NOTIFICATION SYSTEM
# ====================

async def notify_admins(user_data, ad_data, car_type):
    """Send user information to brokers"""
    
    # Format broker phone numbers for message
    broker_phones_formatted = "\n".join([f"• {phone}" for phone in BROKER_PHONES])
    
    # Create admin notification message
    admin_msg = f"""🔔 New car advertisement added!

👤 User Information:
• Name: {user_data.get('full_name', 'N/A')}
• Telegram ID: @{user_data.get('username', 'N/A')}
• Phone Number: {ad_data.get('user_phone', 'N/A')}

🚗 Car Information:
• Type: {'Sale' if car_type == 'sale' else 'Rental'}
• Make: {ad_data.get('make', 'N/A')}
• Model: {ad_data.get('model', 'N/A')}
• Year: {ad_data.get('year', 'N/A')}
• Price: {ad_data.get('price', 'N/A')} Birr
• Condition: {ad_data.get('condition', 'N/A')[:100]}...

⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📢 Advertisement has been posted on channel: {ADMIN_CHANNEL}

📞 Broker Contacts:
{broker_phones_formatted}

🔗 Bot: @AddisCarHubBot
🔗 Channel: {ADMIN_CHANNEL}
"""
    
    # Send to all admins
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=admin_msg)
            print(f"✅ Notification sent to admin {admin_id}")
        except Exception as e:
            print(f"❌ Failed to send to admin {admin_id}: {e}")

# State machine
class CarForm(StatesGroup):
    # Common states
    waiting_for_make = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_phone = State()
    waiting_for_condition = State()
    waiting_for_photos = State()
    
    # Sale specific states
    waiting_for_color = State()
    waiting_for_plate_code = State()
    waiting_for_plate_partial = State()
    waiting_for_plate_region = State()
    waiting_for_price = State()
    
    # Rental specific states
    waiting_for_rental_plate_code = State()
    waiting_for_rental_price = State()
    waiting_for_advanced_payment = State()
    waiting_for_warranty_needed = State()
    waiting_for_rental_purpose = State()
    waiting_for_rental_region = State()

# Format plate number
def format_plate_number(partial):
    """Format plate number: A12 → A12xxx, 546 → 54xxxx"""
    partial = partial.upper().strip()
    
    if any(c.isalpha() for c in partial):
        if len(partial) >= 3:
            return f"{partial[:3]}xxx"
        else:
            return f"{partial}xxx"
    else:
        digits = ''.join(filter(str.isdigit, partial))
        if len(digits) >= 2:
            return f"{digits[:2]}xxxx"
        else:
            return f"{digits}x"

# ====================
# ENGLISH USER INTERFACE
# ====================

# Start command
@dp.message(Command("start"))
async def start_command(message: types.Message):
    welcome_msg = """🏎️ *Welcome to Addis Car Hub!* 🤝

We are reliable and efficient car brokers operating in Addis Ababa!

*Why choose us?*
✅ Accurate and verified cars only
✅ Secure brokerage service
✅ 2-10% commission (based on prior agreement)
✅ All communications through us

*Post your car in 2 minutes:*
1. Choose for sale or rental
2. Enter your car details
3. Add photos
4. It will be listed on @AddisCarHub channel!

*User privacy:* We protect your personal information. All inquiries come through us.

Choose from the options below:"""

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🚗 Car for Sale"), 
             types.KeyboardButton(text="🏢 Car for Rental")],
            [types.KeyboardButton(text="📊 My Statistics"),
             types.KeyboardButton(text="ℹ️ How It Works")],
            [types.KeyboardButton(text="📞 Contact Brokers")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(welcome_msg, parse_mode="Markdown", reply_markup=keyboard)

# How it works
@dp.message(F.text == "ℹ️ How It Works")
async def how_it_works(message: types.Message):
    msg = """*🤝 How Addis Ababa Car Rental & Sales Hub Works*

1. *You enter your car details* through this bot
2. *We verify* and post it on @AddisCarHub
3. *Buyers/renters* contact us (not directly with you)
4. *We connect you* with serious buyers
5. *The transaction completes* with our brokerage service

*Commission:*
• Sale: 2% of sale price
• Rental: 10% of rental price

*Benefits:*
✅ Your privacy is protected
✅ Verified buyers only
✅ Assistance with price negotiation
✅ Assistance with paperwork

🚗 Start by listing your car for sale or 🏢 for rental!"""
    
    await message.answer(msg, parse_mode="Markdown")

# Contact Broker
@dp.message(F.text == "📞 Contact Brokers")
async def contact_broker(message: types.Message):
    broker_phones_list = "\n".join([f"• `{phone}`" for phone in BROKER_PHONES])
    
    msg = f"""*📞 Contact Our Brokers*

{BROKER_NAME}
Phones:
{broker_phones_list}

*Working Hours:* 9:00 AM - 6:00 PM
*Services:* Car brokerage, verification, negotiation

*For urgent matters:* Call directly

*Channel:* {ADMIN_CHANNEL}
*Bot:* @AddisCarHubBot"""
    
    await message.answer(msg, parse_mode="Markdown")

# ====================
# SALE CAR FLOW - ENGLISH
# ====================

@dp.message(F.text == "🚗 Car for Sale")
async def start_sale_ad(message: types.Message, state: FSMContext):
    await state.update_data(car_type="sale")
    
    await message.answer(
        "📝 *Car for Sale - Entering Details*\n\n"
        "We collect your car details. All fields are required.\n\n"
        "*Step 1:* Enter car manufacturer (make):\nExample: Toyota, KIA, Honda",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(CarForm.waiting_for_make)

# Collect car make (for sale)
@dp.message(CarForm.waiting_for_make)
async def get_make(message: types.Message, state: FSMContext):
    await state.update_data(make=message.text)
    await message.answer("*Step 2:* Enter car model:\nExample: Vitz, Stonic, Corolla", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_model)

# Collect model (for sale)
@dp.message(CarForm.waiting_for_model)
async def get_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("*Step 3:* Enter production year:\nExample: 2002, 2020, 2015", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_year)

# ====================
# RENTAL CAR FLOW - ENGLISH
# ====================

@dp.message(F.text == "🏢 Car for Rental")
async def start_rental_ad(message: types.Message, state: FSMContext):
    await state.update_data(car_type="rental")
    
    await message.answer(
        "📝 *Car for Rental - Entering Details*\n\n"
        "We collect rental details. All fields are required.\n\n"
        "*Step 1:* Enter car manufacturer (make):\nExample: Toyota, KIA, Honda",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(CarForm.waiting_for_make)

# ====================
# COMMON HANDLERS (Make, Model, Year)
# ====================

# Collect year (COMMON - fixed duplicate handler issue)
@dp.message(CarForm.waiting_for_year)
async def get_year_common(message: types.Message, state: FSMContext):
    await state.update_data(year=message.text)
    data = await state.get_data()
    
    if data.get('car_type') == 'sale':
        # Sale flow continues with color
        await message.answer("*Step 4:* Enter car color:\nExample: White, Black, Orange, Blue", parse_mode="Markdown")
        await state.set_state(CarForm.waiting_for_color)
    else:
        # Rental flow continues with plate code
        await message.answer(
            "*Step 4:* Enter plate code number:\n"
            "• 1 - Taxi\n"
            "• 2 - Private vehicle\n"
            "• 3 - Commercial/Enterprise\n"
            "Enter only the number (1, 2, or 3):",
            parse_mode="Markdown"
        )
        await state.set_state(CarForm.waiting_for_rental_plate_code)

# ====================
# SALE CONTINUATION
# ====================

# Collect color (sale only)
@dp.message(CarForm.waiting_for_color)
async def get_color(message: types.Message, state: FSMContext):
    await state.update_data(color=message.text)
    
    await message.answer(
        "*Step 5:* Enter plate code number:\n"
        "• 1 - Taxi\n"
        "• 2 - Private vehicle\n"
        "• 3 - Commercial/Enterprise\n"
        "Enter only the number (1, 2, or 3):",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_plate_code)

# Collect plate code (sale only)
@dp.message(CarForm.waiting_for_plate_code)
async def get_plate_code_sale(message: types.Message, state: FSMContext):
    if message.text not in ['1', '2', '3']:
        await message.answer("❌ Please enter only number 1, 2, or 3")
        return
    
    await state.update_data(plate_code=message.text)
    
    await message.answer(
        "*Step 6:* Enter first part of plate number:\n\n"
        "*Examples:*\n"
        "• If plate is A123456 → Enter: A12\n"
        "• If plate is B345678 → Enter: B34\n"
        "• If plate is 546789 → Enter: 546\n"
        "• If plate is 123ABC → Enter: 123\n\n"
        "For privacy, we store it like this: A12xxx / 54xxxx",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_plate_partial)

# Collect plate partial (sale only)
@dp.message(CarForm.waiting_for_plate_partial)
async def get_plate_partial(message: types.Message, state: FSMContext):
    partial = message.text.upper().strip()
    if not re.match(r'^[A-Z0-9]{1,3}$', partial):
        await message.answer("❌ Enter 1-3 letters/numbers (Example: A12, B34, 546)")
        return
    
    formatted = format_plate_number(partial)
    await state.update_data(plate_partial=partial, plate_full=formatted)
    
    await message.answer(
        f"✅ Plate will appear like this: *{formatted}*\n\n"
        "*Step 7:* Enter plate region:\n"
        "Example: Addis Ababa, Oromia, Amhara, SNNPR",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_plate_region)

# Collect plate region (sale only)
@dp.message(CarForm.waiting_for_plate_region)
async def get_plate_region(message: types.Message, state: FSMContext):
    await state.update_data(plate_region=message.text)
    
    await message.answer(
        "*Step 8:* Enter sale price in Birr:\nExample: 1,800,000, 950,000",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_price)

# Collect price (sale only)
@dp.message(CarForm.waiting_for_price)
async def get_price_sale(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await ask_for_phone(message, state)

# ====================
# RENTAL CONTINUATION (UPDATED AS PER REQUIREMENTS)
# ====================

# Collect plate code (rental only)
@dp.message(CarForm.waiting_for_rental_plate_code)
async def get_plate_code_rental(message: types.Message, state: FSMContext):
    if message.text not in ['1', '2', '3']:
        await message.answer("❌ Please enter only number 1, 2, or 3")
        return
    
    await state.update_data(plate_code=message.text)
    
    await message.answer(
        "*Step 5:* Enter daily rental price in Birr:\nExample: 1,200, 1,500, 2,500, 3,000",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_rental_price)

# Collect rental price
@dp.message(CarForm.waiting_for_rental_price)
async def get_rental_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    
    await message.answer(
        "*Step 6:* Advance payment required:\n"
        "• One month\n"
        "• Two months\n"
        "• Three months\n"
        "Enter your choice:",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_advanced_payment)

# Collect advanced payment
@dp.message(CarForm.waiting_for_advanced_payment)
async def get_advanced_payment(message: types.Message, state: FSMContext):
    valid_options = ["One month", "Two months", "Three months"]
    if message.text not in valid_options:
        await message.answer("❌ Please choose: 'One month', 'Two months', or 'Three months'")
        return
    
    await state.update_data(rental_advanced=message.text)
    
    await message.answer(
        "*Step 7:* Warranty needed?\n"
        "• Yes, it's necessary\n"
        "• No, it's not necessary\n"
        "Enter your choice:",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_warranty_needed)

# Collect warranty needed
@dp.message(CarForm.waiting_for_warranty_needed)
async def get_warranty_needed(message: types.Message, state: FSMContext):
    valid_options = ["Yes, it's necessary", "No, it's not necessary"]
    if message.text not in valid_options:
        await message.answer("❌ Please choose: 'Yes, it's necessary' or 'No, it's not necessary'")
        return
    
    await state.update_data(rental_warranty=message.text)
    
    await message.answer(
        "*Step 8:* Rental purpose:\n"
        "• For personal use\n"
        "• For enterprise\n"
        "• For taxi service (Ride)\n"
        "• For tour\n"
        "Enter your choice:",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_rental_purpose)

# Collect rental purpose (UPDATED as per PDF)
@dp.message(CarForm.waiting_for_rental_purpose)
async def get_rental_purpose(message: types.Message, state: FSMContext):
    valid_options = ["For personal use", "For enterprise", "For taxi service (Ride)", "For tour"]
    if message.text not in valid_options:
        await message.answer("❌ Please choose from the options below:")
        for option in valid_options:
            await message.answer(f"• {option}")
        return
    
    await state.update_data(rental_purpose=message.text)
    
    await message.answer(
        "*Step 9:* Enter region where car is available for rental (city):\n"
        "Example: Addis Ababa, Adama, Hawassa",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_rental_region)

# Collect rental region (NEW as per PDF)
@dp.message(CarForm.waiting_for_rental_region)
async def get_rental_region(message: types.Message, state: FSMContext):
    await state.update_data(rental_region=message.text)
    await ask_for_phone(message, state)

# ====================
# COMMON FLOW - ENGLISH
# ====================

async def ask_for_phone(message: types.Message, state: FSMContext):
    await message.answer(
        "*Next step:* Enter your phone number:\n\n"
        "⚠️ *Important:* This number is only for our brokers.\n"
        "It won't appear in public advertisements.\n"
        "Buyers/renters contact us first.\n\n"
        "Example: 0910618029",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_phone)

# Collect phone (common for both)
@dp.message(CarForm.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    if not re.match(r'^09\d{8}$', message.text):
        await message.answer("❌ Please enter a valid Ethiopian phone number (09XXXXXXXX)")
        return
    
    await state.update_data(user_phone=message.text)
    
    data = await state.get_data()
    car_type = data.get('car_type', 'sale')
    
    if car_type == 'sale':
        await message.answer(
            "*Next step:* Describe the car's condition in detail:\n\n"
            "Should include:\n"
            "• Distance (km)\n"
            "• Accident history\n"
            "• Service history\n"
            "• Interior/exterior condition\n"
            "• Any problems or maintenance needed\n\n"
            "*Example:* 'Used, 120,000 km, no accidents, regular service, excellent condition'",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "*Next step:* Describe the car's condition and rental terms:\n\n"
            "Should include:\n"
            "• Distance (km)\n"
            "• Condition\n"
            "• Special rental requirements\n"
            "• Availability date\n"
            "• Any restrictions\n\n"
            "*Example:* 'Well maintained, 80,000 km, available from next week, no smoking in car allowed'",
            parse_mode="Markdown"
        )
    
    await state.set_state(CarForm.waiting_for_condition)

# Collect condition (common for both)
@dp.message(CarForm.waiting_for_condition)
async def get_condition(message: types.Message, state: FSMContext):
    await state.update_data(condition=message.text)
    
    data = await state.get_data()
    car_type = data.get('car_type', 'sale')
    
    photo_prompt = "*Next step (Optional):* Send photos of the car:\n\n"
    
    if car_type == 'sale':
        photo_prompt += "• Front view\n• Side view\n• Interior\n• Odometer\n• Engine\n"
    else:
        photo_prompt += "• Front view\n• Interior\n• Dashboard\n• Special features\n"
    
    photo_prompt += "\nSend up to 5 photos\nTo continue without photos, send /skip"
    
    await message.answer(photo_prompt, parse_mode="Markdown")
    await state.update_data(photos=[])
    await state.set_state(CarForm.waiting_for_photos)

# Handle photos (common for both)
@dp.message(CarForm.waiting_for_photos, F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    
    if len(photos) < 5:
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)
        remaining = 5 - len(photos)
        await message.answer(f"✅ Photo added ({len(photos)}/5)\n{remaining} more can be added. When finished, send /done.")
    else:
        await message.answer("📸 Maximum 5 photos reached. To continue, send /done.")

# Finish photo collection (common for both)
@dp.message(CarForm.waiting_for_photos, Command("done"))
async def finish_ad(message: types.Message, state: FSMContext):
    await process_ad(message, state)

# Skip photos (common for both)
@dp.message(CarForm.waiting_for_photos, Command("skip"))
async def skip_photos(message: types.Message, state: FSMContext):
    await process_ad(message, state)

# Process and post ad
async def process_ad(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    car_type = data.get('car_type', 'sale')
    
    # Format broker phones for ad
    broker_phones_formatted = "\n".join([f"• {phone}" for phone in BROKER_PHONES])
    
    # Format ad based on type
    if car_type == 'sale':
        plate_display = f"{data['plate_code']} {data.get('plate_full', '')} {data.get('plate_region', '')}"
        
        ad_text = f"""🚗 *For Sale - {data['make']} {data['model']} {data['year']}*

📋 *Details:*
• Make: {data['make']}
• Model: {data['model']}
• Year: {data['year']}
• Color: {data['color']}
• Plate: {plate_display}
• Price: *{data['price']} Birr*

🔧 *Condition:*
{data['condition']}

🤝 *Brokerage Service:*
• Verified details
• Seller protection
• Price negotiation assistance
• Paperwork verification

📞 *Contact Our Brokers:*
{broker_phones_formatted}
*Telegram:* @AddisCarHubBot

⚠️ *Note:* All communications through brokers only.

#{data['make'].replace(" ", "")} #{data['model'].replace(" ", "")} 
#CarSale #Automobile #AddisCarHub

*Want to sell your car?* Use @AddisCarHubBot"""
    else:
        # UPDATED RENTAL AD TEXT with rental_region
        ad_text = f"""🏢 *For Rental - {data['make']} {data['model']} {data['year']}*

📋 *Rental Details:*
• Make: {data['make']}
• Model: {data['model']}
• Year: {data['year']}
• Plate Code: {data.get('plate_code', '')}
• Daily Price: *{data['price']} Birr/Day*
• Advance Payment: {data.get('rental_advanced', '')}
• Warranty Required: {data.get('rental_warranty', '')}
• Rental Purpose: {data.get('rental_purpose', '')}
• Available Region: {data.get('rental_region', '')}

🔧 *Condition and Terms:*
{data['condition']}

🤝 *Brokerage Service:*
• Verified rental
• Contract assistance
• Security deposit management
• Maintenance guidance

📞 *Contact Our Brokers:*
{broker_phones_formatted}
*Telegram:* @AddisCarHubBot

⚠️ *Note:* All rental arrangements through brokers only.

#{data['make'].replace(" ", "")} #{data['model'].replace(" ", "")} 
#CarRental #Rental #AddisCarHub

*Need to rent a car?* Use @AddisCarHubBot"""
    
    # Save to database
    async with aiosqlite.connect(DB_PATH) as db:
        if car_type == 'sale':
            await db.execute(
                '''INSERT INTO cars 
                (user_id, user_name, user_phone, make, model, year, color, plate_code, plate_partial, plate_full, plate_region, 
                 price, condition, car_type, photos) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (message.from_user.id, message.from_user.full_name, data['user_phone'], data['make'], data['model'], data['year'], 
                 data['color'], data['plate_code'], data.get('plate_partial', ''), data.get('plate_full', ''), 
                 data.get('plate_region', ''), data['price'], data['condition'], data['car_type'], 
                 json.dumps(photos))
            )
        else:
            await db.execute(
                '''INSERT INTO cars 
                (user_id, user_name, user_phone, make, model, year, plate_code, price, condition, car_type, photos,
                 rental_advanced, rental_warranty, rental_purpose, rental_region) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (message.from_user.id, message.from_user.full_name, data['user_phone'], data['make'], data['model'], data['year'], 
                 data['plate_code'], data['price'], data['condition'], data['car_type'], 
                 json.dumps(photos), data.get('rental_advanced', ''), data.get('rental_warranty', ''), 
                 data.get('rental_purpose', ''), data.get('rental_region', ''))
            )
        await db.commit()
    
    print(f"💾 {car_type.capitalize()} ad saved: {data['make']} {data['model']}")
    
    # Notify admins with user info
    user_data = {
        'full_name': message.from_user.full_name,
        'username': message.from_user.username or 'N/A'
    }
    
    # Send notification to all admins
    await notify_admins(user_data, data, car_type)
    
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
            print(f"📤 {car_type} ad posted with {len(photos)} photos")
        else:
            await bot.send_message(
                chat_id=ADMIN_CHANNEL,
                text=ad_text,
                parse_mode="Markdown"
            )
            print(f"📤 {car_type} text ad posted")
        
        # Send thank you message
        thank_you_msg = f"""🎉 *Thank you for using Addis Car Hub!* 🚗

✅ Your {data['make']} {data['model']} has been posted on @AddisCarHub channel.

*What happens next?*
1. Our brokers verify the details
2. Interested {'buyers' if car_type == 'sale' else 'renters'} contact us
3. We connect you with serious interested parties
4. We assist with negotiation and paperwork

*Your privacy is protected:*
• Your phone number is confidential
• All communications go through us
• We verify all parties

*Commission:* { '2% of sale price' if car_type == 'sale' else '10% of rental price' }

*Share with friends and family:*
🤖 Bot: @AddisCarHubBot
📢 Channel: @AddisCarHub

*Need help?* Contact our brokers: {BROKER_PHONES[0] if BROKER_PHONES else '+251912345678'}

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
        error_msg = f"Error while posting: {str(e)}"
        print(f"❌ {error_msg}")
        await message.answer(f"❌ Error: {str(e)}\n\nPlease try again or call {BROKER_PHONES[0] if BROKER_PHONES else '+251912345678'}")
    
    await state.clear()

# Stats command
@dp.message(F.text == "📊 My Statistics")
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM cars WHERE user_id = ?",
            (message.from_user.id,)
        )
        user_ads = await cursor.fetchone()
        
        cursor = await db.execute("SELECT COUNT(*) FROM cars")
        total_ads = await cursor.fetchone()
        
        cursor = await db.execute(
            "SELECT registered_at FROM users WHERE user_id = ?",
            (message.from_user.id,)
        )
        user_info = await cursor.fetchone()
    
    if user_info:
        stats_msg = f"""📊 *Your Statistics*

• Ads posted: {user_ads[0]}
• Total ads in system: {total_ads[0]}
• Member since: {user_info[0][:10] if user_info[0] else 'today'}

*Broker Information:*
• Channel: {ADMIN_CHANNEL}
• Broker: {BROKER_NAME}
• Phones: {', '.join(BROKER_PHONES[:2]) if BROKER_PHONES else '+251912345678'}

Keep posting! Every ad increases your sales/rental chances."""
    else:
        stats_msg = "You haven't posted any ads yet. To start, use 🚗 Car for Sale or 🏢 Car for Rental!"
    
    await message.answer(stats_msg, parse_mode="Markdown")

# Cancel command
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Operation cancelled.\n\n"
        "To start again, send /start or choose from the options below.",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="🚗 Car for Sale"), 
                 types.KeyboardButton(text="🏢 Car for Rental")],
                [types.KeyboardButton(text="📞 Contact Brokers")]
            ],
            resize_keyboard=True
        )
    )

# ====================
# START BOT
# ====================

async def run_bot():
    await init_db()
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    
    print("🤖 Bot has started running...")
    print("✅ All systems are ready!")
    await dp.start_polling(bot)

def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    asyncio.run(run_bot())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("="*60)
    print("🚗 Addis Ababa Car Hub Bot - English Version")
    print("="*60)
    main()
