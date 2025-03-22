from django.core.management.base import BaseCommand
from supplies.NPViews import evening_task

class Command(BaseCommand):
    help = 'Runs the evening task for processing Nova Poshta orders'

    def handle(self, *args, **options):
        self.stdout.write('Starting evening task...')
        evening_task()
        self.stdout.write(self.style.SUCCESS('Evening task completed successfully')) 