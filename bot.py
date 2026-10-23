import os
import asyncio
import sqlite3
import random
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
BOT_TOKEN = "" 
ADMIN_ID = 8070374602 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY,
        nickname TEXT,
        game_id TEXT,
        elo INTEGER DEFAULT 1000,
        is_registered INTEGER DEFAULT 0,
        matches_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        kills INTEGER DEFAULT 0,
        deaths INTEGER DEFAULT 0,
        assists INTEGER DEFAULT 0,
        ban_until REAL DEFAULT 0,
        mute_until REAL DEFAULT 0,
        ban_reason TEXT,
        lang TEXT DEFAULT 'ru'
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS parties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        leader_id INTEGER,
        status TEXT DEFAULT 'gathering',
        match_id INTEGER
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS party_players (
        party_id INTEGER,
        user_id INTEGER
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        host_id INTEGER,
        code_ct TEXT,
        code_t TEXT,
        status TEXT DEFAULT 'searching',
        start_time REAL,
        score_ct INTEGER,
        score_t INTEGER,
        winner TEXT,
        map_name TEXT,
        screenshot_id TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS match_players (
        match_id INTEGER,
        user_id INTEGER,
        team TEXT,
        kills INTEGER DEFAULT 0,
        deaths INTEGER DEFAULT 0,
        assists INTEGER DEFAULT 0
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT,
        text TEXT,
        status TEXT DEFAULT 'open'
    )''')
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_party_players_user ON party_players(user_id)")
    conn.commit()
    conn.close()

init_db()

# --- СЛОВАРИ ПЕРЕВОДОВ ---
TEXTS = {
    'ru': {
        'choose_lang': "👋 Привет! Выбери язык / Choose language:",
        'lang_set': "✅ Язык установлен: Русский",
        'main_menu': "Главное меню:",
        'play': "🎮 Играть",
        'my_matches': "🔍 Мои матчи",
        'profile': "👤 Профиль",
        'leaderboard': "🏆 Рейтинг",
        'rules': "📜 Правила",
        'ticket': "🆘 Создать тикет",
        'how_to_play': "📖 Как играть",
        'back': "🔙 Назад",
        'cancel': "🔙 Отмена",
        'enter_nick': "👋 Введи свой <b>игровой Никнейм</b>:",
        'enter_id': "Введи свой <b>ID из игры</b>:",
        'reg_done': "✅ <b>Регистрация завершена!</b>",
        'profile_title': "📊 <b>Профиль игрока</b>",
        'history': "⏳ Прошлые игры",
        'edit_data': "📝 Изменить данные",
        'admin_panel': "🛡 Админ-панель",
        'calibration': "⏳ <b>Калибровка:</b> {}/10",
        'elo_lvl': "🏆 <b>ELO:</b> {} (<b>{} LVL</b>)",
        'winrate': "📈 <b>Winrate:</b> {}% ({}W / {}L)",
        'kd': "🎯 <b>K/D:</b> {:.2f} ({} / {})",
        'kda': "🩸 <b>Средний K/D/A:</b> {:.1f} / {:.1f} / {:.1f}",
        'no_history': "⏳ <b>Прошлые игры</b>\n\nТы еще не сыграл ни одного матча.",
        'history_title': "⏳ <b>Прошлые игры:</b>\n\n",
        'back_profile': "🔙 В профиль",
        'no_matches': "Больше матчей нет.",
        'match_row': "Матч #{} | 🗺 {} | {}:{} | {}\n",
        'win': "Победа ✅",
        'lose': "Поражение ❌",
        'top_players': "🏆 <b>ТОП-10 игроков:</b>\n\n",
        'no_players': "Пока никого нет.",
        'top_row': "{}. <b>{}</b> — {} ELO ({} LVL)\n",
        'ticket_cat': "🆘 <b>Выбери категорию тикета:</b>",
        'ticket_admin': "🛡 Администратор",
        'ticket_player': "👤 Игрок",
        'ticket_bug': "🐛 Баг",
        'ticket_other': "📝 Другое",
        'ticket_text': "🆘 <b>Категория:</b> {}\n\nНапиши свой вопрос:",
        'ticket_media': "📸 <b>Прикрепи фото/видео.</b>\nЕсли нет, напиши `-`:",
        'ticket_sent': "✅ Тикет отправлен!",
        'create_party': "➕ Создать пати",
        'search_solo': "🔍 Быстрый поиск (Соло)",
        'already_in_party': "Ты уже в пати.",
        'my_party': "👥 Моя пати",
        'party_title': "👥 <b>Ваше пати ({}/5)</b>\n👑 Капитан: <b>{}</b> ({} ELO, {} LVL)\n\n👤 <b>Игроки:</b>\n",
        'party_player_row': "• <b>{}</b> — {} ELO ({} LVL) | WR: {}%\n",
        'party_status': "\n🔴 <b>Статус:</b> {}",
        'party_gathering': "Сбор",
        'party_searching': "⏳ В поиске...",
        'party_ingame': "В игре",
        'invite_friend': "🔗 Пригласить",
        'find_match': "🔍 Найти матч",
        'cancel_search': "⏳ Остановить поиск",
        'leave_party': "❌ Покинуть пати",
        'back_menu': "🔙 В меню",
        'searching_match': "⏳ <b>Поиск матча...</b>",
        'searching_solo': "⏳ <b>Быстрый поиск...</b>",
        'search_stopped': "❌ Поиск остановлен.",
        'match_found': "🔥 <b>Матч найден! (5x5)</b>",
        'veto_title': "🗺 <b>Вето карт!</b>\nТы Капитан {}. Забань первую карту:",
        'veto_wait': "🗺 Ожидайте, Капитан {} банит карту...",
        'veto_banned': "✅ Ты забанил {}.",
        'veto_final_map': "🗺 Финальная карта: <b>{}</b>",
        'veto_host_instruction': "👑 <b>Ты назначен Хостом матча!</b>\n\n📖 <b>Инструкция:</b>\n1. Создай комнату в игре.\n2. Поставь 13 раундов.\n3. Включи раздельные коды.\n4. Отправь мне: <code>CT-XXXX T-YYYY</code>",
        'veto_host_wait': "🗺 Финальная карта: <b>{}</b>\nХост получил инструкцию.",
        'codes_sent': "✅ Коды разосланы!",
        'match_ready': "🔥 <b>Матч готов!</b>\nКоманда: <b>{}</b>\nКод: <code>{}</code>",
        'team_ct': "Counter-Terrorists",
        'team_t': "Terrorists",
        'admin_panel_title': "🛡 <b>Админ-панель</b>",
        'admin_ban': "🚫 Забанить",
        'admin_mute': "🔇 Выдать мут",
        'admin_id_prompt': "Введи <b>Telegram ID</b>:",
        'admin_reason_prompt': "📝 Причина:",
        'admin_time_prompt': "⏳ На сколько дней? (число):",
        'admin_punished': "✅ Пользователь наказан на {} дн.",
        'rules_text': "📜 Правила: 1. Не читерить. 2. Уважать других.",
        'how_to_play_text': "📖 <b>Как играть:</b>\n\n1. Нажми «Играть».\n2. Собери 10 человек.\n3. Капитаны банят карты.\n4. Хост вводит коды.\n5. Играете и вводите счет.",
        'banned_msg': "⛔ <b>Вы забанены!</b>\nПричина: {}\nДо: {}",
        'muted_msg': "🔇 <b>У вас мут!</b>\nПричина: {}\nДо: {}",
        'edit_nick_prompt': "📝 Введи свой <b>новый Никнейм</b>:",
        'edit_id_prompt': "📝 Введи свой <b>новый ID из игры</b>:",
        'edit_done': "✅ <b>Данные обновлены!</b>",
        'log_edit': "🔔 <b>Игрок изменил данные!</b>\n\n👤 Игрок: {} (@{})\n🆔 TG ID: <code>{}</code>\n\n📝 <b>Было:</b>\nНик: {}\nID: {}\n\n✅ <b>Стало:</b>\nНик: {}\nID: {}",
        'change_lang_btn': "🌐 Сменить язык / Change language",
        'finish_match_btn': "🏁 Завершить матч",
        'finish_match_prompt': "🏁 <b>Пришли скриншот таблицы результатов.</b>\n(Он сохранится в истории)",
        'score_prompt': "✅ Скриншот получен! Теперь введи <b>счет матча</b> в формате <b>CT:T</b> (например, 13:7):",
        'pending_msg': "⏳ <b>Счет отправлен на проверку Администратору.</b>\nОжидайте подтверждения.",
        'match_finished': "🏆 <b>Матч завершен!</b>\nСчет: <b>{}</b>\nТвой результат: <b>{}</b>",
        'finish_only_host': "⛔ Только Хост может завершить матч!",
        'finish_too_early': "⛔ Слишком рано! Матч не может длиться меньше 10 минут.",
        'elo_updated': "💰 <b>Новый ELO:</b> {}",
        'admin_new_result': "🚨 <b>Матч #{} ожидает проверки!</b>\n\n📊 Счет: <b>{}:{}</b>\n👑 Хост: <code>{}</code>\n\nПроверь скриншот и подтверди:",
        'approve_btn': "✅ Подтвердить счет",
        'kda_btn': "📝 Ввести K/D/A",
        'kda_prompt': "📝 <b>Ввод K/D/A для матча #{}</b>\n\nИгроки:\n{}\n\nВведи статистику в формате:\n<code>ID K D A</code>\n(каждого с новой строки)\n\nПример:\n<code>123456 15 10 5</code>",
        'kda_saved': "✅ Статистика сохранена для {} игроков!",
        'match_confirmed': "✅ Матч #{} подтвержден! ELO начислено.",
    },
    'en': {
        'choose_lang': "👋 Привет! Выбери язык / Choose language:",
        'lang_set': "✅ Language set: English",
        'main_menu': "Main menu:",
        'play': "🎮 Play",
        'my_matches': "🔍 My Matches",
        'profile': "👤 Profile",
        'leaderboard': "🏆 Leaderboard",
        'rules': "📜 Rules",
        'ticket': "🆘 Create Ticket",
        'how_to_play': "📖 How to play",
        'back': "🔙 Back",
        'cancel': "🔙 Cancel",
        'enter_nick': "👋 Enter your <b>in-game Nickname</b>:",
        'enter_id': "Enter your <b>in-game ID</b>:",
        'reg_done': "✅ <b>Registration complete!</b>",
        'profile_title': "📊 <b>Player Profile</b>",
        'history': "⏳ Match History",
        'edit_data': "📝 Edit Data",
        'admin_panel': "🛡 Admin Panel",
        'calibration': "⏳ <b>Calibration:</b> {}/10",
        'elo_lvl': "🏆 <b>ELO:</b> {} (<b>{} LVL</b>)",
        'winrate': "📈 <b>Winrate:</b> {}% ({}W / {}L)",
        'kd': "🎯 <b>K/D:</b> {:.2f} ({} / {})",
        'kda': "🩸 <b>Average K/D/A:</b> {:.1f} / {:.1f} / {:.1f}",
        'no_history': "⏳ <b>Match History</b>\n\nYou haven't played any matches yet.",
        'history_title': "⏳ <b>Match History:</b>\n\n",
        'back_profile': "🔙 To Profile",
        'no_matches': "No more matches.",
        'match_row': "Match #{} | 🗺 {} | {}:{} | {}\n",
        'win': "Win ✅",
        'lose': "Loss ❌",
        'top_players': "🏆 <b>TOP-10 Players:</b>\n\n",
        'no_players': "No one yet.",
        'top_row': "{}. <b>{}</b> — {} ELO ({} LVL)\n",
        'ticket_cat': "🆘 <b>Choose ticket category:</b>",
        'ticket_admin': "🛡 Administrator",
        'ticket_player': "👤 Player",
        'ticket_bug': "🐛 Bug",
        'ticket_other': "📝 Other",
        'ticket_text': "🆘 <b>Category:</b> {}\n\nWrite your question:",
        'ticket_media': "📸 <b>Attach photo/video.</b>\nIf none, write `-`:",
        'ticket_sent': "✅ Ticket sent!",
        'create_party': "➕ Create Party",
        'search_solo': "🔍 Quick Search",
        'already_in_party': "You are already in a party.",
        'my_party': "👥 My Party",
        'party_title': "👥 <b>Your Party ({}/5)</b>\n👑 Captain: <b>{}</b> ({} ELO, {} LVL)\n\n👤 <b>Players:</b>\n",
        'party_player_row': "• <b>{}</b> — {} ELO ({} LVL) | WR: {}%\n",
        'party_status': "\n🔴 <b>Status:</b> {}",
        'party_gathering': "Gathering",
        'party_searching': "⏳ Searching...",
        'party_ingame': "In Game",
        'invite_friend': "🔗 Invite",
        'find_match': "🔍 Find Match",
        'cancel_search': "⏳ Stop Search",
        'leave_party': "❌ Leave Party",
        'back_menu': "🔙 To Menu",
        'searching_match': "⏳ <b>Searching for match...</b>",
        'searching_solo': "⏳ <b>Quick search...</b>",
        'search_stopped': "❌ Search stopped.",
        'match_found': "🔥 <b>Match found! (5x5)</b>",
        'veto_title': "🗺 <b>Map Veto!</b>\nYou are Captain {}. Ban the first map:",
        'veto_wait': "🗺 Wait, Captain {} is banning...",
        'veto_banned': "✅ You banned {}.",
        'veto_final_map': "🗺 Final map: <b>{}</b>",
        'veto_host_instruction': "👑 <b>You are the Match Host!</b>\n\n📖 <b>Instructions:</b>\n1. Create a room in game.\n2. Set 13 rounds.\n3. Enable separate team codes.\n4. Send me: <code>CT-XXXX T-YYYY</code>",
        'veto_host_wait': "🗺 Final map: <b>{}</b>\nHost received instructions.",
        'codes_sent': "✅ Codes sent!",
        'match_ready': "🔥 <b>Match ready!</b>\nTeam: <b>{}</b>\nCode: <code>{}</code>",
        'team_ct': "Counter-Terrorists",
        'team_t': "Terrorists",
        'admin_panel_title': "🛡 <b>Admin Panel</b>",
        'admin_ban': "🚫 Ban",
        'admin_mute': "🔇 Mute",
        'admin_id_prompt': "Enter <b>Telegram ID</b>:",
        'admin_reason_prompt': "📝 Reason:",
        'admin_time_prompt': "⏳ Days? (number):",
        'admin_punished': "✅ User punished for {} days.",
        'rules_text': "📜 Rules: 1. No cheating. 2. Respect others.",
        'how_to_play_text': "📖 <b>How to play:</b>\n\n1. Click «Play».\n2. Gather 10 players.\n3. Captains ban maps.\n4. Host enters codes.\n5. Play and enter score.",
        'banned_msg': "⛔ <b>You are banned!</b>\nReason: {}\nUntil: {}",
        'muted_msg': "🔇 <b>You are muted!</b>\nReason: {}\nUntil: {}",
        'edit_nick_prompt': "📝 Enter <b>new Nickname</b>:",
        'edit_id_prompt': "📝 Enter <b>new in-game ID</b>:",
        'edit_done': "✅ <b>Data updated!</b>",
        'log_edit': "🔔 <b>Player changed data!</b>\n\n👤 Player: {} (@{})\n🆔 TG ID: <code>{}</code>\n\n📝 <b>Was:</b>\nNick: {}\nID: {}\n\n✅ <b>Became:</b>\nNick: {}\nID: {}",
        'change_lang_btn': "🌐 Сменить язык / Change language",
        'finish_match_btn': "🏁 Finish Match",
        'finish_match_prompt': "🏁 <b>Send match result screenshot.</b>\n(It will be saved in history)",
        'score_prompt': "✅ Screenshot received! Now enter the <b>match score</b> (CT:T), e.g. 13:7:",
        'pending_msg': "⏳ <b>Score sent for Admin review.</b>\nPlease wait for confirmation.",
        'match_finished': "🏆 <b>Match finished!</b>\nScore: <b>{}</b>\nYour result: <b>{}</b>",
        'finish_only_host': "⛔ Only Host can finish the match!",
        'finish_too_early': "⛔ Too early! Match can't last less than 10 minutes.",
        'elo_updated': "💰 <b>New ELO:</b> {}",
        'admin_new_result': "🚨 <b>Match #{} awaiting review!</b>\n\n📊 Score: <b>{}:{}</b>\n👑 Host: <code>{}</code>\n\nCheck screenshot and confirm:",
        'approve_btn': "✅ Approve Score",
        'kda_btn': "📝 Enter K/D/A",
        'kda_prompt': "📝 <b>Enter K/D/A for match #{}</b>\n\nPlayers:\n{}\n\nEnter stats in format:\n<code>ID K D A</code>\n(each on new line)\n\nExample:\n<code>123456 15 10 5</code>",
        'kda_saved': "✅ Stats saved for {} players!",
        'match_confirmed': "✅ Match #{} confirmed! ELO awarded.",
    }
}

def get_text(user_id, key, *args):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE tg_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    lang = res[0] if res else 'ru'
    text = TEXTS[lang].get(key, key)
    if args:
        return text.format(*args)
    return text

# --- ФУНКЦИИ ---
def get_level_number(elo):
    if elo < 500: return 1
    elif elo < 750: return 2
    elif elo < 1000: return 3
    elif elo < 1250: return 4
    elif elo < 1500: return 5
    elif elo < 1750: return 6
    elif elo < 2000: return 7
    elif elo < 2250: return 8
    elif elo < 2500: return 9
    else: return 10

def check_ban(user_id):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT ban_until, mute_until, ban_reason FROM users WHERE tg_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    if not res: return None, None, None
    ban_until, mute_until, reason = res
    now = time.time()
    if ban_until > now: return "banned", ban_until, reason
    if mute_until > now: return "muted", mute_until, reason
    return None, None, None

# --- СОСТОЯНИЯ ---
class RegisterStates(StatesGroup):
    waiting_for_lang = State()
    waiting_for_nickname = State()
    waiting_for_game_id = State()

class EditProfileStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_game_id = State()

class MatchSettings(StatesGroup):
    waiting_codes = State()

class MatchResult(StatesGroup):
    waiting_for_screenshot = State()
    waiting_for_score = State()

class AdminKDAStates(StatesGroup):
    waiting_for_kda = State()

class TicketStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_media = State()

class AdminStates(StatesGroup):
    waiting_for_id = State()
    waiting_for_reason = State()
    waiting_for_time = State()

# --- КЛАВИАТУРЫ ---
def main_menu(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'play'), callback_data="play")],
        [InlineKeyboardButton(text=get_text(user_id, 'my_matches'), callback_data="my_matches")],
        [InlineKeyboardButton(text=get_text(user_id, 'profile'), callback_data="profile"), 
         InlineKeyboardButton(text=get_text(user_id, 'leaderboard'), callback_data="leaderboard")],
        [InlineKeyboardButton(text=get_text(user_id, 'rules'), callback_data="rules"), 
         InlineKeyboardButton(text=get_text(user_id, 'ticket'), callback_data="ticket")],
        [InlineKeyboardButton(text=get_text(user_id, 'how_to_play'), callback_data="how_to_play")],
        [InlineKeyboardButton(text=get_text(user_id, 'change_lang_btn'), callback_data="change_lang")]
    ])

def admin_menu(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'admin_ban'), callback_data="admin_ban")],
        [InlineKeyboardButton(text=get_text(user_id, 'admin_mute'), callback_data="admin_mute")],
        [InlineKeyboardButton(text=get_text(user_id, 'back'), callback_data="main_menu")]
    ])

# --- СТАРТ ---
@dp.message(CommandStart())
async def start_cmd(message: Message, command: CommandObject, state: FSMContext):
    status, until, reason = check_ban(message.from_user.id)
    if status == "banned":
        until_str = datetime.fromtimestamp(until).strftime('%Y-%m-%d %H:%M')
        await message.answer(get_text(message.from_user.id, 'banned_msg', reason, until_str))
        return
    elif status == "muted":
        until_str = datetime.fromtimestamp(until).strftime('%Y-%m-%d %H:%M')
        await message.answer(get_text(message.from_user.id, 'muted_msg', reason, until_str))

    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT is_registered FROM users WHERE tg_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if not user:
        kb = [
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
        ]
        await message.answer(TEXTS['ru']['choose_lang'], reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await state.set_state(RegisterStates.waiting_for_lang)
        conn.close()
        return
        
    if user[0] == 0:
        await message.answer(get_text(message.from_user.id, 'enter_nick'), parse_mode="HTML")
        await state.set_state(RegisterStates.waiting_for_nickname)
        conn.close()
        return
    conn.close()

    if command.args and command.args.startswith("party_"):
        try:
            party_id = int(command.args.split("_")[1])
            await process_join_party(message, message.from_user.id, party_id)
            return
        except: pass

    await message.answer(get_text(message.from_user.id, 'main_menu'), reply_markup=main_menu(message.from_user.id))
@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await callback.answer()
    
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (tg_id, lang) VALUES (?, ?)", (callback.from_user.id, lang))
    cursor.execute("UPDATE users SET lang = ? WHERE tg_id = ?", (lang, callback.from_user.id))
    conn.commit()
    conn.close()
    
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT is_registered FROM users WHERE tg_id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    try:
        await callback.message.edit_text(get_text(callback.from_user.id, 'lang_set'))
    except: pass

    if not user or user[0] == 0:
        await callback.message.answer(get_text(callback.from_user.id, 'enter_nick'), parse_mode="HTML")
        await state.set_state(RegisterStates.waiting_for_nickname)
    else:
        await callback.message.answer(get_text(callback.from_user.id, 'main_menu'), reply_markup=main_menu(callback.from_user.id))

@dp.callback_query(F.data == "change_lang")
async def change_lang_menu(callback: CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ]
    await callback.message.answer(TEXTS['ru']['choose_lang'], reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.message(RegisterStates.waiting_for_nickname)
async def reg_nickname(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text.strip()[:20])
    await message.answer(get_text(message.from_user.id, 'enter_id'), parse_mode="HTML")
    await state.set_state(RegisterStates.waiting_for_game_id)

@dp.message(RegisterStates.waiting_for_game_id)
async def reg_game_id(message: Message, state: FSMContext):
    if not message.text.isdigit(): 
        await message.answer("❌ ID должен состоять только из цифр. Попробуй еще раз:")
        return
    data = await state.get_data()
    nickname = data.get('nickname', 'Unknown')
    
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT tg_id FROM users WHERE tg_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if user:
        cursor.execute('''UPDATE users SET nickname = ?, game_id = ?, is_registered = 1 WHERE tg_id = ?''', 
                       (nickname, message.text, message.from_user.id))
    else:
        cursor.execute('''INSERT INTO users (tg_id, nickname, game_id, is_registered) VALUES (?, ?, ?, 1)''', 
                       (message.from_user.id, nickname, message.text))
    
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(get_text(message.from_user.id, 'reg_done'), parse_mode="HTML", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(get_text(callback.from_user.id, 'main_menu'), reply_markup=main_menu(callback.from_user.id))

@dp.callback_query(F.data == "play")
async def play_handler(callback: CallbackQuery):
    status, _, _ = check_ban(callback.from_user.id)
    if status in ["banned", "muted"]:
        await callback.answer("⛔", show_alert=True)
        return
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT p.id FROM parties p JOIN party_players pp ON p.id = pp.party_id WHERE pp.user_id = ? AND p.status != 'finished' ''', (callback.from_user.id,))
    party = cursor.fetchone()
    conn.close()
    
    if party:
        kb = [[InlineKeyboardButton(text=get_text(callback.from_user.id, 'my_party'), callback_data="my_party")], [InlineKeyboardButton(text=get_text(callback.from_user.id, 'back'), callback_data="main_menu")]]
        await callback.message.edit_text(get_text(callback.from_user.id, 'already_in_party'), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        kb = [
            [InlineKeyboardButton(text=get_text(callback.from_user.id, 'create_party'), callback_data="create_party")],
            [InlineKeyboardButton(text=get_text(callback.from_user.id, 'search_solo'), callback_data="search_solo")],
            [InlineKeyboardButton(text=get_text(callback.from_user.id, 'back'), callback_data="main_menu")]
        ]
        await callback.message.edit_text(get_text(callback.from_user.id, 'main_menu'), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "my_matches")
async def my_matches_handler(callback: CallbackQuery):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT m.id, m.status, m.map_name, m.host_id FROM matches m JOIN match_players mp ON m.id = mp.match_id WHERE mp.user_id = ? AND m.status IN ('ready', 'waiting', 'pending')''', (callback.from_user.id,))
    active_match = cursor.fetchone()
    if active_match:
        match_id, status, map_name, host_id = active_match
        status_text = {"ready": "Игра началась", "waiting": "Выбор карты", "pending": "Ожидает проверки"}.get(status, "Неизвестно")
        text = f"🎮 <b>Твой активный матч #{match_id}</b>\n🗺 Карта: <b>{map_name or 'Не выбрана'}</b>\n🔴 Статус: <b>{status_text}</b>\n"
        kb = []
        if callback.from_user.id == host_id and status == 'ready':
            kb.append([InlineKeyboardButton(text=get_text(callback.from_user.id, 'finish_match_btn'), callback_data=f"finish_match_{match_id}")])
        kb.append([InlineKeyboardButton(text=get_text(callback.from_user.id, 'back_menu'), callback_data="main_menu")])
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        conn.close()
        return
    cursor.execute('''SELECT p.id FROM parties p JOIN party_players pp ON p.id = pp.party_id WHERE pp.user_id = ? AND p.status != 'finished' ''', (callback.from_user.id,))
    party = cursor.fetchone()
    conn.close()
    if party: await show_party(callback.message, party[0], callback.from_user.id)
    else: await callback.answer("У тебя нет активных матчей.", show_alert=True)

@dp.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, elo, game_id, matches_played, wins, losses, kills, deaths, assists FROM users WHERE tg_id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        winrate = int((user[4] / (user[4] + user[5])) * 100) if (user[4] + user[5]) > 0 else 0
        kd = user[6] / user[7] if user[7] > 0 else user[6]
        wr_color = "🟢" if winrate >= 50 else ("🟡" if winrate >= 40 else "🔴")
        kd_color = "🟢" if kd >= 1.0 else ("🟡" if kd >= 0.8 else "🔴")
        
        text = f"{get_text(callback.from_user.id, 'profile_title')}\n\n💳 TG: <code>{callback.from_user.id}</code>\n👤 Ник: <b>{user[0]}</b>\n💳 ID: <code>{user[2]}</code>\n\n"
        if user[3] < 10:
            text += get_text(callback.from_user.id, 'calibration', user[3])
        else:
            text += get_text(callback.from_user.id, 'elo_lvl', user[1], get_level_number(user[1])) + "\n"
            text += get_text(callback.from_user.id, 'winrate', winrate, user[4], user[5]) + "\n"
            text += get_text(callback.from_user.id, 'kd', kd, user[6], user[7]) + "\n"
            avg_kills = user[6] / user[3] if user[3] > 0 else 0
            avg_deaths = user[7] / user[3] if user[3] > 0 else 0
            avg_assists = user[8] / user[3] if user[3] > 0 else 0
            text += get_text(callback.from_user.id, 'kda', avg_kills, avg_deaths, avg_assists)
            
        kb = [
            [InlineKeyboardButton(text=get_text(callback.from_user.id, 'history'), callback_data="history_0")],
            [InlineKeyboardButton(text=get_text(callback.from_user.id, 'edit_data'), callback_data="edit_profile")],
            [InlineKeyboardButton(text=get_text(callback.from_user.id, 'back'), callback_data="main_menu")]
        ]
        if callback.from_user.id == ADMIN_ID:
            kb.insert(0, [InlineKeyboardButton(text=get_text(callback.from_user.id, 'admin_panel'), callback_data="admin_panel")])
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("history_"))
async def history_handler(callback: CallbackQuery):
    try:
        offset = int(callback.data.split("_")[1])
    except IndexError:
        offset = 0

    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT COUNT(*) FROM matches m JOIN match_players mp ON m.id = mp.match_id WHERE mp.user_id = ? AND m.status = 'finished' ''', (callback.from_user.id,))
    total_matches = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT m.id, m.score_ct, m.score_t, m.winner, mp.team, m.map_name 
        FROM matches m 
        JOIN match_players mp ON m.id = mp.match_id 
        WHERE mp.user_id = ? AND m.status = 'finished'
        ORDER BY m.id DESC LIMIT 5 OFFSET ?
    ''', (callback.from_user.id, offset))
    history = cursor.fetchall()
    conn.close()
    
    if not history:
        text = get_text(callback.from_user.id, 'no_history') if offset == 0 else get_text(callback.from_user.id, 'no_matches')
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_text(callback.from_user.id, 'back_profile'), callback_data="profile")]]))
        await callback.answer()
        return

    text = get_text(callback.from_user.id, 'history_title')
    for match in history:
        m_id, s_ct, s_t, winner, my_team, map_name = match
        res = get_text(callback.from_user.id, 'win') if my_team == winner else get_text(callback.from_user.id, 'lose')
        text += get_text(callback.from_user.id, 'match_row', m_id, map_name or '?', s_ct, s_t, res)
    
    kb = []
    nav_buttons = []
    if offset > 0: nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"history_{offset - 5}"))
    if offset + 5 < total_matches: nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"history_{offset + 5}"))
    if nav_buttons: kb.append(nav_buttons)
    kb.append([InlineKeyboardButton(text=get_text(callback.from_user.id, 'back_profile'), callback_data="profile")])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data == "leaderboard")
async def leaderboard_handler(callback: CallbackQuery):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, elo FROM users WHERE matches_played >= 10 ORDER BY elo DESC LIMIT 10")
    top = cursor.fetchall()
    conn.close()
    
    text = get_text(callback.from_user.id, 'top_players')
    if not top: text += get_text(callback.from_user.id, 'no_players')
    else:
        for i, (name, elo) in enumerate(top, 1):
            text += get_text(callback.from_user.id, 'top_row', i, name, elo, get_level_number(elo))
            
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_text(callback.from_user.id, 'back'), callback_data="main_menu")]]))
    await callback.answer()

@dp.callback_query(F.data == "ticket")
async def ticket_start(callback: CallbackQuery):
    kb = [
        [InlineKeyboardButton(text=get_text(callback.from_user.id, 'ticket_admin'), callback_data="ticket_cat_0")],
        [InlineKeyboardButton(text=get_text(callback.from_user.id, 'ticket_player'), callback_data="ticket_cat_1")],
        [InlineKeyboardButton(text=get_text(callback.from_user.id, 'ticket_bug'), callback_data="ticket_cat_2")],
        [InlineKeyboardButton(text=get_text(callback.from_user.id, 'ticket_other'), callback_data="ticket_cat_3")],
        [InlineKeyboardButton(text=get_text(callback.from_user.id, 'cancel'), callback_data="main_menu")]
    ]
    await callback.message.edit_text(get_text(callback.from_user.id, 'ticket_cat'), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("ticket_cat_"))
async def ticket_category(callback: CallbackQuery, state: FSMContext):
    cat_id = callback.data.split("_")[2]
    cat_map = {"0": "ticket_admin", "1": "ticket_player", "2": "ticket_bug", "3": "ticket_other"}
    category = get_text(callback.from_user.id, cat_map.get(cat_id, "ticket_other"))
    await state.update_data(category=category)
    kb = [[InlineKeyboardButton(text=get_text(callback.from_user.id, 'cancel'), callback_data="main_menu")]]
    await callback.message.edit_text(get_text(callback.from_user.id, 'ticket_text', category), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(TicketStates.waiting_for_text)
    await callback.answer()

@dp.message(TicketStates.waiting_for_text)
async def ticket_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer(get_text(message.from_user.id, 'ticket_media'), parse_mode="HTML")
    await state.set_state(TicketStates.waiting_for_media)

@dp.message(TicketStates.waiting_for_media, F.photo | F.video | F.text)
async def ticket_media(message: Message, state: FSMContext):
    data = await state.get_data()
    caption = f"🚨 TICKET\nCategory: {data['category']}\nFrom: {message.from_user.first_name} (<code>{message.from_user.id}</code>)\n\nText: {data['text']}"
    try:
        if message.photo: await bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=caption, parse_mode="HTML")
        elif message.video: await bot.send_video(ADMIN_ID, video=message.video.file_id, caption=caption, parse_mode="HTML")
        else: await bot.send_message(ADMIN_ID, caption, parse_mode="HTML")
        await message.answer(get_text(message.from_user.id, 'ticket_sent'), reply_markup=main_menu(message.from_user.id))
    except: await message.answer("Error.", reply_markup=main_menu(message.from_user.id))
    await state.clear()
@dp.callback_query(F.data == "create_party")
async def create_party_start(callback: CallbackQuery):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO parties (leader_id) VALUES (?)", (callback.from_user.id,))
    party_id = cursor.lastrowid
    cursor.execute("INSERT INTO party_players (party_id, user_id) VALUES (?, ?)", (party_id, callback.from_user.id))
    conn.commit()
    conn.close()
    await show_party(callback.message, party_id, callback.from_user.id)

@dp.callback_query(F.data == "search_solo")
async def search_solo(callback: CallbackQuery):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO parties (leader_id) VALUES (?)", (callback.from_user.id,))
    party_id = cursor.lastrowid
    cursor.execute("INSERT INTO party_players (party_id, user_id) VALUES (?, ?)", (party_id, callback.from_user.id))
    cursor.execute("UPDATE parties SET status = 'searching' WHERE id = ?", (party_id,))
    conn.commit()
    conn.close()
    kb = [[InlineKeyboardButton(text=get_text(callback.from_user.id, 'cancel_search'), callback_data=f"cancel_search_{party_id}")]]
    await callback.message.edit_text(get_text(callback.from_user.id, 'searching_solo'), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await try_matchmaking()

async def show_party(message_or_callback, party_id, user_id):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT leader_id, status, match_id FROM parties WHERE id = ?", (party_id,))
    leader_id, status, match_id = cursor.fetchone()
    cursor.execute('''SELECT u.nickname, u.elo, u.tg_id, u.wins, u.losses, u.matches_played FROM party_players pp JOIN users u ON pp.user_id = u.tg_id WHERE pp.party_id = ?''', (party_id,))
    players = cursor.fetchall()
    conn.close()
    
    leader = players[0]
    text = f"👥 <b>Ваше пати ({len(players)}/5)</b>\n"
    
    if leader[5] < 10:
        text += f"👑 Капитан: <b>{leader[0]}</b> (Калибровка)\n\n"
    else:
        text += f"👑 Капитан: <b>{leader[0]}</b> ({leader[1]} ELO, {get_level_number(leader[1])} LVL)\n\n"
    
    text += "👤 <b>Игроки:</b>\n"
    for p in players:
        nick, elo, tg_id, wins, losses, matches_played = p
        if matches_played < 10:
            text += f"• <b>{nick}</b> — Калибровка ({matches_played}/10)\n"
        else:
            total_games = wins + losses
            winrate = int((wins / total_games) * 100) if total_games > 0 else 0
            wr_color = "🟢" if winrate >= 50 else ("🟡" if winrate >= 40 else "🔴")
            text += f"• <b>{nick}</b> — {elo} ELO ({get_level_number(elo)} LVL) | {wr_color} WR: {winrate}%\n"
    
    status_map = {"gathering": "party_gathering", "searching": "party_searching", "in_game": "party_ingame"}
    text += get_text(user_id, 'party_status', get_text(user_id, status_map.get(status, "party_gathering")))
    
    kb = []
    if status == 'gathering':
        bot_info = await bot.get_me()
        invite_link = f"https://t.me/{bot_info.username}?start=party_{party_id}"
        kb.append([InlineKeyboardButton(text=get_text(user_id, 'invite_friend'), url=f"https://t.me/share/url?url={invite_link}&text=Join!")])
        if user_id == leader_id: kb.append([InlineKeyboardButton(text=get_text(user_id, 'find_match'), callback_data=f"start_search_{party_id}")])
    elif status == 'searching':
        kb.append([InlineKeyboardButton(text=get_text(user_id, 'cancel_search'), callback_data=f"cancel_search_{party_id}")])
    elif status == 'in_game':
        conn = sqlite3.connect('faceit.db')
        cursor = conn.cursor()
        cursor.execute("SELECT host_id FROM matches WHERE id = ?", (match_id,))
        match_host = cursor.fetchone()
        conn.close()
        if match_host and user_id == match_host[0]:
            kb.append([InlineKeyboardButton(text=get_text(user_id, 'finish_match_btn'), callback_data=f"finish_match_{match_id}")])

    kb.append([InlineKeyboardButton(text=get_text(user_id, 'leave_party'), callback_data=f"leave_party_{party_id}")])
    kb.append([InlineKeyboardButton(text=get_text(user_id, 'back_menu'), callback_data="main_menu")])
    
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        try: await message_or_callback.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        except: await message_or_callback.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

async def process_join_party(target, user_id, party_id):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM parties WHERE id = ?", (party_id,))
    party_data = cursor.fetchone()
    if not party_data:
        await target.answer("Пати не найдено.")
        conn.close()
        return
        
    if party_data[0] != 'gathering':
        await target.answer("В эту пати уже нельзя зайти (идет поиск или игра).")
        conn.close()
        return

    cursor.execute("SELECT p.id FROM parties p JOIN party_players pp ON p.id = pp.party_id WHERE pp.user_id = ? AND p.status != 'finished'", (user_id,))
    if cursor.fetchone():
        await target.answer("⛔ Ты уже находишься в пати! Сначала выйди из текущей.", show_alert=True)
        conn.close()
        return

    cursor.execute("SELECT COUNT(*) FROM party_players WHERE party_id = ?", (party_id,))
    if cursor.fetchone()[0] >= 5:
        await target.answer("Пати заполнена (5/5).")
        conn.close()
        return

    cursor.execute("INSERT INTO party_players (party_id, user_id) VALUES (?, ?)", (party_id, user_id))
    conn.commit()
    conn.close()
    
    await show_party(target, party_id, user_id)

@dp.callback_query(F.data.startswith("start_search_"))
async def start_search(callback: CallbackQuery):
    party_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE parties SET status = 'searching' WHERE id = ?", (party_id,))
    conn.commit()
    conn.close()
    kb = [[InlineKeyboardButton(text=get_text(callback.from_user.id, 'cancel_search'), callback_data=f"cancel_search_{party_id}")]]
    await callback.message.edit_text(get_text(callback.from_user.id, 'searching_match'), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await try_matchmaking()

@dp.callback_query(F.data.startswith("cancel_search_"))
async def cancel_search(callback: CallbackQuery):
    party_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE parties SET status = 'gathering' WHERE id = ?", (party_id,))
    cursor.execute("SELECT COUNT(*) FROM party_players WHERE party_id = ?", (party_id,))
    if cursor.fetchone()[0] == 1:
        cursor.execute("DELETE FROM party_players WHERE party_id = ?", (party_id,))
        cursor.execute("DELETE FROM parties WHERE id = ?", (party_id,))
    conn.commit()
    conn.close()
    await callback.message.edit_text(get_text(callback.from_user.id, 'search_stopped'), reply_markup=main_menu(callback.from_user.id))
    await callback.answer()

async def try_matchmaking():
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM parties WHERE status = 'searching'")
    parties = [row[0] for row in cursor.fetchall()]
    total_players = 0
    party_sizes = {}
    for p_id in parties:
        cursor.execute("SELECT COUNT(*) FROM party_players WHERE party_id = ?", (p_id,))
        size = cursor.fetchone()[0]
        party_sizes[p_id] = size
        total_players += size
        
    if total_players >= 10:
        selected_parties = []
        current_count = 0
        for p_id in parties:
            if current_count + party_sizes[p_id] <= 10:
                selected_parties.append(p_id)
                current_count += party_sizes[p_id]
            if current_count == 10:
                break
                
        if current_count == 10:
            cursor.execute("INSERT INTO matches (status) VALUES ('waiting')")
            match_id = cursor.lastrowid
            all_players = []
            for p_id in selected_parties:
                cursor.execute("SELECT user_id FROM party_players WHERE party_id = ?", (p_id,))
                all_players.extend([row[0] for row in cursor.fetchall()])
            for pid in all_players:
                cursor.execute("INSERT INTO match_players (match_id, user_id, team) VALUES (?, ?, 'CT')", (match_id, pid))
            for p_id in selected_parties:
                cursor.execute("UPDATE parties SET status = 'in_game', match_id = ? WHERE id = ?", (match_id, p_id))
            conn.commit()
            conn.close()
            for pid in all_players:
                try: await bot.send_message(pid, get_text(pid, 'match_found'), parse_mode="HTML")
                except: pass
            await balance_and_start(match_id)
            return
    conn.close()

async def balance_and_start(match_id):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT u.tg_id, u.nickname, u.elo FROM match_players mp JOIN users u ON mp.user_id = u.tg_id WHERE mp.match_id = ?''', (match_id,))
    players = cursor.fetchall()
    players.sort(key=lambda x: x[2], reverse=True)
    team_ct, team_t = [], []
    elo_ct, elo_t = 0, 0
    for p_id, nick, elo in players:
        if elo_ct <= elo_t:
            team_ct.append((p_id, nick, elo)); elo_ct += elo
        else:
            team_t.append((p_id, nick, elo)); elo_t += elo
    cursor.execute("DELETE FROM match_players WHERE match_id = ?", (match_id,))
    for p_id, _, _ in team_ct: cursor.execute("INSERT INTO match_players (match_id, user_id, team) VALUES (?, ?, 'CT')", (match_id, p_id))
    for p_id, _, _ in team_t: cursor.execute("INSERT INTO match_players (match_id, user_id, team) VALUES (?, ?, 'T')", (match_id, p_id))
    cap_ct = max(team_ct, key=lambda x: x[2])[0]
    cap_t = max(team_t, key=lambda x: x[2])[0]
    host_id = random.choice(players)[0]
    cursor.execute("UPDATE matches SET host_id = ? WHERE id = ?", (host_id, match_id))
    conn.commit()
    conn.close()
    maps = ["Vertigo", "Mirage", "Inferno", "Dust 2"]
    await start_veto(match_id, cap_ct, cap_t, maps)

async def start_veto(match_id, cap_ct, cap_t, maps):
    kb = [[InlineKeyboardButton(text=f"❌ {m}", callback_data=f"veto_{match_id}_CT_{m}")] for m in maps]
    await bot.send_message(cap_ct, get_text(cap_ct, 'veto_title', "CT"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await bot.send_message(cap_t, get_text(cap_t, 'veto_wait', "CT"), parse_mode="HTML")

@dp.callback_query(F.data.startswith("veto_"))
async def process_veto(callback: CallbackQuery):
    data = callback.data.split("_")
    match_id = int(data[1])
    team = data[2]
    map_banned = data[3]
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT u.tg_id FROM match_players mp JOIN users u ON mp.user_id = u.tg_id WHERE mp.match_id = ? AND mp.team = ? ORDER BY u.elo DESC LIMIT 1''', (match_id, team))
    captain = cursor.fetchone()[0]
    if callback.from_user.id != captain:
        await callback.answer("Only Captain!", show_alert=True)
        return
    maps = ["Vertigo", "Mirage", "Inferno", "Dust 2"]
    if map_banned in maps: maps.remove(map_banned)
    await callback.message.edit_text(get_text(callback.from_user.id, 'veto_banned', map_banned))
    
    if len(maps) == 1:
        final_map = maps[0]
        cursor.execute("UPDATE matches SET map_name = ? WHERE id = ?", (final_map, match_id))
        conn.commit()
        cursor.execute("SELECT host_id FROM matches WHERE id = ?", (match_id,))
        host_id = cursor.fetchone()[0]
        conn.close()
        
        await bot.send_message(host_id, get_text(host_id, 'veto_final_map', final_map) + "\n\n" + get_text(host_id, 'veto_host_instruction'), parse_mode="HTML")
        await dp.fsm.get_context(bot, chat_id=host_id, user_id=host_id).set_state(MatchSettings.waiting_codes)
        await dp.fsm.get_context(bot, chat_id=host_id, user_id=host_id).update_data(match_id=match_id)
        await callback.message.answer(get_text(callback.from_user.id, 'veto_host_wait', final_map), parse_mode="HTML")
        
    else:
        next_team = "T" if team == "CT" else "CT"
        cursor.execute('''SELECT u.tg_id FROM match_players mp JOIN users u ON mp.user_id = u.tg_id WHERE mp.match_id = ? AND mp.team = ? ORDER BY u.elo DESC LIMIT 1''', (match_id, next_team))
        next_cap_id = cursor.fetchone()[0]
        conn.close()
        kb = [[InlineKeyboardButton(text=f"❌ {m}", callback_data=f"veto_{match_id}_{next_team}_{m}")] for m in maps]
        await bot.send_message(next_cap_id, get_text(next_cap_id, 'veto_title', next_team), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.message(MatchSettings.waiting_codes, F.text.startswith("CT-"))
async def receive_codes(message: Message, state: FSMContext):
    parts = message.text.split()
    if len(parts) != 2 or not parts[0].startswith("CT-") or not parts[1].startswith("T-"):
        await message.answer("❌ Format: <code>CT-111 T-222</code>", parse_mode="HTML")
        return
    code_ct, code_t = parts[0], parts[1]
    data = await state.get_data()
    match_id = data.get('match_id')
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    start_time = time.time()
    cursor.execute("UPDATE matches SET code_ct = ?, code_t = ?, status = 'ready', start_time = ? WHERE id = ?", (code_ct, code_t, start_time, match_id))
    cursor.execute('''SELECT user_id, team FROM match_players WHERE match_id = ?''', (match_id,))
    players = cursor.fetchall()
    conn.commit()
    conn.close()
    await state.clear()
    for p_id, team in players:
        assigned_code = code_ct if team == 'CT' else code_t
        team_name = get_text(p_id, 'team_ct') if team == 'CT' else get_text(p_id, 'team_t')
        try: await bot.send_message(p_id, get_text(p_id, 'match_ready', team_name, assigned_code), parse_mode="HTML")
        except: pass
    await message.answer(get_text(message.from_user.id, 'codes_sent'))

@dp.callback_query(F.data.startswith("finish_match_"))
async def finish_match_start(callback: CallbackQuery, state: FSMContext):
    match_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT host_id, start_time FROM matches WHERE id = ?", (match_id,))
    match = cursor.fetchone()
    conn.close()
    if not match: return
    host_id, start_time = match
    if callback.from_user.id != host_id:
        await callback.answer(get_text(callback.from_user.id, 'finish_only_host'), show_alert=True)
        return
    if time.time() - start_time < 600:
        await callback.answer(get_text(callback.from_user.id, 'finish_too_early'), show_alert=True)
        return
    await state.update_data(match_id=match_id)
    await callback.message.answer(get_text(callback.from_user.id, 'finish_match_prompt'))
    await state.set_state(MatchResult.waiting_for_screenshot)
    await callback.answer()

@dp.message(MatchResult.waiting_for_screenshot, F.photo)
async def match_screenshot_received(message: Message, state: FSMContext):
    photo = message.photo[-1]
    data = await state.get_data()
    match_id = data['match_id']
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE matches SET screenshot_id = ? WHERE id = ?", (photo.file_id, match_id))
    conn.commit()
    conn.close()
    await message.answer(get_text(message.from_user.id, 'score_prompt'), parse_mode="HTML")
    await state.set_state(MatchResult.waiting_for_score)

@dp.message(MatchResult.waiting_for_score)
async def match_score_received(message: Message, state: FSMContext):
    try:
        score_ct, score_t = map(int, message.text.split(":"))
    except:
        await message.answer("❌ Format: 13:7")
        return
    data = await state.get_data()
    match_id = data['match_id']
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE matches SET score_ct = ?, score_t = ?, status = 'pending' WHERE id = ?", (score_ct, score_t, match_id))
    cursor.execute("SELECT screenshot_id, host_id FROM matches WHERE id = ?", (match_id,))
    res = cursor.fetchone()
    screenshot_id, host_id = res if res else (None, None)
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(get_text(message.from_user.id, 'pending_msg'), parse_mode="HTML")
    
    try:
        admin_text = get_text(ADMIN_ID, 'admin_new_result', match_id, score_ct, score_t, host_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(ADMIN_ID, 'approve_btn'), callback_data=f"approve_match_{match_id}")],
            [InlineKeyboardButton(text=get_text(ADMIN_ID, 'kda_btn'), callback_data=f"enter_kda_{match_id}")]
        ])
        if screenshot_id:
            await bot.send_photo(ADMIN_ID, photo=screenshot_id, caption=admin_text, parse_mode="HTML", reply_markup=kb)
        else:
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        print(f"Ошибка: {e}")

@dp.callback_query(F.data.startswith("approve_match_"))
async def approve_match(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    match_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT score_ct, score_t FROM matches WHERE id = ?", (match_id,))
    score_ct, score_t = cursor.fetchone()
    winner = 'CT' if score_ct > score_t else 'T'
    round_diff = abs(score_ct - score_t)
    cursor.execute("SELECT user_id, team FROM match_players WHERE match_id = ?", (match_id,))
    players = cursor.fetchall()
    
    for p_id, team in players:
        cursor.execute("SELECT matches_played FROM users WHERE tg_id = ?", (p_id,))
        matches = cursor.fetchone()[0]
        elo_change = (25 + round_diff) * 2 if matches < 10 else 25 + round_diff
        if team == winner:
            cursor.execute("UPDATE users SET elo = elo + ?, matches_played = matches_played + 1, wins = wins + 1 WHERE tg_id = ?", (elo_change, p_id))
        else:
            cursor.execute("UPDATE users SET elo = elo - ?, matches_played = matches_played + 1, losses = losses + 1 WHERE tg_id = ?", (elo_change, p_id))
    
    cursor.execute("UPDATE matches SET status = 'finished', winner = ? WHERE id = ?", (winner, match_id))
    conn.commit()
    conn.close()
    await callback.message.edit_text(get_text(callback.from_user.id, 'match_confirmed', match_id))
    for p_id, team in players:
        try:
            res = get_text(p_id, 'win') if team == winner else get_text(p_id, 'lose')
            conn = sqlite3.connect('faceit.db')
            cursor = conn.cursor()
            cursor.execute("SELECT elo FROM users WHERE tg_id = ?", (p_id,))
            new_elo = cursor.fetchone()[0]
            conn.close()
            await bot.send_message(p_id, get_text(p_id, 'match_finished', f"{score_ct}:{score_t}", res) + "\n\n" + get_text(p_id, 'elo_updated', new_elo), parse_mode="HTML")
        except: pass
    await callback.answer()

@dp.callback_query(F.data.startswith("enter_kda_"))
async def enter_kda_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    match_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT u.nickname, mp.user_id, mp.team FROM match_players mp JOIN users u ON mp.user_id = u.tg_id WHERE mp.match_id = ?''', (match_id,))
    players = cursor.fetchall()
    conn.close()
    players_text = "\n".join([f"{p[2]}: {p[0]} (<code>{p[1]}</code>)" for p in players])
    text = get_text(callback.from_user.id, 'kda_prompt', match_id, players_text)
    await state.update_data(match_id=match_id)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_text(callback.from_user.id, 'cancel'), callback_data=f"approve_match_{match_id}")]]))
    await state.set_state(AdminKDAStates.waiting_for_kda)
    await callback.answer()

@dp.message(AdminKDAStates.waiting_for_kda)
async def save_kda(message: Message, state: FSMContext):
    data = await state.get_data()
    match_id = data['match_id']
    lines = message.text.strip().split('\n')
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    saved_count = 0
    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit():
            p_id = int(parts[0])
            k, d, a = parts[1], parts[2], parts[3]
            cursor.execute("UPDATE match_players SET kills = ?, deaths = ?, assists = ? WHERE match_id = ? AND user_id = ?", (k, d, a, match_id, p_id))
            cursor.execute("UPDATE users SET kills = kills + ?, deaths = deaths + ?, assists = assists + ? WHERE tg_id = ?", (k, d, a, p_id))
            saved_count += 1
    conn.commit()
    conn.close()
    await message.answer(get_text(message.from_user.id, 'kda_saved', saved_count), reply_markup=admin_menu(message.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ No rights!", show_alert=True)
        return
    await callback.message.edit_text(get_text(callback.from_user.id, 'admin_panel_title'), parse_mode="HTML", reply_markup=admin_menu(callback.from_user.id))

@dp.callback_query(F.data.in_({"admin_ban", "admin_mute"}))
async def admin_punish_start(callback: CallbackQuery, state: FSMContext):
    action = "ban" if callback.data == "admin_ban" else "mute"
    await state.update_data(action=action)
    kb = [[InlineKeyboardButton(text=get_text(callback.from_user.id, 'cancel'), callback_data="admin_panel")]]
    await callback.message.edit_text(get_text(callback.from_user.id, 'admin_id_prompt'), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(AdminStates.waiting_for_id)
    await callback.answer()

@dp.message(AdminStates.waiting_for_id)
async def admin_get_id(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    await state.update_data(target_id=int(message.text))
    await message.answer(get_text(message.from_user.id, 'admin_reason_prompt'))
    await state.set_state(AdminStates.waiting_for_reason)

@dp.message(AdminStates.waiting_for_reason)
async def admin_get_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await message.answer(get_text(message.from_user.id, 'admin_time_prompt'))
    await state.set_state(AdminStates.waiting_for_time)

@dp.message(AdminStates.waiting_for_time)
async def admin_get_time(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    days = int(message.text)
    data = await state.get_data()
    until = time.time() + (days * 86400)
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    if data['action'] == "ban":
        cursor.execute("UPDATE users SET ban_until = ?, ban_reason = ? WHERE tg_id = ?", (until, data['reason'], data['target_id']))
    else:
        cursor.execute("UPDATE users SET mute_until = ?, ban_reason = ? WHERE tg_id = ?", (until, data['reason'], data['target_id']))
    conn.commit()
    conn.close()
    await message.answer(get_text(message.from_user.id, 'admin_punished', days), reply_markup=admin_menu(message.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "rules")
async def rules_handler(callback: CallbackQuery):
    await callback.message.edit_text(get_text(callback.from_user.id, 'rules_text'), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_text(callback.from_user.id, 'back'), callback_data="main_menu")]]))

@dp.callback_query(F.data == "how_to_play")
async def how_to_play_handler(callback: CallbackQuery):
    await callback.message.edit_text(get_text(callback.from_user.id, 'how_to_play_text'), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_text(callback.from_user.id, 'back'), callback_data="main_menu")]]))

@dp.callback_query(F.data.startswith("leave_party_"))
async def leave_party(callback: CallbackQuery):
    party_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM party_players WHERE party_id = ? AND user_id = ?", (party_id, callback.from_user.id))
    cursor.execute("SELECT COUNT(*) FROM party_players WHERE party_id = ?", (party_id,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("DELETE FROM parties WHERE id = ?", (party_id,))
    conn.commit()
    conn.close()
    await callback.message.edit_text(get_text(callback.from_user.id, 'leave_party'), reply_markup=main_menu(callback.from_user.id))

@dp.callback_query(F.data == "edit_profile")
async def edit_profile_start(callback: CallbackQuery, state: FSMContext):
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, game_id FROM users WHERE tg_id = ?", (callback.from_user.id,))
    old_data = cursor.fetchone()
    conn.close()
    
    await state.update_data(old_nick=old_data[0], old_id=old_data[1])
    kb = [[InlineKeyboardButton(text=get_text(callback.from_user.id, 'cancel'), callback_data="profile")]]
    await callback.message.edit_text(get_text(callback.from_user.id, 'edit_nick_prompt'), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(EditProfileStates.waiting_for_nickname)
    await callback.answer()

@dp.message(EditProfileStates.waiting_for_nickname)
async def edit_nickname(message: Message, state: FSMContext):
    await state.update_data(new_nick=message.text.strip()[:20])
    kb = [[InlineKeyboardButton(text=get_text(message.from_user.id, 'cancel'), callback_data="profile")]]
    await message.answer(get_text(message.from_user.id, 'edit_id_prompt'), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(EditProfileStates.waiting_for_game_id)

@dp.message(EditProfileStates.waiting_for_game_id)
async def edit_game_id(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    new_id = message.text
    data = await state.get_data()
    old_nick, old_id, new_nick = data['old_nick'], data['old_id'], data['new_nick']
    
    conn = sqlite3.connect('faceit.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET nickname = ?, game_id = ? WHERE tg_id = ?", (new_nick, new_id, message.from_user.id))
    conn.commit()
    conn.close()
    
    try:
        await bot.send_message(
            ADMIN_ID,
            et_text(ADMIN_ID, 'log_edit', message.from_user.first_name, message.from_user.username, message.from_user.id, old_nick, old_id, new_nick, new_id),
            parse_mode="HTML"
        )
    except: pass
    
    await state.clear()
    await message.answer(get_text(message.from_user.id, 'edit_done'), parse_mode="HTML", reply_markup=main_menu(message.from_user.id))

async def main():
    print("Бот запущен! Версия 50.0 (Исправлены баги)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())