import os
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed the database with tables, triggers, and sample data'

    def handle(self, *args, **options):
        seed_path = os.path.join(os.path.dirname(__file__), '../../../../seed.py')
        seed_path = os.path.abspath(seed_path)
        if not os.path.exists(seed_path):
            self.stderr.write(f'seed.py not found at {seed_path}')
            return
        self.stdout.write('Running seed.py ...')
        sys.path.insert(0, os.path.dirname(seed_path))
        exec(open(seed_path).read())
        self.stdout.write(self.style.SUCCESS('Database seeded successfully.'))
