import os
import typing
import data
import math
import datetime
import telebot
from telebot.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from token_storage import MEISNER_BOT_TOKEN
from datetime import datetime, timedelta
from data import MONTHS_RUS_NOM, MONTHS_RUS_GEN

# start - Привет, ребята!
# rent - Введи ренту в ₽ (например, 75555).
# cleaning - Узнай дату следующей уборки или задай новую.

bot = telebot.TeleBot(MEISNER_BOT_TOKEN)
cleaning_marker = 0
cleaning_choice_marker = 0
cleaning_options = ["Дата уборки",
                    "Задать дату следующей уборки"]


class IsAllowedID(telebot.custom_filters.SimpleCustomFilter):
    key = "is_allowed_id"

    @staticmethod
    def check(message: Message) -> int:
        return message.from_user.id in data.ALLOWED_IDS


def message_cutter(message: Message) -> str:
    count = 0
    initial = message.text
    for letter in initial:
        if letter == " ":
            return initial[count:]
        count += 1
    return ""


def add_date(days_amount: int) -> str:
    delta_days = timedelta(days=days_amount)
    future_date = datetime.now().date() + delta_days
    return future_date.isoformat()


def change_date_format(custom_date: datetime) -> str:
    return f"{custom_date.date().day} {MONTHS_RUS_GEN[custom_date.date().month]}"


def update_cleaning_date(filename: typing.Union[str, bytes, os.PathLike], new_date: typing.AnyStr) -> None:
    file = open(filename, mode="w")
    file.write(new_date)
    file.close()


def read_cleaning_date(filename: typing.Union[str, bytes, os.PathLike]) -> datetime:
    file = open(filename, mode="r")
    lines = file.readlines()
    file.close()
    return datetime.fromisoformat(lines[-1])


# @bot.message_handler()
# def testing(message: Message) -> None:
#     bot.send_message(chat_id=message.chat.id,
#                      text=f"{message.from_user.id}",
#                      reply_markup=ReplyKeyboardRemove())


@bot.message_handler(is_allowed_id=True, commands=["start"])
def greetings(message: Message) -> None:
    bot.send_message(chat_id=message.chat.id,
                     text="Привет, ребята!",
                     reply_markup=ReplyKeyboardRemove())


@bot.message_handler(is_allowed_id=True, commands=["rent"])
def rent_calculation(message: Message) -> None:
    try:
        if message_cutter(message) == "":
            bot.reply_to(message=message,
                         text="Ты забыл ввести сумму ренты.",
                         reply_markup=ReplyKeyboardRemove())
        else:
            command_text = message_cutter(message)
            rent = int(command_text)
            debt_neighbour = math.ceil((data.CLEANING_PRICE + data.INTERNET_PRICE) / 3)
            if rent > data.BASIC_RENT:
                bill = rent - data.BASIC_RENT
                room_one = data.RENT_SHARE[0] + math.ceil(bill / 3)
                room_two = data.RENT_SHARE[1] + math.ceil(bill / 3)
                room_three = data.RENT_SHARE[2] + math.ceil(bill / 3)
                bot.send_message(chat_id=message.chat.id,
                                 text=(
                                     f"Ребята, вот детализация за {MONTHS_RUS_NOM[(datetime.now().month + 1) % 12]}:"
                                     f"\n\n"
                                     f"{data.NAMES[0]} — `{room_one}` ₽\n"
                                     f"{data.NAMES[1]} — `{room_two}` ₽\n"
                                     f"{data.NAMES[2]} — `{room_three}` ₽\n\n"
                                     "Дополнительно:\n"
                                     f"{data.CLEANING_PRICE} ₽ — две уборки общей территории\n"
                                     f"{data.INTERNET_PRICE} ₽ — интернет\n\n"
                                     f"{data.NAMES[1]} и {data.NAMES[2]}, "
                                     f"переведите {data.NAMES_GEN[0]} по `{debt_neighbour}` ₽"),
                                 parse_mode="MarkdownV2",
                                 reply_markup=ReplyKeyboardRemove())
            else:
                bot.reply_to(message=message,
                             text=f"Что-то не так, должно быть больше {data.BASIC_RENT} руб.",
                             reply_markup=ReplyKeyboardRemove())
    except Exception:
        bot.send_message(chat_id=message.chat.id,
                         text="[" + message.from_user.first_name + "](tg://user?id=" +
                              str(message.from_user.id) + "), дружище, это же не число\.\.\.",
                         parse_mode="MarkdownV2",
                         reply_markup=ReplyKeyboardRemove())


@bot.message_handler(is_allowed_id=True, commands=["cleaning"])
def cleaning(message: Message) -> None:
    global cleaning_marker
    cleaning_marker = 1
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
    for i in range(len(cleaning_options)):
        keyboard.add(KeyboardButton(cleaning_options[i]))
    bot.reply_to(message=message,
                 text="Выбери опцию.",
                 reply_markup=keyboard)


@bot.message_handler(is_allowed_id=True, func=lambda message: message.text == cleaning_options[0])
def get_cleaning_date(message: Message) -> None:
    cleaning_date = read_cleaning_date("cleaning_date.txt")
    if datetime.now().date() <= cleaning_date.date():
        bot.send_message(chat_id=message.chat.id,
                         text=f"Следующая уборка будет {change_date_format(cleaning_date)} в 12:00!",
                         reply_markup=ReplyKeyboardRemove())
    else:
        cleaning_date += timedelta(days=14)
        update_cleaning_date("cleaning_date.txt", cleaning_date.date().isoformat())
        bot.send_message(chat_id=message.chat.id,
                         text=f"Обновила дату! Следующая уборка будет {change_date_format(cleaning_date)} в 12:00!",
                         reply_markup=ReplyKeyboardRemove())


@bot.message_handler(is_allowed_id=True, func=lambda message: message.text == cleaning_options[1])
def schedule_choice(message: Message) -> None:
    global cleaning_choice_marker
    days = []
    cleaning_choice_marker = 1
    if cleaning_marker == 1:
        for i in range(15):
            days.append(add_date(i))
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True, row_width=3)
        keyboard.add(*days)
        bot.reply_to(message=message,
                     text="Выбери день недели, в который будет проходить уборка.",
                     reply_markup=keyboard)


@bot.message_handler(is_allowed_id=True, func=lambda message: True)
def cleaning_reply(message: Message) -> None:
    global cleaning_marker, cleaning_choice_marker
    if cleaning_marker == 1 and cleaning_choice_marker == 1:
        filename = "cleaning_date.txt"
        file = open(filename, mode="w")
        file.write(message.text)
        file.close()
        date_chosen = datetime.fromisoformat(message.text)
        bot.reply_to(message=message,
                     text=f"Я запомнила: уборка будет {change_date_format(date_chosen)}!",
                     reply_markup=ReplyKeyboardRemove())
    cleaning_marker = 0
    cleaning_choice_marker = 0


bot.add_custom_filter(IsAllowedID())


bot.polling(none_stop=True)
