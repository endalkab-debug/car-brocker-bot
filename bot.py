import os
import asyncio
import logging
import re
import json
import threading
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite

from flask import Flask

# =====================
# BASIC CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL = os.getenv("ADMIN_CHANNEL", "@AddisCarHub")
ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS", "[]"))
BROKER_PHONES = json.loads(os.getenv(
    "BROKER_PHONES",
    '["+251912345678", "+251911223344"]'
))

DB_PATH = "car_broker.db"

# =====================
# FLASK KEEP-ALIVE
# =====================
app = Flask(__name__)

@app.route("/")
def home():
    return "🚗 Addis Car Hub Bot is Running"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))

# =====================
# BOT INIT
# =====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =====================
# DATABASE
# =====================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            user_phone TEXT,
            make TEXT,
            model TEXT,
            year TEXT,
            plate_code TEXT,
            price TEXT,
            condition TEXT,
            car_type TEXT,
            photos TEXT,
            rental_advanced TEXT,
            rental_warranty TEXT,
            rental_purpose TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()

# =====================
# STATES
# =====================
class CarForm(StatesGroup):
    waiting_for_make = State()
    waiting_for_model = State()
    waiting_for_year = State()

    # SALE
    waiting_for_color = State()
    waiting_for_sale_price = State()

    # RENTAL
    waiting_for_rental_plate_code = State()
    waiting_for_rental_price = State()
    waiting_for_advanced_payment = State()
    waiting_for_warranty_needed = State()
    waiting_for_rental_purpose = State()
    waiting_for_rental_region = State()

    # COMMON
    waiting_for_phone = State()
    waiting_for_condition = State()
    waiting_for_photos = State()

# =====================
# START
# =====================
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="🚗 መኪና ለመሸጥ"),
         types.KeyboardButton(text="🏢 መኪና ለመከራየት")]
    ]
    await message.answer(
        "🚗 *Addis Car Hub*\n\nመኪና ለመሸጥ ወይም ለመከራየት ይምረጡ፡",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=kb, resize_keyboard=True
        )
    )

# =====================
# SALE FLOW
# =====================
@dp.message(F.text == "🚗 መኪና ለመሸጥ")
async def sale_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(car_type="sale")
    await message.answer("*Make* ያስገቡ፡", parse_mode="Markdown",
                         reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CarForm.waiting_for_make)

# =====================
# RENTAL FLOW
# =====================
@dp.message(F.text == "🏢 መኪና ለመከራየት")
async def rental_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(car_type="rental")
    await message.answer("*Make* ያስገቡ፡", parse_mode="Markdown",
                         reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CarForm.waiting_for_make)

# =====================
# COMMON MAKE / MODEL / YEAR
# =====================
@dp.message(CarForm.waiting_for_make)
async def get_make(message: types.Message, state: FSMContext):
    await state.update_data(make=message.text)
    await message.answer("*Model* ያስገቡ፡", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_model)

@dp.message(CarForm.waiting_for_model)
async def get_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("*Year* ያስገቡ፡", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_year)

@dp.message(CarForm.waiting_for_year)
async def get_year(message: types.Message, state: FSMContext):
    await state.update_data(year=message.text)
    data = await state.get_data()

    if data["car_type"] == "sale":
        await message.answer("*Color* ያስገቡ፡", parse_mode="Markdown")
        await state.set_state(CarForm.waiting_for_color)
    else:
        await message.answer(
            "Plate Code (1, 2, or 3) ያስገቡ፡",
            parse_mode="Markdown"
        )
        await state.set_state(CarForm.waiting_for_rental_plate_code)

# =====================
# SALE CONTINUATION
# =====================
@dp.message(CarForm.waiting_for_color)
async def sale_color(message: types.Message, state: FSMContext):
    await state.update_data(color=message.text)
    await message.answer("*Sale Price* በብር፡", parse_mode="Markdown")
    await state.set_state(CarForm.waiting_for_sale_price)

@dp.message(CarForm.waiting_for_sale_price)
async def sale_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await ask_phone(message, state)

# =====================
# RENTAL CONTINUATION (UPDATED)
# =====================
@dp.message(CarForm.waiting_for_rental_plate_code)
async def rental_plate(message: types.Message, state: FSMContext):
    if message.text not in ["1", "2", "3"]:
        await message.answer("❌ 1, 2, ወይም 3 ብቻ")
        return
    await state.update_data(plate_code=message.text)
    await message.answer(
        "Rental Price per Day (ለምሳሌ 1200, 1500, 3000)",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_rental_price)

@dp.message(CarForm.waiting_for_rental_price)
async def rental_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer(
        "Advanced Payment:\n• One Month\n• Two Months\n• Three Months",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_advanced_payment)

@dp.message(CarForm.waiting_for_advanced_payment)
async def rental_advance(message: types.Message, state: FSMContext):
    await state.update_data(rental_advanced=message.text)
    await message.answer(
        "Warranty Needed?\n• Yes, It’s Mandatory\n• No, It’s not Necessary",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_warranty_needed)

@dp.message(CarForm.waiting_for_warranty_needed)
async def rental_warranty(message: types.Message, state: FSMContext):
    await state.update_data(rental_warranty=message.text)
    await message.answer(
        "Rental Purpose:\n"
        "• ለግለሰብ\n"
        "• ለድርጅት\n"
        "• ታክሲ አገልግሎት (Ride)\n"
        "• ለጉብኝት (Tour)",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_rental_purpose)

@dp.message(CarForm.waiting_for_rental_purpose)
async def rental_purpose(message: types.Message, state: FSMContext):
    await state.update_data(rental_purpose=message.text)
    await message.answer(
        "Region where rental is available ONLY\n"
        "(Addis Ababa, Adama, Hawassa...)",
        parse_mode="Markdown"
    )
    await state.set_state(CarForm.waiting_for_rental_region)

@dp.message(CarForm.waiting_for_rental_region)
async def rental_region(message: types.Message, state: FSMContext):
    await state.update_data(rental_region=message.text)
    await ask_phone(message, state)

# =====================
# COMMON CONTINUATION
# =====================
async def ask_phone(message: types.Message, state: FSMContext):
    await message.answer("Phone Number (09XXXXXXXX):")
    await state.set_state(CarForm.waiting_for_phone)

@dp.message(CarForm.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    if not re.match(r"^09\d{8}$", message.text):
        await message.answer("❌ ትክክለኛ ቁጥር ያስገቡ")
        return
    await state.update_data(user_phone=message.text)
    await message.answer("Condition / Description:")
    await state.set_state(CarForm.waiting_for_condition)

@dp.message(CarForm.waiting_for_condition)
async def finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO cars
            (user_id, user_name, user_phone, make, model, year,
             plate_code, price, condition, car_type,
             rental_advanced, rental_warranty, rental_purpose)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message.from_user.id,
                message.from_user.full_name,
                data["user_phone"],
                data["make"],
                data["model"],
                data["year"],
                data.get("plate_code", ""),
                data["price"],
                message.text,
                data["car_type"],
                data.get("rental_advanced", ""),
                data.get("rental_warranty", ""),
                f"{data.get('rental_purpose','')} | {data.get('rental_region','')}"
            )
        )
        await db.commit()

    await message.answer("✅ ማስታወቂያዎ ተመዝግቧል\n/start")

# =====================
# RUN
# =====================
async def run_bot():
    await init_db()
    await dp.start_polling(bot)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(run_bot())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
