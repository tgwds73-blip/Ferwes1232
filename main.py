import telebot
from telebot import types
import json
import os
import time
import random
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
from collections import Counter

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = '8456295069:AAGz48djuL19fYnn9FCz8DgJRQgIO6rLlq0'
bot = telebot.TeleBot(BOT_TOKEN)
GAMES_CHANNEL_ID = -1003421344618

# Файлы данных
ORDERS_FILE = 'orders.json'
LIKES_FILE = 'likes.json'
ADMINS_FILE = 'admins.json'
USER_STATS_FILE = 'user_stats.json'
LIKE_COOLDOWN_FILE = 'like_cooldown.json'
GAME_STATS_FILE = 'game_stats.json'
WEEKLY_STATS_FILE = 'weekly_stats.json'
PREMIUM_FILE = 'premium_users.json'
BANNED_FILE = 'banned_users.json'
MUTED_FILE = 'muted_users.json'
ORDER_STATS_FILE = 'order_stats.json'

# Константы
LIKE_COOLDOWN_DAYS = 1000
ORDERS_PER_PAGE = 5
PREMIUM_CHAT_LINK = "https://t.me/+Cy47-Mts-h00ZDYy"
PREMIUM_CONTACT = "@sweacher"

# ========== ДАННЫЕ ==========
orders = []
likes_data = {}
admins = ["7885915159"]
user_states = {}
user_stats = {}
like_cooldowns = {}
game_stats = {}
weekly_stats = {}
premium_users = {}
banned_users = {}  # {"user_id": {"type": "silent"/"normal", "reason": "...", "until": "дата"}}
muted_users = {}  # {"user_id": {"reason": "...", "until": "дата"}}
order_stats = {}  # статистика заказов


# ========== ЗАГРУЗКА/СОХРАНЕНИЕ ==========
def load_all():
    global orders, likes_data, admins, user_stats, like_cooldowns, game_stats, weekly_stats, premium_users, banned_users, muted_users, order_stats

    files = {
        ORDERS_FILE: orders,
        LIKES_FILE: likes_data,
        ADMINS_FILE: admins,
        USER_STATS_FILE: user_stats,
        LIKE_COOLDOWN_FILE: like_cooldowns,
        GAME_STATS_FILE: game_stats,
        WEEKLY_STATS_FILE: weekly_stats,
        PREMIUM_FILE: premium_users,
        BANNED_FILE: banned_users,
        MUTED_FILE: muted_users,
        ORDER_STATS_FILE: order_stats
    }

    for file, data_var in files.items():
        if os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    if isinstance(data_var, list):
                        data_var.clear()
                        data_var.extend(json.load(f))
                    elif isinstance(data_var, dict):
                        data_var.clear()
                        data_var.update(json.load(f))
            except Exception as e:
                print(f"Ошибка загрузки {file}: {e}")


def save_all():
    files = {
        ORDERS_FILE: orders,
        LIKES_FILE: likes_data,
        ADMINS_FILE: admins,
        USER_STATS_FILE: user_stats,
        LIKE_COOLDOWN_FILE: like_cooldowns,
        GAME_STATS_FILE: game_stats,
        WEEKLY_STATS_FILE: weekly_stats,
        PREMIUM_FILE: premium_users,
        BANNED_FILE: banned_users,
        MUTED_FILE: muted_users,
        ORDER_STATS_FILE: order_stats
    }

    for file, data in files.items():
        try:
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения {file}: {e}")


# ========== ПРОВЕРКИ ==========
def is_admin(user_id):
    return str(user_id) in admins


def is_premium(user_id):
    return str(user_id) in premium_users


def is_banned(user_id):
    user_id = str(user_id)
    if user_id not in banned_users:
        return False, None

    ban_info = banned_users[user_id]

    # Проверяем, не истёк ли бан
    if 'until' in ban_info and ban_info['until']:
        try:
            until = datetime.fromisoformat(ban_info['until'])
            if datetime.now() > until:
                # Бан истёк
                del banned_users[user_id]
                save_all()
                return False, None
        except:
            pass

    return True, ban_info


def is_muted(user_id):
    user_id = str(user_id)
    if user_id not in muted_users:
        return False, None

    mute_info = muted_users[user_id]

    # Проверяем, не истёк ли мут
    if 'until' in mute_info and mute_info['until']:
        try:
            until = datetime.fromisoformat(mute_info['until'])
            if datetime.now() > until:
                del muted_users[user_id]
                save_all()
                return False, None
        except:
            pass

    return True, mute_info


def can_like(user_id):
    user_id_str = str(user_id)
    if user_id_str not in like_cooldowns:
        return True, None
    last_like_str = like_cooldowns[user_id_str]
    try:
        last_like_date = datetime.fromisoformat(last_like_str)
        next_like_date = last_like_date + timedelta(days=LIKE_COOLDOWN_DAYS)
        now = datetime.now()
        if now >= next_like_date:
            return True, None
        else:
            days_left = (next_like_date - now).days
            return False, days_left
    except:
        return True, None


def update_like_cooldown(user_id):
    user_id_str = str(user_id)
    like_cooldowns[user_id_str] = datetime.now().isoformat()
    save_all()


def get_user_display_name(user_id, username=None, first_name=None):
    user_id_str = str(user_id)
    if user_id_str in premium_users:
        prefix = premium_users[user_id_str].get('prefix', '')
        if prefix:
            return f"[{prefix}] {first_name or username or user_id}"
    return first_name or username or str(user_id)


def check_ban(message):
    """Проверяет, забанен ли пользователь"""
    user_id = message.from_user.id
    banned, ban_info = is_banned(user_id)

    if not banned:
        return True

    # Если обычный бан - уведомляем
    if ban_info.get('type') == 'normal':
        reason = ban_info.get('reason', 'Причина не указана')
        until = ban_info.get('until', 'навсегда')
        if until and until != 'навсегда':
            try:
                until_date = datetime.fromisoformat(until).strftime("%d.%m.%Y %H:%M")
                text = f"🚫 *Вы заблокированы*\n\n📝 Причина: {reason}\n⏱ До: {until_date}"
            except:
                text = f"🚫 *Вы заблокированы*\n\n📝 Причина: {reason}\n⏱ Навсегда"
        else:
            text = f"🚫 *Вы заблокированы*\n\n📝 Причина: {reason}\n⏱ Навсегда"

        bot.reply_to(message, text, parse_mode='Markdown')

    # Тихий бан - просто игнорируем
    return False


def check_mute_for_order(user_id):
    """Проверяет, может ли пользователь создавать заказы"""
    muted, mute_info = is_muted(user_id)
    return not muted, mute_info


# ========== БАЗА ИГР ==========
GAMES_DATABASE = {
    # ... (все игры из предыдущей версии) ...
    'frostpunk 2': list(range(1619, 1628)),
    'frostpunk2': list(range(1619, 1628)),
    's.t.a.l.k.e.r anomaly': list(range(1628, 1635)),
    'stalker anomaly': list(range(1628, 1635)),
    'аномали': list(range(1628, 1635)),
}


# ========== ДЕКОРАТОР ДЛЯ ПРОВЕРКИ БАНА ==========
def check_ban_decorator(func):
    def wrapper(message, *args, **kwargs):
        if not check_ban(message):
            return
        return func(message, *args, **kwargs)

    return wrapper


# ========== КОМАНДА START ==========
@bot.message_handler(commands=['start'])
@check_ban_decorator
def start_cmd(message):
    user_id = str(message.from_user.id)
    if user_id not in user_stats:
        user_stats[user_id] = {
            'downloads': 0,
            'created_orders': 0,
            'first_seen': datetime.now().isoformat(),
            'username': message.from_user.username,
            'first_name': message.from_user.first_name
        }
        save_all()

    text = """🎮 *Ferwes Games Bot*

🔍 *Напиши название игры* — я пришлю, если есть в базе.

📋 `/orders` — стол заказов  
📝 `/neworder` — заказать игру  
👤 `/myorders` — мои заказы  
📊 `/stats` — моя статистика  
🔥 `/top` — топ игр  
💎 `/premium` — премиум"""

    if is_admin(message.from_user.id):
        text += "\n\n👑 `/moderator` — панель модератора"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 Заказы", callback_data="show_orders"),
        types.InlineKeyboardButton("📝 Новый заказ", callback_data="new_order"),
        types.InlineKeyboardButton("👤 Мои заказы", callback_data="my_orders"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="my_stats"),
        types.InlineKeyboardButton("🔥 Топ игр", callback_data="show_top"),
        types.InlineKeyboardButton("💎 Премиум", callback_data="show_premium")
    )

    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)


# ========== КОМАНДА PREMIUM ==========
@bot.message_handler(commands=['premium'])
@check_ban_decorator
def premium_cmd(message):
    user_id = str(message.from_user.id)

    if user_id in premium_users:
        prefix_info = premium_users[user_id]
        text = f"""💎 *У вас уже есть премиум!*

Ваш префикс: `[{prefix_info.get('prefix', '')}]`
Куплен: {prefix_info.get('purchased_date', 'неизвестно')}

📌 Префикс работает, пока вы в чате:  
{PREMIUM_CHAT_LINK}

⚠️ *Важно:* не выходите из чата, иначе префикс сбросится.
📩 По вопросам: {PREMIUM_CONTACT}"""
    else:
        text = f"""💎 *Ferwes Premium — префикс в чате*

🔥 При покупке префикс сохраняется навсегда!

**Что даёт премиум:**
• Уникальный префикс в чате
• Выделение среди других пользователей
• Поддержка проекта

💳 *Реквизиты для оплаты:*  
ЮMoney: `4100119022808101`  
Стоимость: **150 рублей**

После оплаты пришлите скриншот {PREMIUM_CONTACT}

📌 *Обязательно:* вступите в чат:  
{PREMIUM_CHAT_LINK}

⚠️ Не выходите из чата, чтобы префикс не сбился."""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Вступить в чат", url=PREMIUM_CHAT_LINK))
    markup.add(types.InlineKeyboardButton("✍️ Написать @sweacher", url="https://t.me/sweacher"))

    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)


# ========== СТОЛ ЗАКАЗОВ ==========
@bot.message_handler(commands=['orders'])
@check_ban_decorator
def orders_cmd(message):
    show_orders_page(message.chat.id, 0, message)


def show_orders_page(chat_id, page=0, original_message=None):
    if not orders:
        bot.send_message(chat_id, "📭 *Нет заказов*")
        return

    total_pages = (len(orders) + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0

    start_idx = page * ORDERS_PER_PAGE
    end_idx = min(start_idx + ORDERS_PER_PAGE, len(orders))
    page_orders = orders[start_idx:end_idx]

    text = f"📋 *Стол заказов* (Страница {page + 1}/{total_pages})\n\n"

    for order in page_orders:
        try:
            order_date = datetime.fromisoformat(order['date']).strftime("%d.%m.%Y")
        except:
            order_date = "неизвестно"

        user_display = get_user_display_name(
            order.get('user_id'),
            order.get('username'),
            None
        )

        # Количество присоединившихся
        joined_count = len(order.get('joined', []))
        joined_text = f" 👥 {joined_count}" if joined_count > 0 else ""

        text += f"🎮 *{order['game']}*\n"
        text += f"👤 {user_display}\n"
        text += f"📅 {order_date} | 💾 {order.get('size', 'N/A')}\n"
        text += f"❤️ {order.get('likes', 0)} лайков{joined_text}\n"
        text += f"🆔 {order['id']}\n"
        text += "─\n"

    markup = types.InlineKeyboardMarkup(row_width=3)

    # Кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"orders_page_{page - 1}"))
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="current_page"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"orders_page_{page + 1}"))
    if nav_buttons:
        markup.row(*nav_buttons)

    # Кнопки для каждого заказа
    for order in page_orders:
        btn_text = f"❤️ {order['game'][:12]}"
        if len(order['game']) > 12:
            btn_text += "..."

        # Строка кнопок для заказа
        markup.row(
            types.InlineKeyboardButton(btn_text, callback_data=f"like_{order['id']}"),
            types.InlineKeyboardButton("👥 Хочу!", callback_data=f"join_{order['id']}"),
            types.InlineKeyboardButton("📤 Поделиться", callback_data=f"share_{order['id']}")
        )

    bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)


# ========== КОМАНДА MYORDERS ==========
@bot.message_handler(commands=['myorders'])
@check_ban_decorator
def myorders_cmd(message):
    user_id = message.chat.id
    user_orders = [o for o in orders if o.get('user_id') == user_id]

    if not user_orders:
        bot.send_message(message.chat.id, "📭 *У вас нет заказов*")
        return

    text = "👤 *Мои заказы*\n\n"
    for order in user_orders[-10:]:
        joined_count = len(order.get('joined', []))
        joined_text = f" 👥 {joined_count}" if joined_count > 0 else ""

        text += f"🎮 {order['game']}\n"
        text += f"🆔 {order['id']} | 💾 {order.get('size', 'N/A')}\n"
        text += f"❤️ {order.get('likes', 0)} лайков{joined_text}\n"
        text += "─\n"

    bot.send_message(message.chat.id, text, parse_mode='Markdown')


# ========== КОМАНДА NEWORDER ==========
@bot.message_handler(commands=['neworder'])
@check_ban_decorator
def neworder_cmd(message):
    # Проверяем мут на создание заказов
    muted, mute_info = check_mute_for_order(message.from_user.id)
    if muted:
        reason = mute_info.get('reason', 'Причина не указана')
        until = mute_info.get('until', 'навсегда')
        if until and until != 'навсегда':
            try:
                until_date = datetime.fromisoformat(until).strftime("%d.%m.%Y %H:%M")
                text = f"🔇 *Вы не можете создавать заказы*\n\n📝 Причина: {reason}\n⏱ До: {until_date}"
            except:
                text = f"🔇 *Вы не можете создавать заказы*\n\n📝 Причина: {reason}\n⏱ Навсегда"
        else:
            text = f"🔇 *Вы не можете создавать заказы*\n\n📝 Причина: {reason}\n⏱ Навсегда"

        bot.reply_to(message, text, parse_mode='Markdown')
        return

    user_states[message.chat.id] = 'waiting_game'
    bot.reply_to(message, "📝 *Напиши название игры:*", parse_mode='Markdown')


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'waiting_game')
@check_ban_decorator
def get_game(message):
    user_states[message.chat.id] = {'game': message.text, 'state': 'waiting_size'}
    bot.reply_to(message, "💾 *Напиши размер в ГБ:*", parse_mode='Markdown')


@bot.message_handler(
    func=lambda m: user_states.get(m.chat.id) and user_states[m.chat.id].get('state') == 'waiting_size')
@check_ban_decorator
def get_size(message):
    data = user_states[message.chat.id]
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"

    order_id = len(orders) + 1
    orders.append({
        'id': order_id,
        'game': data['game'],
        'size': message.text.upper() + " ГБ",
        'likes': 0,
        'liked_by': [],
        'joined': [],  # Кто присоединился
        'user_id': message.chat.id,
        'username': user_info,
        'date': datetime.now().isoformat()
    })

    user_id_str = str(message.from_user.id)
    if user_id_str not in user_stats:
        user_stats[user_id_str] = {'downloads': 0, 'created_orders': 0}
    user_stats[user_id_str]['created_orders'] = user_stats[user_id_str].get('created_orders', 0) + 1

    save_all()
    del user_states[message.chat.id]
    bot.reply_to(message, f"✅ *Заказ создан!*\n🆔 ID: {order_id}", parse_mode='Markdown')


# ========== КОМАНДА STATS ==========
@bot.message_handler(commands=['stats'])
@check_ban_decorator
def stats_cmd(message):
    user_id_str = str(message.from_user.id)

    if user_id_str not in user_stats:
        bot.reply_to(message, "📊 *Вы еще ничего не скачали*")
        return

    stats = user_stats[user_id_str]
    downloads = stats.get('downloads', 0)
    created_orders = stats.get('created_orders', 0)

    try:
        first_seen = datetime.fromisoformat(stats.get('first_seen', datetime.now().isoformat()))
        days_active = (datetime.now() - first_seen).days
    except:
        days_active = 0

    # Заказы пользователя
    user_orders = [o for o in orders if o.get('user_id') == message.chat.id]
    total_likes_received = sum(o.get('likes', 0) for o in user_orders)

    # Лайки, которые поставил пользователь
    total_likes_given = len([uid for uid in like_cooldowns if uid == user_id_str])

    premium_status = "✅ Да" if is_premium(message.from_user.id) else "❌ Нет"

    text = f"👤 *Ваша статистика*\n\n"
    text += f"📥 Скачано игр: {downloads}\n"
    text += f"📋 Создано заказов: {created_orders}\n"
    text += f"❤️ Получено лайков: {total_likes_received}\n"
    text += f"👍 Поставлено лайков: {total_likes_given}\n"
    text += f"📅 Активен дней: {days_active}\n"
    text += f"💎 Премиум: {premium_status}\n"

    # Кнопка для подробной статистики с графиком
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 Подробная статистика", callback_data="detailed_stats"))

    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)


# ========== ПОДРОБНАЯ СТАТИСТИКА С ГРАФИКОМ ==========
def generate_stats_chart(user_id):
    """Генерирует график активности пользователя"""
    try:
        # Собираем данные
        user_orders = [o for o in orders if o.get('user_id') == user_id]

        if not user_orders:
            return None

        # Группируем по месяцам
        months = {}
        for order in user_orders:
            try:
                date = datetime.fromisoformat(order['date'])
                month_key = date.strftime("%Y-%m")
                if month_key not in months:
                    months[month_key] = 0
                months[month_key] += 1
            except:
                pass

        if not months:
            return None

        # Сортируем по дате
        sorted_months = sorted(months.keys())
        values = [months[m] for m in sorted_months]
        labels = [m[5:7] + "/" + m[2:4] for m in sorted_months]  # ММ/ГГ

        # Создаём график
        plt.figure(figsize=(10, 6))
        plt.bar(labels, values, color='#36A2EB')
        plt.title('Активность по заказам', fontsize=16)
        plt.xlabel('Месяц/Год', fontsize=12)
        plt.ylabel('Количество заказов', fontsize=12)
        plt.grid(axis='y', alpha=0.3)

        # Сохраняем в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()

        return buf
    except Exception as e:
        print(f"Ошибка создания графика: {e}")
        return None


@bot.callback_query_handler(func=lambda call: call.data == "detailed_stats")
def detailed_stats_callback(call):
    user_id = call.from_user.id

    # Получаем статистику
    user_orders = [o for o in orders if o.get('user_id') == user_id]

    if not user_orders:
        bot.answer_callback_query(call.id, "❌ Недостаточно данных для статистики")
        return

    # Считаем статистику
    total_orders = len(user_orders)
    total_likes = sum(o.get('likes', 0) for o in user_orders)
    avg_likes = total_likes / total_orders if total_orders > 0 else 0

    # Самая популярная игра пользователя
    games_count = {}
    for order in user_orders:
        game = order['game']
        games_count[game] = games_count.get(game, 0) + 1

    most_popular = max(games_count.items(), key=lambda x: x[1]) if games_count else ("нет", 0)

    # Текст статистики
    text = f"📊 *Детальная статистика*\n\n"
    text += f"📋 Всего заказов: {total_orders}\n"
    text += f"❤️ Всего лайков: {total_likes}\n"
    text += f"⭐ Средний лайк: {avg_likes:.1f}\n"
    text += f"🎮 Частая игра: {most_popular[0]} ({most_popular[1]} раз)\n\n"

    # График
    chart_buf = generate_stats_chart(user_id)

    if chart_buf:
        bot.send_photo(
            call.message.chat.id,
            photo=chart_buf,
            caption=text,
            parse_mode='Markdown'
        )
    else:
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

    bot.answer_callback_query(call.id)


# ========== КОМАНДА TOP ==========
@bot.message_handler(commands=['top'])
@check_ban_decorator
def top_cmd(message):
    # Топ по скачиваниям
    if game_stats:
        sorted_games = sorted(game_stats.items(), key=lambda x: x[1]['downloads'], reverse=True)[:10]

        text = "🔥 *Топ игр по скачиваниям*\n\n"
        for i, (game, stats) in enumerate(sorted_games, 1):
            text += f"{i}. 🎮 {game} — {stats['downloads']} 📥\n"

        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "📊 *Нет данных для топа*")


# ========== КОМАНДА MODERATOR ==========
@bot.message_handler(commands=['moderator'])
def moderator_cmd(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ *Нет прав*")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("📢 Рассылка", callback_data="mod_broadcast"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="mod_stats"),
        types.InlineKeyboardButton("❌ Удалить заказ", callback_data="mod_delorder"),
        types.InlineKeyboardButton("👑 Добавить админа", callback_data="mod_addadmin"),
        types.InlineKeyboardButton("🔨 Бан", callback_data="mod_ban"),
        types.InlineKeyboardButton("🔇 Мут (заказы)", callback_data="mod_mute"),
        types.InlineKeyboardButton("📈 Графики", callback_data="mod_charts"),
        types.InlineKeyboardButton("💎 Премиум", callback_data="mod_premium"),
    ]

    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i + 1])
        else:
            markup.row(buttons[i])

    # Статистика для админа
    banned_count = len(banned_users)
    muted_count = len(muted_users)
    active_users = len(user_stats)

    text = f"""👑 *Панель модератора*

📊 *Статистика:*
• Заказов: {len(orders)}
• Пользователей: {active_users}
• Админов: {len(admins)}
• Забанено: {banned_count}
• Замучено: {muted_count}
• Премиум: {len(premium_users)}

⚡ *Команды:*
`/delorder 5` - Удалить заказ
`/addadmin 123` - Добавить админа
`/ban 123 причина [silent]` - Бан
`/mute 123 причина [часы]` - Мут
`/unban 123` - Разбан
`/unmute 123` - Снять мут
`/broadcast текст` - Рассылка"""

    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)


# ========== КОМАНДЫ БАНА ==========
@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 3:
            bot.reply_to(message,
                         "❌ */ban <ID> <причина> [silent]*\n\nПример: /ban 123456 Спам\nПример с тихим: /ban 123456 Спам silent",
                         parse_mode='Markdown')
            return

        user_id = parts[1]
        reason = parts[2]

        # Проверяем на silent
        ban_type = 'normal'
        if len(parts) > 3 and parts[3].lower() == 'silent':
            ban_type = 'silent'

        # Баним
        banned_users[user_id] = {
            'type': ban_type,
            'reason': reason,
            'until': None,  # None = навсегда
            'banned_by': str(message.from_user.id),
            'banned_at': datetime.now().isoformat()
        }

        save_all()

        type_text = "тихий" if ban_type == 'silent' else "обычный"
        bot.reply_to(message, f"✅ *Пользователь {user_id} забанен*\nТип: {type_text}\nПричина: {reason}",
                     parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")


@bot.message_handler(commands=['tempban'])
def tempban_cmd(message):
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split(maxsplit=4)
        if len(parts) < 4:
            bot.reply_to(message, "❌ */tempban <ID> <часы> <причина> [silent]*", parse_mode='Markdown')
            return

        user_id = parts[1]
        hours = int(parts[2])
        reason = parts[3]

        ban_type = 'normal'
        if len(parts) > 4 and parts[4].lower() == 'silent':
            ban_type = 'silent'

        until = datetime.now() + timedelta(hours=hours)

        banned_users[user_id] = {
            'type': ban_type,
            'reason': reason,
            'until': until.isoformat(),
            'banned_by': str(message.from_user.id),
            'banned_at': datetime.now().isoformat()
        }

        save_all()

        until_str = until.strftime("%d.%m.%Y %H:%M")
        type_text = "тихий" if ban_type == 'silent' else "обычный"
        bot.reply_to(message, f"✅ *Пользователь {user_id} забанен до {until_str}*\nТип: {type_text}\nПричина: {reason}",
                     parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")


@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = message.text.split()[1]

        if user_id in banned_users:
            del banned_users[user_id]
            save_all()
            bot.reply_to(message, f"✅ *Пользователь {user_id} разбанен*", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ Пользователь {user_id} не в бане")

    except:
        bot.reply_to(message, "❌ */unban <ID>*")


# ========== КОМАНДЫ МУТА (ТОЛЬКО НА ЗАКАЗЫ) ==========
@bot.message_handler(commands=['mute'])
def mute_cmd(message):
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 3:
            bot.reply_to(message,
                         "❌ */mute <ID> <причина> [часы]*\n\nПример: /mute 123456 Спам\nПример с временем: /mute 123456 Спам 24",
                         parse_mode='Markdown')
            return

        user_id = parts[1]
        reason = parts[2]

        until = None
        if len(parts) > 3:
            try:
                hours = int(parts[3])
                until = datetime.now() + timedelta(hours=hours)
            except:
                pass

        muted_users[user_id] = {
            'reason': reason,
            'until': until.isoformat() if until else None,
            'muted_by': str(message.from_user.id),
            'muted_at': datetime.now().isoformat()
        }

        save_all()

        if until:
            until_str = until.strftime("%d.%m.%Y %H:%M")
            bot.reply_to(message, f"✅ *Пользователь {user_id} замучен до {until_str}*\nПричина: {reason}",
                         parse_mode='Markdown')
        else:
            bot.reply_to(message, f"✅ *Пользователь {user_id} замучен навсегда*\nПричина: {reason}",
                         parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")


@bot.message_handler(commands=['unmute'])
def unmute_cmd(message):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = message.text.split()[1]

        if user_id in muted_users:
            del muted_users[user_id]
            save_all()
            bot.reply_to(message, f"✅ *С пользователя {user_id} снят мут*", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ Пользователь {user_id} не в муте")

    except:
        bot.reply_to(message, "❌ */unmute <ID>*")


# ========== КОМАНДА DELORDER ==========
@bot.message_handler(commands=['delorder'])
def delorder_cmd(message):
    if not is_admin(message.from_user.id):
        return
    try:
        order_id = int(message.text.split()[1])
        order_to_delete = None
        for order in orders:
            if order['id'] == order_id:
                order_to_delete = order
                break

        if not order_to_delete:
            bot.reply_to(message, f"❌ *Заказ #{order_id} не найден*")
            return

        liked_by = order_to_delete.get('liked_by', [])
        joined = order_to_delete.get('joined', [])
        game_name = order_to_delete['game']

        # Объединяем всех, кого нужно уведомить
        notify_users = list(set(liked_by + joined))

        user_states[message.chat.id] = {
            'state': 'waiting_delete_reason',
            'order_id': order_id,
            'notify_users': notify_users,
            'game_name': game_name
        }

        bot.reply_to(message,
                     f"📝 *Напиши причину удаления заказа #{order_id}*\n\n"
                     f"Уведомление получат: {len(notify_users)} пользователей (лайкнувшие и присоединившиеся)",
                     parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, "❌ */delorder <ID заказа>*")


@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('state') == 'waiting_delete_reason')
def process_delete_reason(message):
    data = user_states[message.chat.id]
    order_id = data['order_id']
    notify_users = data['notify_users']
    game_name = data['game_name']
    reason = message.text

    for i, order in enumerate(orders):
        if order['id'] == order_id:
            del orders[i]
            break

    save_all()

    # Отправляем уведомления
    sent_count = 0
    for user_id in notify_users:
        try:
            bot.send_message(int(user_id),
                             f"⚠️ *Заказ #{order_id} был удален*\n\n"
                             f"🎮 Игра: {game_name}\n"
                             f"📝 Причина: {reason}\n\n"
                             f"Спасибо за интерес! ❤️",
                             parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.1)
        except:
            pass

    bot.reply_to(message,
                 f"✅ *Заказ #{order_id} удален*\n\n"
                 f"📤 Уведомления отправлены: {sent_count}/{len(notify_users)} пользователям",
                 parse_mode='Markdown')

    del user_states[message.chat.id]


# ========== КОМАНДА ADDADMIN ==========
@bot.message_handler(commands=['addadmin'])
def addadmin_cmd(message):
    if not is_admin(message.from_user.id):
        return
    try:
        user_id = str(message.text.split()[1])
        if user_id in admins:
            bot.reply_to(message, "⚠️ *Уже админ*")
        else:
            admins.append(user_id)
            save_all()
            bot.reply_to(message, f"✅ *ID {user_id} получил права модератора*", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ */addadmin <ID>*")


# ========== КОМАНДА BROADCAST ==========
@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(message):
    if not is_admin(message.from_user.id):
        return

    try:
        message_text = message.text.split(' ', 1)[1]

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Да, отправить", callback_data="broadcast_confirm"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
        )

        bot.reply_to(
            message,
            f"📢 *Подтверждение рассылки*\n\n"
            f"Получателей: {len(user_stats)}\n\n"
            f"Сообщение:\n{message_text[:500]}...\n\n"
            f"Отправить всем пользователям?",
            parse_mode='Markdown',
            reply_markup=markup
        )

        user_states[message.chat.id] = {
            'broadcast_message': message_text,
            'state': 'awaiting_broadcast_confirmation'
        }

    except IndexError:
        bot.reply_to(message, "❌ */broadcast <текст сообщения>*")


# ========== ОБРАБОТЧИК КОМАНДЫ SHARE ==========
def share_order(order_id, chat_id, user_id):
    """Отправляет заказ для шеринга"""
    order = None
    for o in orders:
        if o['id'] == order_id:
            order = o
            break

    if not order:
        return None

    text = f"📤 *Вам поделились заказом*\n\n"
    text += f"🎮 Игра: {order['game']}\n"
    text += f"💾 Размер: {order.get('size', 'N/A')}\n"
    text += f"👤 Автор: {order.get('username', 'Unknown')}\n"
    text += f"❤️ Лайков: {order.get('likes', 0)}\n"
    text += f"🆔 ID: {order['id']}\n\n"
    text += f"Открыть заказ: /order_{order['id']}"

    return text


# ========== CALLBACK ОБРАБОТЧИК ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # Проверяем бан для callback (кроме админских)
    if not call.data.startswith('mod_') and not is_admin(call.from_user.id):
        banned, _ = is_banned(call.from_user.id)
        if banned:
            bot.answer_callback_query(call.id, "❌ Вы забанены")
            return

    # ЛАЙКИ
    if call.data.startswith('like_'):
        can_like_now, days_left = can_like(call.from_user.id)

        if not can_like_now:
            bot.answer_callback_query(
                call.id,
                f"❌ Вы уже ставили лайк! Следующий через {days_left} дней",
                show_alert=True
            )
            return

        order_id = int(call.data.split('_')[1])
        for order in orders:
            if order['id'] == order_id:
                if 'liked_by' not in order:
                    order['liked_by'] = []

                if str(call.from_user.id) in order['liked_by']:
                    bot.answer_callback_query(call.id, "❌ Вы уже лайкали этот заказ", show_alert=True)
                    return

                order['likes'] = order.get('likes', 0) + 1
                order['liked_by'].append(str(call.from_user.id))
                update_like_cooldown(call.from_user.id)
                save_all()

                bot.answer_callback_query(call.id, "❤️ Лайк поставлен!")
                return
        bot.answer_callback_query(call.id, "❌ Заказ не найден")

    # ПРИСОЕДИНИТЬСЯ К ЗАКАЗУ (ХОЧУ!)
    elif call.data.startswith('join_'):
        order_id = int(call.data.split('_')[1])
        user_id = str(call.from_user.id)

        for order in orders:
            if order['id'] == order_id:
                if 'joined' not in order:
                    order['joined'] = []

                if user_id in order['joined']:
                    bot.answer_callback_query(call.id, "✅ Вы уже присоединились")
                    return

                order['joined'].append(user_id)
                save_all()

                # Уведомляем автора заказа
                author_id = order.get('user_id')
                if author_id and author_id != call.from_user.id:
                    try:
                        user_name = call.from_user.first_name or f"ID {user_id}"
                        bot.send_message(
                            author_id,
                            f"👥 *К вашему заказу #{order_id} присоединились!*\n\n"
                            f"Пользователь: {user_name}\n"
                            f"Игра: {order['game']}",
                            parse_mode='Markdown'
                        )
                    except:
                        pass

                bot.answer_callback_query(call.id, "✅ Вы присоединились к заказу!")
                return

        bot.answer_callback_query(call.id, "❌ Заказ не найден")

    # ПОДЕЛИТЬСЯ ЗАКАЗОМ
    elif call.data.startswith('share_'):
        order_id = int(call.data.split('_')[1])

        share_text = share_order(order_id, call.message.chat.id, call.from_user.id)

        if share_text:
            # Создаём кнопку для отправки другу
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "📤 Отправить другу",
                switch_inline_query=f"order_{order_id}"
            ))

            bot.send_message(
                call.message.chat.id,
                share_text,
                parse_mode='Markdown',
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, "❌ Заказ не найден")

    # ПАГИНАЦИЯ
    elif call.data.startswith('orders_page_'):
        try:
            page = int(call.data.split('_')[2])
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_orders_page(call.message.chat.id, page, call.message)
        except:
            bot.answer_callback_query(call.id, "❌ Ошибка перехода")

    # КНОПКИ ИЗ START
    elif call.data == "show_orders":
        bot.delete_message(call.message.chat.id, call.message.message_id)

        # Создаём заглушку для вызова
        class MockMessage:
            def __init__(self, chat_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': call.from_user.id})

        orders_cmd(MockMessage(call.message.chat.id))

    elif call.data == "new_order":
        bot.delete_message(call.message.chat.id, call.message.message_id)

        class MockMessage:
            def __init__(self, chat_id, from_user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': from_user_id})

        neworder_cmd(MockMessage(call.message.chat.id, call.from_user.id))

    elif call.data == "my_orders":
        bot.delete_message(call.message.chat.id, call.message.message_id)

        class MockMessage:
            def __init__(self, chat_id, from_user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': from_user_id})

        myorders_cmd(MockMessage(call.message.chat.id, call.from_user.id))

    elif call.data == "my_stats":
        bot.delete_message(call.message.chat.id, call.message.message_id)

        class MockMessage:
            def __init__(self, chat_id, from_user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': from_user_id})

        stats_cmd(MockMessage(call.message.chat.id, call.from_user.id))

    elif call.data == "show_top":
        bot.delete_message(call.message.chat.id, call.message.message_id)

        class MockMessage:
            def __init__(self, chat_id, from_user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': from_user_id})

        top_cmd(MockMessage(call.message.chat.id, call.from_user.id))

    elif call.data == "show_premium":
        bot.delete_message(call.message.chat.id, call.message.message_id)

        class MockMessage:
            def __init__(self, chat_id, from_user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': from_user_id})

        premium_cmd(MockMessage(call.message.chat.id, call.from_user.id))

    # АДМИНСКИЕ КНОПКИ
    elif call.data.startswith('mod_'):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Нет прав")
            return

        if call.data == 'mod_broadcast':
            bot.send_message(call.message.chat.id,
                             "📢 */broadcast <текст>* - отправить сообщение всем пользователям")

        elif call.data == 'mod_stats':
            # Статистика для админа
            active_users = len(
                [u for u in user_stats if u in like_cooldowns or u in [str(o['user_id']) for o in orders]])

            text = "📊 *Полная статистика бота*\n\n"
            text += f"👥 Всего пользователей: {len(user_stats)}\n"
            text += f"📋 Заказов: {len(orders)}\n"
            text += f"❤️ Всего лайков: {sum(o.get('likes', 0) for o in orders)}\n"
            text += f"👑 Админов: {len(admins)}\n"
            text += f"🔨 Забанено: {len(banned_users)}\n"
            text += f"🔇 Замучено: {len(muted_users)}\n"
            text += f"💎 Премиум: {len(premium_users)}\n\n"

            # Топ игр
            if game_stats:
                top_games = sorted(game_stats.items(), key=lambda x: x[1]['downloads'], reverse=True)[:5]
                text += "🏆 *Топ-5 игр:*\n"
                for game, stats in top_games:
                    text += f"• {game} — {stats['downloads']} 📥\n"

            bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

        elif call.data == 'mod_delorder':
            bot.send_message(call.message.chat.id, "❌ */delorder <ID>*")

        elif call.data == 'mod_addadmin':
            bot.send_message(call.message.chat.id, "👑 */addadmin <ID>*")

        elif call.data == 'mod_ban':
            bot.send_message(call.message.chat.id,
                             "🔨 *Команды бана*\n\n"
                             "`/ban 123 причина [silent]` - навсегда\n"
                             "`/tempban 123 часы причина [silent]` - временно\n"
                             "`/unban 123` - разбанить\n\n"
                             "silent - тихий бан (без уведомления)")

        elif call.data == 'mod_mute':
            bot.send_message(call.message.chat.id,
                             "🔇 *Команды мута (только на заказы)*\n\n"
                             "`/mute 123 причина [часы]` - замутить\n"
                             "`/unmute 123` - снять мут")

        elif call.data == 'mod_charts':
            # Генерируем графики для админа
            try:
                # График заказов по дням
                dates = []
                for order in orders:
                    try:
                        date = datetime.fromisoformat(order['date']).strftime("%d.%m")
                        dates.append(date)
                    except:
                        pass

                if dates:
                    date_counts = Counter(dates)
                    sorted_dates = sorted(date_counts.keys())
                    values = [date_counts[d] for d in sorted_dates]

                    plt.figure(figsize=(12, 6))
                    plt.plot(range(len(sorted_dates)), values, marker='o', color='#36A2EB')
                    plt.xticks(range(len(sorted_dates)), sorted_dates, rotation=45)
                    plt.title('Заказы по дням', fontsize=16)
                    plt.grid(alpha=0.3)

                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', dpi=100)
                    buf.seek(0)
                    plt.close()

                    bot.send_photo(call.message.chat.id, photo=buf, caption="📈 *График заказов*", parse_mode='Markdown')
                else:
                    bot.send_message(call.message.chat.id, "📊 Нет данных для графика")

            except Exception as e:
                bot.send_message(call.message.chat.id, f"❌ Ошибка создания графика: {e}")

        elif call.data == 'mod_premium':
            bot.send_message(call.message.chat.id,
                             "💎 *Управление премиум*\n\n"
                             "`/addpremium 123 ник` - добавить премиум\n"
                             "`/removepremium 123` - удалить премиум")

    # РАССЫЛКА
    elif call.data == 'broadcast_confirm':
        if not is_admin(call.from_user.id):
            return

        if 'broadcast_message' in user_states.get(call.from_user.id, {}):
            message_text = user_states[call.from_user.id]['broadcast_message']
            users_sent = 0
            users_failed = 0

            bot.answer_callback_query(call.id, "📤 Начинаю рассылку...")

            bot.edit_message_text(
                "⏳ *Рассылка началась...*\n\n"
                "Пожалуйста, подождите.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )

            for user_id_str in user_stats.keys():
                # Не отправляем забаненным
                if user_id_str in banned_users:
                    continue

                try:
                    bot.send_message(int(user_id_str), f"📢 *Объявление*\n\n{message_text}", parse_mode='Markdown')
                    users_sent += 1
                    time.sleep(0.1)
                except Exception as e:
                    users_failed += 1

            bot.edit_message_text(
                f"✅ *Рассылка завершена!*\n\n"
                f"📤 Отправлено: {users_sent}\n"
                f"❌ Не отправлено: {users_failed}",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )

            if call.from_user.id in user_states:
                del user_states[call.from_user.id]

    elif call.data == 'broadcast_cancel':
        if call.from_user.id in user_states:
            del user_states[call.from_user.id]
        bot.edit_message_text("❌ *Рассылка отменена*", call.message.chat.id, call.message.message_id,
                              parse_mode='Markdown')


# ========== ОБРАБОТЧИК СООБЩЕНИЙ (ПОИСК ИГР) ==========
@bot.message_handler(func=lambda m: True)
@check_ban_decorator
def search_handler(message):
    if message.text.startswith('/'):
        return

    if message.chat.id in user_states:
        return

    query = message.text.strip().lower()

    if query in GAMES_DATABASE:
        send_game_files(message.chat.id, query, message.from_user.id)
        return

    # Похожие игры
    similar = []
    for game in GAMES_DATABASE.keys():
        if query in game or game in query:
            similar.append(game)

    if similar:
        text = f"❌ *'{message.text}' не найдено*\n\n"
        text += "🎯 *Возможно вы искали:*\n\n"

        markup = types.InlineKeyboardMarkup(row_width=1)

        for game in similar[:5]:
            markup.add(types.InlineKeyboardButton(
                f"🎮 {game.title()}",
                callback_data=f"play_{game}"
            ))

        text += "Нажмите на кнопку, чтобы скачать:"

        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

    else:
        text = f"❌ *'{message.text}' не найдено*\n\n"
        text += "📝 *Заказать игру:* /neworder\n"
        text += "📋 *Посмотреть заказы:* /orders\n"
        text += "🔥 *Популярные игры:* /top"

        bot.send_message(message.chat.id, text, parse_mode='Markdown')


# ========== ФУНКЦИЯ ОТПРАВКИ ИГР ==========
def send_game_files(chat_id, game_name, user_id=None):
    sent_count = 0

    if game_name in GAMES_DATABASE:
        bot.send_message(chat_id, f"🎮 *{game_name.upper()}*\n📥 Отправляю...", parse_mode='Markdown')

        for file_id in GAMES_DATABASE[game_name]:
            try:
                bot.copy_message(chat_id, GAMES_CHANNEL_ID, file_id)
                sent_count += 1
                time.sleep(0.3)
            except:
                pass

        if user_id:
            user_id_str = str(user_id)
            if user_id_str not in user_stats:
                user_stats[user_id_str] = {'downloads': 0, 'created_orders': 0}
            user_stats[user_id_str]['downloads'] = user_stats[user_id_str].get('downloads', 0) + 1

            # Обновляем статистику игры
            if game_name not in game_stats:
                game_stats[game_name] = {'downloads': 0, 'last_download': None}
            game_stats[game_name]['downloads'] += 1
            game_stats[game_name]['last_download'] = datetime.now().isoformat()

            save_all()

        bot.send_message(chat_id, f"✅ *Готово! Отправлено {sent_count} файлов*")
        return True

    return False


# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 ЗАПУСК FERWES GAMES БОТА")
    print("=" * 60)

    # Создаём файлы если их нет
    files_to_create = [
        ORDERS_FILE, LIKES_FILE, ADMINS_FILE,
        USER_STATS_FILE, LIKE_COOLDOWN_FILE,
        GAME_STATS_FILE, WEEKLY_STATS_FILE,
        PREMIUM_FILE, BANNED_FILE, MUTED_FILE,
        ORDER_STATS_FILE
    ]

    for file in files_to_create:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                if file.endswith('.json'):
                    json.dump([] if 'orders' in file else {}, f)

    load_all()

    print(f"🎮 Игр в базе: {len(GAMES_DATABASE)}")
    print(f"📋 Заказов: {len(orders)}")
    print(f"👥 Пользователей: {len(user_stats)}")
    print(f"👑 Админов: {len(admins)}")
    print(f"🔨 Забанено: {len(banned_users)}")
    print(f"🔇 Замучено: {len(muted_users)}")
    print(f"💎 Премиум: {len(premium_users)}")
    print("=" * 60)
    print("⚡ Бот запущен и готов!")
    print("=" * 60)

    # Запуск с обработкой ошибок
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)