import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from telegram.ext import CallbackContext
import logging
import config  # Импортируем настройки из config.py

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен и настройки
TOKEN = config.TOKEN
ADMIN_ID = config.ADMIN_ID
PHOTO_PATH = config.PHOTO_PATH
IMAGE_DIR = config.IMAGE_DIR

# Состояния для ConversationHandler
ENTER_PHONE = 0
CONFIRM_ENTRY = 1
ADMIN_CONFIRM = 2

# Словарь для хранения данных пользователей
users = {}

# Функция для создания необходимых папок
def create_dirs():
    # Проверка и создание директории для изображений, если она не существует
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
        logger.info(f"Создана папка: {IMAGE_DIR}")
    # Если файл изображения не существует, логируем это
    if not os.path.exists(PHOTO_PATH):
        logger.warning(f"Изображение для отправки пользователю не найдено по пути: {PHOTO_PATH}")

# Начало взаимодействия с ботом
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Добро пожаловать! Отправьте ваш номер, чтобы начать.')
    return ENTER_PHONE

# Получаем номер телефона пользователя
def receive_phone(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    phone_number = update.message.text

    # Сохраняем номер в словарь
    users[user_id] = {'phone': phone_number}

    # Отправляем информацию в панель администратора
    context.bot.send_message(chat_id=ADMIN_ID, text=f"Новый запрос от пользователя {user_id}, номер: {phone_number}")

    # Отправляем код и фото пользователю
    context.bot.send_photo(
        chat_id=user_id,
        photo=open(PHOTO_PATH, 'rb'),  # Отправляем изображение, путь указанный в config.py
        caption=f"👤 Запрошен вход в ваш ВЦ с номером {phone_number}. Вот скриншот логина, присланный покупателем.\n\nАвторизуйте номер, затем либо пришлите скриншот с доказательством входа в ответ на данное сообщение, либо нажмите кнопку '✅ Вошел' в течение 3 минут."
    )

    # Создаем кнопки для подтверждения входа
    keyboard = [
        [InlineKeyboardButton("✅ Вошел", callback_data='success')],
        [InlineKeyboardButton("❌ Не смог войти, перешлите скриншот", callback_data='failed')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Нажмите одну из кнопок для подтверждения', reply_markup=reply_markup)

    return CONFIRM_ENTRY

# Обработка нажатий на кнопки
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    choice = query.data

    if choice == 'success':
        context.bot.send_message(chat_id=ADMIN_ID, text=f"Пользователь {user_id} успешно вошел.")
    elif choice == 'failed':
        context.bot.send_message(chat_id=ADMIN_ID, text=f"Пользователь {user_id} не смог войти.")

    query.answer()

# Прайс и инструкции
def price(update: Update, context: CallbackContext):
    update.message.reply_text("Цены на ВЦ:\n1 час — 9$\nПоследующий час — 3$")

def instructions(update: Update, context: CallbackContext):
    update.message.reply_text("Для того чтобы сдать ВЦ, отправьте номер, который вы хотите сдать, и ожидайте код, который пришлет вам бот.")

# Кнопки для администратора
def admin_buttons(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("✅ Успешно встал", callback_data='success_admin')],
        [InlineKeyboardButton("❌ Слет", callback_data='failed_admin')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Администратор, выберите действие:', reply_markup=reply_markup)

# Обработчик кнопок для администратора
def admin_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    choice = query.data

    if choice == 'success_admin':
        query.message.reply_text("Статус: Успешно встал.")
    elif choice == 'failed_admin':
        query.message.reply_text("Статус: Слет.")

    query.answer()

# Функция завершения
def end(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Процесс завершен.')
    return ConversationHandler.END

# Основная функция для бота
def main() -> None:
    # Создаем необходимые папки и файлы
    create_dirs()

    updater = Updater(TOKEN)

    dp = updater.dispatcher

    # Добавляем обработчики
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_PHONE: [MessageHandler(Filters.text & ~Filters.command, receive_phone)],
            CONFIRM_ENTRY: [CallbackQueryHandler(button)],
            ADMIN_CONFIRM: [CallbackQueryHandler(admin_button)],
        },
        fallbacks=[CommandHandler('end', end)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('price', price))
    dp.add_handler(CommandHandler('instructions', instructions))
    dp.add_handler(CommandHandler('admin', admin_buttons))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
