from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def main_keyboard(is_admin=False):
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="💰 Пополнить")
    )
    builder.row(
        KeyboardButton(text="💸 Вывод"),
        KeyboardButton(text="🤝 Поддержать")
    )

    if is_admin:
        builder.row(
            KeyboardButton(text="🎫 Создать чек"),
            KeyboardButton(text="🗃️ Редактировать БД")
        )

    return builder.as_markup(resize_keyboard=True)


def currency_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🍌 Бананы", callback_data="currency_bananas"))
    builder.row(InlineKeyboardButton(text="⭐ Звезды", callback_data="currency_stars"))
    builder.row(InlineKeyboardButton(text="🎂 Торты", callback_data="currency_cakes"))

    return builder.as_markup()


def edit_currency_keyboard():
    """Инлайн клавиатура для редактирования валют"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🍌 Бананы", callback_data="edit_bananas"))
    builder.row(InlineKeyboardButton(text="⭐ Звезды", callback_data="edit_stars"))
    builder.row(InlineKeyboardButton(text="🎂 Торты", callback_data="edit_cakes"))
    builder.row(InlineKeyboardButton(text="⭐ Личные звезды", callback_data="edit_startL"))
    builder.row(InlineKeyboardButton(text="🌟 Звезды бота", callback_data="edit_startB"))

    return builder.as_markup()


def activate_check_keyboard(check_code):
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🎁 Получить награду", callback_data=f"activate_{check_code}")
    )

    return builder.as_markup()


def support_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="⭐ Поддержать 2000 звезд", callback_data="support_2000")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Поддержать 70000 звезд", callback_data="support_70000")
    )

    return builder.as_markup()