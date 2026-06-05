from django.core.management.base import BaseCommand
from supplies.views import teams_reminders_task

class Command(BaseCommand):
    help = 'Sends push reminders for orders and preorders that need attention'

    def handle(self, *args, **options):
        self.stdout.write('Starting push reminders task...')
        teams_reminders_task()
        self.stdout.write(self.style.SUCCESS('Push reminders task completed successfully')) 
        