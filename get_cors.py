import os

import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage


load_dotenv()  # it is needed if i run from localhost
API_TOKEN = os.getenv("API_TOKEN")
url_for_check_cors = "https://kakdobratsyado.ru/poisk-po-koordinatam/"

class Get_Data_Send_Cors(StatesGroup):
    hendl1 = State()  # get city name
    hendl2 = State()  # get street name
    hendl3 = State()  # get home number


def get_cors(street: str, home_number: str, city="Алматы"):
    url = f"https://www.google.kz/maps/place/улица+{street}+{home_number},+{city}"
    response = requests.get(url=url)
    print(response.status_code)
    if str(response.status_code) == "200":
        content = BeautifulSoup(response.content, "html.parser")
        first_splitter = f"{city}\",null,[null,null,"
        next_splitter = city

        needed_parts = str(content).split(first_splitter)[-1].split(next_splitter)[0].split("]")[0].split(",")
        if needed_parts[0].startswith("<!DOCTYPE"):
            return "Пожалуйста введите правильные данные", 404, url
        return needed_parts[0], needed_parts[1], url
    else:
        return "Ошибка сети. Попробуйте чуть позже", 500, url


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot, storage=MemoryStorage())


@dp.message_handler(commands=["start"])
async def say_hi(message: types.Message):
    await bot.send_message(message.from_user.id, f"Привет {message.from_user.first_name}\nЧтобы получить координаты по заданному адресу нажми /get_cors")


@dp.message_handler(commands=["get_cors"])
async def get_city_name(message: types.Message):
    await bot.send_message(message.from_user.id, "Введите город")
    await Get_Data_Send_Cors.hendl1.set()


@dp.message_handler(state=Get_Data_Send_Cors.hendl1)
async def get_street_name(message: types.Message, state: FSMContext):
    await bot.send_message(message.from_user.id, "Введите название улицы")
    await state.get_state()
    await state.update_data(city=message.text.title())
    await Get_Data_Send_Cors.hendl2.set()


@dp.message_handler(state=Get_Data_Send_Cors.hendl2)
async def get_street_name(message: types.Message, state: FSMContext):
    await bot.send_message(message.from_user.id, "Введите номер дома")
    await state.update_data(street_name=message.text.title())
    await Get_Data_Send_Cors.hendl3.set()


@dp.message_handler(state=Get_Data_Send_Cors.hendl3)
async def send_cors(message: types.Message, state: FSMContext):
    data = await state.get_data("city")
    city = data["city"]
    street_name = data["street_name"]
    cor1, cor2, url = get_cors(city=city, street=street_name, home_number=message.text)
    await bot.send_message(message.from_user.id, f"Координаты по адресу:\nулица {street_name} дом {message.text}\nгород {city}\n\n{cor1}\n{cor2}")
    if cor2 != 500 and cor2 != 404:
        await bot.send_message(message.from_user.id, f"Проверить правильность координат можете пройдя по ссылке: {url}")
    await state.finish()


@dp.message_handler()
async def say_hi(message: types.Message):
    await bot.send_message(message.from_user.id, f"Чтобы получить координату нажмите /get_cors")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
