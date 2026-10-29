"""Корзина хранится в FSM-данных пользователя как список словарей."""

from html import escape

from .catalog import Item, Size

STATUS_TITLES = {
    "new": "🆕 Новый",
    "accepted": "👨‍🍳 Готовится",
    "ready": "✅ Готов",
    "cancelled": "❌ Отменён",
}


def add(cart: list[dict], item: Item, size: Size) -> list[dict]:
    for line in cart:
        if line["item_id"] == item.id and line["size"] == size.name:
            line["qty"] += 1
            return cart
    cart.append({"item_id": item.id, "title": item.title, "size": size.name, "price": size.price, "qty": 1})
    return cart


def total(cart: list[dict]) -> int:
    return sum(line["price"] * line["qty"] for line in cart)


def count(cart: list[dict]) -> int:
    return sum(line["qty"] for line in cart)


def render(cart: list[dict]) -> str:
    lines = [
        f"• {escape(line['title'])}, {escape(line['size'])} × {line['qty']} — {line['price'] * line['qty']} ₽"
        for line in cart
    ]
    lines.append(f"\n<b>Итого: {total(cart)} ₽</b>")
    return "\n".join(lines)


def render_order(order: dict) -> str:
    """Карточка заказа для чата бариста."""
    customer = f"@{escape(order['username'])}" if order["username"] else f"id {order['user_id']}"
    text = (
        f"<b>Заказ №{order['id']}</b> — {STATUS_TITLES[order['status']]}\n"
        f"Клиент: {customer}\n"
        f"Забрать: {escape(order['pickup'])}\n\n"
        f"{render(order['items'])}"
    )
    if order["comment"]:
        text += f"\n\n💬 {escape(order['comment'])}"
    return text
