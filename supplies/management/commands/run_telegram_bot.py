from django.core.management.base import BaseCommand
from django.conf import settings
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from supplies.models import Supply, Place, Order, CustomUser, GeneralSupply
from django.db import Error as DBError
import traceback
from asgiref.sync import sync_to_async
import os
from django.contrib.auth import authenticate
from django.db.models import Q
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the Telegram bot'

    def __init__(self):
        super().__init__()
        self.authenticated_users = {}  # Store authenticated users by chat_id
        self.user_states = {}  # Store user states for conversation flow

    @sync_to_async
    def authenticate_user(self, username, password):
        """Authenticate user with Django's authentication system."""
        user = authenticate(username=username, password=password)
        return user is not None, user

    @sync_to_async
    def search_supplies(self, query):
        """Search supplies by name, ref, or SMN_code."""
        try:
            general_supplies = GeneralSupply.objects.filter(
                Q(name__icontains=query) |
                Q(ref__icontains=query) |
                Q(SMN_code__icontains=query)
            ).distinct()
            return list(general_supplies)
        except Exception as e:
            logger.error(f"Error in search_supplies: {str(e)}")
            return []

    @sync_to_async
    def get_supplies_for_general(self, general_supply):
        """Get all supplies for a general supply."""
        try:
            supplies = Supply.objects.filter(general_supply=general_supply)
            return list(supplies)
        except Exception as e:
            logger.error(f"Error in get_supplies_for_general: {str(e)}")
            return []

    @sync_to_async
    def get_supplies(self):
        """Get supplies from database synchronously."""
        supplies = Supply.objects.all()
        count = supplies.count()
        return list(supplies[:10]), count

    @sync_to_async
    def get_places(self):
        """Get places from database synchronously."""
        places = Place.objects.all()
        count = places.count()
        return list(places[:10]), count

    @sync_to_async
    def get_orders(self):
        """Get orders from database synchronously."""
        orders = Order.objects.all()
        count = orders.count()
        return list(orders[:10]), count

    @sync_to_async
    def get_general_supply_info(self, general_supply):
        """Get formatted information about a general supply."""
        try:
            return {
                'name': general_supply.name,
                'ref': general_supply.ref or 'N/A',
                'smn_code': general_supply.SMN_code or 'N/A',
                'package': general_supply.package_and_tests or 'N/A',
                'category': general_supply.category.name if general_supply.category else 'N/A'
            }
        except Exception as e:
            logger.error(f"Error getting general supply info: {str(e)}")
            return None

    @sync_to_async
    def get_supply_info(self, supply):
        """Get formatted information about a supply."""
        try:
            current_date = datetime.now().date()
            is_expired = supply.expiredDate and supply.expiredDate < current_date
            
            expiry_status = "❌ Протерміновано" if is_expired else "✅ Придатний"
            expiry_date = supply.expiredDate.strftime('%d-%m-%Y') if supply.expiredDate else 'N/A'
            
            return {
                'lot': supply.supplyLot or 'N/A',
                'count': supply.count or 0,
                'count_on_hold': supply.countOnHold or 0,
                'expiry_date': expiry_date,
                'expiry_status': expiry_status,
                'is_expired': is_expired
            }
        except Exception as e:
            logger.error(f"Error getting supply info: {str(e)}")
            return None

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in the bot."""
        logger.error("Exception while handling an update:", exc_info=context.error)
        if update and hasattr(update, 'effective_message'):
            await update.effective_message.reply_text(
                "Sorry, an error occurred while processing your request. Please try again later."
            )

    def get_main_menu_keyboard(self):
        """Create the main menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("🔍 Пошук товарів", callback_data='search')],
            [InlineKeyboardButton("📦 Перегляд товарів", callback_data='supplies')],
            [InlineKeyboardButton("🏢 Перегляд місць", callback_data='places')],
            [InlineKeyboardButton("📋 Перегляд замовлень", callback_data='orders')],
            [InlineKeyboardButton("❓ Допомога", callback_data='help')],
            [InlineKeyboardButton("🔑 Вхід", callback_data='login')]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        welcome_message = (
            "Ласкаво просимо до DMDX Бота! 🤖\n\n"
            "Будь ласка, виберіть дію з меню нижче:"
        )
        await update.message.reply_text(welcome_message, reply_markup=self.get_main_menu_keyboard())

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()

        if query.data == 'help':
            help_message = (
                "Доступні дії:\n\n"
                "🔍 Пошук товарів - Пошук за назвою, референсом або SMN кодом (потребує входу)\n"
                "📦 Перегляд товарів - Показати всі товари (потребує входу)\n"
                "🏢 Перегляд місць - Показати всі місця (потребує входу)\n"
                "📋 Перегляд замовлень - Показати останні замовлення (потребує входу)\n"
                "🔑 Вхід - Увійти для доступу до обмежених функцій"
            )
            await query.message.edit_text(help_message, reply_markup=self.get_main_menu_keyboard())
            return

        if query.data == 'login':
            if self.is_authenticated(query.message.chat_id):
                await query.message.edit_text(
                    "Ви вже увійшли в систему!",
                    reply_markup=self.get_main_menu_keyboard()
                )
                return
            self.user_states[query.message.chat_id] = {'state': 'waiting_username'}
            await query.message.edit_text(
                "Будь ласка, введіть ваш логін:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Скасувати", callback_data='cancel')]])
            )
            return

        if query.data == 'search':
            if not self.is_authenticated(query.message.chat_id):
                await query.message.edit_text(
                    "Будь ласка, спочатку увійдіть для пошуку товарів.",
                    reply_markup=self.get_main_menu_keyboard()
                )
                return
            self.user_states[query.message.chat_id] = {'state': 'waiting_search_query'}
            await query.message.edit_text(
                "Будь ласка, введіть ваш пошуковий запит:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Скасувати", callback_data='cancel')]])
            )
            return

        if query.data == 'supplies':
            if not self.is_authenticated(query.message.chat_id):
                await query.message.edit_text(
                    "Будь ласка, спочатку увійдіть для перегляду товарів.",
                    reply_markup=self.get_main_menu_keyboard()
                )
                return
            await self.show_supplies(query, context)
            return

        if query.data == 'places':
            if not self.is_authenticated(query.message.chat_id):
                await query.message.edit_text(
                    "Будь ласка, спочатку увійдіть для перегляду місць.",
                    reply_markup=self.get_main_menu_keyboard()
                )
                return
            await self.show_places(query, context)
            return

        if query.data == 'orders':
            if not self.is_authenticated(query.message.chat_id):
                await query.message.edit_text(
                    "Будь ласка, спочатку увійдіть для перегляду замовлень.",
                    reply_markup=self.get_main_menu_keyboard()
                )
                return
            await self.show_orders(query, context)
            return

        if query.data == 'cancel':
            self.user_states.pop(query.message.chat_id, None)
            await query.message.edit_text(
                "Дію скасовано. Будь ласка, виберіть опцію:",
                reply_markup=self.get_main_menu_keyboard()
            )
            return

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages based on user state."""
        chat_id = update.message.chat_id
        text = update.message.text
        user_state = self.user_states.get(chat_id)

        if not user_state:
            await update.message.reply_text(
                "Будь ласка, виберіть дію з меню:",
                reply_markup=self.get_main_menu_keyboard()
            )
            return

        if user_state['state'] == 'waiting_username':
            self.user_states[chat_id] = {'state': 'waiting_password', 'username': text}
            await update.message.reply_text(
                "Будь ласка, введіть ваш пароль:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Скасувати", callback_data='cancel')]])
            )
            return

        if user_state['state'] == 'waiting_password':
            username = user_state['username']
            is_authenticated, user = await self.authenticate_user(username, text)
            
            if is_authenticated:
                self.authenticated_users[chat_id] = user
                user_info = (
                    "✅ Успішний вхід!\n\n"
                    f"👤 Інформація про користувача:\n"
                    f"Ім'я: {user.get_full_name() or 'Не встановлено'}\n"
                    f"Логін: {user.username}\n"
                    f"Email: {user.email or 'Не встановлено'}\n"
                    f"Роль: {'Адміністратор' if user.is_superuser else 'Співробітник' if user.is_staff else 'Клієнт'}\n"
                )
                await update.message.reply_text(user_info, reply_markup=self.get_main_menu_keyboard())
            else:
                await update.message.reply_text(
                    "❌ Невірні облікові дані. Будь ласка, спробуйте ще раз.",
                    reply_markup=self.get_main_menu_keyboard()
                )
            
            self.user_states.pop(chat_id)
            return

        if user_state['state'] == 'waiting_search_query':
            if not self.is_authenticated(chat_id):
                await update.message.reply_text(
                    "Будь ласка, спочатку увійдіть для пошуку товарів.",
                    reply_markup=self.get_main_menu_keyboard()
                )
                self.user_states.pop(chat_id)
                return
            context.args = [text]
            await self.search(update, context)
            self.user_states.pop(chat_id)
            return

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        help_message = (
            "Available commands:\n"
            "/login - Login to access data\n"
            "/search - Search supplies by name, ref, or SMN code\n"
            "/supplies - Show all supplies (requires login)\n"
            "/places - Show all places (requires login)\n"
            "/orders - Show recent orders (requires login)\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(help_message)

    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search supplies by name, ref, or SMN code."""
        chat_id = update.message.chat_id
        if not self.is_authenticated(chat_id):
            await update.message.reply_text(
                "Будь ласка, спочатку увійдіть для пошуку товарів.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return

        if not context.args:
            await update.message.reply_text(
                "Будь ласка, введіть пошуковий запит.\n"
                "Використання: /search запит"
            )
            return

        query = ' '.join(context.args)
        try:
            logger.info(f"Searching for supplies with query: {query}")
            general_supplies = await self.search_supplies(query)
            
            if not general_supplies:
                await update.message.reply_text("Не знайдено товарів, що відповідають вашому запиту.")
                return

            for general_supply in general_supplies:
                try:
                    # Get general supply info
                    general_info = await self.get_general_supply_info(general_supply)
                    if not general_info:
                        continue

                    # Create header message with general supply info
                    header = (
                        f"📦 <b>{general_info['name']}</b>\n"
                        f"<i>Референс:</i> {general_info['ref']}\n"
                        f"<i>SMN код:</i> {general_info['smn_code']}\n"
                        f"<i>Упаковка:</i> {general_info['package']}\n"
                        f"<i>Категорія:</i> {general_info['category']}\n"
                        "-------------------\n"
                    )
                    
                    # Get related supplies
                    supplies = await self.get_supplies_for_general(general_supply)
                    
                    if supplies:
                        # Create supplies list message
                        supplies_list = "📋 Доступні товари:\n"
                        for supply in supplies:
                            supply_info = await self.get_supply_info(supply)
                            if supply_info:
                                supplies_list += (
                                    f"<i>Партія:</i> {supply_info['lot']}\n"
                                    f"<i>Кількість:</i> {supply_info['count']}\n"
                                    f"<i>На утриманні:</i> {supply_info['count_on_hold']}\n"
                                    f"<i>Термін придатності:</i> {supply_info['expiry_date']} {supply_info['expiry_status']}\n"
                                    "-------------------\n"
                                )
                        
                        # Send both messages with HTML parsing enabled
                        await update.message.reply_text(header, parse_mode='HTML')
                        await update.message.reply_text(supplies_list, parse_mode='HTML')
                    else:
                        # If no supplies found, just send header with "No supplies available" message
                        await update.message.reply_text(header + "Немає доступних товарів для цього предмету.", parse_mode='HTML')
                    
                    # Add a separator between different general supplies
                    await update.message.reply_text("-------------------")
                except Exception as e:
                    logger.error(f"Error processing general supply {general_supply.id}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            logger.error(traceback.format_exc())
            await update.message.reply_text("Вибачте, не вдалося виконати пошук через помилку.")

    def is_authenticated(self, chat_id):
        """Check if user is authenticated."""
        return chat_id in self.authenticated_users

    async def show_supplies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all supplies from the database."""
        chat_id = update.message.chat_id if hasattr(update, 'message') else update.effective_chat.id
        if not self.is_authenticated(chat_id):
            message = "Будь ласка, спочатку увійдіть для перегляду товарів."
            if hasattr(update, 'message'):
                await update.message.reply_text(message, reply_markup=self.get_main_menu_keyboard())
            else:
                await update.edit_text(message, reply_markup=self.get_main_menu_keyboard())
            return

        try:
            logger.info("Attempting to fetch supplies from database")
            supplies, count = await self.get_supplies()
            logger.info(f"Found {count} supplies in database")
            
            if count == 0:
                message = "Не знайдено товарів у базі даних."
                if hasattr(update, 'message'):
                    await update.message.reply_text(message)
                else:
                    await update.edit_text(message)
                return

            message = "📦 Останні товари:\n\n"
            for supply in supplies:
                message += f"<b>{supply.name}</b>\n"
                message += f"<i>Кількість:</i> {supply.count}\n"
                message += f"<i>Термін придатності:</i> {supply.expiredDate}\n"
                message += "-------------------\n"

            if hasattr(update, 'message'):
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.edit_text(message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in show_supplies: {str(e)}")
            logger.error(traceback.format_exc())
            error_message = "Вибачте, не вдалося отримати товари через помилку."
            if hasattr(update, 'message'):
                await update.message.reply_text(error_message)
            else:
                await update.edit_text(error_message)

    async def show_places(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all places from the database."""
        chat_id = update.message.chat_id if hasattr(update, 'message') else update.effective_chat.id
        if not self.is_authenticated(chat_id):
            message = "Будь ласка, спочатку увійдіть для перегляду місць."
            if hasattr(update, 'message'):
                await update.message.reply_text(message, reply_markup=self.get_main_menu_keyboard())
            else:
                await update.edit_text(message, reply_markup=self.get_main_menu_keyboard())
            return

        try:
            logger.info("Attempting to fetch places from database")
            places, count = await self.get_places()
            logger.info(f"Found {count} places in database")
            
            if count == 0:
                message = "Не знайдено місць у базі даних."
                if hasattr(update, 'message'):
                    await update.message.reply_text(message)
                else:
                    await update.edit_text(message)
                return

            message = "🏢 Останні місця:\n\n"
            for place in places:
                message += f"<b>{place.name}</b>\n"
                message += f"<i>Місто:</i> {place.city}\n"
                message += f"<i>Адреса:</i> {place.address}\n"
                message += "-------------------\n"

            if hasattr(update, 'message'):
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.edit_text(message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in show_places: {str(e)}")
            logger.error(traceback.format_exc())
            error_message = "Вибачте, не вдалося отримати місця через помилку."
            if hasattr(update, 'message'):
                await update.message.reply_text(error_message)
            else:
                await update.edit_text(error_message)

    async def show_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent orders from the database."""
        chat_id = update.message.chat_id if hasattr(update, 'message') else update.effective_chat.id
        if not self.is_authenticated(chat_id):
            message = "Будь ласка, спочатку увійдіть для перегляду замовлень."
            if hasattr(update, 'message'):
                await update.message.reply_text(message, reply_markup=self.get_main_menu_keyboard())
            else:
                await update.edit_text(message, reply_markup=self.get_main_menu_keyboard())
            return

        try:
            logger.info("Attempting to fetch orders from database")
            orders, count = await self.get_orders()
            logger.info(f"Found {count} orders in database")
            
            if count == 0:
                message = "Не знайдено замовлень у базі даних."
                if hasattr(update, 'message'):
                    await update.message.reply_text(message)
                else:
                    await update.edit_text(message)
                return

            message = "📋 Останні замовлення:\n\n"
            for order in orders:
                message += f"<b>Замовлення #{order.id}</b>\n"
                message += f"<i>Місце:</i> {order.place.name}\n"
                message += f"<i>Дата створення:</i> {order.dateCreated}\n"
                message += f"<i>Статус:</i> {'Завершено' if order.isComplete else 'В обробці'}\n"
                message += "-------------------\n"

            if hasattr(update, 'message'):
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.edit_text(message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in show_orders: {str(e)}")
            logger.error(traceback.format_exc())
            error_message = "Вибачте, не вдалося отримати замовлення через помилку."
            if hasattr(update, 'message'):
                await update.message.reply_text(error_message)
            else:
                await update.edit_text(error_message)

    def handle(self, *args, **options):
        """Run the bot."""
        self.stdout.write('Starting bot...')
        
        # Get the bot token from settings
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stdout.write(self.style.ERROR('Please set your TELEGRAM_BOT_TOKEN in Heroku environment variables'))
            return

        try:
            # Create the Application and pass it your bot's token
            application = Application.builder().token(token).build()

            # Add command handlers
            application.add_handler(CommandHandler("start", self.start))
            application.add_handler(CommandHandler("help", self.help_command))
            
            # Add callback query handler for buttons
            application.add_handler(CallbackQueryHandler(self.button_handler))
            
            # Add message handler for text messages
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

            # Add error handler
            application.add_error_handler(self.error_handler)

            # Start the Bot
            self.stdout.write('Bot is running...')
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error starting bot: {e}'))
            self.stdout.write(self.style.ERROR(traceback.format_exc())) 