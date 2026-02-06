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
                <p class="status">✅ ቦት እና ቻናል በስራ ላይ ናቸው!</p>
                <p style="color: #666;">በአዲስ አበባ ውስጥ የሚገኝ የመኪና ብሮከር አገልግሎት</p>
                
                <div class="links">
                    <a href="https://t.me/AddisCarHubBot" class="btn">🤖 ቦታችን</a>
                    <a href="https://t.me/AddisCarHub" class="btn">📢 ቻናላችን</a>
                </div>
                
                <div class="info">
                    <p>📍 መኪና ለመሸጥ ወይም ለመከራየት በ2 ደቂቃ ውስጥ ይለጥፉ</p>
                    <p>✅ የተረጋገጡ ዝርዝሮች ብቻ</p>
                    <p>🤝 የብሮከር አገልግሎት ከ2-10% ኮሚሽን</p>
                    <p>📞 እውቂያ፡ +251 XXX XXX XXX</p>
                </div>
                
                <p style="color: #888; font-size: 12px; margin-top: 30px;">
                    ጊዜ፡ """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """<br>
                    አገልግሎት፡ የመኪና ብሮከር ቦት v2.0
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

# Configuration with better error handling
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL = os.getenv("ADMIN_CHANNEL", "@AddisCarHub")

# Safe JSON loading for environment variables
def safe_json_loads(env_var, default):
    """Safely load JSON from environment variable"""
    value = os.getenv(env_var)
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        print(f"⚠️ Warning: Invalid JSON for {env_var}, using default")
        return default

# Default broker phone numbers
DEFAULT_BROKER_PHONES = ["+251913550415", "+251948002320", "+251911564697", "+251912391541"]
DEFAULT_ADMIN_IDS = []  # Empty by default

ADMIN_IDS = safe_json_loads("ADMIN_IDS", DEFAULT_ADMIN_IDS)
BROKER_PHONES = safe_json_loads("BROKER_PHONES", DEFAULT_BROKER_PHONES)
BROKER_NAME = os.getenv("BROKER_NAME", "Addis Car Hub")

print("="*60)
print("🚗 ADDIS CAR HUB - የመኪና ብሮከር ቦት")
print("="*60)
print(f"🤖 ቦት: @AddisCarHubBot")
print(f"📢 ቻናል: {ADMIN_CHANNEL}")
print(f"👥 ብሮከሮች: {len(BROKER_PHONES)} ሰዎች")
print(f"📞 እውቂያ: {', '.join(BROKER_PHONES)}")
print("="*60)

if not BOT_TOKEN:
    print("❌ ስህተት: BOT_TOKEN የለም!")
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
    print("✅ የውሂብ ጎታ ተጠናቀቀ")

# ====================
# ADMIN NOTIFICATION SYSTEM
# ====================

async def notify_admins(user_data, ad_data, car_type):
    """ለብሮከሮች የተጠቃሚ መረጃ ይላክ"""
    
    # Format broker phone numbers for message
    broker_phones_formatted = "\n".join([f"• {phone}" for phone in BROKER_PHONES])
    
    # Create admin notification message
    admin_msg = f"""🔔 አዲስ የመኪና ማስታወቂያ ተጨምሯል!

👤 የተጠቃሚ መረጃ:
• ስም: {user_data.get('full_name', 'N/A')}
• የቴሌግራም መታወቂያ: @{user_data.get('username', 'N/A')}
• ስልክ ቁጥር: {ad_data.get('user_phone', 'N/A')}

🚗 የመኪና መረጃ:
• ዓይነት: {'ሽያጭ' if car_type == 'sale' else 'ኪራይ'}
• አምራች: {ad_data.get('make', 'N/A')}
• ሞዴል: {ad_data.get('model', 'N/A')}
• ዓመት: {ad_data.get('year', 'N/A')}
• ዋጋ: {ad_data.get('price', 'N/A')} {'ብር' if car_type == 'sale' else 'ብር/ቀን'}

⏰ ጊዜ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📢 ማስታወቂያው በቻናሉ ላይ ተለጥፏል: {ADMIN_CHANNEL}

📞 ብሮከር እውቂያዎች:
{broker_phones_formatted}

🔗 ቦት: @AddisCarHubBot
🔗 ቻናል: {ADMIN_CHANNEL}
"""
    
    # Send to all admins
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=admin_msg)
            print(f"✅ ማስታወቂያ ለአስተዳዳሪ {admin_id} ተላከ")
        except Exception as e:
            print(f"❌ ለአስተዳዳሪ {admin_id} መላክ አልተሳካም: {e}")

# State machine - SIMPLIFIED
class CarForm(StatesGroup):
    # Common states
    waiting_for_make = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_phone = State()
    waiting_for_photos = State()
    
    # Sale specific states
    waiting_for_color = State()
    waiting_for_plate_code = State()
    waiting_for_plate_partial = State()
    waiting_for_plate_region = State()
    waiting_for_price = State()
    waiting_for_condition = State()
    
    # Rental specific states (NEW SIMPLIFIED VERSION)
    waiting_for_rental_plate_code = State()
    waiting_for_rental_price = State()
    waiting_for_advanced_payment = State()
    waiting_for_warranty_needed = State()
    waiting_for_rental_purpose = State()
    waiting_for_rental_region = State()

# Format plate number
def format_plate_number(partial):
    """ፕሌት ቁጥር ያቀናብሩ: A12 → A12xxx, 546 → 54xxxx"""
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
# AMHARIC USER INTERFACE
# ====================

# Start command
@dp.message(Command("start"))
async def start_command(message: types.Message):
    welcome_msg = """🏎️ *እንኳን ወደ አዲስ አበባ መኪና ማዕከል በደህና መጡ!* 🤝

እኛ በአዲስ አበባ ውስጥ የሚገኝ የታመነ የመኪና ብሮከር እንሰራለን!

*ለምን እኛን መምረጥ ይገባል?*
✅ የተረጋገጡ ዝርዝሮች ብቻ
✅ ደህንነቱ የተጠበቀ የብሮከር አገልግሎት
✅ 2-10% ኮሚሽን (እንደ ተስማማነው)
✅ ሁሉም ንግግሮች በእኛ በኩል

*መኪናዎን በ2 ደቂቃ ውስጥ ይለጥፉ፡*
1. ለመሸጥ ወይም ለመከራየት ይምረጡ
2. ዝርዝሮችን ይሙሉ
3. ፎቶዎችን ይጨምሩ (ከፈለጉ)
4. በ @AddisCarHub ቻናል ላይ እናስተላፍናለን

*የተጠቃሚ ግላዊነት፡* የእርስዎን እውቂያ መረጃ እንጠብቃለን። ሁሉም ጥያቄዎች በእኛ በኩል ይመጣሉ።

ከታች ያለውን አማራጭ ይምረጡ፡"""

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🚗 መኪና ለመሸጥ"), 
             types.KeyboardButton(text="🏢 መኪና ለመከራየት")],
            [types.KeyboardButton(text="📊 የእኔ ስታቲስቲክስ"),
             types.KeyboardButton(text="ℹ️ እንዴት እንደሚሰራ")],
            [types.KeyboardButton(text="📞 ብሮከር ለመገናኘት")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(welcome_msg, parse_mode="Markdown", reply_markup=keyboard)

# How it works
@dp.message(F.text == "ℹ️ እንዴት እንደሚሰራ")
async def how_it_works(message: types.Message):
    msg = """*🤝 አዲስ አበባ መኪና ማዕከል እንዴት እንደሚሰራ*

1. *እርስዎ መኪናዎን* በዚህ ቦት ያስገቡ
2. *እኛ እናረጋግጣለን* እና በ @AddisCarHub ላይ እናስተላፍናለን
3. *ገዢዎች/ተከራያዎች* ከእኛ ጋር ይገናኛሉ (ከእርስዎ ጋር በቀጥታ አይደለም)
4. *እኛ እርስዎን* ከከባድ ገዢዎች ጋር እናገናኛለን
5. *ግብይቱ ተጠናቅቋል* ከእኛ የብሮከር አገልግሎት ጋር

*ኮሚሽን፡*
• ሽያጭ፡ 2% የመጨረሻ ዋጋ
• ኪራይ፡ 10% የኪራይ ዋጋ

*ጥቅሞች፡*
✅ ግላዊነትዎ የተጠበቀ
✅ የተረጋገጡ ገዢዎች ብቻ
✅ በዋጋ ስምምነት እገዛ
✅ በወረቀት ስራ እገዛ

በ 🚗 መኪና ለመሸጥ ወይም 🏢 መኪና ለመከራየት ይጀምሩ"""
    
    await message.answer(msg, parse_mode="Markdown")

# Contact Broker
@dp.message(F.text == "📞 ብሮከር ለመገናኘት")
async def contact_broker(message: types.Message):
    broker_phones_list = "\n".join([f"• `{phone}`" for phone in BROKER_PHONES])
    
    msg = f"""*📞 ከብሮከራችን ጋር ይገናኙ*

{BROKER_NAME}
ስልኮች፡
{broker_phones_list}

*የስራ ሰዓት፡* 9፡00 ጥዋት - 6፡00 ማታ
*አገልግሎቶች፡* የመኪና ብሮከር፣ ማረጋገጫ፣ ድርድር

*ለአስቸኳይ ጉዳዮች፡* በቀጥታ ይደውሉ

*ቻናል፡* {ADMIN_CHANNEL}
*ቦት፡* @AddisCarHubBot"""
    
    await message.answer(msg, parse_mode="Markdown")

# ====================
# SALE CAR FLOW - AMHARIC (UNCHANGED)
# ====================

@dp.message(F.text == "🚗 መኪና ለመሸጥ")
async def start_sale_ad(message: types.Message, state: FSMContext):
    await state.update_data(car_type="sale")
    
    await message.answer(
        "📝 *መኪና ለመሸጥ - ዝርዝሮች ማስገባት*\n\n"
        "የመኪናዎን ዝርዝሮች እንሰበስባለን። ሁሉም መስኮች አስፈላጊ ናቸው።\n\n"
        "*1ኛ ደረጃ፡* የመኪና አምራች (ማርካ) ያስገቡ፡\nምሳሌ፡ Toyota, KIA, Honda",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(CarForm.waiting_for_make)

# Collect car make (for sale)
@dp.message(CarForm.waiting_for_make)
async def get_make(message: types.Message, state: FSMContext):
    await state.update_data(make=message.text)
    await message.answer("*2ኛ ደረጃ፡* የመኪና ሞዴል ያስገቡ፡\nምሳሌ፡ Vitz, Stonic, Corolla", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_model)

# Collect model (for sale)
@dp.message(CarForm.waiting_for_model)
async def get_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("*3ኛ ደረጃ፡* የምርት ዓመት ያስገቡ፡\nምሳሌ፡ 2002, 2020, 2015", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_year)

# Collect year (for sale)
@dp.message(CarForm.waiting_for_year)
async def get_year_sale(message: types.Message, state: FSMContext):
    await state.update_data(year=message.text)
    await message.answer("*4ኛ ደረጃ፡* የመኪና ቀለም ያስገቡ፡\nምሳሌ፡ ነጭ, ጥቁር, ብርቱካናማ, ሰማያዊ", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_color)

# Collect color (sale only)
@dp.message(CarForm.waiting_for_color)
async def get_color(message: types.Message, state: FSMContext):
    await state.update_data(color=message.text)
    
    await message.answer(
        "*5ኛ ደረጃ፡* የፕሌት ኮድ ቁጥር ያስገቡ፡\n"
        "• 1 - ታክሲ\n"
        "• 2 - የግል\n"
        "• 3 - የንግድ/የድርጅት\n"
        "ቁጥሩን ብቻ ያስገቡ (1, 2, ወይም 3)፡",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_plate_code)

# Collect plate code (sale only)
@dp.message(CarForm.waiting_for_plate_code)
async def get_plate_code_sale(message: types.Message, state: FSMContext):
    if message.text not in ['1', '2', '3']:
        await message.answer("❌ እባክዎ ቁጥር 1, 2, ወይም 3 ብቻ ያስገቡ")
        return
    
    await state.update_data(plate_code=message.text)
    
    await message.answer(
        "*6ኛ ደረጃ፡* የፕሌት ቁጥር የመጀመሪያ ክፍል ያስገቡ፡\n\n"
        "*ምሳሌዎች፡*\n"
        "• ፕሌቱ A123456 ከሆነ → ያስገቡ፡ A12\n"
        "• ፕሌቱ B345678 ከሆነ → ያስገቡ፡ B34\n"
        "• ፕሌቱ 546789 ከሆነ → ያስገቡ፡ 546\n"
        "• ፕሌቱ 123ABC ከሆነ → ያስገቡ፡ 123\n\n"
        "ለግላዊነት እንደዚህ እናስቀምጠዋለን፡ A12xxx / 54xxxx",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_plate_partial)

# Collect plate partial (sale only)
@dp.message(CarForm.waiting_for_plate_partial)
async def get_plate_partial(message: types.Message, state: FSMContext):
    partial = message.text.upper().strip()
    if not re.match(r'^[A-Z0-9]{1,3}$', partial):
        await message.answer("❌ 1-3 ፊደላት/ቁጥሮች ያስገቡ (ምሳሌ፡ A12, B34, 546)")
        return
    
    formatted = format_plate_number(partial)
    await state.update_data(plate_partial=partial, plate_full=formatted)
    
    await message.answer(
        f"✅ ፕሌት እንዲህ ይታያል፡ *{formatted}*\n\n"
        "*7ኛ ደረጃ፡* የፕሌት ክልል ያስገቡ፡\n"
        "ምሳሌ፡ አዲስ አበባ, ኦሮሚያ, አማራ, SNNPR",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_plate_region)

# Collect plate region (sale only)
@dp.message(CarForm.waiting_for_plate_region)
async def get_plate_region(message: types.Message, state: FSMContext):
    await state.update_data(plate_region=message.text)
    
    await message.answer(
        "*8ኛ ደረጃ፡* የሽያጭ ዋጋ በብር ያስገቡ፡\nምሳሌ፡ 1,800,000, 950,000",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_price)

# Collect price (sale only)
@dp.message(CarForm.waiting_for_price)
async def get_price_sale(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    
    await message.answer(
        "*9ኛ ደረጃ፡* የመኪናውን ሁኔታ በዝርዝር ይግለጹ፡\n\n"
        "የሚካተት፡\n"
        "• ርቀት (ኪ.ሜ.)\n"
        "• የአደጋ ታሪክ\n"
        "• የአገልግሎት ታሪክ\n"
        "• ውስጣዊ/ውጫዊ ሁኔታ\n"
        "• ያሉት ችግሮች ወይም ጥገናዎች\n\n"
        "*ምሳሌ፡* 'ተጠቅሟል፣ 120,000 ኪ.ሜ.፣ አደጋ የለውም፣ መደበኛ አገልግሎት፣ በጣም ጥሩ ሁኔታ'",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_condition)

# Collect condition (sale only)
@dp.message(CarForm.waiting_for_condition)
async def get_condition_sale(message: types.Message, state: FSMContext):
    await state.update_data(condition=message.text)
    await ask_for_phone(message, state)

# ====================
# RENTAL CAR FLOW - AMHARIC (NEW SIMPLIFIED VERSION)
# ====================

@dp.message(F.text == "🏢 መኪና ለመከራየት")
async def start_rental_ad(message: types.Message, state: FSMContext):
    await state.update_data(car_type="rental")
    
    await message.answer(
        "📝 *መኪና ለመከራየት - ዝርዝሮች ማስገባት*\n\n"
        "የኪራይ ዝርዝሮችን እንሰበስባለን። ሁሉም መስኮች አስፈላጊ ናቸው።\n\n"
        "*1ኛ ደረጃ፡* የመኪና አምራች (ማርካ) ያስገቡ፡\nምሳሌ፡ Toyota, KIA, Honda",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(CarForm.waiting_for_make)

# Note: The get_make, get_model, get_year_rental handlers are shared with sale

# After year for rental, we branch to SIMPLIFIED rental flow
@dp.message(CarForm.waiting_for_year)
async def get_year_rental(message: types.Message, state: FSMContext):
    data = await state.get_data()
    car_type = data.get('car_type', 'sale')
    
    await state.update_data(year=message.text)
    
    if car_type == 'rental':
        # SIMPLIFIED RENTAL FLOW - Step 4: Plate Code
        await message.answer(
            "*4ኛ ደረጃ፡* የፕሌት ኮድ ቁጥር ያስገቡ፡\n"
            "• 1 - ታክሲ\n"
            "• 2 - የግል\n"
            "• 3 - የንግድ/የድርጅት\n"
            "ቁጥሩን ብቻ ያስገቡ (1, 2, ወይም 3)፡",
            parse_mode="Markdown"
        )
        await state.set_state(CarForm.waiting_for_rental_plate_code)
    else:
        # Sale continues with color
        await message.answer("*4ኛ ደረጃ፡* የመኪና ቀለም ያስገቡ፡\nምሳሌ፡ ነጭ, ጥቁር, ብርቱካናማ, ሰማያዊ", parse_mode="Markdown")
        await state.set_state(CarForm.waiting_for_color)

# Step 4: Plate Code for rental
@dp.message(CarForm.waiting_for_rental_plate_code)
async def get_plate_code_rental(message: types.Message, state: FSMContext):
    if message.text not in ['1', '2', '3']:
        await message.answer("❌ እባክዎ ቁጥር 1, 2, ወይም 3 ብቻ ያስገቡ")
        return
    
    await state.update_data(plate_code=message.text)
    
    # Step 5: Rental Price per Day
    await message.answer(
        "*5ኛ ደረጃ፡* የኪራይ ዋጋ በቀን በብር ያስገቡ፡\nምሳሌ፡ 1,200, 1,500, 2,500, 3,000",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_rental_price)

# Step 5: Rental Price
@dp.message(CarForm.waiting_for_rental_price)
async def get_rental_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    
    # Step 6: Advanced Payment
    await message.answer(
        "*6ኛ ደረጃ፡* ቅድመ ክፍያ ያስፈልጋል፡\n"
        "• አንድ ወር ቅድመ ክፍያ\n"
        "• ሁለት ወር ቅድመ ክፍያ\n"
        "• ሶስት ወር ቅድመ ክፍያ\n"
        "ምርጫዎን ያስገቡ፡",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_advanced_payment)

# Step 6: Advanced Payment
@dp.message(CarForm.waiting_for_advanced_payment)
async def get_advanced_payment(message: types.Message, state: FSMContext):
    valid_options = ["አንድ ወር ቅድመ ክፍያ", "ሁለት ወር ቅድመ ክፍያ", "ሶስት ወር ቅድመ ክፍያ"]
    if message.text not in valid_options:
        await message.answer("❌ እባክዎ ይምረጡ፡ አንድ ወር ቅድመ ክፍያ, ሁለት ወር ቅድመ ክፍያ, ወይም ሶስት ወር ቅድመ ክፍያ")
        return
    
    await state.update_data(rental_advanced=message.text)
    
    # Step 7: Warranty Needed
    await message.answer(
        "*7ኛ ደረጃ፡* ዋስትና ያስፈልጋል?\n"
        "• አዎ፣ ዋስትና አስፈላጊ ነው (Mandatory)\n"
        "• አይ፣ አስፈላጊ አይደለም (Not Necessary)\n"
        "ምርጫዎን ያስገቡ፡",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_warranty_needed)

# Step 7: Warranty Needed
@dp.message(CarForm.waiting_for_warranty_needed)
async def get_warranty_needed(message: types.Message, state: FSMContext):
    valid_options = ["አዎ፣ ዋስትና አስፈላጊ ነው (Mandatory)", "አይ፣ አስፈላጊ አይደለም (Not Necessary)"]
    if message.text not in valid_options:
        await message.answer("❌ እባክዎ ይምረጡ፡ 'አዎ፣ ዋስትና አስፈላጊ ነው (Mandatory)' ወይም 'አይ፣ አስፈላጊ አይደለም (Not Necessary)'")
        return
    
    await state.update_data(rental_warranty=message.text)
    
    # Step 8: Rental Purpose
    await message.answer(
        "*8ኛ ደረጃ፡* ኪራይ ለማን ነው?\n"
        "• ለግል\n"
        "• ለድርጅት\n"
        "• ታክሲ አገልግሎት (Ride)\n"
        "• ለጉብኝት (Tour)\n"
        "ምርጫዎን ያስገቡ፡",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_rental_purpose)

# Step 8: Rental Purpose
@dp.message(CarForm.waiting_for_rental_purpose)
async def get_rental_purpose(message: types.Message, state: FSMContext):
    valid_options = ["ለግል", "ለድርጅት", "ታክሲ አገልግሎት (Ride)", "ለጉብኝት (Tour)"]
    if message.text not in valid_options:
        await message.answer("❌ እባክዎ ይምረጡ፡ ለግል, ለድርጅት, ታክሲ አገልግሎት (Ride), ወይም ለጉብኝት (Tour)")
        return
    
    await state.update_data(rental_purpose=message.text)
    
    # Step 9: Region
    await message.answer(
        "*9ኛ ደረጃ፡* ኪራይ የሚገኝበት ክልል ያስገቡ፡\nምሳሌ፡ አዲስ አበባ, አዳማ, ሀዋሳ",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_rental_region)

# Step 9: Region
@dp.message(CarForm.waiting_for_rental_region)
async def get_rental_region(message: types.Message, state: FSMContext):
    await state.update_data(rental_region=message.text)
    
    # Skip condition and go directly to phone
    await ask_for_phone_rental(message, state)

# ====================
# COMMON FLOW - AMHARIC
# ====================

async def ask_for_phone(message: types.Message, state: FSMContext):
    # For sale flow
    await message.answer(
        "*ቀጣይ ደረጃ፡* የእርስዎ ስልክ ቁጥር ያስገቡ፡\n\n"
        "⚠️ *ጠቃሚ፡* ይህ ቁጥር ለብሮከራችን ብቻ ነው።\n"
        "በህዝባዊ ማስታወቂያ ውስጥ አይታይም።\n"
        "ገዢዎች/ተከራያዎች በመጀመሪያ ከእኛ ጋር ይገናኛሉ።\n\n"
        "ምሳሌ፡ 0910618029",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_phone)

async def ask_for_phone_rental(message: types.Message, state: FSMContext):
    # For rental flow - set condition to empty
    await state.update_data(condition="")
    
    await message.answer(
        "*ቀጣይ ደረጃ፡* የእርስዎ ስልክ ቁጥር ያስገቡ፡\n\n"
        "⚠️ *ጠቃሚ፡* ይህ ቁጥር ለብሮከራችን ብቻ ነው።\n"
        "በህዝባዊ ማስታወቂያ ውስጥ አይታይም።\n"
        "ገዢዎች/ተከራያዎች በመጀመሪያ ከእኛ ጋር ይገናኛሉ።\n\n"
        "ምሳሌ፡ 0910618029",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_phone)

# Collect phone (common for both)
@dp.message(CarForm.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    if not re.match(r'^09\d{8}$', message.text):
        await message.answer("❌ እባክዎ ትክክለኛ የኢትዮጵያ ስልክ ቁጥር ያስገቡ (09XXXXXXXX)")
        return
    
    await state.update_data(user_phone=message.text)
    
    data = await state.get_data()
    car_type = data.get('car_type', 'sale')
    
    photo_prompt = "*ቀጣይ ደረጃ (አማራጭ)፡* የመኪናውን ፎቶዎች ይላኩ፡\n\n"
    
    if car_type == 'sale':
        photo_prompt += "• ፊት ለፊት እይታ\n• ጎን እይታ\n• ውስጥ\n• ርቀት መለኪያ\n• ሞተር\n"
    else:
        photo_prompt += "• ፊት ለፊት እይታ\n• ጎን እይታ\n• ውስጥ\n• ዳሽቦርድ\n• ሞተር\n"
    
    photo_prompt += "\nእስከ 5 ፎቶዎች ይላኩ\nያለ ፎቶ ለመቀጠል /skip ይላኩ"
    
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
        await message.answer(f"✅ ፎቶ ታክሏል ({len(photos)}/5)\n{remaining} ተጨማሪ ሊጨመር ይችላል። ሲጠናቀቁ /done ይላኩ።")
    else:
        await message.answer("📸 ከፍተኛው 5 ፎቶዎች ተደርገዋል። ለመቀጠል /done ይላኩ።")

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
        
        ad_text = f"""🚗 *ለመሸጥ - {data['make']} {data['model']} {data['year']}*

📋 *ዝርዝሮች፡*
• አምራች፡ {data['make']}
• ሞዴል፡ {data['model']}
• ዓመት፡ {data['year']}
• ቀለም፡ {data['color']}
• ፕሌት፡ {plate_display}
• ዋጋ፡ *{data['price']} ብር*

🔧 *ሁኔታ፡*
{data['condition']}

📞 *ከብሮከራችን ጋር ይገናኙ፡*
{broker_phones_formatted}

⚠️ *ማስታወሻ፡* ሁሉም ንግግሮች በብሮከር በኩል ብቻ።

#{data['make'].replace(" ", "")} #{data['model'].replace(" ", "")} 
#CarSale #አውቶሞቢል #AddisCarHub

*መኪናዎን ለመሸጥ ይፈልጋሉ?* በ @AddisCarHubBot ያስገቡ"""
    else:
        ad_text = f"""🏢 *ለኪራይ - {data['make']} {data['model']} {data['year']}*

📋 *የኪራይ ዝርዝሮች፡*
• አምራች፡ {data['make']}
• ሞዴል፡ {data['model']}
• ዓመት፡ {data['year']}
• የፕሌት ኮድ፡ {data.get('plate_code', '')}
• የቀን ዋጋ፡ *{data['price']} ብር/ቀን*
• ቅድመ ክፍያ፡ {data.get('rental_advanced', '')}
• የሚፈለገው ዋስትና፡ {data.get('rental_warranty', '')}
• ኪራይ ለ፡ {data.get('rental_purpose', '')}
• ክልል፡ {data.get('rental_region', 'N/A')}

📞 *ከብሮከራችን ጋር ይገናኙ፡*
{broker_phones_formatted}

⚠️ *ማስታወሻ፡* ሁሉም ቦታ ማሰራዎች በብሮከር በኩል ብቻ።

#{data['make'].replace(" ", "")} #{data['model'].replace(" ", "")} 
#CarRental #ኪራይ #AddisCarHub

*መኪናዎን ለኪራይ ይፈልጋሉ?* በ @AddisCarHubBot ያስገቡ"""
    
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
                 data['plate_code'], data['price'], "", data['car_type'], 
                 json.dumps(photos), data.get('rental_advanced', ''), data.get('rental_warranty', ''), 
                 data.get('rental_purpose', ''), data.get('rental_region', ''))
            )
        await db.commit()
    
    print(f"💾 {car_type.capitalize()} ማስታወቂያ ተቀምጧል: {data['make']} {data['model']}")
    
    # Notify admins with user info
    user_data = {
        'full_name': message.from_user.full_name,
        'username': message.from_user.username or 'N/A'
    }
    
    # Send notification to all admins (using the exact format you requested)
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
            print(f"📤 {car_type} ማስታወቂያ በ {len(photos)} ፎቶዎች ተለጠፈ")
        else:
            await bot.send_message(
                chat_id=ADMIN_CHANNEL,
                text=ad_text,
                parse_mode="Markdown"
            )
            print(f"📤 {car_type} ጽሑፍ ማስታወቂያ ተለጠፈ")
        
        # Send thank you message in Amharic
        thank_you_msg = f"""🎉 *አዲስ አበባ መኪና ማዕከልን ስለተጠቀሙ እናመሰግናለን!* 🚗

✅ የእርስዎ {data['make']} {data['model']} በ @AddisCarHub ቻናል ላይ ተለጥፏል።

*ምን ይሆናል?*
1. ብሮከራችን ዝርዝሩን ያረጋግጣል
2. ፍላጎት ያላቸው {'ገዢዎች' if car_type == 'sale' else 'ተከራያዎች'} ከእኛ ጋር ይገናኛሉ
3. እርስዎን ከከባድ ፍላጎት ባለቤቶች ጋር እናገናኛለን
4. በድርድር እና በወረቀት ስራ እንረዳለን

*የእርስዎ ግላዊነት የተጠበቀ ነው፡*
• የእርስዎ ስልክ ቁጥር ሚስጥራዊ ነው
• ሁሉም ንግግሮች በእኛ በኩል ይሆናሉ
• ሁሉንም ወገኖች እናረጋግጣለን

*ኮሚሽን፡* { '2% የመጨረሻ ዋጋ' if car_type == 'sale' else '10% የኪራይ ዋጋ' }

*ከወዳጆችዎ እና ከቤተሰቦችዎ ጋር ያጋሩ፡*
🤖 ቦት: @AddisCarHubBot
📢 ቻናል: @AddisCarHub

*እገዛ ያስፈልግዎታል?* ከብሮከራችን ጋር ይገናኙ: {BROKER_PHONES[0]}

አዲስ አበባ መኪና ማዕከልን ስለታመኑ እናመሰግናለን! 🙏"""
        
        await message.answer(
            thank_you_msg,
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="/start")]],
                resize_keyboard=True
            )
        )
        
    except Exception as e:
        error_msg = f"ስህተት በማስተላለፍ: {str(e)}"
        print(f"❌ {error_msg}")
        await message.answer(f"❌ ስህተት: {str(e)}\n\nእባክዎ እንደገና ይሞክሩ ወይም {BROKER_PHONES[0]} ይደውሉ")
    
    await state.clear()

# Stats command
@dp.message(F.text == "📊 የእኔ ስታቲስቲክስ")
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
        stats_msg = f"""📊 *የእርስዎ ስታቲስቲክስ*

• የተለጠፉ ማስታወቂያዎች: {user_ads[0]}
• በስርዓቱ ውስጥ ያሉ አጠቃላይ ማስታወቂያዎች: {total_ads[0]}
• ከዚህ ጊዜ ጀምሮ አባል: {user_info[0][:10] if user_info[0] else 'ዛሬ'}

*የብሮከር መረጃ፡*
• ቻናል: {ADMIN_CHANNEL}
• ብሮከር: {BROKER_NAME}
• ስልኮች: {', '.join(BROKER_PHONES[:2])}

በመለጠፍ ይቀጥሉ! እያንዳንዱ ማስታወቂያ የመሸጥ/ኪራይ እድልዎን ይጨምራል።"""
    else:
        stats_msg = "እስካሁን ምንም ማስታወቂያ አልለጠፉም። ለመጀመር 🚗 መኪና ለመሸጥ ወይም 🏢 መኪና ለመከራየት ይጠቀሙ!"
    
    await message.answer(stats_msg, parse_mode="Markdown")

# Cancel command
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ ስራው ተሰርዟል።\n\n"
        "እንደገና ለመጀመር /start ይላኩ ወይም ከታች ካለው አማራጭ ይምረጡ።",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="🚗 መኪና ለመሸጥ"), 
                 types.KeyboardButton(text="🏢 መኪና ለመከራየት")],
                [types.KeyboardButton(text="📞 ብሮከር ለመገናኘት")]
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
    
    print("🤖 ቦት መስራት ጀምሯል...")
    print("✅ ሁሉም ስርዓቶች ዝግጁ ናቸው!")
    await dp.start_polling(bot)

def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    asyncio.run(run_bot())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("="*60)
    print("🚗 አዲስ አበባ መኪና ማዕከል ቦት - ሙሉ አማርኛ ስሪት")
    print("="*60)
    main()
