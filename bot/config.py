import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_chat_id: int
    anthropic_api_key: str | None
    claude_model: str
    db_path: str


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан — заполните .env (см. .env.example)")

    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if not admin_chat_id:
        raise RuntimeError("ADMIN_CHAT_ID не задан — куда отправлять заказы бариста?")

    return Config(
        bot_token=token,
        admin_chat_id=int(admin_chat_id),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        claude_model=os.getenv("CLAUDE_MODEL", "claude-opus-5-5"),
        db_path=os.getenv("DB_PATH", "data/orders.db"),
    )
