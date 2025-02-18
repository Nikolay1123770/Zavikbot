import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from telegram.ext import CallbackContext
import os
import config  # Импортируем настройки из config.py

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен и ID администратора из config.py
TOKEN = config.TOKEN
ADMIN_ID = config.ADMIN_ID

# Путь к изображению
PHOTO_PATH = config.PHOTO_PATH

# Состояния для ConversationHandler
ENTER_PHONE = 0
CONFIRM_ENTRY = 1

# Словарь для хранения данных пользователей
users = {}

# Функция для отправки скриншота с кодом от администратора
def send_screenshot_to_user(update: Update, phone_number: str, user_id: int):
    # Отправляем скриншот с кодом входа пользователю
    with open(PHOTO_PATH, 'rb') as photo_file:
        update.message.reply_photo(
            photo=photo_file,
            caption=f"👤 Запрошен вход в ваш ВЦ с номером {phone_number}. Вот скриншот логина, присланный покупателем.\n\nАвторизуйте номер, затем либо пришлите скриншот с доказательством входа в ответ на данное сообщение, либо нажмите кнопку '✅ Вошел' в течение 3 минут."
        )

    # Создаем кнопки для подтверждения входа
    keyboard = [
        [InlineKeyboardButton("✅ Вошел", callback_data=f'success_{user_id}')],
        [InlineKeyboardButton("❌ Не смог войти, перешлите скриншот", callback_data=f'failed_{user_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Нажмите одну из кнопок для подтверждения', reply_markup=reply_markup)

    # Сохраняем данные в словарь
    users[user_id] = {'phone': phone_number, 'status': 'waiting'}

# Обработчик для старта бота
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Добро пожаловать! Пожалуйста, отправьте ваш номер, чтобы начать.')
    return ENTER_PHONE

# Получаем номер телефона пользователя
def receive_phone(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    phone_number = update.message.text

    # Сохраняем номер в словарь
    users[user_id] = {'phone': phone_number}

    # Отправляем информацию в панель администратора
    context.bot.send_message(chat_id=ADMIN_ID, text=f"Новый запрос от пользователя {user_id}, номер: {phone_number}")

    # Отправляем автоматически скриншот и код
    send_screenshot_to_user(update, phone_number, user_id)

    return CONFIRM_ENTRY

# Обработка нажатий на кнопки подтверждения
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = int(query.data.split('_')[1])
    choice = query.data.split('_')[0]

    if user_id not in users:
        query.answer()
        return

    # Если пользователь подтверждает вход
    if choice == 'success':
        users[user_id]['status'] = 'success'
        context.bot.send_message(chat_id=ADMIN_ID, text=f"Пользователь {user_id} успешно вошел.")

    # Если пользователь не смог войти
    elif choice == 'failed':
        users[user_id]['status'] = 'failed'
        context.bot.send_message(chat_id=ADMIN_ID, text=f"Пользователь {user_id} не смог войти, ожидается скриншот.")

    query.answer()

# Команда для отправки скриншота с кодом пользователю
def send_code(update: Update, context: CallbackContext) -> None:
    # Проверяем, что это администратор
    if update.message.from_user.id == ADMIN_ID:
        if len(context.args) > 0:
            user_id = int(context.args[0])  # Получаем ID пользователя
            if user_id in users:
                phone_number = users[user_id]['phone']
                send_screenshot_to_user(update, phone_number, user_id)
                update.message.reply_text(f"Скриншот отправлен пользователю {user_id}.")
            else:
                update.message.reply_text(f"Пользователь с ID {user_id} не найден.")
        else:
            update.message.reply_text("Пожалуйста, укажите ID пользователя, которому нужно отправить скриншот.")
    else:
        update.message.reply_text("У вас нет доступа к этой команде.")

# Прайс и инструкции
def price(update: Update, context: CallbackContext):
    price_text = f"Цены на ВЦ:\n1 час — {config.PRICE_INFO['1_hour']}$\nПоследующий час — {config.PRICE_INFO['subsequent_hour']}$"
    update.message.reply_text(price_text)

def instructions(update: Update, context: CallbackContext):
    update.message.reply_text("Для того чтобы сдать ВЦ, отправьте номер, который вы хотите сдать, и ожидайте код, который пришлет вам бот.")

# Функция завершения
def end(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Процесс завершен.')
    return ConversationHandler.END

# Основная функция для бота
def main() -> None:
    updater = Updater(TOKEN)

    dp = updater.dispatcher

    # Добавляем обработчики
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_PHONE: [MessageHandler(Filters.text & ~Filters.command, receive_phone)],
            CONFIRM_ENTRY: [CallbackQueryHandler(button)],
        },
        fallbacks=[CommandHandler('end', end)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('send_code', send_code))  # Команда для отправки скриншота
    dp.add_handler(CommandHandler('price', price))
    dp.add_handler(CommandHandler('instructions', instructions))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
