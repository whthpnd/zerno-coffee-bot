import re
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import cart
from ..ai import Consultant
from ..catalog import Catalog
from ..config import Config
from ..db import Database
from ..keyboards import (
    BTN_CART,
    BTN_CONTACTS,
    BTN_MENU,
    CartCB,
    CheckoutCB,
    MenuCB,
    added_kb,
    cart_kb,
    categories_kb,
    comment_kb,
    confirm_kb,
    items_kb,
    main_kb,
    order_admin_kb,
    pickup_kb,
    sizes_kb,
)

router = Router()

TIME_RE = re.compile(r"^([01]?\d|2[0-3])[:.]([0-5]\d)$")


class Checkout(StatesGroup):
    pickup = State()
    comment = State()
    confirm = State()


async def get_cart(state: FSMContext) -> list[dict]:
    return (await state.get_data()).get("cart", [])


# --- Старт и контакты ---------------------------------------------------------


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, catalog: Catalog, ai: Consultant):
    await state.set_state(None)
    text = (
        f"Привет! Это бот {escape(catalog.shop['name'])} ☕\n\n"
        "Закажите напиток заранее — придёте, а он уже готов."
    )
    if ai.enabled:
        text += "\n\nА ещё можно просто спросить: «есть овсяное молоко?», «что взять не очень крепкое?»"
    await message.answer(text, reply_markup=main_kb())


@router.message(F.text == BTN_CONTACTS)
async def contacts(message: Message, catalog: Catalog):
    shop = catalog.shop
    await message.answer(
        f"<b>{escape(shop['name'])}</b>\n"
        f"📍 {escape(shop['address'])}\n"
        f"🕐 {escape(shop['hours'])}\n"
        f"📞 {escape(shop['phone'])}"
    )


# --- Меню ---------------------------------------------------------------------


@router.message(F.text == BTN_MENU)
async def menu(message: Message, catalog: Catalog):
    await message.answer("Что будете?", reply_markup=categories_kb(catalog))


@router.callback_query(MenuCB.filter(F.action == "cats"))
async def menu_categories(callback: CallbackQuery, catalog: Catalog):
    await callback.message.edit_text("Что будете?", reply_markup=categories_kb(catalog))
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "cat"))
async def menu_category(callback: CallbackQuery, callback_data: MenuCB, catalog: Catalog):
    category = catalog.category(callback_data.cat)
    if category is None:
        await callback.answer("Раздел не найден")
        return
    await callback.message.edit_text(f"<b>{category.title}</b>", reply_markup=items_kb(category))
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "item"))
async def menu_item(callback: CallbackQuery, callback_data: MenuCB, catalog: Catalog):
    item = catalog.item(callback_data.item)
    if item is None:
        await callback.answer("Позиция не найдена")
        return
    text = f"<b>{escape(item.title)}</b>\n{escape(item.description)}\n\nВыберите объём:"
    await callback.message.edit_text(text, reply_markup=sizes_kb(callback_data.cat, item))
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "add"))
async def menu_add(callback: CallbackQuery, callback_data: MenuCB, state: FSMContext, catalog: Catalog):
    item = catalog.item(callback_data.item)
    if item is None or not 0 <= callback_data.size < len(item.sizes):
        await callback.answer("Позиция не найдена")
        return
    size = item.sizes[callback_data.size]
    items = cart.add(await get_cart(state), item, size)
    await state.update_data(cart=items)

    await callback.message.edit_text(
        f"Добавлено: {escape(item.title)}, {escape(size.name)} 👌\n"
        f"В корзине {cart.count(items)} шт. на {cart.total(items)} ₽",
        reply_markup=added_kb(),
    )
    await callback.answer("Добавлено")


# --- Корзина ------------------------------------------------------------------


@router.message(F.text == BTN_CART)
async def cart_message(message: Message, state: FSMContext, catalog: Catalog):
    items = await get_cart(state)
    if not items:
        await message.answer("Корзина пуста. Загляните в меню 👇", reply_markup=categories_kb(catalog))
        return
    await message.answer(f"<b>Ваш заказ:</b>\n\n{cart.render(items)}", reply_markup=cart_kb())


@router.callback_query(CartCB.filter(F.action == "show"))
async def cart_show(callback: CallbackQuery, state: FSMContext, catalog: Catalog):
    items = await get_cart(state)
    if not items:
        await callback.message.edit_text("Корзина пуста. Загляните в меню 👇", reply_markup=categories_kb(catalog))
    else:
        await callback.message.edit_text(f"<b>Ваш заказ:</b>\n\n{cart.render(items)}", reply_markup=cart_kb())
    await callback.answer()


@router.callback_query(CartCB.filter(F.action == "clear"))
async def cart_clear(callback: CallbackQuery, state: FSMContext, catalog: Catalog):
    await state.update_data(cart=[])
    await callback.message.edit_text("Корзина очищена.", reply_markup=categories_kb(catalog))
    await callback.answer()


# --- Оформление ---------------------------------------------------------------


@router.callback_query(CartCB.filter(F.action == "checkout"))
async def checkout_start(callback: CallbackQuery, state: FSMContext):
    if not await get_cart(state):
        await callback.answer("Корзина пуста", show_alert=True)
        return
    await state.set_state(Checkout.pickup)
    await callback.message.edit_text(
        "Когда заберёте? Выберите вариант или напишите время, например <b>14:30</b>",
        reply_markup=pickup_kb(),
    )
    await callback.answer()


async def ask_comment(message: Message, state: FSMContext, pickup: str):
    await state.update_data(pickup=pickup)
    await state.set_state(Checkout.comment)
    await message.answer(
        "Есть пожелания? Например: «на овсяном», «без сахара», «покрепче».",
        reply_markup=comment_kb(),
    )


@router.callback_query(Checkout.pickup, CheckoutCB.filter(F.action == "pickup"))
async def checkout_pickup_button(callback: CallbackQuery, callback_data: CheckoutCB, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await ask_comment(callback.message, state, f"через {callback_data.minutes} мин")
    await callback.answer()


@router.message(Checkout.pickup, F.text)
async def checkout_pickup_text(message: Message, state: FSMContext):
    match = TIME_RE.match(message.text.strip())
    if not match:
        await message.answer("Не понял время 🤔 Напишите в формате ЧЧ:ММ, например 14:30", reply_markup=pickup_kb())
        return
    await ask_comment(message, state, f"к {int(match[1]):02d}:{match[2]}")


async def ask_confirm(message: Message, state: FSMContext, comment: str | None):
    await state.update_data(comment=comment)
    await state.set_state(Checkout.confirm)
    data = await state.get_data()
    text = f"<b>Проверьте заказ:</b>\n\n{cart.render(data['cart'])}\n\n🕐 Заберу {escape(data['pickup'])}"
    if comment:
        text += f"\n💬 {escape(comment)}"
    text += "\n\nОплата при получении."
    await message.answer(text, reply_markup=confirm_kb())


@router.callback_query(Checkout.comment, CheckoutCB.filter(F.action == "skip_comment"))
async def checkout_skip_comment(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await ask_confirm(callback.message, state, None)
    await callback.answer()


@router.message(Checkout.comment, F.text)
async def checkout_comment(message: Message, state: FSMContext):
    await ask_confirm(message, state, message.text.strip()[:300])


@router.callback_query(Checkout.confirm, CheckoutCB.filter(F.action == "confirm"))
async def checkout_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, db: Database, config: Config):
    data = await state.get_data()
    order_id = await db.create_order(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        items=data["cart"],
        total=cart.total(data["cart"]),
        pickup=data["pickup"],
        comment=data.get("comment"),
    )
    await state.set_state(None)
    await state.update_data(cart=[], pickup=None, comment=None)

    order = await db.get_order(order_id)
    await bot.send_message(config.admin_chat_id, cart.render_order(order), reply_markup=order_admin_kb(order_id, "new"))

    await callback.message.edit_text(
        f"🎉 Заказ №{order_id} отправлен бариста!\nНапишем, когда начнём готовить и когда будет готово."
    )
    await callback.answer()


@router.callback_query(CheckoutCB.filter(F.action == "cancel"))
async def checkout_cancel(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await callback.message.edit_text("Оформление отменено. Корзина сохранена — вернуться можно через «🛒 Корзина».")
    await callback.answer()


@router.callback_query(CheckoutCB.filter())
async def checkout_stale(callback: CallbackQuery):
    # Кнопка от старого сообщения, когда оформление уже прошло другой шаг
    await callback.answer("Эта кнопка уже неактуальна")


# --- Свободный текст → ИИ-консультант (должен быть последним) -----------------


@router.message(StateFilter(None), F.text)
async def free_text(message: Message, bot: Bot, ai: Consultant, catalog: Catalog):
    if not ai.enabled:
        await message.answer(
            f"Я пока понимаю только кнопки 🙂 Вопросы можно задать по телефону {escape(catalog.shop['phone'])}",
            reply_markup=main_kb(),
        )
        return
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    reply = await ai.answer(message.text[:1000])
    await message.answer(escape(reply), reply_markup=main_kb())
