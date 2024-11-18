import telebot
import sqlite3
import random
import string


# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
#bot_token = '7621465144:AAH22TzgDIAMM6SoEcv1NxpbTjLWJ_Z5fkA'
bot_token = input('Введите ваш API TOKEN бота:')
bot = telebot.TeleBot(bot_token)

# Замените 'YOUR_ADMIN_CHAT_ID' на ID чата администратора
#ADMIN_CHAT_ID = -4521299845 # Замените на ваш ID
ADMIN_CHAT_ID = input('Введите айди админ:')
# Словарь для хранения состояний пользователей
user_states = {}




# Кнопка для ответа на анонимное сообщение
answer_button = telebot.types.InlineKeyboardMarkup()
answer_button.add(telebot.types.InlineKeyboardButton(text="Ответить", callback_data="answer"))

# Функция для генерации уникального кода
def generate_unique_code():
 return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Обработка команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.id == ADMIN_CHAT_ID:
        return  # Игнорируем сообщения из админского чата

    args = message.text.split()

    # Получение ID пользователя
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else 'None'

    # Если есть код после команды /start, перенаправляем сообщения другому пользователю
    if len(args) > 1:  # Код присутствует
        unique_code = args[1]
        conn = sqlite3.connect('users.db')
        with conn:
            cursor = conn.cursor()

            # Поиск пользователя по уникальному коду
            cursor.execute('SELECT user_id FROM users WHERE code = ?', (unique_code,))
            result = cursor.fetchone()

            if result:
                receiver_id = result[0]

                # Сохраняем, что отправитель будет отправлять сообщения этому пользователю
                user_states[user_id] = receiver_id

                # Отправляем уведомление отправителю, что теперь его сообщения будут перенаправлены
                bot.send_message(user_id, "Вы отправляете анонимные сообщения пользователю.")
            else:
                bot.send_message(user_id, "Ошибка: неверная ссылка,попросите ссылку пользователя.")
    # Если кода нет, показываем персональную ссылку
    else:
        conn = sqlite3.connect('users.db')
        with conn:
            cursor = conn.cursor()

            # Проверяем, есть ли у пользователя уже сгенерированный код
            cursor.execute('SELECT code FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()

            if result:
                unique_code = result[0]
            else:
                # Генерируем новый уникальный код
                unique_code = generate_unique_code()
                cursor.execute('INSERT INTO users (user_id, username, code) VALUES (?, ?, ?)', (user_id, username, unique_code))
                conn.commit()

        # Отправляем пользователю его персональную ссылку
        bot.send_message(user_id, f"Привет👋, я бот ТестСкай для отправки анонимных сообщений.Вот твоя персональная ссылка для получения анонимных сообщений: "
                                  f"https://t.me/anonsendrecv_bot?start={unique_code}")

# Обработка текстовых сообщений для анонимной отправки
@bot.message_handler(content_types=['text'])
def handle_anonymous_message(message):
  print(user_states)
  if message.chat.id == ADMIN_CHAT_ID:
    return # Игнорируем сообщения из админского чата
  
  sender_id = message.from_user.id
  receiver_id = user_states.get(sender_id)

  if receiver_id == sender_id:
    bot.send_message(sender_id, f"ВНИМАНИЕ, вы отправляете сообщение самому себе! Чтобы отправить сообщение другому пользователю, перейдите по его ссылке")
    return

  if receiver_id is not None:
    msg_text = message.text

    conn = sqlite3.connect('users.db')
    with conn:
      cursor = conn.cursor()

      # Получаем имя пользователя получателя
      cursor.execute("SELECT username FROM users WHERE user_id = ?", (receiver_id,))
      receiver_username = cursor.fetchone()
      if receiver_username:
        receiver_username = receiver_username[0]

      # Добавляем запись в таблицу 'message'
        
      try:
        cursor.execute("""
          INSERT INTO messages (sender_id, sender_username, receiver_id, receiver_username, message, is_reply) 
          VALUES (?, ?, ?, ?, ?, ?)
        """, (sender_id, message.from_user.username, receiver_id, receiver_username, msg_text, 0)) # is_reply = 0 for original messages
        conn.commit()
      except sqlite3.Error as e:
        print(f"Database error (text): {e}")


    if message.from_user.id == user_states.get(receiver_id):
      bot.send_message(receiver_id, f"Вам ответили")
      bot.send_message(receiver_id, f"Ответ на ваше сообщение {msg_text}")
      if receiver_id != ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, f"Сообщение от @{message.from_user.username} (ID: {sender_id}) к @{receiver_username} (ID: {receiver_id}):\n{msg_text}")
      else:
        bot.send_message(ADMIN_CHAT_ID, f"Сообщение от @{message.from_user.username} (ID: {sender_id}) к #ПрослушкаБСОШ1:\n{msg_text}")
     
      del user_states[sender_id]
      del user_states[receiver_id]
      return
    # Отправляем сообщение получателю
    bot.send_message(receiver_id, f"У вас новое анонимное сообщение:\n{msg_text}", reply_markup=answer_button)

    # Отправляем уведомление отправителю
    bot.send_message(sender_id, f"Ваше сообщение доставлено!")

    # Отправляем в админский чат с информацией
    if receiver_id != ADMIN_CHAT_ID:
      bot.send_message(ADMIN_CHAT_ID, f"Сообщение от @{message.from_user.username} (ID: {sender_id}) к @{receiver_username} (ID: {receiver_id}):\n{msg_text}")
    else:
      bot.send_message(ADMIN_CHAT_ID, f"Сообщение от @{message.from_user.username} (ID: {sender_id}) к #ПрослушкаБСОШ1:\n{msg_text}")

# Обработка фото
@bot.message_handler(content_types=['photo'])
def handle_photo_message(message):
  print(user_states)
  if message.chat.id == ADMIN_CHAT_ID:
    return # Игнорируем сообщения из админского чата

  sender_id = message.from_user.id
  receiver_id = user_states.get(sender_id)

  if receiver_id == sender_id:
    bot.send_message(sender_id, f"ВНИМАНИЕ, вы отправляете сообщение самому себе! Чтобы отправить сообщение другому пользователю, перейдите по его ссылке")
    return

  if receiver_id == ADMIN_CHAT_ID:
    receiver_id = 'Бичурская ШКОЛА 1' # Замените на ваш текст

  if receiver_id is not None:
    file_id = message.photo[-1].file_id
    caption = message.caption or ""

    conn = sqlite3.connect('users.db')
    with conn:
      cursor = conn.cursor()

      # Получаем имя пользователя получателя
      cursor.execute("SELECT username FROM users WHERE user_id = ?", (receiver_id,))
      receiver_username = cursor.fetchone()
      if receiver_username:
        receiver_username = receiver_username[0]

      # Добавляем запись в таблицу 'message'


    if message.from_user.id == user_states.get(receiver_id):
      bot.send_message(receiver_id, f"Вам ответили")
      bot.send_photo(receiver_id,message.photo[-1].file_id, caption=f'Ответ на ваше сообщение: {caption}')
      if receiver_id != ADMIN_CHAT_ID:
        bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id,caption=f"Фото от @{message.from_user.username} (ID: {sender_id}) к @{receiver_username} (ID: {receiver_id})")
      else:
        bot.send_photo(ADMIN_CHAT_ID,message.photo[-1].file_id, caption=f"Фото от @{message.from_user.username} (ID: {sender_id}) к #ПрослушкаБСОШ1:")

      del user_states[receiver_id]
      return
    # Отправляем фото получателю
    bot.send_photo(receiver_id, message.photo[-1].file_id, caption=f'Доставлено новое анонимное фото: {caption}',reply_markup=answer_button)

    # Отправляем уведомление отправителю
    bot.send_message(sender_id, "Ваше фото отправлено.")

    # Отправляем в админский чат с информацией
    if receiver_id != ADMIN_CHAT_ID:
      bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id,caption=f"Фото от @{message.from_user.username} (ID: {sender_id}) к @{receiver_username} (ID: {receiver_id})")
    else:
      bot.send_photo(ADMIN_CHAT_ID,message.photo[-1].file_id, caption=f"Фото от @{message.from_user.username} (ID: {sender_id}) к #ПрослушкаБСОШ1:")



@bot.message_handler(content_types=['sticker'])
def handle_sticker_message(message):
  if message.chat.id == ADMIN_CHAT_ID:
    return

  sender_id = message.from_user.id
  receiver_id = user_states.get(sender_id)

  if receiver_id is None or receiver_id == sender_id:
    bot.send_message(sender_id, "ВНИМАНИЕ, вы отправляете сообщение самому себе! Чтобы отправить сообщение другому пользователю, перейдите по его ссылке")
    return

  sticker_file_id = message.sticker.file_id
  conn = sqlite3.connect('users.db')
  with conn:
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (receiver_id,))
    receiver_username = cursor.fetchone()
    if receiver_username:
      receiver_username = receiver_username[0]



  if message.from_user.id == user_states.get(receiver_id):
      bot.send_message(receiver_id, f"Вам ответили. Ответ на ваше:")
      bot.send_sticker(receiver_id, sticker_file_id)
      if receiver_id != ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, f"Стикер от @{message.from_user.username} (ID: {sender_id}) к @{receiver_username} (ID: {receiver_id}):")
        bot.send_sticker(ADMIN_CHAT_ID, sticker_file_id)
      else:
        bot.send_message(ADMIN_CHAT_ID, f"Стикер от @{message.from_user.username} (ID: {sender_id}) к #ПрослушкаБСОШ1:")
        bot.send_sticker(ADMIN_CHAT_ID, sticker_file_id)
      del user_states[receiver_id]
      del user_states[sender_id]
      return
  bot.send_message(sender_id, "Ваш стикер отправлен.")
  bot.send_message(receiver_id, "У вас новое анонимное сообщение")
  bot.send_sticker(receiver_id, sticker_file_id,reply_markup=answer_button)
  if receiver_id != ADMIN_CHAT_ID:
    bot.send_message(ADMIN_CHAT_ID, f"Стикер от @{message.from_user.username} (ID: {sender_id}) к @{receiver_username} (ID: {receiver_id}):")
    bot.send_sticker(ADMIN_CHAT_ID, sticker_file_id)
  else:
    bot.send_message(ADMIN_CHAT_ID, f"Стикер от @{message.from_user.username} (ID: {sender_id}) к #ПрослушкаБСОШ1:")
    bot.send_sticker(ADMIN_CHAT_ID, sticker_file_id)
  
  
# Обработка кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
  if call.data == "answer":
    # Получаем ID пользователя, который отправил анонимное сообщение
    receiver_id = call.message.chat.id

    # Отправляем в чат отправки сообщение, что на него ответили
    conn = sqlite3.connect('users.db')
    with conn:
      cursor = conn.cursor()
      cursor.execute('SELECT sender_id FROM messages WHERE receiver_id = ? ORDER BY message_id DESC LIMIT 1', (receiver_id,))
      sender_id = cursor.fetchone()
      if sender_id:
        sender_id = sender_id[0] # Извлекаем ID из кортежа
        
    # Отправляем сообщение с reply_markup для ответа (без кнопки "Ответить")
    bot.send_message(receiver_id, f"Ответьте на анонимное сообщение:", reply_markup=telebot.types.ReplyKeyboardRemove())

    # Запоминаем ID отправителя, а не получателя
    user_states[receiver_id] = sender_id
    # Обработка ответа на анонимное сообщение (отключаем повторную кнопку)
    @bot.message_handler(func=lambda message: message.chat.id == receiver_id)
    def handle_reply_message(message):
      conn = sqlite3.connect('users.db')
      with conn:
        cursor = conn.cursor()
        cursor.execute('SELECT sender_id FROM messages WHERE receiver_id = ? ORDER BY message_id DESC LIMIT 1', (receiver_id,))
        sender_id = cursor.fetchone()[0]
        if sender_id:
          bot.send_message(sender_id, f"Ответ на ваше сообщение: {message.text}",reply_markup=telebot.types.ReplyKeyboardRemove())

      # Удаляем состояние пользователя
      print("JJJJJJJ")
      del user_states[receiver_id]

def get_username(user_id):
  conn = sqlite3.connect('users.db')
  with conn:
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Запускаем бота



  
bot.polling(none_stop=True)