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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import aiosqlite
from datetime import datetime
from flask import Flask
import threading
import sys

# ====================
# ENHANCED LOGGING
# ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

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
                    <p>📞 Hotline: 5555 (Coming Soon)</p>
                    <p>📞 Agents: 0911564697, 0913550415</p>
                </div>
                
                <p style="color: #888; font-size: 12px; margin-top: 30px;">
                    Time: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """<br>
                    Service: Car Brokerage Bot v2.1
                </p>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "healthy", "service": "Addis Car Hub Bot"}, 200

def run_flask():
    port = int(os.environ.get('PORT', 3000))
    logger.info(f"Starting Flask server on port {port}")
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask server error: {e}")

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
            logger.warning(f"{env_name} has invalid JSON format, using default")
            return default
    return default

def get_env_value(env_name, default):
    """Safely get value from environment variable"""
    return os.getenv(env_name, default)

BOT_TOKEN = get_env_value("BOT_TOKEN", "")
ADMIN_CHANNEL = get_env_value("ADMIN_CHANNEL", "@AddisCarHub")
ADMIN_IDS = get_env_list("ADMIN_IDS", [])

# UPDATED: New broker phone numbers with agent labels
BROKER_PHONES = get_env_list("BROKER_PHONES", ["0911564697", "0913550415"])
BROKER_NAME = get_env_value("BROKER_NAME", "Addis Car Hub")

# NEW: Formatted broker phones with agent labels
def get_formatted_broker_phones():
    """Return formatted broker phones with agent labels and hotline"""
    formatted = []
    
    # Add agents
    if len(BROKER_PHONES) >= 1:
        formatted.append(f"• Agent #1 - {BROKER_PHONES[0]}")
    if len(BROKER_PHONES) >= 2:
        formatted.append(f"• Agent #2 - {BROKER_PHONES[1]}")
    
    # Add remaining agents if any
    for i in range(2, len(BROKER_PHONES)):
        formatted.append(f"• Agent #{i+1} - {BROKER_PHONES[i]}")
    
    # Add hotline
    formatted.append("• Hotline/Call Center - 5555 (Coming Soon)")
    
    return "\n".join(formatted)

def get_broker_contact_summary():
    """Return a brief contact summary for short displays"""
    if BROKER_PHONES:
        return f"{BROKER_PHONES[0]}, {BROKER_PHONES[1] if len(BROKER_PHONES) > 1 else '0913550415'}"
    return "0911564697, 0913550415"

def get_primary_contact():
    """Return primary contact number"""
    if BROKER_PHONES:
        return BROKER_PHONES[0]
    return "0911564697"

# Check for required BOT_TOKEN
if not BOT_TOKEN:
    logger.error("❌ Critical Error: BOT_TOKEN environment variable is not set!")
    logger.error("Please set the BOT_TOKEN environment variable in Railway.")
    print("="*60)
    print("❌ Critical Error: BOT_TOKEN environment variable is not set!")
    print("Please set the BOT_TOKEN environment variable in Railway.")
    print("="*60)
    exit(1)

logger.info("="*60)
logger.info("🚗 ADDIS CAR HUB - Car Sales & Rental Brokerage Bot")
logger.info("="*60)
logger.info(f"🤖 Bot Token: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
logger.info(f"🤖 Bot: @AddisCarHubBot")
logger.info(f"📢 Channel: {ADMIN_CHANNEL}")
logger.info(f"👥 Agents: {len(BROKER_PHONES)} agents")
logger.info(f"📞 Agent #1: 0911564697")
logger.info(f"📞 Agent #2: 0913550415")
logger.info(f"📞 Hotline: 5555 (Coming Soon)")
logger.info("="*60)

print("="*60)
print("🚗 ADDIS CAR HUB - Car Sales & Rental Brokerage Bot")
print("="*60)
print(f"🤖 Bot Token: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
print(f"🤖 Bot: @AddisCarHubBot")
print(f"📢 Channel: {ADMIN_CHANNEL}")
print(f"👥 Agents: {len(BROKER_PHONES)} agents")
print(f"📞 Agent #1: 0911564697")
print(f"📞 Agent #2: 0913550415")
print(f"📞 Hotline: 5555 (Coming Soon)")
print("="*60)

# Initialize bot with error handling
try:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    logger.info("✅ Bot and Dispatcher initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize bot: {e}")
    print(f"❌ Failed to initialize bot: {e}")
    exit(1)

# Database setup
DB_PATH = "car_broker.db"

async def init_db():
    try:
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
        logger.info("✅ Database setup completed")
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")

# ====================
# ADMIN NOTIFICATION SYSTEM - UPDATED WITH NEW PHONES
# ====================

async def notify_admins(user_data, ad_data, car_type):
    """Send user information to brokers"""
    try:
        # Format broker phones for message - UPDATED
        broker_phones_formatted = get_formatted_broker_phones()
        
        # Create admin notification message - UPDATED
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

📞 Contact Information:
{broker_phones_formatted}

🔗 Bot: @AddisCarHubBot
🔗 Channel: {ADMIN_CHANNEL}
"""
        
        # Send to all admins
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=admin_msg)
                logger.info(f"✅ Notification sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"❌ Error in notify_admins: {e}")

# State machine
class CarForm(StatesGroup):
    # Common states
    waiting_for_make = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_phone = State()
    waiting_for_condition = State()
    waiting_for_photos = State()
    waiting_for_confirmation = State()  # NEW: Confirmation state
    
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
    try:
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
    except Exception as e:
        logger.error(f"Error formatting plate: {e}")
        return partial

# ====================
# KEYBOARD BUILDERS
# ====================

def get_plate_code_keyboard():
    """Plate code selection keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 - Taxi")],
            [KeyboardButton(text="2 - Private vehicle")],
            [KeyboardButton(text="3 - Commercial/Enterprise")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_rental_advanced_keyboard():
    """Advanced payment keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="One month")],
            [KeyboardButton(text="Two months")],
            [KeyboardButton(text="Three months")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_rental_warranty_keyboard():
    """Warranty keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Yes, it's necessary")],
            [KeyboardButton(text="No, it's not necessary")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_rental_purpose_keyboard():
    """Rental purpose keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="For personal use")],
            [KeyboardButton(text="For enterprise")],
            [KeyboardButton(text="For taxi service (Ride)")],
            [KeyboardButton(text="For tour")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_photo_actions_keyboard():
    """Photo actions keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Done - Finish Adding Photos")],
            [KeyboardButton(text="⏩ Skip - No Photos")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_confirmation_keyboard():
    """Confirmation screen keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Confirm & Post")],
            [KeyboardButton(text="✏️ Edit Details")],
            [KeyboardButton(text="❌ Cancel")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# ====================
# ENGLISH USER INTERFACE - UPDATED CONTACT INFO
# ====================

# Start command with enhanced error handling
@dp.message(Command("start"))
async def start_command(message: types.Message):
    try:
        logger.info(f"Start command from user {message.from_user.id} (@{message.from_user.username})")
        
        # UPDATED: Added hotline to welcome message
        welcome_msg = """🏎️ *Welcome to Addis Car Hub!* 🤝

We are reliable and efficient car brokers operating in Addis Ababa!

*Why choose us?*
✅ Accurate and verified cars only
✅ Secure brokerage service
✅ 2-10% commission (based on prior agreement)
✅ All communications through us
✅ Dedicated hotline coming soon!

*Post your car in 2 minutes:*
1. Choose for sale or rental
2. Enter your car details
3. Add photos
4. It will be listed on @AddisCarHub channel!

*User privacy:* We protect your personal information. All inquiries come through us.

*Need help?* Call our agents or use our hotline!

Choose from the options below:"""

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🚗 Car for Sale"), 
                 KeyboardButton(text="🏢 Car for Rental")],
                [KeyboardButton(text="📊 My Statistics"),
                 KeyboardButton(text="ℹ️ How It Works")],
                [KeyboardButton(text="📞 Contact Agents")]
            ],
            resize_keyboard=True
        )
        
        await message.answer(welcome_msg, parse_mode="Markdown", reply_markup=keyboard)
        logger.info(f"Start message sent to user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await message.answer("An error occurred. Please try again or contact support.")

# How it works - UPDATED CONTACT INFO
@dp.message(F.text == "ℹ️ How It Works")
async def how_it_works(message: types.Message):
    try:
        # UPDATED: Added contact info to how it works
        msg = f"""*🤝 How Addis Ababa Car Rental & Sales Hub Works*

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

*Contact Options:*
• Call our agents directly
• Use our hotline (coming soon)
• Message us on Telegram

🚗 Start by listing your car for sale or 🏢 for rental!"""
        
        await message.answer(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in how_it_works: {e}")

# Contact Broker - UPDATED TO "CONTACT AGENTS" WITH NEW PHONES
@dp.message(F.text == "📞 Contact Agents")
async def contact_broker(message: types.Message):
    try:
        # UPDATED: Get formatted broker phones with agent labels and hotline
        broker_phones_formatted = get_formatted_broker_phones()
        
        msg = f"""*📞 Contact Our Team*

{BROKER_NAME}
*Agents & Hotline:*
{broker_phones_formatted}

*Working Hours:* 9:00 AM - 6:00 PM
*Services:* Car brokerage, verification, negotiation

*For urgent matters:* Call agents directly

*Note:* Hotline/Call Center (5555) coming soon!

*Channel:* {ADMIN_CHANNEL}
*Bot:* @AddisCarHubBot"""
        
        await message.answer(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in contact_broker: {e}")

# ====================
# SALE CAR FLOW - ENGLISH
# ====================

@dp.message(F.text == "🚗 Car for Sale")
async def start_sale_ad(message: types.Message, state: FSMContext):
    try:
        await state.update_data(car_type="sale")
        logger.info(f"User {message.from_user.id} started sale ad")
        
        await message.answer(
            "📝 *Car for Sale - Entering Details*\n\n"
            "We collect your car details. All fields are required.\n\n"
            "*Step 1:* Enter car manufacturer (make):\nExample: Toyota, KIA, Honda",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(CarForm.waiting_for_make)
    except Exception as e:
        logger.error(f"Error in start_sale_ad: {e}")
        await message.answer("An error occurred. Please try again.")

# Collect car make (for sale)
@dp.message(CarForm.waiting_for_make)
async def get_make(message: types.Message, state: FSMContext):
    try:
        await state.update_data(make=message.text)
        await message.answer("*Step 2:* Enter car model:\nExample: Vitz, Stonic, Corolla", parse_mode="Markdown")
        await state.set_state(CarForm.waiting_for_model)
    except Exception as e:
        logger.error(f"Error in get_make: {e}")

# Collect model (for sale)
@dp.message(CarForm.waiting_for_model)
async def get_model(message: types.Message, state: FSMContext):
    try:
        await state.update_data(model=message.text)
        await message.answer("*Step 3:* Enter production year:\nExample: 2002, 2020, 2015", parse_mode="Markdown")
        await state.set_state(CarForm.waiting_for_year)
    except Exception as e:
        logger.error(f"Error in get_model: {e}")

# ====================
# RENTAL CAR FLOW - ENGLISH
# ====================

@dp.message(F.text == "🏢 Car for Rental")
async def start_rental_ad(message: types.Message, state: FSMContext):
    try:
        await state.update_data(car_type="rental")
        logger.info(f"User {message.from_user.id} started rental ad")
        
        await message.answer(
            "📝 *Car for Rental - Entering Details*\n\n"
            "We collect rental details. All fields are required.\n\n"
            "*Step 1:* Enter car manufacturer (make):\nExample: Toyota, KIA, Honda",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(CarForm.waiting_for_make)
    except Exception as e:
        logger.error(f"Error in start_rental_ad: {e}")
        await message.answer("An error occurred. Please try again.")

# ====================
# COMMON HANDLERS (Make, Model, Year)
# ====================

# Collect year (COMMON)
@dp.message(CarForm.waiting_for_year)
async def get_year_common(message: types.Message, state: FSMContext):
    try:
        await state.update_data(year=message.text)
        data = await state.get_data()
        
        if data.get('car_type') == 'sale':
            # Sale flow continues with color
            await message.answer("*Step 4:* Enter car color:\nExample: White, Black, Orange, Blue", parse_mode="Markdown")
            await state.set_state(CarForm.waiting_for_color)
        else:
            # Rental flow continues with plate code
            await message.answer(
                "*Step 4:* Select plate code number:\n"
                "• 1 - Taxi\n"
                "• 2 - Private vehicle\n"
                "• 3 - Commercial/Enterprise\n"
                "Choose from the buttons below:",
                parse_mode="Markdown",
                reply_markup=get_plate_code_keyboard()
            )
            await state.set_state(CarForm.waiting_for_rental_plate_code)
    except Exception as e:
        logger.error(f"Error in get_year_common: {e}")

# ====================
# SALE CONTINUATION
# ====================

# Collect color (sale only)
@dp.message(CarForm.waiting_for_color)
async def get_color(message: types.Message, state: FSMContext):
    try:
        await state.update_data(color=message.text)
        
        await message.answer(
            "*Step 5:* Select plate code number:\n"
            "• 1 - Taxi\n"
            "• 2 - Private vehicle\n"
            "• 3 - Commercial/Enterprise\n"
            "Choose from the buttons below:",
            parse_mode="Markdown",
            reply_markup=get_plate_code_keyboard()
        )
        await state.set_state(CarForm.waiting_for_plate_code)
    except Exception as e:
        logger.error(f"Error in get_color: {e}")

# Collect plate code (sale only)
@dp.message(CarForm.waiting_for_plate_code)
async def get_plate_code_sale(message: types.Message, state: FSMContext):
    try:
        plate_code_map = {
            "1 - Taxi": "1",
            "2 - Private vehicle": "2", 
            "3 - Commercial/Enterprise": "3"
        }
        
        if message.text not in plate_code_map:
            await message.answer("❌ Please select from the buttons below:", reply_markup=get_plate_code_keyboard())
            return
        
        plate_code = plate_code_map[message.text]
        await state.update_data(plate_code=plate_code)
        
        await message.answer(
            "*Step 6:* Enter first part of plate number:\n\n"
            "*Examples:*\n"
            "• If plate is A123456 → Enter: A12\n"
            "• If plate is B345678 → Enter: B34\n"
            "• If plate is 546789 → Enter: 546\n"
            "• If plate is 123ABC → Enter: 123\n\n"
            "For privacy, we store it like this: A12xxx / 54xxxx",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(CarForm.waiting_for_plate_partial)
    except Exception as e:
        logger.error(f"Error in get_plate_code_sale: {e}")

# Collect plate partial (sale only)
@dp.message(CarForm.waiting_for_plate_partial)
async def get_plate_partial(message: types.Message, state: FSMContext):
    try:
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
    except Exception as e:
        logger.error(f"Error in get_plate_partial: {e}")

# Collect plate region (sale only)
@dp.message(CarForm.waiting_for_plate_region)
async def get_plate_region(message: types.Message, state: FSMContext):
    try:
        await state.update_data(plate_region=message.text)
        
        await message.answer(
            "*Step 8:* Enter sale price in Birr:\nExample: 1,800,000, 950,000",
            parse_mode="Markdown"
        )
        await state.set_state(CarForm.waiting_for_price)
    except Exception as e:
        logger.error(f"Error in get_plate_region: {e}")

# Collect price (sale only)
@dp.message(CarForm.waiting_for_price)
async def get_price_sale(message: types.Message, state: FSMContext):
    try:
        await state.update_data(price=message.text)
        await ask_for_phone(message, state)
    except Exception as e:
        logger.error(f"Error in get_price_sale: {e}")

# ====================
# RENTAL CONTINUATION
# ====================

# Collect plate code (rental only)
@dp.message(CarForm.waiting_for_rental_plate_code)
async def get_plate_code_rental(message: types.Message, state: FSMContext):
    try:
        plate_code_map = {
            "1 - Taxi": "1",
            "2 - Private vehicle": "2", 
            "3 - Commercial/Enterprise": "3"
        }
        
        if message.text not in plate_code_map:
            await message.answer("❌ Please select from the buttons below:", reply_markup=get_plate_code_keyboard())
            return
        
        plate_code = plate_code_map[message.text]
        await state.update_data(plate_code=plate_code)
        
        await message.answer(
            "*Step 5:* Enter daily rental price in Birr:\nExample: 1,200, 1,500, 2,500, 3,000",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(CarForm.waiting_for_rental_price)
    except Exception as e:
        logger.error(f"Error in get_plate_code_rental: {e}")

# Collect rental price
@dp.message(CarForm.waiting_for_rental_price)
async def get_rental_price(message: types.Message, state: FSMContext):
    try:
        await state.update_data(price=message.text)
        
        await message.answer(
            "*Step 6:* Advance payment required:\n"
            "• One month\n"
            "• Two months\n"
            "• Three months\n"
            "Choose from the buttons below:",
            parse_mode="Markdown",
            reply_markup=get_rental_advanced_keyboard()
        )
        await state.set_state(CarForm.waiting_for_advanced_payment)
    except Exception as e:
        logger.error(f"Error in get_rental_price: {e}")

# Collect advanced payment
@dp.message(CarForm.waiting_for_advanced_payment)
async def get_advanced_payment(message: types.Message, state: FSMContext):
    try:
        valid_options = ["One month", "Two months", "Three months"]
        if message.text not in valid_options:
            await message.answer("❌ Please choose from the buttons below:", reply_markup=get_rental_advanced_keyboard())
            return
        
        await state.update_data(rental_advanced=message.text)
        
        await message.answer(
            "*Step 7:* Warranty needed?\n"
            "• Yes, it's necessary\n"
            "• No, it's not necessary\n"
            "Choose from the buttons below:",
            parse_mode="Markdown",
            reply_markup=get_rental_warranty_keyboard()
        )
        await state.set_state(CarForm.waiting_for_warranty_needed)
    except Exception as e:
        logger.error(f"Error in get_advanced_payment: {e}")

# Collect warranty needed
@dp.message(CarForm.waiting_for_warranty_needed)
async def get_warranty_needed(message: types.Message, state: FSMContext):
    try:
        valid_options = ["Yes, it's necessary", "No, it's not necessary"]
        if message.text not in valid_options:
            await message.answer("❌ Please choose from the buttons below:", reply_markup=get_rental_warranty_keyboard())
            return
        
        await state.update_data(rental_warranty=message.text)
        
        await message.answer(
            "*Step 8:* Rental purpose:\n"
            "• For personal use\n"
            "• For enterprise\n"
            "• For taxi service (Ride)\n"
            "• For tour\n"
            "Choose from the buttons below:",
            parse_mode="Markdown",
            reply_markup=get_rental_purpose_keyboard()
        )
        await state.set_state(CarForm.waiting_for_rental_purpose)
    except Exception as e:
        logger.error(f"Error in get_warranty_needed: {e}")

# Collect rental purpose
@dp.message(CarForm.waiting_for_rental_purpose)
async def get_rental_purpose(message: types.Message, state: FSMContext):
    try:
        valid_options = ["For personal use", "For enterprise", "For taxi service (Ride)", "For tour"]
        if message.text not in valid_options:
            await message.answer("❌ Please choose from the buttons below:", reply_markup=get_rental_purpose_keyboard())
            return
        
        await state.update_data(rental_purpose=message.text)
        
        await message.answer(
            "*Step 9:* Enter region where car is available for rental (city):\n"
            "Example: Addis Ababa, Adama, Hawassa",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(CarForm.waiting_for_rental_region)
    except Exception as e:
        logger.error(f"Error in get_rental_purpose: {e}")

# Collect rental region
@dp.message(CarForm.waiting_for_rental_region)
async def get_rental_region(message: types.Message, state: FSMContext):
    try:
        await state.update_data(rental_region=message.text)
        await ask_for_phone(message, state)
    except Exception as e:
        logger.error(f"Error in get_rental_region: {e}")

# ====================
# COMMON FLOW
# ====================

async def ask_for_phone(message: types.Message, state: FSMContext):
    try:
        # UPDATED: Changed example phone number
        await message.answer(
            "*Next step:* Enter your phone number:\n\n"
            "⚠️ *Important:* This number is only for our agents.\n"
            "It won't appear in public advertisements.\n"
            "Buyers/renters contact us first.\n\n"
            "Example: 0911564697 (10 digits starting with 09)",
            parse_mode="Markdown"
        )
        await state.set_state(CarForm.waiting_for_phone)
    except Exception as e:
        logger.error(f"Error in ask_for_phone: {e}")

# Collect phone (common for both)
@dp.message(CarForm.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    try:
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
    except Exception as e:
        logger.error(f"Error in get_phone: {e}")

# Collect condition (common for both)
@dp.message(CarForm.waiting_for_condition)
async def get_condition(message: types.Message, state: FSMContext):
    try:
        await state.update_data(condition=message.text)
        
        data = await state.get_data()
        car_type = data.get('car_type', 'sale')
        
        photo_prompt = "*Next step (Optional):* Send photos of the car:\n\n"
        
        if car_type == 'sale':
            photo_prompt += "• Front view\n• Side view\n• Interior\n• Odometer\n• Engine\n"
        else:
            photo_prompt += "• Front view\n• Interior\n• Dashboard\n• Special features\n"
        
        photo_prompt += "\nSend up to 5 photos\nUse buttons below when finished:"
        
        await message.answer(photo_prompt, parse_mode="Markdown", reply_markup=get_photo_actions_keyboard())
        await state.update_data(photos=[])
        await state.set_state(CarForm.waiting_for_photos)
    except Exception as e:
        logger.error(f"Error in get_condition: {e}")

# ====================
# PHOTO HANDLING WITH BUTTON SUPPORT
# ====================

# Handle photos - UPDATED: This handler only processes photos
@dp.message(CarForm.waiting_for_photos, F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    try:
        logger.info(f"User {message.from_user.id} sent a photo")
        data = await state.get_data()
        photos = data.get('photos', [])
        
        if len(photos) < 5:
            photos.append(message.photo[-1].file_id)
            await state.update_data(photos=photos)
            remaining = 5 - len(photos)
            
            if remaining > 0:
                await message.answer(
                    f"✅ Photo added ({len(photos)}/5)\n"
                    f"{remaining} more can be added.\n\n"
                    f"When finished, click '📸 Done' below or send another photo.",
                    reply_markup=get_photo_actions_keyboard()
                )
            else:
                await message.answer(
                    "📸 Maximum 5 photos reached!\n"
                    "Click '📸 Done' below to continue.",
                    reply_markup=get_photo_actions_keyboard()
                )
        else:
            await message.answer(
                "📸 Maximum 5 photos reached!\n"
                "Click '📸 Done' below to continue.",
                reply_markup=get_photo_actions_keyboard()
            )
    except Exception as e:
        logger.error(f"Error in handle_photo: {e}")
        await message.answer(
            "❌ Error processing photo. Please try again or skip photos.",
            reply_markup=get_photo_actions_keyboard()
        )

# Handle photo actions (buttons) - UPDATED: This handler only processes text/buttons
@dp.message(CarForm.waiting_for_photos)
async def handle_photo_actions(message: types.Message, state: FSMContext):
    try:
        logger.info(f"User {message.from_user.id} sent text in photo state: {message.text}")
        
        if message.text == "📸 Done - Finish Adding Photos":
            # User finished adding photos
            logger.info(f"User {message.from_user.id} clicked 'Done' for photos")
            data = await state.get_data()
            photos = data.get('photos', [])
            
            if len(photos) > 0:
                await message.answer(
                    f"✅ You added {len(photos)} photo(s).\n"
                    "Now let's review your ad before posting...",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await message.answer(
                    "✅ No photos added.\n"
                    "Now let's review your ad before posting...",
                    reply_markup=ReplyKeyboardRemove()
                )
            
            # Wait a moment for better UX
            await asyncio.sleep(1)
            await show_confirmation(message, state)
            
        elif message.text == "⏩ Skip - No Photos":
            # User skipped photos
            logger.info(f"User {message.from_user.id} clicked 'Skip' for photos")
            await state.update_data(photos=[])
            await message.answer(
                "✅ Skipped photos.\n"
                "Now let's review your ad before posting...",
                reply_markup=ReplyKeyboardRemove()
            )
            await asyncio.sleep(1)
            await show_confirmation(message, state)
            
        else:
            # If user sends text that's not a button
            logger.info(f"User {message.from_user.id} sent unexpected text in photo state")
            await message.answer(
                "📸 Please send photos or use the buttons below:\n\n"
                "• Send photos (up to 5)\n"
                "• Click '📸 Done' when finished\n"
                "• Click '⏩ Skip' to continue without photos",
                reply_markup=get_photo_actions_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in handle_photo_actions: {e}")
        await message.answer(
            "❌ Error processing photo action. Please try sending photos again or use the buttons.",
            reply_markup=get_photo_actions_keyboard()
        )

# Show confirmation screen
async def show_confirmation(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        car_type = data.get('car_type', 'sale')
        photos = data.get('photos', [])
        
        # Create preview based on type
        if car_type == 'sale':
            plate_code_map = {
                "1": "1 - Taxi",
                "2": "2 - Private vehicle", 
                "3": "3 - Commercial/Enterprise"
            }
            plate_code_display = plate_code_map.get(data.get('plate_code', ''), data.get('plate_code', ''))
            plate_display = f"{plate_code_display} {data.get('plate_full', '')} {data.get('plate_region', '')}"
            
            preview_text = f"""📋 *AD PREVIEW - Car for Sale*

🚗 *Car Details:*
• Make: {data['make']}
• Model: {data['model']}
• Year: {data['year']}
• Color: {data.get('color', 'N/A')}
• Plate: {plate_display}
• Price: *{data['price']} Birr*

📝 *Condition:*
{data['condition'][:300]}{'...' if len(data['condition']) > 300 else ''}

📞 *Contact (Agents Only):*
{data['user_phone']}

📸 *Photos:* {len(photos)} photo(s) will be posted

*This ad will be posted on:* {ADMIN_CHANNEL}
*Agents will contact you at:* {data['user_phone']}

⚠️ *Please review carefully before posting!*"""
        else:
            # Rental preview
            preview_text = f"""📋 *AD PREVIEW - Car for Rental*

🚗 *Rental Details:*
• Make: {data['make']}
• Model: {data['model']}
• Year: {data['year']}
• Plate Code: {data.get('plate_code', 'N/A')}
• Daily Price: *{data['price']} Birr/Day*
• Advance: {data.get('rental_advanced', 'N/A')}
• Warranty: {data.get('rental_warranty', 'N/A')}
• Purpose: {data.get('rental_purpose', 'N/A')}
• Region: {data.get('rental_region', 'N/A')}

📝 *Condition & Terms:*
{data['condition'][:300]}{'...' if len(data['condition']) > 300 else ''}

📞 *Contact (Agents Only):*
{data['user_phone']}

📸 *Photos:* {len(photos)} photo(s) will be posted

*This ad will be posted on:* {ADMIN_CHANNEL}
*Agents will contact you at:* {data['user_phone']}

⚠️ *Please review carefully before posting!*"""
        
        await message.answer(
            preview_text,
            parse_mode="Markdown",
            reply_markup=get_confirmation_keyboard()
        )
        await state.set_state(CarForm.waiting_for_confirmation)
        
    except Exception as e:
        logger.error(f"Error in show_confirmation: {e}")
        await message.answer(
            "❌ Error creating preview. Please try again or contact support.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/start")]],
                resize_keyboard=True
            )
        )
        await state.clear()

# Handle confirmation
@dp.message(CarForm.waiting_for_confirmation)
async def handle_confirmation(message: types.Message, state: FSMContext):
    try:
        if message.text == "✅ Confirm & Post":
            await process_ad(message, state)
        elif message.text == "✏️ Edit Details":
            await message.answer(
                "❌ Edit feature coming soon. For now, please cancel and start again.\n\n"
                "You can cancel and start over with updated details.",
                reply_markup=get_confirmation_keyboard()
            )
        elif message.text == "❌ Cancel":
            await state.clear()
            await message.answer(
                "❌ Advertisement cancelled.\n\n"
                "Your data has been deleted. You can start again anytime!",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="/start")]
                    ],
                    resize_keyboard=True
                )
            )
        else:
            await message.answer("Please choose one of the options below:", reply_markup=get_confirmation_keyboard())
    except Exception as e:
        logger.error(f"Error in handle_confirmation: {e}")

# Process and post ad - UPDATED WITH NEW PHONE NUMBERS
async def process_ad(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        photos = data.get('photos', [])
        car_type = data.get('car_type', 'sale')
        
        # UPDATED: Get formatted broker phones with agent labels and hotline
        broker_phones_formatted = get_formatted_broker_phones()
        
        # Format ad based on type
        if car_type == 'sale':
            plate_display = f"{data['plate_code']} {data.get('plate_full', '')} {data.get('plate_region', '')}"
            
            # UPDATED: Changed "Brokers" to "Agents" in ad text
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

📞 *Contact Our Agents:*
{broker_phones_formatted}
*Telegram:* @AddisCarHubBot

⚠️ *Note:* All communications through agents only.

#{data['make'].replace(" ", "")} #{data['model'].replace(" ", "")} 
#CarSale #Automobile #AddisCarHub

*Want to sell your car?* Use @AddisCarHubBot"""
        else:
            # UPDATED RENTAL AD TEXT with new phone numbers
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

📞 *Contact Our Agents:*
{broker_phones_formatted}
*Telegram:* @AddisCarHubBot

⚠️ *Note:* All rental arrangements through agents only.

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
        
        logger.info(f"💾 {car_type.capitalize()} ad saved: {data['make']} {data['model']} by user {message.from_user.id}")
        
        # Notify admins with user info
        user_data = {
            'full_name': message.from_user.full_name,
            'username': message.from_user.username or 'N/A'
        }
        
        # Send notification to all admins
        await notify_admins(user_data, data, car_type)
        
        # Post to channel
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
            logger.info(f"📤 {car_type} ad posted with {len(photos)} photos")
        else:
            await bot.send_message(
                chat_id=ADMIN_CHANNEL,
                text=ad_text,
                parse_mode="Markdown"
            )
            logger.info(f"📤 {car_type} text ad posted")
        
        # UPDATED: Thank you message with new contact info
        thank_you_msg = f"""🎉 *Thank you for using Addis Car Hub!* 🚗

✅ Your {data['make']} {data['model']} has been posted on @AddisCarHub channel.

*What happens next?*
1. Our agents verify the details
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

*Need help?* Contact our agents:
• Agent #1 - 0911564697
• Agent #2 - 0913550415
• Hotline - 5555 (Coming Soon)

Thank you for trusting Addis Car Hub! 🙏"""
        
        await message.answer(
            thank_you_msg,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/start")]],
                resize_keyboard=True
            )
        )
        
    except Exception as e:
        error_msg = f"Error while posting: {str(e)}"
        logger.error(f"❌ {error_msg}")
        await message.answer(f"❌ Error: {str(e)}\n\nPlease try again or call {get_primary_contact()}")
    
    await state.clear()

# Stats command - UPDATED WITH NEW PHONE NUMBERS
@dp.message(F.text == "📊 My Statistics")
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    try:
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
            # UPDATED: Changed broker info to agent info with new numbers
            stats_msg = f"""📊 *Your Statistics*

• Ads posted: {user_ads[0]}
• Total ads in system: {total_ads[0]}
• Member since: {user_info[0][:10] if user_info[0] else 'today'}

*Contact Information:*
• Channel: {ADMIN_CHANNEL}
• Agent #1: 0911564697
• Agent #2: 0913550415
• Hotline: 5555 (Coming Soon)

Keep posting! Every ad increases your sales/rental chances."""
        else:
            stats_msg = "You haven't posted any ads yet. To start, use 🚗 Car for Sale or 🏢 Car for Rental!"
        
        await message.answer(stats_msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await message.answer("Error retrieving statistics. Please try again later.")

# Cancel command - UPDATED BUTTON TEXT
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    try:
        await state.clear()
        await message.answer(
            "❌ Operation cancelled.\n\n"
            "To start again, send /start or choose from the options below.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🚗 Car for Sale"), 
                     KeyboardButton(text="🏢 Car for Rental")],
                    [KeyboardButton(text="📞 Contact Agents")]  # UPDATED: Changed from "Contact Brokers"
                ],
                resize_keyboard=True
            )
        )
    except Exception as e:
        logger.error(f"Error in cancel_command: {e}")

# ====================
# ERROR HANDLER
# ====================

@dp.errors()
async def error_handler(event: types.ErrorEvent):
    logger.error(f"Unhandled error: {event.exception}", exc_info=True)
    try:
        await event.update.message.answer(
            "An unexpected error occurred. Please try again or contact support."
        )
    except:
        pass

# ====================
# START BOT WITH ENHANCED ERROR HANDLING
# ====================

async def run_bot():
    try:
        logger.info("Initializing database...")
        await init_db()
        
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted successfully")
        except Exception as e:
            logger.warning(f"Could not delete webhook: {e}")
        
        logger.info("🤖 Bot has started polling...")
        print("🤖 Bot has started polling...")
        print("✅ All systems are ready!")
        
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        logger.error(f"Fatal error in run_bot: {e}", exc_info=True)
        print(f"❌ Fatal error: {e}")

def main():
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server thread started")
    
    # Run the bot
    asyncio.run(run_bot())

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🚗 Addis Ababa Car Hub Bot - Starting")
    logger.info("="*60)
    
    print("="*60)
    print("🚗 Addis Ababa Car Hub Bot - Starting")
    print("="*60)
    
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 Bot stopped")
    except Exception as e:
        logger.error(f"Main function error: {e}", exc_info=True)
        print(f"❌ Main function error: {e}")
