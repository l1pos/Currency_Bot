import telebot
from telebot import types
import requests
from config import TOKEN

bot = telebot.TeleBot(TOKEN)
user_data = {}

texts = {
    "ru": {
        "start": "👋 Привет! Выбери язык:",
        "choose_from": "Выбери валюту, из которой конвертировать:",
        "choose_to": "Теперь выбери валюту, в которую конвертировать:",
        "ask_amount": "Введите сумму для конвертации:",
        "error": "Ошибка. Попробуй ещё раз.",
        "result": "{} {} = {} {}",
        "invalid_amount": "Пожалуйста, введи число.",
        "language_selected": "Язык выбран: Русский 🇷🇺",
        "what_next": "Что дальше?",
        "repeat": "🔁 Повторить",
        "change_lang": "🌍 Сменить язык",
        "exit": "❌ Выход",
        "back": "⬅ Назад",
        "same_currency": "Валюты не должны совпадать.",
        "okay": "👍 Ок!"
    },
    "uk": {
        "start": "👋 Привіт! Обери мову:",
        "choose_from": "Обери валюту, з якої конвертувати:",
        "choose_to": "Тепер обери валюту, в яку конвертувати:",
        "ask_amount": "Введи суму для конвертації:",
        "error": "Помилка. Спробуй ще раз.",
        "result": "{} {} = {} {}",
        "invalid_amount": "Будь ласка, введи число.",
        "language_selected": "Мову обрано: Українська 🇺🇦",
        "what_next": "Що далі?",
        "repeat": "🔁 Повторити",
        "change_lang": "🌍 Змінити мову",
        "exit": "❌ Вихід",
        "back": "⬅ Назад",
        "same_currency": "Валюти не повинні співпадати.",
        "okay": "👍 Гаразд!"
    },
    "en": {
        "start": "👋 Hello! Please choose a language:",
        "choose_from": "Choose the currency to convert from:",
        "choose_to": "Now choose the currency to convert to:",
        "ask_amount": "Enter the amount to convert:",
        "error": "Error. Please try again.",
        "result": "{} {} = {} {}",
        "invalid_amount": "Please enter a valid number.",
        "language_selected": "Language selected: English 🇬🇧",
        "what_next": "What next?",
        "repeat": "🔁 Repeat",
        "change_lang": "🌍 Change language",
        "exit": "❌ Exit",
        "back": "⬅ Back",
        "same_currency": "Currencies must not be the same.",
        "okay": "👍 Okay!"
    }
}

currencies = ["USD", "EUR", "UAH", "GBP", "JPY"]


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id in user_data and "lang" in user_data[user_id]:
        lang = user_data[user_id]["lang"]
        bot.send_message(message.chat.id, texts[lang]["language_selected"])
        send_currency_from_buttons(message, lang)
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            types.InlineKeyboardButton(
                "🇺🇦 Українська", callback_data="lang_uk"),
            types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        )
        bot.send_message(
            message.chat.id, "👋 Choose your language / Обери мову / Выберите язык:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_language(call):
    lang = call.data.split("_")[1]
    user_data[call.from_user.id] = {"lang": lang}
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=texts[lang]["language_selected"])
    send_currency_from_buttons(call.message, lang)


def send_currency_from_buttons(message, lang):
    markup = types.InlineKeyboardMarkup()
    for cur in currencies:
        markup.add(types.InlineKeyboardButton(
            cur, callback_data=f"from_{cur}"))
    markup.add(types.InlineKeyboardButton(
        texts[lang]["back"], callback_data="back_lang"))
    bot.send_message(
        message.chat.id, texts[lang]["choose_from"], reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("from_") or call.data == "back_lang")
def choose_from_currency(call):
    user_id = call.from_user.id
    if user_id not in user_data or "lang" not in user_data[user_id]:
        start(call.message)
        return

    lang = user_data[user_id]["lang"]

    if call.data == "back_lang":
        start(call.message)
        return

    base = call.data.split("_")[1]
    user_data[user_id]["base"] = base

    markup = types.InlineKeyboardMarkup()
    for cur in currencies:
        if cur != base:
            markup.add(types.InlineKeyboardButton(
                cur, callback_data=f"to_{cur}"))
    markup.add(types.InlineKeyboardButton(
        texts[lang]["back"], callback_data="back_from"))
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=texts[lang]["choose_to"],
                          reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("to_") or call.data == "back_from")
def choose_to_currency(call):
    user_id = call.from_user.id
    if user_id not in user_data or "lang" not in user_data[user_id]:
        start(call.message)
        return

    lang = user_data[user_id]["lang"]

    if call.data == "back_from":
        send_currency_from_buttons(call.message, lang)
        return

    target = call.data.split("_")[1]
    user_data[user_id]["target"] = target
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=texts[lang]["ask_amount"])


def convert_currency(amount, base, target):
    url = f"https://open.er-api.com/v6/latest/{base}"
    r = requests.get(url)
    data = r.json()
    if data.get("result") != "success":
        return None
    rates = data.get("rates", {})
    if target not in rates:
        return None
    return round(amount * rates[target], 2)


@bot.message_handler(func=lambda message: message.from_user.id in user_data and "target" in user_data[message.from_user.id])
def handle_amount(message):
    user_id = message.from_user.id
    lang = user_data[user_id]["lang"]
    try:
        amount = float(message.text.replace(",", "."))
        base = user_data[user_id]["base"]
        target = user_data[user_id]["target"]

        if base == target:
            bot.send_message(message.chat.id, texts[lang]["same_currency"])
            return

        converted = convert_currency(amount, base, target)
        if converted is not None:
            bot.send_message(message.chat.id, texts[lang]["result"].format(
                amount, base, converted, target))
        else:
            bot.send_message(message.chat.id, texts[lang]["error"])
    except ValueError:
        bot.send_message(message.chat.id, texts[lang]["invalid_amount"])
    except Exception as e:
        bot.send_message(message.chat.id, f"{texts[lang]['error']}\n🔧 {e}")
    finally:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                texts[lang]["repeat"], callback_data="repeat"),
            types.InlineKeyboardButton(
                texts[lang]["change_lang"], callback_data="change_lang"),
            types.InlineKeyboardButton(
                texts[lang]["exit"], callback_data="exit")
        )
        bot.send_message(
            message.chat.id, texts[lang]["what_next"], reply_markup=markup)
        user_data.pop(user_id, None)


@bot.callback_query_handler(func=lambda call: call.data in ["repeat", "change_lang", "exit"])
def handle_next_actions(call):
    user_id = call.from_user.id
    lang = user_data.get(user_id, {}).get("lang", "en")

    if call.data == "repeat":
        send_currency_from_buttons(call.message, lang)
    elif call.data == "change_lang":
        start(call.message)
    elif call.data == "exit":
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=texts[lang]["okay"])


if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
