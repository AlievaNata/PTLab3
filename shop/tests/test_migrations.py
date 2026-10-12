from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class MigrationsTestCase(TestCase):
    def test_models_and_migrations_are_in_sync(self):
        """Если упадёт - выполните `python manage.py makemigrations`."""
        try:
            call_command('makemigrations', '--check', '--dry-run',
                         verbosity=0, stdout=StringIO(), stderr=StringIO())
        except SystemExit:
            self.fail('Модели изменены, а миграции для них не созданы.')
