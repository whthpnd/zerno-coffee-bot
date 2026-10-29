import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery

from .. import cart
from ..catalog import Catalog
from ..config import Config
from ..db import Database
from ..keyboards import OrderCB, order_admin_kb

log = logging.getLogger(__name__)
router = Router()

CUSTOMER_MESSAGES = {
    "accepted": "👨‍🍳 Бариста принял заказ №{id}, уже готовим!",
    "ready": "✅ Заказ №{id} готов! Ждём вас: {address}",
    "cancelled": "😔 Заказ №{id} отменён. Если есть вопросы — позвоните нам: {phone}",
}


@router.callback_query(OrderCB.filter())
async def change_status(
    callback: CallbackQuery, callback_data: OrderCB, bot: Bot, db: Database, catalog: Catalog, config: Config
):
    if callback.message.chat.id != config.admin_chat_id:
        await callback.answer("Нет доступа", show_alert=True)
        return

    order = await db.get_order(callback_data.order_id)
    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order["status"] in ("ready", "cancelled"):
        await callback.answer("Заказ уже закрыт")
        return

    await db.set_status(order["id"], callback_data.action)
    order["status"] = callback_data.action

    await callback.message.edit_text(
        cart.render_order(order), reply_markup=order_admin_kb(order["id"], order["status"])
    )
    await callback.answer(cart.STATUS_TITLES[order["status"]])

    text = CUSTOMER_MESSAGES[order["status"]].format(
        id=order["id"], address=catalog.shop["address"], phone=catalog.shop["phone"]
    )
    try:
        await bot.send_message(order["user_id"], text)
    except TelegramForbiddenError:
        log.info("Клиент %s заблокировал бота", order["user_id"])
