from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .catalog import Catalog, Category, Item

BTN_MENU = "☕ Меню"
BTN_CART = "🛒 Корзина"
BTN_CONTACTS = "📍 Контакты"

PICKUP_OPTIONS = (10, 20, 30)


class MenuCB(CallbackData, prefix="m"):
    action: str  # cats | cat | item | add
    cat: str = ""
    item: str = ""
    size: int = -1


class CartCB(CallbackData, prefix="c"):
    action: str  # show | clear | checkout


class CheckoutCB(CallbackData, prefix="k"):
    action: str  # pickup | skip_comment | confirm | cancel
    minutes: int = 0


class OrderCB(CallbackData, prefix="o"):
    action: str  # accepted | ready | cancelled
    order_id: int


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_MENU), KeyboardButton(text=BTN_CART)], [KeyboardButton(text=BTN_CONTACTS)]],
        resize_keyboard=True,
        input_field_placeholder="Или задайте вопрос…",
    )


def categories_kb(catalog: Catalog) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for cat in catalog.categories:
        kb.button(text=cat.title, callback_data=MenuCB(action="cat", cat=cat.id))
    kb.button(text=BTN_CART, callback_data=CartCB(action="show"))
    kb.adjust(1)
    return kb.as_markup()


def items_kb(category: Category) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in category.items:
        prefix = "от " if len(item.sizes) > 1 else ""
        kb.button(
            text=f"{item.title} — {prefix}{item.min_price} ₽",
            callback_data=MenuCB(action="item", cat=category.id, item=item.id),
        )
    kb.button(text="← Назад", callback_data=MenuCB(action="cats"))
    kb.adjust(1)
    return kb.as_markup()


def sizes_kb(category_id: str, item: Item) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for index, size in enumerate(item.sizes):
        kb.button(
            text=f"➕ {size.name} — {size.price} ₽",
            callback_data=MenuCB(action="add", cat=category_id, item=item.id, size=index),
        )
    kb.button(text="← Назад", callback_data=MenuCB(action="cat", cat=category_id))
    kb.adjust(1)
    return kb.as_markup()


def added_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить ещё", callback_data=MenuCB(action="cats"))
    kb.button(text=BTN_CART, callback_data=CartCB(action="show"))
    return kb.as_markup()


def cart_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Оформить предзаказ", callback_data=CartCB(action="checkout"))
    kb.button(text="Добавить ещё", callback_data=MenuCB(action="cats"))
    kb.button(text="🗑 Очистить", callback_data=CartCB(action="clear"))
    kb.adjust(1, 2)
    return kb.as_markup()


def pickup_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for minutes in PICKUP_OPTIONS:
        kb.button(text=f"Через {minutes} мин", callback_data=CheckoutCB(action="pickup", minutes=minutes))
    kb.button(text="Отмена", callback_data=CheckoutCB(action="cancel"))
    kb.adjust(len(PICKUP_OPTIONS), 1)
    return kb.as_markup()


def comment_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Без комментария", callback_data=CheckoutCB(action="skip_comment"))
    return kb.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=CheckoutCB(action="confirm"))
    kb.button(text="Отмена", callback_data=CheckoutCB(action="cancel"))
    return kb.as_markup()


def order_admin_kb(order_id: int, status: str) -> InlineKeyboardMarkup | None:
    if status not in ("new", "accepted"):
        return None
    kb = InlineKeyboardBuilder()
    if status == "new":
        kb.button(text="👨‍🍳 Принять", callback_data=OrderCB(action="accepted", order_id=order_id))
    kb.button(text="✅ Готов", callback_data=OrderCB(action="ready", order_id=order_id))
    kb.button(text="❌ Отменить", callback_data=OrderCB(action="cancelled", order_id=order_id))
    if status == "new":
        kb.adjust(1, 2)
    else:
        kb.adjust(2)
    return kb.as_markup()
