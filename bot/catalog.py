import json
from dataclasses import dataclass
from pathlib import Path

MENU_PATH = Path(__file__).resolve().parent.parent / "menu.json"


@dataclass(frozen=True)
class Size:
    name: str
    price: int


@dataclass(frozen=True)
class Item:
    id: str
    title: str
    description: str
    sizes: list[Size]

    @property
    def min_price(self) -> int:
        return min(size.price for size in self.sizes)


@dataclass(frozen=True)
class Category:
    id: str
    title: str
    items: list[Item]


class Catalog:
    """Меню кофейни из menu.json. Чтобы поменять цены — правьте файл и перезапустите бота."""

    def __init__(self, path: Path = MENU_PATH):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.shop: dict[str, str] = data["shop"]
        self.faq: list[str] = data["faq"]
        self.categories = [
            Category(
                id=cat["id"],
                title=cat["title"],
                items=[
                    Item(
                        id=item["id"],
                        title=item["title"],
                        description=item.get("description", ""),
                        sizes=[Size(**size) for size in item["sizes"]],
                    )
                    for item in cat["items"]
                ],
            )
            for cat in data["categories"]
        ]
        self._categories = {cat.id: cat for cat in self.categories}
        self._items = {item.id: item for cat in self.categories for item in cat.items}

    def category(self, category_id: str) -> Category | None:
        return self._categories.get(category_id)

    def item(self, item_id: str) -> Item | None:
        return self._items.get(item_id)

    def as_text(self) -> str:
        """Всё меню и инфо одним текстом — для подсказки нейросети."""
        lines = [
            f"Название: {self.shop['name']}",
            f"Адрес: {self.shop['address']}",
            f"Часы работы: {self.shop['hours']}",
            f"Телефон: {self.shop['phone']}",
            "",
            "Меню:",
        ]
        for cat in self.categories:
            lines.append(cat.title)
            for item in cat.items:
                sizes = ", ".join(f"{s.name} — {s.price} ₽" for s in item.sizes)
                lines.append(f"- {item.title} ({sizes}). {item.description}")
        lines += ["", "Дополнительно:"]
        lines += [f"- {fact}" for fact in self.faq]
        return "\n".join(lines)
