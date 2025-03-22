from django.core.management.base import BaseCommand
from supplies.NPViews import complete_all_orders_with_np_status_code_1

class Command(BaseCommand):
    help = 'Runs the evening task for processing Nova Poshta orders'

    def handle(self, *args, **options):
        self.stdout.write('Starting evening task...')
        complete_all_orders_with_np_status_code_1()
        self.stdout.write(self.style.SUCCESS('Evening task completed successfully')) 