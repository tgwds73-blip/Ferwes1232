import telebot
from telebot import types
import json
import os
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import re

# НАСТРОЙКИ
BOT_TOKEN = '8456295069:AAGz48djuL19fYnn9FCz8DgJRQgIO6rLlq0'
bot = telebot.TeleBot(BOT_TOKEN)
GAMES_CHANNEL_ID = -1003421344618

# ФАЙЛЫ
ORDERS_FILE = 'orders.json'
LIKES_FILE = 'likes.json'
ADMINS_FILE = 'admins.json'
USER_STATS_FILE = 'user_stats.json'
LIKE_COOLDOWN_FILE = 'like_cooldown.json'
GAME_STATS_FILE = 'game_stats.json'
WEEKLY_STATS_FILE = 'weekly_stats.json'
PREMIUM_FILE = 'premium_users.json'

# ДАННЫЕ
orders = []
likes_data = {}
admins = ["7885915159"]
user_states = {}
user_stats = {}
like_cooldowns = {}
game_stats = {}
weekly_stats = {}
premium_users = {}  # {user_id: {"prefix": "ник", "purchased_date": "дата"}}

# КОНСТАНТЫ
LIKE_COOLDOWN_DAYS = 1000
ORDERS_PER_PAGE = 5
SIMILARITY_THRESHOLD = 0.6
PREMIUM_CHAT_LINK = "https://t.me/+Cy47-Mts-h00ZDYy"
PREMIUM_CONTACT = "@sweacher"


# ЛОГИРОВАНИЕ
def log_event(event):
    try:
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        with open('bot_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {event}\n")
    except:
        pass


# ЗАГРУЗКА ДАННЫХ
def load_all():
    global orders, likes_data, admins, user_stats, like_cooldowns, game_stats, weekly_stats, premium_users
    files = {
        ORDERS_FILE: orders,
        LIKES_FILE: likes_data,
        ADMINS_FILE: admins,
        USER_STATS_FILE: user_stats,
        LIKE_COOLDOWN_FILE: like_cooldowns,
        GAME_STATS_FILE: game_stats,
        WEEKLY_STATS_FILE: weekly_stats,
        PREMIUM_FILE: premium_users
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
                log_event(f"Ошибка загрузки {file}: {str(e)}")


def save_all():
    files = {
        ORDERS_FILE: orders,
        LIKES_FILE: likes_data,
        ADMINS_FILE: admins,
        USER_STATS_FILE: user_stats,
        LIKE_COOLDOWN_FILE: like_cooldowns,
        GAME_STATS_FILE: game_stats,
        WEEKLY_STATS_FILE: weekly_stats,
        PREMIUM_FILE: premium_users
    }
    for file, data in files.items():
        try:
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_event(f"ОШИБКА СОХРАНЕНИЯ {file}: {str(e)}")


# ПРОВЕРКИ
def is_admin(user_id):
    return str(user_id) in admins


def is_premium(user_id):
    return str(user_id) in premium_users


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


def update_game_stats(game_name):
    if game_name not in game_stats:
        game_stats[game_name] = {'downloads': 0, 'last_download': None}
    game_stats[game_name]['downloads'] += 1
    game_stats[game_name]['last_download'] = datetime.now().isoformat()

    today = datetime.now().strftime("%Y-%m-%d")
    if game_name not in weekly_stats:
        weekly_stats[game_name] = {}
    if today not in weekly_stats[game_name]:
        weekly_stats[game_name][today] = 0
    weekly_stats[game_name][today] += 1

    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    for game in list(weekly_stats.keys()):
        for date in list(weekly_stats[game].keys()):
            if date < week_ago:
                del weekly_stats[game][date]
    save_all()


def get_top_weekly(limit=3):
    result = []
    game_totals = {}
    for game_name, days in weekly_stats.items():
        total = sum(days.values())
        if total > 0:
            game_totals[game_name] = total
    sorted_games = sorted(game_totals.items(), key=lambda x: x[1], reverse=True)[:limit]
    for game_name, downloads in sorted_games:
        result.append((game_name, downloads))
    return result


def get_top_alltime(limit=3):
    result = []
    sorted_games = sorted(game_stats.items(), key=lambda x: x[1]['downloads'], reverse=True)[:limit]
    for game_name, stats in sorted_games:
        result.append((game_name, stats['downloads']))
    return result


def find_similar_games(query, threshold=SIMILARITY_THRESHOLD):
    query = query.lower().strip()
    similar = []
    query = re.sub(r'[^\w\s]', '', query)
    all_games = list(GAMES_DATABASE.keys()) + list(MOVIES_DATABASE.keys()) + list(SOFT_DATABASE.keys())
    all_games = list(set(all_games))
    for game_name in all_games:
        game_lower = game_name.lower()
        if query in game_lower:
            similarity = 0.9
        else:
            similarity = SequenceMatcher(None, query, game_lower).ratio()
        if similarity >= threshold:
            similar.append((game_name, similarity))
    similar.sort(key=lambda x: x[1], reverse=True)
    return [game for game, sim in similar[:5]]


def get_user_display_name(user_id, username=None, first_name=None):
    """Возвращает имя пользователя с префиксом, если есть"""
    user_id_str = str(user_id)
    if user_id_str in premium_users:
        prefix = premium_users[user_id_str].get('prefix', '')
        if prefix:
            return f"[{prefix}] {first_name or username or user_id}"
    return first_name or username or str(user_id)


# 🎮 ПОЛНАЯ БАЗА ВСЕХ ИГР
GAMES_DATABASE = {
    'minecraft': list(range(932, 936)),
    'gta v': list(range(705, 743)),
    'cyberpunk 2077': list(range(658, 705)),
    'elden ring': list(range(552, 588)),
    'witcher 3': list(range(986, 1006)),
    'hotline miami 2': [1159, 1160],
    'nier automata': list(range(164, 174)),
    'little nightmares 3': list(range(174, 183)),
    'rock star life simulator': list(range(184, 187)),
    'system shock 2 remaster': list(range(187, 193)),
    'gta san andreas': list(range(193, 196)),
    'uber soldier': list(range(197, 202)),
    'palworld': list(range(202, 217)),
    'scorn': list(range(217, 228)),
    'one shot': list(range(1065, 1070)),
    'jewel match': list(range(234, 237)),
    'far cry 5': list(range(242, 255)),
    'red dead redemption 2': list(range(428, 486)),
    'spider man remastered': list(range(486, 517)),
    'no im not a human': list(range(517, 521)),
    'call of duty ww2': list(range(521, 542)),
    'red dead redemption': list(range(542, 549)),
    'plants vs zombies': list(range(549, 552)),
    'quasimorph': list(range(589, 592)),
    'goat simulator': list(range(618, 622)),
    'finding frankie': list(range(622, 627)),
    'sally face': list(range(628, 633)),
    'the forest': list(range(633, 636)),
    'hollow knight silksong': [1204, 1205, 1206],
    'slime rancher 2': list(range(1323, 1326)),
    'far cry 4': list(range(1354, 1370)),
    'bendy and the ink machine': list(range(652, 655)),
    'caves of qud': list(range(655, 658)),
    's.t.a.l.k.e.r. shadow of chernobyl': list(range(1326, 1330)),
    'stalker shadow of chernobyl': list(range(1326, 1330)),
    'stalker soc': list(range(1326, 1330)),
    'hearts of iron iv': list(range(743, 748)),
    'friday night funkin': list(range(748, 751)),
    'dying light': list(range(751, 776)),
    'borderlands 2': list(range(776, 783)),
    'far cry 3': list(range(783, 788)),
    'resident evil revelations 2': list(range(788, 799)),
    'gta iv': list(range(799, 811)),
    'my gaming club': list(range(811, 814)),
    'orion sandbox': list(range(814, 817)),
    'cuphead': list(range(817, 822)),
    'beholder': list(range(823, 826)),
    'resident evil village': list(range(826, 846)),
    'resident evil resistance': list(range(1330, 1347)),
    'my winter car': list(range(1347, 1350)),
    'frostpunk 2': list(range(1619, 1628)),
    'frostpunk2': list(range(1619, 1628)),
    's.t.a.l.k.e.r anomaly': list(range(1628, 1635)),
    'stalker anomaly': list(range(1628, 1635)),
    'terraria 1.4.4.9': list(range(1350, 1353)),
    'the spike': list(range(846, 853)),
    'slim rancher': list(range(853, 858)),
    'garrys mod': list(range(858, 861)),
    'beamng drive': list(range(861, 874)),
    'payday the heist': list(range(876, 880)),
    'dark souls 3': list(range(880, 895)),
    'prototype 1': list(range(895, 902)),
    'gta vice city stories': list(range(902, 905)),
    'teardown': list(range(906, 913)),
    'antonblast': list(range(913, 916)),
    'fifa 17': list(range(916, 932)),
    'hollow knight silksong': list(range(1204, 1207)),
    'half life 2': list(range(1207, 1212)),
    'call of duty modern 2': list(range(1212, 1222)),
    'frostpunk': list(range(1222, 1229)),
    'fallout 4': list(range(1277, 1297)),
    'portal knights': list(range(1237, 1240)),
    'fallout 3': list(range(1231, 1237)),
    'stray': list(range(936, 942)),
    'mafia 1': list(range(1241, 1244)),
    'devil may cry 4 special edition': list(range(1244, 1259)),
    'gta san andreas definitive edition': list(range(1259, 1271)),
    'gta sa definitive': list(range(1259, 1271)),
    'mafia 2': list(range(942, 948)),
    'five nights at freddys': list(range(948, 951)),
    'rimworld': list(range(1298, 1302)),
    'third crisis': list(range(1302, 1306)),
    'hitman blood money': list(range(951, 961)),
    'hitman 2016': list(range(962, 986)),
    'dispatch': list(range(1311, 1321)),
    'hard time 3': list(range(1006, 1010)),
    'watch dogs 2': list(range(1010, 1028)),
    'assassins creed': list(range(1028, 1034)),
    'world box': list(range(1036, 1041)),
    'streets of rogue 2': list(range(1041, 1044)),
    'prototype 2': list(range(1044, 1051)),
    'metro 2033': list(range(1051, 1057)),
    'mysided': list(range(1057, 1060)),
    'hollow knight': list(range(1060, 1063)),
    'project zomboid': list(range(1093, 1096)),
    'humanit z': list(range(1096, 1111)),
    'bioshock remaster': list(range(1070, 1081)),
    'the last of us': list(range(1119, 1153)),
    'gta liberty city stories': list(range(1082, 1085)),
    'hotline miami': list(range(1085, 1088)),
    'gta iii': list(range(1088, 1091)),
    'undertale': list(range(1376, 1379)),
    'ghostrunner': list(range(1379, 1389)),
    'корсары 3': list(range(1370, 1373)),
    'korsary 3': list(range(1370, 1373)),
    'construction simulator 4': list(range(1373, 1376)),
    'строительный симулятор 4': list(range(1373, 1376)),
    'hytale': list(range(1398, 1403)),
    'detroit become human': list(range(1407, 1437)),
    'detroit': list(range(1407, 1437)),
    'far cry 2': list(range(1437, 1441)),
    'my summer car': list(range(1441, 1444)),
    'the long drive': list(range(1444, 1447)),
    'lonarpg': list(range(1447, 1450)),
    'gta vice city': list(range(1450, 1453)),
    'counter strike 1.6': list(range(1453, 1456)),
    'cs 1.6': list(range(1453, 1456)),
    'farm frenzy': list(range(1456, 1459)),
    'terraria': list(range(1459, 1462)),
    'five nights at freddys secret of the mimic': list(range(1462, 1474)),
    'fnaf secret of the mimic': list(range(1462, 1474)),
    'bully': list(range(1474, 1478)),
    'bully scholarship edition': list(range(1474, 1478)),
    'cry of fear': list(range(1481, 1487)),
    'cry of fear 2012': list(range(1481, 1487)),
    'tomb raider 2013': list(range(1487, 1497)),
    'tomb raider': list(range(1487, 1497)),
    'лара крофт': list(range(1487, 1497)),
    'hearts of iron iv: ultimate bundle': list(range(1497, 1502)),
    'hearts of iron iv ultimate bundle': list(range(1497, 1502)),
    'dying light: the beast': list(range(1502, 1526)),
    'dying light the beast': list(range(1502, 1526)),
    'ghost of tsushima': list(range(1527, 1552)),
    'clair obscur: expedition 33': list(range(1552, 1576)),
    'clair obscur expedition 33': list(range(1552, 1576)),
    'dead space': list(range(1576, 1581)),
    'dead space remake': list(range(1581, 1600)),
    'hollow knight: silksong': list(range(1600, 1603)),
    'people playground': list(range(1603, 1606)),
    'metro last light redux': list(range(1606, 1612)),
}

# 🎬 БАЗА ФИЛЬМОВ
MOVIES_DATABASE = {
    'fight club': list(range(1389, 1393)),
    'старикам тут не место': list(range(1394, 1398)),
    'no country for old men': list(range(1394, 1398)),
    'drive': list(range(1403, 1407)),
    'драйв': list(range(1403, 1407)),
}

# 💻 БАЗА СОФТА
SOFT_DATABASE = {
    'blender': list(range(1306, 1311)),
    'fl studio 25': list(range(1153, 1157)),
    'fl studio': list(range(1153, 1157)),
}


# 📋 ОСНОВНЫЕ КОМАНДЫ
@bot.message_handler(commands=['start'])
def start_cmd(m):
    if str(m.from_user.id) not in user_stats:
        user_stats[str(m.from_user.id)] = {
            'downloads': 0,
            'created_orders': 0,
            'first_seen': datetime.now().isoformat()
        }
        save_all()

    # Проверяем, есть ли реферальный код
    args = m.text.split()
    if len(args) > 1 and args[1].startswith('ref'):
        referrer_id = args[1][3:]
        if referrer_id != str(m.from_user.id) and referrer_id in user_stats:
            # Начисляем бонусы (можно добавить позже)
            log_event(f"Реферальный переход: {referrer_id} -> {m.from_user.id}")

    text = """🎮 *Ferwes Games Bot*

🔍 *Напиши название игры/фильма/софта* — я пришлю, если есть в базе.

📋 `/orders` — стол заказов  
📝 `/neworder` — заказать игру  
👤 `/myorders` — мои заказы  
📊 `/stats` — моя статистика  
🔥 `/top` — топ игр  
💎 `/ferwespremium` — префикс"""

    if is_admin(m.from_user.id):
        text += "\n\n👑 `/moderator` — панель модератора"

    # Создаем удобные кнопки
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 Заказы", callback_data="show_orders"),
        types.InlineKeyboardButton("📝 Новый заказ", callback_data="new_order"),
        types.InlineKeyboardButton("👤 Мои заказы", callback_data="my_orders"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="my_stats"),
        types.InlineKeyboardButton("🔥 Топ игр", callback_data="show_top"),
        types.InlineKeyboardButton("💎 Премиум", callback_data="show_premium")
    )

    bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=markup)


@bot.message_handler(commands=['ferwespremium'])
def premium_cmd(m):
    user_id = str(m.from_user.id)

    if user_id in premium_users:
        prefix_info = premium_users[user_id]
        text = f"""💎 *У вас уже есть префикс!*

Ваш префикс: `[{prefix_info.get('prefix', '')}]`
Куплен: {prefix_info.get('purchased_date', 'неизвестно')}

📌 Префикс работает, пока вы в чате:  
{PREMIUM_CHAT_LINK}

⚠️ *Важно:* не выходите из чата, иначе префикс сбросится.
📩 По вопросам: {PREMIUM_CONTACT}"""
    else:
        text = f"""💎 *Ferwes Premium — префикс в чате за 95 рублей!*

🔥 При покупке префикс сохраняется навсегда!

**Входит в префикс:**
• Уникальный префикс в чате
• Выделение среди других пользователей
• Поддержка проекта

📌 *Обязательно:* вступите в чат, иначе префикс не будет работать:  
{PREMIUM_CHAT_LINK}

⚠️ Не выходите из чата, чтобы префикс не сбился.

📩 По вопросам покупки/возврата префикса: {PREMIUM_CONTACT}"""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Вступить в чат", url=PREMIUM_CHAT_LINK))
    markup.add(types.InlineKeyboardButton("✍️ Написать @sweacher", url="https://t.me/sweacher"))

    bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=markup)


# СТОЛ ЗАКАЗОВ С ПАГИНАЦИЕЙ
@bot.message_handler(commands=['orders'])
def orders_cmd(m):
    show_orders_page(m.chat.id, 0)


def show_orders_page(chat_id, page=0):
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

        # Получаем имя пользователя с префиксом
        user_display = get_user_display_name(
            order.get('user_id'),
            order.get('username'),
            None
        )

        text += f"🎮 *{order['game']}*\n"
        text += f"👤 {user_display}\n"
        text += f"📅 {order_date} | 💾 {order.get('size', 'N/A')}\n"
        text += f"❤️ {order.get('likes', 0)} лайков\n"
        text += f"🆔 {order['id']}\n"
        text += "─\n"

    markup = types.InlineKeyboardMarkup(row_width=3)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"orders_page_{page - 1}"))
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="current_page"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"orders_page_{page + 1}"))
    if nav_buttons:
        markup.row(*nav_buttons)

    for order in page_orders:
        btn_text = f"❤️ {order['game'][:15]}"
        if len(order['game']) > 15:
            btn_text += "..."
        markup.add(types.InlineKeyboardButton(
            btn_text,
            callback_data=f"like_{order['id']}"
        ))

    bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)


@bot.message_handler(commands=['myorders'])
def myorders_cmd(m):
    user_orders = [o for o in orders if o.get('user_id') == m.chat.id]
    if not user_orders:
        bot.send_message(m.chat.id, "📭 *У вас нет заказов*")
        return

    text = "👤 *Мои заказы*\n\n"
    for order in user_orders[-10:]:
        text += f"🎮 {order['game']}\n"
        text += f"🆔 {order['id']} | 💾 {order.get('size', 'N/A')}\n"
        text += f"❤️ {order.get('likes', 0)} лайков\n"
        text += "─\n"

    bot.send_message(m.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['neworder'])
def neworder_cmd(m):
    user_states[m.chat.id] = 'waiting_game'
    bot.send_message(m.chat.id, "📝 *Напиши название игры:*")


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == 'waiting_game')
def get_game(m):
    user_states[m.chat.id] = {'game': m.text, 'state': 'waiting_size'}
    bot.send_message(m.chat.id, "💾 *Напиши размер в ГБ:*")


@bot.message_handler(
    func=lambda m: user_states.get(m.chat.id) and user_states[m.chat.id].get('state') == 'waiting_size')
def get_size(m):
    data = user_states[m.chat.id]
    user_info = f"@{m.from_user.username}" if m.from_user.username else f"ID:{m.from_user.id}"

    log_event(f"НОВЫЙ ЗАКАЗ: {data['game']} | РАЗМЕР: {m.text} | ОТ: {user_info}")

    order_id = len(orders) + 1
    orders.append({
        'id': order_id,
        'game': data['game'],
        'size': m.text.upper() + " ГБ",
        'likes': 0,
        'liked_by': [],
        'user_id': m.chat.id,
        'username': user_info,
        'date': datetime.now().isoformat()
    })

    user_id_str = str(m.from_user.id)
    if user_id_str not in user_stats:
        user_stats[user_id_str] = {'downloads': 0, 'created_orders': 0}
    user_stats[user_id_str]['created_orders'] = user_stats[user_id_str].get('created_orders', 0) + 1

    save_all()
    del user_states[m.chat.id]
    bot.send_message(m.chat.id, f"✅ *Заказ создан!*\n🆔 ID: {order_id}")


@bot.message_handler(commands=['stats'])
def user_stats_cmd(m):
    user_id_str = str(m.from_user.id)

    if user_id_str not in user_stats:
        bot.send_message(m.chat.id, "📊 *Вы еще ничего не скачали*")
        return

    stats = user_stats[user_id_str]
    downloads = stats.get('downloads', 0)
    created_orders = stats.get('created_orders', 0)

    try:
        first_seen = datetime.fromisoformat(stats.get('first_seen', datetime.now().isoformat()))
        days_active = (datetime.now() - first_seen).days
    except:
        days_active = 0

    # Премиум статус
    premium_status = "✅ Да" if is_premium(m.from_user.id) else "❌ Нет"

    text = f"👤 *Ваша статистика*\n\n"
    text += f"📥 Скачано игр: {downloads}\n"
    text += f"📋 Создано заказов: {created_orders}\n"
    text += f"📅 Активен дней: {days_active}\n"
    text += f"💎 Премиум: {premium_status}\n"

    bot.send_message(m.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['top'])
def top_cmd(m):
    top_weekly = get_top_weekly(3)
    top_alltime = get_top_alltime(3)

    text = "🔥 *ТОП ИГР*\n\n"

    text += "📅 *За неделю:*\n"
    if top_weekly:
        for i, (game, downloads) in enumerate(top_weekly, 1):
            text += f"{i}. 🎮 {game} — {downloads} 📥\n"
    else:
        text += "Нет данных за неделю\n"

    text += "\n🏆 *За все время:*\n"
    if top_alltime:
        for i, (game, downloads) in enumerate(top_alltime, 1):
            text += f"{i}. 🎮 {game} — {downloads} 📥\n"
    else:
        text += "Нет данных\n"

    bot.send_message(m.chat.id, text, parse_mode='Markdown')


# 👑 КОМАНДЫ МОДЕРАТОРА
@bot.message_handler(commands=['moderator'])
def moderator_cmd(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ *Нет прав*")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("📢 Рассылка", callback_data="mod_broadcast"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="mod_stats"),
        types.InlineKeyboardButton("❌ Удалить заказ", callback_data="mod_delorder"),
        types.InlineKeyboardButton("👑 Добавить админа", callback_data="mod_addadmin"),
        types.InlineKeyboardButton("💎 Управление премиум", callback_data="mod_premium"),
    ]
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i + 1])
        else:
            markup.row(buttons[i])

    text = f"""👑 *Панель модератора*

📊 *Статистика:*
• Заказов: {len(orders)}
• Пользователей: {len(user_stats)}
• Админов: {len(admins)}
• Премиум: {len(premium_users)}

⚡ *Команды:*
`/delorder 5` - Удалить заказ
`/addadmin 123` - Добавить админа
`/broadcast текст` - Рассылка
`/addpremium 123 ник` - Добавить премиум
`/removepremium 123` - Удалить премиум"""

    bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=markup)


@bot.message_handler(commands=['addpremium'])
def addpremium_cmd(m):
    if not is_admin(m.from_user.id):
        return
    try:
        parts = m.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.send_message(m.chat.id, "❌ */addpremium <ID> <ник>*")
            return

        user_id = parts[1]
        prefix = parts[2]

        premium_users[user_id] = {
            'prefix': prefix,
            'purchased_date': datetime.now().isoformat(),
            'added_by': str(m.from_user.id)
        }
        save_all()
        log_event(f"ВЫДАЧА ПРЕМИУМ: ID {user_id} с префиксом '{prefix}'")
        bot.send_message(m.chat.id, f"✅ *ID {user_id} получил премиум с префиксом: {prefix}*")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Ошибка: {str(e)}")


@bot.message_handler(commands=['removepremium'])
def removepremium_cmd(m):
    if not is_admin(m.from_user.id):
        return
    try:
        user_id = m.text.split()[1]
        if user_id in premium_users:
            del premium_users[user_id]
            save_all()
            log_event(f"УДАЛЕНИЕ ПРЕМИУМ: ID {user_id}")
            bot.send_message(m.chat.id, f"✅ *Премиум удален у ID {user_id}*")
        else:
            bot.send_message(m.chat.id, f"❌ *ID {user_id} не имеет премиума*")
    except:
        bot.send_message(m.chat.id, "❌ */removepremium <ID>*")


@bot.message_handler(commands=['delorder'])
def delorder_cmd(m):
    if not is_admin(m.from_user.id):
        return
    try:
        order_id = int(m.text.split()[1])
        order_to_delete = None
        for order in orders:
            if order['id'] == order_id:
                order_to_delete = order
                break

        if not order_to_delete:
            bot.send_message(m.chat.id, f"❌ *Заказ #{order_id} не найден*")
            return

        liked_by = order_to_delete.get('liked_by', [])
        game_name = order_to_delete['game']

        user_states[m.chat.id] = {
            'state': 'waiting_delete_reason',
            'order_id': order_id,
            'liked_by': liked_by,
            'game_name': game_name
        }

        bot.send_message(m.chat.id,
                         f"📝 *Напиши причину удаления заказа #{order_id}*\n\n"
                         f"Это сообщение будет отправлено {len(liked_by)} пользователям, которые лайкнули этот заказ.",
                         parse_mode='Markdown')

    except Exception as e:
        bot.send_message(m.chat.id, "❌ */delorder <ID заказа>*")


@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('state') == 'waiting_delete_reason')
def process_delete_reason(m):
    data = user_states[m.chat.id]
    order_id = data['order_id']
    liked_by = data['liked_by']
    game_name = data['game_name']
    reason = m.text

    for i, order in enumerate(orders):
        if order['id'] == order_id:
            del orders[i]
            break

    save_all()
    log_event(f"УДАЛЕНИЕ ЗАКАЗА: #{order_id} '{game_name}', причина: {reason}")

    sent_count = 0
    for user_id in liked_by:
        try:
            bot.send_message(int(user_id),
                             f"⚠️ *Заказ #{order_id} был удален*\n\n"
                             f"🎮 Игра: {game_name}\n"
                             f"📝 Причина: {reason}\n\n"
                             f"Спасибо за ваш лайк! ❤️",
                             parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.1)
        except:
            pass

    bot.send_message(m.chat.id,
                     f"✅ *Заказ #{order_id} удален*\n\n"
                     f"📤 Уведомления отправлены: {sent_count}/{len(liked_by)} пользователям",
                     parse_mode='Markdown')

    del user_states[m.chat.id]


@bot.message_handler(commands=['addadmin'])
def addadmin_cmd(m):
    if not is_admin(m.from_user.id):
        return
    try:
        user_id = str(m.text.split()[1])
        if user_id in admins:
            bot.send_message(m.chat.id, "⚠️ *Уже админ*")
        else:
            admins.append(user_id)
            save_all()
            log_event(f"ВЫДАЧА АДМИНКИ: ID {user_id}")
            bot.send_message(m.chat.id, f"✅ *ID {user_id} получил права модератора*")
    except:
        bot.send_message(m.chat.id, "❌ */addadmin <ID>*")


@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ *Нет прав*")
        return

    try:
        message_text = m.text.split(' ', 1)[1]

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Да, отправить", callback_data="broadcast_confirm"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
        )

        m.reply_text(
            f"📢 *Подтверждение рассылки*\n\n"
            f"Получателей: {len(user_stats)}\n\n"
            f"Сообщение:\n{message_text[:500]}...\n\n"
            f"Отправить всем пользователям?",
            parse_mode='Markdown',
            reply_markup=markup
        )

        user_states[m.chat.id] = {
            'broadcast_message': message_text,
            'state': 'awaiting_broadcast_confirmation'
        }

    except IndexError:
        bot.send_message(m.chat.id, "❌ */broadcast <текст сообщения>*")


# CALLBACK ОБРАБОТЧИКИ
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # ЛАЙКИ
    if call.data.startswith('like_'):
        can_like_now, days_left = can_like(call.from_user.id)

        if not can_like_now:
            bot.answer_callback_query(
                call.id,
                f"❌ Вы уже ставили лайк! Следующий можно будет поставить через {days_left} дней",
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

                log_event(f"ЛАЙК: заказ #{order_id} '{order['game']}' | от: ID {call.from_user.id}")
                bot.answer_callback_query(call.id, "❤️ Лайк поставлен!")
                return
        bot.answer_callback_query(call.id, "❌ Заказ не найден")

    # ПАГИНАЦИЯ СТОЛА ЗАКАЗОВ
    elif call.data.startswith('orders_page_'):
        try:
            page = int(call.data.split('_')[2])
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_orders_page(call.message.chat.id, page)
        except:
            bot.answer_callback_query(call.id, "❌ Ошибка перехода")

    # ПОИСК ПО КНОПКЕ С ПОХОЖЕЙ ИГРОЙ
    elif call.data.startswith('play_'):
        game_name = call.data[5:]
        send_game_files(call.message.chat.id, game_name, call.from_user.id)
        bot.answer_callback_query(call.id)

    # КНОПКИ ИЗ /start
    elif call.data == "show_orders":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        orders_cmd(call.message)
    elif call.data == "new_order":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        neworder_cmd(call.message)
    elif call.data == "my_orders":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        myorders_cmd(call.message)
    elif call.data == "my_stats":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        user_stats_cmd(call.message)
    elif call.data == "show_top":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        top_cmd(call.message)
    elif call.data == "show_premium":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        premium_cmd(call.message)

    # МОДЕРАТОР
    elif call.data.startswith('mod_'):
        if not is_admin(call.from_user.id):
            return

        if call.data == 'mod_broadcast':
            bot.send_message(call.message.chat.id,
                             "📢 */broadcast <текст>* - отправить сообщение всем пользователям")

        elif call.data == 'mod_stats':
            stats_text = "📊 *Статистика бота*\n\n"
            stats_text += f"👥 Пользователей: {len(user_stats)}\n"
            stats_text += f"📋 Заказов: {len(orders)}\n"
            stats_text += f"👑 Админов: {len(admins)}\n"
            stats_text += f"💎 Премиум: {len(premium_users)}\n\n"

            if user_stats:
                sorted_users = sorted(user_stats.items(), key=lambda x: x[1].get('downloads', 0), reverse=True)[:5]
                stats_text += "🏆 *Топ-5 пользователей:*\n"
                for i, (user_id, data) in enumerate(sorted_users, 1):
                    stats_text += f"{i}. ID {user_id}: {data.get('downloads', 0)} скачиваний\n"

            bot.send_message(call.message.chat.id, stats_text, parse_mode='Markdown')

        elif call.data == 'mod_delorder':
            bot.send_message(call.message.chat.id, "❌ */delorder <ID>*")

        elif call.data == 'mod_addadmin':
            bot.send_message(call.message.chat.id, "👑 */addadmin <ID>*")

        elif call.data == 'mod_premium':
            bot.send_message(call.message.chat.id,
                             "💎 *Управление премиум*\n\n"
                             "`/addpremium <ID> <ник>` - добавить премиум\n"
                             "`/removepremium <ID>` - удалить премиум")

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
                try:
                    bot.send_message(int(user_id_str), f"📢 *Объявление*\n\n{message_text}", parse_mode='Markdown')
                    users_sent += 1
                    time.sleep(0.1)
                except Exception as e:
                    users_failed += 1
                    log_event(f"ОШИБКА РАССЫЛКИ: ID {user_id_str} - {str(e)}")

            log_event(f"РАССЫЛКА: отправлено {users_sent}, не отправлено {users_failed}")

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


# ФУНКЦИЯ ДЛЯ ОТПРАВКИ ИГРЫ ИЛИ ФИЛЬМА
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
            update_game_stats(game_name)
            save_all()

        bot.send_message(chat_id, f"✅ *Готово! Отправлено {sent_count} файлов*")
        return True

    elif game_name in MOVIES_DATABASE:
        bot.send_message(chat_id, f"🎬 *{game_name.upper()}*\n📥 Отправляю фильм...", parse_mode='Markdown')
        for file_id in MOVIES_DATABASE[game_name]:
            try:
                bot.copy_message(chat_id, GAMES_CHANNEL_ID, file_id)
                sent_count += 1
                time.sleep(0.3)
            except:
                pass
        bot.send_message(chat_id, f"✅ *Фильм отправлен! Отправлено {sent_count} файлов*")
        return True

    elif game_name in SOFT_DATABASE:
        bot.send_message(chat_id, f"💻 *{game_name.upper()}*\n📥 Отправляю софт...", parse_mode='Markdown')
        for file_id in SOFT_DATABASE[game_name]:
            try:
                bot.copy_message(chat_id, GAMES_CHANNEL_ID, file_id)
                sent_count += 1
                time.sleep(0.3)
            except:
                pass
        bot.send_message(chat_id, f"✅ *Софт отправлен! Отправлено {sent_count} файлов*")
        return True

    return False


# ПОИСК ИГР И ФИЛЬМОВ
@bot.message_handler(func=lambda m: True)
def search_handler(m):
    if m.text.startswith('/'):
        return

    if m.chat.id in user_states:
        return

    query = m.text.strip().lower()

    if query in GAMES_DATABASE or query in MOVIES_DATABASE or query in SOFT_DATABASE:
        send_game_files(m.chat.id, query, m.from_user.id)
        return

    similar_games = find_similar_games(query)

    if similar_games:
        text = f"❌ *'{m.text}' не найдено*\n\n"
        text += "🎯 *Возможно вы искали:*\n\n"

        markup = types.InlineKeyboardMarkup(row_width=1)

        for game in similar_games[:5]:
            # Определяем иконку
            icon = "🎮"
            if game in MOVIES_DATABASE:
                icon = "🎬"
            elif game in SOFT_DATABASE:
                icon = "💻"

            display_name = game.title()
            markup.add(types.InlineKeyboardButton(
                f"{icon} {display_name}",
                callback_data=f"play_{game}"
            ))

        text += "Нажмите на кнопку, чтобы скачать:"

        bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=markup)

    else:
        text = f"❌ *'{m.text}' не найдено*\n\n"
        text += "📝 *Заказать игру:* /neworder\n"
        text += "📋 *Посмотреть заказы:* /orders\n"
        text += "🔥 *Популярные игры:* /top\n"
        text += "💎 *Премиум:* /ferwespremium"

        bot.send_message(m.chat.id, text, parse_mode='Markdown')


# 🚀 ЗАПУСК
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 ЗАПУСК FERWES GAMES БОТА")
    print("=" * 60)

    files_to_create = [
        ORDERS_FILE, LIKES_FILE, ADMINS_FILE,
        USER_STATS_FILE, LIKE_COOLDOWN_FILE,
        GAME_STATS_FILE, WEEKLY_STATS_FILE,
        PREMIUM_FILE
    ]

    for file in files_to_create:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                if file.endswith('.json'):
                    json.dump([] if 'orders' in file else {}, f)

    load_all()

    print(f"🎮 Игр в базе: {len(GAMES_DATABASE)}")
    print(f"🎬 Фильмов в базе: {len(MOVIES_DATABASE)}")
    print(f"💻 Софта в базе: {len(SOFT_DATABASE)}")
    print(f"📋 Заказов: {len(orders)}")
    print(f"👥 Пользователей: {len(user_stats)}")
    print(f"💎 Премиум: {len(premium_users)}")
    print("=" * 60)
    print("⚡ Бот запущен и готов!")
    print("=" * 60)

    bot.polling(none_stop=True, skip_pending=True)