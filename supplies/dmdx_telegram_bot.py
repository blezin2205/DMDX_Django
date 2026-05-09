import asyncio
import logging
from datetime import date

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Q
from django.utils import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .models import (
    GeneralSupply,
    TelegramAuthenticatedSession,
    TelegramPendingLogin,
)


logger = logging.getLogger(__name__)

_application = None
_application_lock = asyncio.Lock()


@sync_to_async
def _is_user_authenticated(telegram_user_id: int) -> bool:
    return TelegramAuthenticatedSession.objects.filter(telegram_user_id=telegram_user_id).exists()


@sync_to_async
def _start_login_flow(telegram_user_id: int) -> None:
    TelegramPendingLogin.objects.update_or_create(
        telegram_user_id=telegram_user_id,
        defaults={"requested_at": timezone.now()},
    )


@sync_to_async
def _cancel_login_flow(telegram_user_id: int) -> None:
    TelegramPendingLogin.objects.filter(telegram_user_id=telegram_user_id).delete()


@sync_to_async
def _is_waiting_for_credentials(telegram_user_id: int) -> bool:
    return TelegramPendingLogin.objects.filter(telegram_user_id=telegram_user_id).exists()


@sync_to_async
def _authenticate_and_save_session(
    telegram_user,
    username: str,
    password: str,
) -> tuple[bool, str]:
    user = authenticate(username=username, password=password)
    if not user or not user.is_active:
        return False, "❌ Невірний логін або пароль"

    TelegramAuthenticatedSession.objects.update_or_create(
        telegram_user_id=telegram_user.id,
        defaults={
            "user": user,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "last_activity": timezone.now(),
        },
    )
    TelegramPendingLogin.objects.filter(telegram_user_id=telegram_user.id).delete()
    display_name = f"{user.first_name} {user.last_name}".strip() or user.username
    return True, display_name


@sync_to_async
def _logout_user(telegram_user_id: int) -> bool:
    deleted_count, _ = TelegramAuthenticatedSession.objects.filter(
        telegram_user_id=telegram_user_id
    ).delete()
    TelegramPendingLogin.objects.filter(telegram_user_id=telegram_user_id).delete()
    return deleted_count > 0


@sync_to_async
def _touch_last_activity(telegram_user_id: int) -> None:
    TelegramAuthenticatedSession.objects.filter(telegram_user_id=telegram_user_id).update(
        last_activity=timezone.now()
    )


@sync_to_async
def _search_supplies(search_text: str) -> list[dict]:
    generals = (
        GeneralSupply.objects.select_related("category")
        .prefetch_related("general")
        .filter(
            Q(name__icontains=search_text)
            | Q(ref__icontains=search_text)
            | Q(SMN_code__icontains=search_text)
        )
        .distinct()
        .order_by("name")
    )
    payload = []
    for general in generals:
        lots_payload = []
        for lot in general.general.all().order_by("expiredDate", "id"):
            lots_payload.append(
                {
                    "lot": lot.supplyLot or "",
                    "expired": lot.expiredDate,
                    "count": int(lot.count or 0),
                    "on_hold": int(lot.countOnHold or 0),
                }
            )
        payload.append(
            {
                "name": general.name or "",
                "category_name": general.category.name if general.category else "",
                "ref": general.ref or "",
                "smn_code": general.SMN_code or "",
                "package_and_tests": general.package_and_tests or "",
                "lots": lots_payload,
            }
        )
    return payload


def _render_supply_message(supply_item: dict) -> str:
    name = f'<i>📦 Назва:</i> <b>{supply_item["name"]}</b>'
    category = f'<i>📁 Категорія:</i> <b>{supply_item["category_name"] or "-"}</b>'
    message_parts = [name, category]

    if supply_item["ref"]:
        message_parts.append(f'<i>🏷️ REF:</i> <b>{supply_item["ref"]}</b>')
    if supply_item["smn_code"]:
        message_parts.append(f'<i>🔢 SMN:</i> <b>{supply_item["smn_code"]}</b>')
    if supply_item["package_and_tests"]:
        message_parts.append(
            f'<i>📋 Пакування/Тести:</i> <b>{supply_item["package_and_tests"]}</b>'
        )

    for lot in supply_item["lots"]:
        exp_date = lot["expired"]
        exp_status = "🟢" if exp_date and exp_date >= date.today() else "🔴"
        exp_date_str = exp_date.strftime("%d.%m.%Y") if exp_date else "-"

        message_parts.append("---------------------------------------")
        if lot["lot"]:
            message_parts.append(f'<i>• 📦 LOT:</i> <b>{lot["lot"]}</b>')
        message_parts.append(f'<i>• термін:</i> <b>{exp_date_str}</b> {exp_status}')
        message_parts.append(f'<i>• 📊 Кількість:</i> <b>{lot["count"]}</b>')
        if lot["on_hold"] > 0:
            available_count = lot["count"] - lot["on_hold"]
            message_parts.append(f'<i>• 🔒 Заброньовано:</i> <b>{lot["on_hold"]}</b>')
            message_parts.append(f'<i>• ✅ Доступно:</i> <b>{available_count}</b>')
        message_parts.append("---------------------------------------")

    return "\n".join(message_parts)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    greeting = f"Привіт, <b>{first_name} {last_name}</b>!".strip()
    await update.message.reply_html(
        f"{greeting}\nДля пошуку введи назву, REF або SMN code\nДля входу використовуйте команду /login"
    )


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id
    if await _is_user_authenticated(telegram_user_id):
        await update.message.reply_html("✅ Ви вже увійшли в систему")
        return

    keyboard = [[InlineKeyboardButton("Відмінити", callback_data="cancel_login")]]
    await _start_login_flow(telegram_user_id)
    await update.message.reply_html(
        "🔐 Введіть логін та пароль у форматі:\n<code>login:password</code>",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id
    if await _logout_user(telegram_user_id):
        await update.message.reply_html("👋 Ви вийшли з системи")
        return
    await update.message.reply_html("ℹ️ Ви не увійшли в систему")


async def handle_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data != "cancel_login":
        return
    await _cancel_login_flow(query.from_user.id)
    await query.message.edit_text("❌ Вхід скасовано")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if await _is_user_authenticated(telegram_user_id):
        await _touch_last_activity(telegram_user_id)
        await handle_search(update, text)
        return

    if not await _is_waiting_for_credentials(telegram_user_id):
        await update.message.reply_html(
            "⚠️ Будь ласка, спочатку увійдіть в систему командою /login"
        )
        return

    if ":" not in text:
        await update.message.reply_html(
            "❌ Невірний формат. Використовуйте:\n<code>login:password</code>"
        )
        return

    username, password = text.split(":", 1)
    username = username.strip()
    password = password.strip()
    if not username or not password:
        await update.message.reply_html(
            "❌ Невірний формат. Використовуйте:\n<code>login:password</code>"
        )
        return

    success, result = await _authenticate_and_save_session(update.effective_user, username, password)
    if success:
        await update.message.reply_html(
            f"✅ Вітаємо, {result}!\nТепер ви можете використовувати пошук."
        )
        return
    await update.message.reply_html(result)


async def handle_search(update: Update, search_text: str):
    results = await _search_supplies(search_text)
    if not results:
        await update.message.reply_html("<strong>Нічого не знайдено</strong>")
        return

    for supply_item in results:
        await update.message.reply_html(_render_supply_message(supply_item))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


async def get_telegram_application() -> Application:
    global _application
    if _application is not None:
        return _application

    async with _application_lock:
        if _application is not None:
            return _application

        token = settings.TELEGRAM_BOT_TOKEN
        app = Application.builder().token(token).updater(None).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("login", login))
        app.add_handler(CommandHandler("logout", logout))
        app.add_handler(CallbackQueryHandler(handle_login_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        app.add_error_handler(error_handler)

        await app.initialize()
        _application = app
        return _application


async def process_telegram_webhook(payload: dict) -> None:
    app = await get_telegram_application()
    update = Update.de_json(payload, app.bot)
    await app.process_update(update)