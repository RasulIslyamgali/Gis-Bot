import os
import json

import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from colorama import init, Fore
from fp.fp import FreeProxy


load_dotenv()  # it is needed if i run from localhost
API_TOKEN = os.getenv("API_TOKEN")
url_for_check_cors = "https://kakdobratsyado.ru/poisk-po-koordinatam/"


class Get_Data_Send_Cors(StatesGroup):
    hendl1 = State()  # get city name
    hendl2 = State()  # get street name
    hendl3 = State()  # get home number


def get_cors(street: str, home_number: str, city="Алматы"):
    street = "+".join(street.split(" ")).replace("++", "+")
    city = "+".join(city.split(" ")).replace("++", "+")
    url = f"https://www.google.kz/maps/place/улица+{street}+{home_number},+{city}"
    try:
        proxy = FreeProxy().get()
    except Exception as e:
        print(f"[INFO] Raise err while get proxy Exception: {e}")
        proxy = FreeProxy().get()
    print(Fore.GREEN, f"[INFO] proxy: {proxy}")
    print(Fore.BLUE, f"[INFO] url: {url}")
    proxyDict = {
        proxy.split(":")[0]: proxy
    }
    response = requests.get(url=url, proxies=proxyDict)
    print(Fore.GREEN, response.status_code)
    if str(response.status_code) == "200":
        content = BeautifulSoup(response.content, "html.parser")
        content.prettify()
        first_splitter = f"{city}\",null,[null,null,"
        next_splitter = city

        needed_parts = str(content).split(first_splitter)[-1].split(next_splitter)[0].split("]")[0].split(",")
        if needed_parts[0].startswith("<!DOCTYPE"):
            return "Пожалуйста введите правильные данные", 404, url
        return needed_parts[0], needed_parts[1], url
    else:
        return "Ошибка сети. Попробуйте чуть позже", 500, url


def get_keyboard():
    keyboard = types.ReplyKeyboardMarkup()
    button = types.KeyboardButton("Поделиться координатами", request_location=True)
    keyboard.add(button)
    return keyboard


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot, storage=MemoryStorage())


@dp.message_handler(commands=["start"])
async def say_hi(message: types.Message):
    await bot.send_message(message.from_user.id, f"Привет {message.from_user.first_name}\nЧтобы получить координаты по заданному адресу нажми /get_cors")
    print(message)


@dp.message_handler(commands=['locate_me'])
async def cmd_locate_me(message: types.Message):
    reply = "Нажмите на кнопку 'Поделиться координатами', чтобы поделиться координатами"
    await bot.send_message(message.from_user.id, reply, reply_markup=get_keyboard())


@dp.message_handler(content_types=['location'])
async def handle_location(message: types.Message):
    latitude = message.location.latitude
    longitude = message.location.longitude
    reply = "Широта:  {}\nДолгота: {}".format(latitude, longitude)
    with open(os.path.join(os.getcwd(), "Tools", "Banzai_addrs.json"), encoding="utf-8") as f:
        _data = json.load(f)

    addrs = _data["addrs"]

    hipot_list = []
    for i, a in enumerate(addrs):
        for key in a:
            cors = (a[key])
            kat1 = abs(cors[0] - latitude)
            kat2 = abs(cors[1] - longitude)
            hipot = (kat1 ** 2 + kat2 ** 2) ** 0.5
            hipot_list.append((hipot, i))
    hipot_list.sort(key=lambda k: k[0])

    most_closed_addr = addrs[hipot_list[0][1]]
    print("most_closed_addr", most_closed_addr)
    most_closed_addr_ = most_closed_addr
    for key in most_closed_addr:
        most_closed_addr = key

    sorted_addrs = ""
    for hip in hipot_list:
        addr = addrs[hip[1]]
        for k in addr:
            sorted_addrs += k + "\n"

    # send location
    for k in most_closed_addr_:
        cors = most_closed_addr_[k]
        await bot.send_location(message.from_user.id, cors[0], cors[1])

    await message.answer(reply, reply_markup=types.ReplyKeyboardRemove())
    await bot.send_message(message.from_user.id, f"Самый ближайший зал: {most_closed_addr}\n\nВсе залы по возрастанию расстояния:\n{sorted_addrs}")


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
    if message.from_user.id != 596834788:
        await bot.send_message(596834788,
                               f"Пользователь: {message.from_user.full_name}\nID: {message.from_user.id}\nКоординаты по адресу:\nулица {street_name} дом {message.text}\nгород {city}\n\n{cor1}\n{cor2}")
    if cor2 != 500 and cor2 != 404:
        await bot.send_message(message.from_user.id, f"Проверить правильность координат можете пройдя по ссылке: {url}\n\nЛибо в этом сайте: https://kakdobratsyado.ru/poisk-po-koordinatam/")
    await state.finish()
    with open(os.path.join(os.getcwd(), "Tools", "Banzai_addrs.json"), encoding="utf-8") as f:
        _data = json.load(f)

    addrs = _data["addrs"]

    hipot_list = []
    for i, a in enumerate(addrs):
        for key in a:
            cors = (a[key])
            kat1 = abs(cors[0] - float(cor1))
            kat2 = abs(cors[1] - float(cor2))
            hipot = (kat1 ** 2 + kat2 ** 2) ** 0.5
            hipot_list.append((hipot, i))
    hipot_list.sort(key=lambda k: k[0])

    most_closed_addr = addrs[hipot_list[0][1]]
    most_closed_addr_ = most_closed_addr

    for key in most_closed_addr:
        most_closed_addr = key

    sorted_addrs = ""
    for hip in hipot_list:
        addr = addrs[hip[1]]
        for k in addr:
            sorted_addrs += k + "\n"
    for k in most_closed_addr_:
        cors = most_closed_addr_[k]
        await bot.send_location(message.from_user.id, cors[0], cors[1])
    await bot.send_message(message.from_user.id,
                           f"Самый ближайший зал: {most_closed_addr}\n\nВсе залы по возрастанию расстояния:\n{sorted_addrs}")


@dp.message_handler()
async def say_hi(message: types.Message):
    await bot.send_message(message.from_user.id, f"Чтобы получить координату нажмите /get_cors")


if __name__ == "__main__":
    # init colorama
    init()
    executor.start_polling(dp, skip_updates=True)
