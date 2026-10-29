from aiogram import Router

from . import admin, user


def setup_routers() -> Router:
    root = Router()
    # admin первым: у user в конце стоит обработчик любого текста (ИИ)
    root.include_routers(admin.router, user.router)
    return root
