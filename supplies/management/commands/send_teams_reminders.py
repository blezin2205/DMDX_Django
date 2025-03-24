from django.core.management.base import BaseCommand
from supplies.views import teams_reminders_task

class Command(BaseCommand):
    help = 'Sends Teams reminders for orders and preorders that need attention'

    def handle(self, *args, **options):
        self.stdout.write('Starting evening task...')
        teams_reminders_task()
        self.stdout.write(self.style.SUCCESS('Evening task completed successfully')) 
        