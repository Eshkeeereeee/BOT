from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, BufferedInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import uuid
import io

import cfg
from database import Database
from keyboards import main_keyboard, currency_keyboard, activate_check_keyboard, support_keyboard, \
    edit_currency_keyboard
from utils import generate_qk_code

router = Router()
db = Database()


class CheckStates(StatesGroup):
    waiting_for_currency = State()
    waiting_for_activations = State()
    waiting_for_amount = State()
    waiting_for_code = State()


class DepositStates(StatesGroup):
    waiting_for_amount = State()


class WithdrawStates(StatesGroup):
    waiting_for_amount = State()


class EditDBStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_currency = State()
    waiting_for_amount = State()


@router.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без username"
    is_admin = user_id == cfg.admin_id

    if len(message.text.split()) > 1:
        check_code = message.text.split()[1]
        await handle_check_activation(message, check_code)
        return

    if await db.user_exists(user_id):
        await message.answer(
            "🌟 Доброго времени суток!",
            reply_markup=main_keyboard(is_admin)
        )
    else:
        await message.answer(
            f"👋 Добро пожаловать!\n\n"
            f"Рад видеть вас в нашем боте! Сейчас я зарегистрирую вас в системе..."
        )

        qk_code = await generate_qk_code(db)
        await db.add_user(user_id, username, qk_code)

        await message.answer(
            f"✅ Регистрация успешно завершена!\n"
            f"Ваш уникальный код: `{qk_code}`",
            parse_mode="Markdown",
            reply_markup=main_keyboard(is_admin)
        )


async def handle_check_activation(message: Message, check_code: str):
    user_id = message.from_user.id
    username = message.from_user.username or "Без username"
    is_admin = user_id == cfg.admin_id

    if not await db.user_exists(user_id):
        qk_code = await generate_qk_code(db)
        await db.add_user(user_id, username, qk_code)
        await message.answer(
            f"👋 Добро пожаловать! Вы зарегистрированы в системе.\n"
            f"Ваш уникальный код: `{qk_code}`\n\n",
            parse_mode="Markdown"
        )

    check_data = await db.get_check(check_code)

    if not check_data:
        await message.answer(
            "❌ Чек не найден или недействителен.",
            reply_markup=main_keyboard(is_admin)
        )
        return

    if not check_data['is_active']:
        await message.answer(
            "❌ Этот чек уже использован.",
            reply_markup=main_keyboard(is_admin)
        )
        return

    if check_data['activations'] >= check_data['max_activations']:
        await message.answer(
            "❌ Лимит активаций чека исчерпан.",
            reply_markup=main_keyboard(is_admin)
        )
        return

    if await db.check_user_activated(check_code, user_id):
        await message.answer(
            "❌ Вы уже активировали этот чек ранее.",
            reply_markup=main_keyboard(is_admin)
        )
        return

    currency_emoji = {
        'bananas': '🍌',
        'stars': '⭐',
        'cakes': '🎂'
    }

    currency_name = {
        'bananas': 'Бананы',
        'stars': 'Звезды',
        'cakes': 'Торты'
    }

    await message.answer(
        f"🎁 **Чек найден!**\n\n"
        f"💰 Награда: {check_data['amount']} {currency_emoji[check_data['currency']]} {currency_name[check_data['currency']]}\n"
        f"🎯 Активаций: {check_data['activations']}/{check_data['max_activations']}\n\n"
        f"Хотите получить награду?",
        parse_mode="Markdown",
        reply_markup=activate_check_keyboard(check_code)
    )


@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)

    if user_data:
        await message.answer(
            f"👤 **Ваш профиль**\n\n"
            f"🆔 ID: `{user_data['user_id']}`\n"
            f"👤 Username: @{user_data['username']}\n"
            f"🔑 Код: `{user_data['qk_code']}`\n\n"
            f"💰 **Баланс:**\n"
            f"🍌 Бананы: {user_data['bananas']}\n"
            f"⭐ Звезды: {user_data['stars']}\n"
            f"🎂 Торты: {user_data['cakes']}\n"
            f"⭐ Личные звезды: {user_data['startL']}\n"
            f"🌟 Звезды бота: {user_data['startB']}",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Ошибка: профиль не найден")


@router.message(F.text == "💰 Пополнить")
async def deposit_handler(message: Message, state: FSMContext):
    await message.answer(
        "💰 **На сколько?**\n\n"
        "Введите количество звезд для пополнения (минимум 150):"
    )
    await state.set_state(DepositStates.waiting_for_amount)


@router.message(DepositStates.waiting_for_amount)
async def deposit_amount_handler(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = int(message.text)
        if amount < 150:
            await message.answer("❌ Минимальная сумма пополнения: 150 звезд")
            return

        await create_payment(message, message.from_user.id, amount, bot, "deposit")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(F.text == "💸 Вывод")
async def withdraw_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)

    if not user_data:
        await message.answer("❌ Ошибка: профиль не найден")
        return

    balance = user_data['startL']

    if balance < 100:
        await message.answer(
            f"❌ **Недостаточно средств для вывода**\n\n"
            f"💰 Ваш баланс: {balance} звезд\n"
            f"📝 Минимальная сумма вывода: 100 звезд",
            parse_mode="Markdown"
        )
        return

    await message.answer(
        f"💸 **Вывод средств**\n\n"
        f"💰 Ваш баланс: {balance} звезд\n"
        f"📝 Минимальная сумма вывода: 100 звезд\n"
        f"🎯 Максимальная сумма вывода: {balance} звезд\n\n"
        f"Введите сумму для вывода:",
        parse_mode="Markdown"
    )
    await state.set_state(WithdrawStates.waiting_for_amount)


@router.message(WithdrawStates.waiting_for_amount)
async def withdraw_amount_handler(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = int(message.text)
        user_id = message.from_user.id
        username = message.from_user.username or "Без username"

        user_data = await db.get_user(user_id)
        balance = user_data['startL']

        if amount < 100:
            await message.answer("❌ Минимальная сумма вывода: 100 звезд")
            return

        if amount > balance:
            await message.answer(f"❌ Недостаточно средств. Ваш баланс: {balance} звезд")
            return

        withdrawal_id = f"WD-{str(uuid.uuid4())[:8].upper()}"

        await db.subtract_stars(user_id, amount)
        await db.create_withdrawal(user_id, amount, withdrawal_id)

        await message.answer(
            f"✅ **Заявка на вывод создана!**\n\n"
            f"💰 Сумма: {amount} звезд\n"
            f"🆔 ID транзакции: `{withdrawal_id}`\n\n"
            f"📋 Ваша заявка отправлена на обработку администратору.\n"
            f"⏰ Обработка заявок происходит в течение 24 часов.\n"
            f"✉️ Вы получите уведомление о статусе заявки.",
            parse_mode="Markdown"
        )

        try:
            await bot.send_message(
                cfg.admin_id,
                f"💸 **Новая заявка на вывод!**\n\n"
                f"👤 Пользователь: @{username} (ID: {user_id})\n"
                f"💰 Сумма: {amount} звезд\n"
                f"🆔 ID транзакции: `{withdrawal_id}`\n"
                f"📅 Дата: {message.date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🔥 Средства списаны с баланса пользователя.",
                parse_mode="Markdown"
            )
        except:
            pass

        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(F.text == "🤝 Поддержать")
async def support_handler(message: Message):
    await message.answer(
        "🤝 **Поддержать бота**\n\n"
        "Выберите сумму для поддержки разработчиков:",
        reply_markup=support_keyboard()
    )


@router.callback_query(F.data.startswith("support_"))
async def support_amount_callback(callback: CallbackQuery, bot: Bot):
    amount = int(callback.data.replace("support_", ""))
    await create_payment(callback.message, callback.from_user.id, amount, bot, "support")
    await callback.answer()


@router.message(F.text == "🗃️ Редактировать БД")
async def edit_db_handler(message: Message, state: FSMContext):
    if message.from_user.id != cfg.admin_id:
        await message.answer("❌ У вас нет доступа к этой функции")
        return

    # Получаем всех пользователей
    users = await db.get_all_users()

    if not users:
        await message.answer("❌ В базе данных нет пользователей")
        return

    # Создаем текстовый файл со списком пользователей
    users_text = "📋 СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ:\n\n"
    for user in users:
        username = user['username'] if user['username'] != 'Без username' else 'Нет username'
        users_text += f"ID: {user['user_id']} | @{username}\n"

    # Создаем файл правильным способом для aiogram 3.21.0
    file_bytes = users_text.encode('utf-8')
    file_document = BufferedInputFile(file_bytes, filename="users_list.txt")

    # Отправляем файл
    await message.answer_document(
        document=file_document,
        caption="📋 **Список всех пользователей**\n\nПришлите ID пользователя для редактирования:",
        parse_mode="Markdown"
    )

    await state.set_state(EditDBStates.waiting_for_user_id)


@router.message(EditDBStates.waiting_for_user_id)
async def edit_user_id_handler(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())

        # Проверяем существует ли пользователь
        user_data = await db.get_user(user_id)

        if not user_data:
            await message.answer("❌ Пользователь с таким ID не найден. Попробуйте еще раз:")
            return

        # Сохраняем ID пользователя
        await state.update_data(edit_user_id=user_id, user_data=user_data)

        await message.answer(
            f"✅ **Найден пользователь:**\n"
            f"👤 @{user_data['username']} (ID: {user_id})\n\n"
            f"💰 **Текущие балансы:**\n"
            f"🍌 Бананы: {user_data['bananas']}\n"
            f"⭐ Звезды: {user_data['stars']}\n"
            f"🎂 Торты: {user_data['cakes']}\n"
            f"⭐ Личные звезды: {user_data['startL']}\n"
            f"🌟 Звезды бота: {user_data['startB']}\n\n"
            f"Какую валюту хотите отредактировать?",
            parse_mode="Markdown",
            reply_markup=edit_currency_keyboard()
        )

        await state.set_state(EditDBStates.waiting_for_currency)

    except ValueError:
        await message.answer("❌ Введите корректный числовой ID пользователя:")


@router.callback_query(F.data.startswith("edit_"), EditDBStates.waiting_for_currency)
async def edit_currency_selected(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.replace("edit_", "")
    data = await state.get_data()
    user_data = data['user_data']

    current_amount = user_data[currency]

    currency_names = {
        'bananas': '🍌 Бананы',
        'stars': '⭐ Звезды',
        'cakes': '🎂 Торты',
        'startL': '⭐ Личные звезды',
        'startB': '🌟 Звезды бота'
    }

    await state.update_data(edit_currency=currency)

    await callback.message.edit_text(
        f"✅ **Выбрана валюта:** {currency_names[currency]}\n"
        f"👤 Пользователь: @{user_data['username']} (ID: {user_data['user_id']})\n\n"
        f"💰 **Текущий баланс:** {current_amount}\n\n"
        f"Введите новое значение (будет установлено точное значение):"
    )

    await state.set_state(EditDBStates.waiting_for_amount)
    await callback.answer()


@router.message(EditDBStates.waiting_for_amount)
async def edit_amount_handler(message: Message, state: FSMContext):
    try:
        new_amount = int(message.text.strip())

        if new_amount < 0:
            await message.answer("❌ Значение не может быть отрицательным. Введите корректное число:")
            return

        data = await state.get_data()
        user_id = data['edit_user_id']
        currency = data['edit_currency']
        user_data = data['user_data']
        old_amount = user_data[currency]

        # Обновляем валюту пользователя
        await db.update_user_currency(user_id, currency, new_amount)

        currency_names = {
            'bananas': '🍌 Бананы',
            'stars': '⭐ Звезды',
            'cakes': '🎂 Торты',
            'startL': '⭐ Личные звезды',
            'startB': '🌟 Звезды бота'
        }

        await message.answer(
            f"✅ **Баланс успешно изменен!**\n\n"
            f"👤 Пользователь: @{user_data['username']} (ID: {user_id})\n"
            f"💰 Валюта: {currency_names[currency]}\n"
            f"📊 Было: {old_amount}\n"
            f"📈 Стало: {new_amount}\n"
            f"🔄 Изменение: {new_amount - old_amount:+d}",
            parse_mode="Markdown"
        )

        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное числовое значение:")


async def create_payment(message: Message, user_id: int, amount: int, bot: Bot, payment_type: str):
    transaction_id = str(uuid.uuid4())

    await db.add_transaction(user_id, amount, transaction_id, payment_type)

    try:
        if payment_type == "deposit":
            title = "Пополнение баланса"
            description = f"Пополнение личного баланса на {amount} звезд"
        else:
            title = "Поддержка бота"
            description = f"Поддержка разработчиков на {amount} звезд"

        invoice_link = await bot.create_invoice_link(
            title=title,
            description=description,
            payload=transaction_id,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{title} {amount} звезд", amount=amount)]
        )

        await message.answer(
            f"💰 **{title}**\n\n"
            f"💫 Сумма: {amount} звезд\n\n"
            f"🔗 Нажмите на ссылку ниже для оплаты:\n"
            f"[Оплатить {amount} звезд]({invoice_link})\n\n"
            f"После успешной оплаты звезды поступят на {"ваш баланс" if payment_type == "deposit" else "поддержку бота"}.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка создания платежа: {str(e)}")


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    transaction_id = pre_checkout_query.invoice_payload
    transaction = await db.get_transaction(transaction_id)

    if transaction and transaction['status'] == 'pending':
        await pre_checkout_query.answer(ok=True)
    else:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Транзакция не найдена или уже обработана"
        )


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    payment = message.successful_payment
    transaction_id = payment.invoice_payload
    amount = payment.total_amount
    user_id = message.from_user.id
    username = message.from_user.username or "Без username"

    transaction = await db.get_transaction(transaction_id)

    if not transaction:
        await message.answer("❌ Ошибка: транзакция не найдена")
        return

    await db.update_transaction_status(transaction_id, 'completed')

    payment_type = transaction['payment_type']

    if payment_type == "deposit":
        await db.add_stars_user(user_id, amount)

        await message.answer(
            f"✅ **Пополнение успешно!**\n\n"
            f"💰 На ваш личный баланс зачислено {amount} звезд\n"
            f"🎉 Теперь вы можете использовать их в боте!",
            parse_mode="Markdown"
        )

        try:
            await bot.send_message(
                cfg.admin_id,
                f"💰 **Пополнение баланса!**\n\n"
                f"👤 Пользователь: @{username} (ID: {user_id})\n"
                f"💰 Сумма: {amount} звезд\n"
                f"🆔 Транзакция: `{transaction_id}`",
                parse_mode="Markdown"
            )
        except:
            pass

    else:
        await db.add_stars_bot(amount)

        await message.answer(
            f"🤝 **Спасибо за поддержку!**\n\n"
            f"💝 Вы поддержали разработчиков на {amount} звезд\n"
            f"🙏 Ваша поддержка очень важна для развития бота!",
            parse_mode="Markdown"
        )

        try:
            await bot.send_message(
                cfg.admin_id,
                f"🤝 **Поддержка бота!**\n\n"
                f"👤 Пользователь: @{username} (ID: {user_id})\n"
                f"💝 Сумма поддержки: {amount} звезд\n"
                f"🆔 Транзакция: `{transaction_id}`",
                parse_mode="Markdown"
            )
        except:
            pass


@router.message(F.text == "🎫 Создать чек")
async def create_check_handler(message: Message, state: FSMContext):
    if message.from_user.id != cfg.admin_id:
        await message.answer("❌ У вас нет доступа к этой функции")
        return

    stats = await db.get_stats()
    await message.answer(
        f"📊 **Статистика бота:**\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"🍌 Всего бананов: {stats['total_bananas']}\n"
        f"⭐ Всего звезд: {stats['total_stars']}\n"
        f"🎂 Всего тортов: {stats['total_cakes']}\n"
        f"⭐ Личных звезд: {stats['total_startL']}\n"
        f"🌟 Звезд бота: {stats['total_startB']}\n"
        f"🎫 Всего чеков: {stats['total_checks']}\n"
        f"🎯 Всего активаций: {stats['total_activations']}\n"
        f"💸 Заявок на вывод: {stats['total_withdrawals']}\n\n"
        f"💰 Выберите валюту для чека:",
        parse_mode="Markdown",
        reply_markup=currency_keyboard()
    )
    await state.set_state(CheckStates.waiting_for_currency)


@router.callback_query(F.data.startswith("currency_"), CheckStates.waiting_for_currency)
async def currency_selected(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.replace("currency_", "")
    await state.update_data(currency=currency)

    currency_names = {
        'bananas': '🍌 Бананы',
        'stars': '⭐ Звезды',
        'cakes': '🎂 Торты'
    }

    await callback.message.edit_text(
        f"✅ Выбрана валюта: {currency_names[currency]}\n\n"
        f"Введите количество активаций чека:"
    )
    await state.set_state(CheckStates.waiting_for_activations)
    await callback.answer()


@router.message(CheckStates.waiting_for_activations)
async def activations_handler(message: Message, state: FSMContext):
    try:
        activations = int(message.text)
        if activations <= 0:
            await message.answer("❌ Количество активаций должно быть больше 0")
            return

        await state.update_data(max_activations=activations)
        await message.answer("💰 Введите количество валюты:")
        await state.set_state(CheckStates.waiting_for_amount)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(CheckStates.waiting_for_amount)
async def amount_handler(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("❌ Количество валюты должно быть больше 0")
            return

        await state.update_data(amount=amount)
        await message.answer("🏷️ Введите код для чека (без пробелов):")
        await state.set_state(CheckStates.waiting_for_code)
    except ValueError:
        await message.answer("❌ Введите корректное число")


@router.message(CheckStates.waiting_for_code)
async def code_handler(message: Message, state: FSMContext, bot: Bot):
    check_code = message.text.strip().replace(" ", "")

    if len(check_code) < 3:
        await message.answer("❌ Код должен содержать минимум 3 символа")
        return

    existing_check = await db.get_check(check_code)
    if existing_check:
        await message.answer("❌ Чек с таким кодом уже существует")
        return

    data = await state.get_data()

    await db.create_check(
        code=check_code,
        amount=data['amount'],
        currency=data['currency'],
        max_activations=data['max_activations'],
        creator_id=message.from_user.id
    )

    currency_names = {
        'bananas': '🍌 Бананы',
        'stars': '⭐ Звезды',
        'cakes': '🎂 Торты'
    }

    bot_info = await bot.get_me()
    check_link = f"https://t.me/{bot_info.username}?start={check_code}"

    await message.answer(
        f"✅ **Ваш чек готов!**\n\n"
        f"🎫 Код: `{check_code}`\n"
        f"💰 Награда: {data['amount']} {currency_names[data['currency']]}\n"
        f"🎯 Активаций: {data['max_activations']}\n\n"
        f"🔗 **Ссылка на чек:**\n"
        f"`{check_link}`",
        parse_mode="Markdown"
    )

    await state.clear()


@router.callback_query(F.data.startswith("activate_"))
async def activate_check_callback(callback: CallbackQuery, bot: Bot):
    check_code = callback.data.replace("activate_", "")
    user_id = callback.from_user.id
    username = callback.from_user.username or "Без username"

    check_data = await db.get_check(check_code)

    if not check_data or not check_data['is_active']:
        await callback.answer("❌ Чек недействителен", show_alert=True)
        return

    if await db.check_user_activated(check_code, user_id):
        await callback.answer("❌ Вы уже активировали этот чек", show_alert=True)
        return

    if check_data['activations'] >= check_data['max_activations']:
        await callback.answer("❌ Лимит активаций исчерпан", show_alert=True)
        return

    await db.activate_check(check_code, user_id)
    await db.add_currency(user_id, check_data['currency'], check_data['amount'])

    currency_emoji = {
        'bananas': '🍌',
        'stars': '⭐',
        'cakes': '🎂'
    }

    currency_name = {
        'bananas': 'бананов',
        'stars': 'звезд',
        'cakes': 'тортов'
    }

    await callback.message.edit_text(
        f"🎉 **Поздравляем!**\n\n"
        f"Вы получили {check_data['amount']} {currency_emoji[check_data['currency']]} {currency_name[check_data['currency']]}!\n"
        f"Награда добавлена в ваш профиль.",
        parse_mode="Markdown"
    )

    updated_check = await db.get_check(check_code)

    try:
        await bot.send_message(
            cfg.admin_id,
            f"🎫 **Чек активирован!**\n\n"
            f"👤 Пользователь: @{username} (ID: {user_id})\n"
            f"🎫 Код чека: `{check_code}`\n"
            f"💰 Награда: {check_data['amount']} {currency_emoji[check_data['currency']]}\n"
            f"🎯 Активаций: {updated_check['activations']}/{updated_check['max_activations']}",
            parse_mode="Markdown"
        )
    except:
        pass

    if updated_check['activations'] >= updated_check['max_activations']:
        await db.deactivate_check(check_code)
        try:
            await bot.send_message(
                cfg.admin_id,
                f"🔚 **Чек использован!**\n\n"
                f"Чек `{check_code}` достиг лимита активаций и деактивирован.",
                parse_mode="Markdown"
            )
        except:
            pass

    await callback.answer()