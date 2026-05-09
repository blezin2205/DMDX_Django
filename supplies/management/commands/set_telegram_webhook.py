import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from telegram import Bot, Update


class Command(BaseCommand):
    help = "Set Telegram webhook URL for Django-integrated bot"

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            required=True,
            help="Full HTTPS webhook URL, e.g. https://example.com/telegram/webhook/",
        )
        parser.add_argument(
            "--drop-pending-updates",
            action="store_true",
            help="Drop queued updates in Telegram before switching to webhook mode.",
        )

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN is not configured")

        webhook_url = options["url"]
        if not webhook_url.startswith("https://"):
            raise CommandError("Webhook URL must start with https://")

        secret_token = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or None
        drop_pending = bool(options["drop_pending_updates"])

        async def _set_webhook():
            bot = Bot(token=token)
            await bot.set_webhook(
                url=webhook_url,
                secret_token=secret_token,
                drop_pending_updates=drop_pending,
                allowed_updates=Update.ALL_TYPES,
            )

        asyncio.run(_set_webhook())
        self.stdout.write(self.style.SUCCESS(f"Webhook configured: {webhook_url}"))
