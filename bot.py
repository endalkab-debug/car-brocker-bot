# ================================
# ADDIS CAR HUB – BUTTON-BASED BOT
# With Confirmation Screen
# ================================

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

# ====================
# FLASK WEB SERVER
# ====================
app = Flask(__name__)

@app.route("/")
def home():
    return "🚗 Addis Car Hub Bot is running."

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

# ====================
# ENV CONFIG
# ====================
def get_env_list(name, default):
    try:
        return json.loads(os.getenv(name, "")) or default
    except:
        return default

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL = os.getenv("ADMIN_CHANNEL", "@AddisCarHub")
ADMIN_IDS = get_env_list("ADMIN_IDS", [])
BROKER_PHONES = get_env_list("BROKER_PHONES", ["+251912345678"])
BROKER_NAME = os.getenv("BROKER_NAME", "Addis Car Hub")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_PATH = "car_broker.db"

# ====================
# DATABASE
# ====================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            make TEXT,
            model TEXT,
            year TEXT,
            color TEXT,
            plate_code TEXT,
            plate_region TEXT,
            price TEXT,
            condition TEXT,
            car_type TEXT,
            photos TEXT,
            rental_advanced TEXT,
            rental_warranty TEXT,
            rental_purpose TEXT,
            rental_region TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()

# ====================
# FSM STATES
# ====================
class CarForm(StatesGroup):
    make = State()
    model = State()
    year = State()
    color = State()
    plate_code = State()
    plate_region = State()
    price = State()
    rental_advanced = State()
    rental_warranty = State()
    rental_purpose = State()
    rental_region = State()
    phone = State()
    condition = State()
    photos = State()
    confirm = State()

# ====================
# KEYBOARDS
# ====================
main_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="🚗 Car for Sale"), types.KeyboardButton(text="🏢 Car for Rental")],
        [types.KeyboardButton(text="📞 Contact Brokers")]
    ],
    resize_keyboard=True
)

plate_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="1 - Taxi")],
        [types.KeyboardButton(text="2 - Private")],
        [types.KeyboardButton(text="3 - Commercial")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

advance_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="One month")],
        [types.KeyboardButton(text="Two months")],
        [types.KeyboardButton(text="Three months")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

yes_no_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="Yes")],
        [types.KeyboardButton(text="No")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

purpose_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="Personal")],
        [types.KeyboardButton(text="Enterprise")],
        [types.KeyboardButton(text="Taxi (Ride)")],
        [types.KeyboardButton(text="Tour")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

photo_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="✅ Done"), types.KeyboardButton(text="⏭ Skip")]
    ],
    resize_keyboard=True
)

confirm_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="✅ Confirm & Post")],
        [types.KeyboardButton(text="✏️ Edit"), types.KeyboardButton(text="❌ Cancel")]
    ],
    resize_keyboard=True
)

# ====================
# START
# ====================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🚗 *Welcome to Addis Car Hub*\n\nPost your car for Sale or Rental.",
        parse_mode="Markdown",
        reply_markup=main_kb
    )

# ====================
# ENTRY POINTS
# ====================
@dp.message(F.text == "🚗 Car for Sale")
async def sale_start(message: types.Message, state: FSMContext):
    await state.update_data(car_type="sale")
    await message.answer("Enter car *Make*:", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CarForm.make)

@dp.message(F.text == "🏢 Car for Rental")
async def rental_start(message: types.Message, state: FSMContext):
    await state.update_data(car_type="rental")
    await message.answer("Enter car *Make*:", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CarForm.make)

# ====================
# COMMON INPUT FLOW
# ====================
@dp.message(CarForm.make)
async def get_make(message: types.Message, state: FSMContext):
    await state.update_data(make=message.text)
    await message.answer("Enter *Model*:", parse_mode="Markdown")
    await state.set_state(CarForm.model)

@dp.message(CarForm.model)
async def get_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Enter *Year*:", parse_mode="Markdown")
    await state.set_state(CarForm.year)

@dp.message(CarForm.year)
async def get_year(message: types.Message, state: FSMContext):
    await state.update_data(year=message.text)
    data = await state.get_data()
    if data["car_type"] == "sale":
        await message.answer("Enter *Color*:", parse_mode="Markdown")
        await state.set_state(CarForm.color)
    else:
        await message.answer("Select *Plate Code*:", reply_markup=plate_kb)
        await state.set_state(CarForm.plate_code)

@dp.message(CarForm.color)
async def get_color(message: types.Message, state: FSMContext):
    await state.update_data(color=message.text)
    await message.answer("Select *Plate Code*:", reply_markup=plate_kb)
    await state.set_state(CarForm.plate_code)

@dp.message(CarForm.plate_code)
async def get_plate(message: types.Message, state: FSMContext):
    await state.update_data(plate_code=message.text)
    data = await state.get_data()
    if data["car_type"] == "sale":
        await message.answer("Enter *Price (Birr)*:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(CarForm.price)
    else:
        await message.answer("Select *Advance Payment*:", reply_markup=advance_kb)
        await state.set_state(CarForm.rental_advanced)

# ====================
# RENTAL ONLY
# ====================
@dp.message(CarForm.rental_advanced)
async def rental_advance(message: types.Message, state: FSMContext):
    await state.update_data(rental_advanced=message.text)
    await message.answer("Warranty required?", reply_markup=yes_no_kb)
    await state.set_state(CarForm.rental_warranty)

@dp.message(CarForm.rental_warranty)
async def rental_warranty(message: types.Message, state: FSMContext):
    await state.update_data(rental_warranty=message.text)
    await message.answer("Select *Rental Purpose*:", reply_markup=purpose_kb)
    await state.set_state(CarForm.rental_purpose)

@dp.message(CarForm.rental_purpose)
async def rental_purpose(message: types.Message, state: FSMContext):
    await state.update_data(rental_purpose=message.text)
    await message.answer("Enter *Rental Region*:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CarForm.rental_region)

@dp.message(CarForm.rental_region)
async def rental_region(message: types.Message, state: FSMContext):
    await state.update_data(rental_region=message.text)
    await message.answer("Enter *Daily Price*:", parse_mode="Markdown")
    await state.set_state(CarForm.price)

# ====================
# FINAL DETAILS
# ====================
@dp.message(CarForm.price)
async def get_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Describe *Condition*:", parse_mode="Markdown")
    await state.set_state(CarForm.condition)

@dp.message(CarForm.condition)
async def get_condition(message: types.Message, state: FSMContext):
    await state.update_data(condition=message.text, photos=[])
    await message.answer("Send photos (up to 5) or choose:", reply_markup=photo_kb)
    await state.set_state(CarForm.photos)

@dp.message(CarForm.photos, F.photo)
async def add_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data["photos"]
    if len(photos) < 5:
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)

@dp.message(CarForm.photos, F.text.in_(["✅ Done", "⏭ Skip"]))
async def confirm_screen(message: types.Message, state: FSMContext):
    data = await state.get_data()

    summary = f"""
📋 *Review Your Ad*

🚗 {data['make']} {data['model']} ({data['year']})
💰 Price: {data['price']}
📄 Plate: {data['plate_code']}
📝 Condition:
{data['condition']}
"""

    await message.answer(summary, parse_mode="Markdown", reply_markup=confirm_kb)
    await state.set_state(CarForm.confirm)

# ====================
# CONFIRM / EDIT / CANCEL
# ====================
@dp.message(CarForm.confirm, F.text == "❌ Cancel")
async def cancel_all(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Cancelled.", reply_markup=main_kb)

@dp.message(CarForm.confirm, F.text == "✏️ Edit")
async def edit_restart(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("✏️ Let's start again.", reply_markup=main_kb)

@dp.message(CarForm.confirm, F.text == "✅ Confirm & Post")
async def post_ad(message: types.Message, state: FSMContext):
    data = await state.get_data()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO cars 
            (user_id, make, model, year, color, plate_code, price, condition, car_type, photos,
             rental_advanced, rental_warranty, rental_purpose, rental_region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message.from_user.id,
                data.get("make"),
                data.get("model"),
                data.get("year"),
                data.get("color"),
                data.get("plate_code"),
                data.get("price"),
                data.get("condition"),
                data.get("car_type"),
                json.dumps(data.get("photos", [])),
                data.get("rental_advanced"),
                data.get("rental_warranty"),
                data.get("rental_purpose"),
                data.get("rental_region")
            )
        )
        await db.commit()

    await message.answer("✅ Your ad has been posted successfully!", reply_markup=main_kb)
    await state.clear()

# ====================
# RUN
# ====================
async def run_bot():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(run_bot())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
