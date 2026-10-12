from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase

from shop.apps import ShopConfig


class AppConfigTestCase(SimpleTestCase):
    def test_app_config(self):
        self.assertEqual(ShopConfig.name, 'shop')
        self.assertEqual(ShopConfig.default_auto_field, 'django.db.models.BigAutoField')

    def test_app_is_installed(self):
        self.assertEqual(apps.get_app_config('shop').name, 'shop')

    def test_all_models_are_registered(self):
        names = {model.__name__ for model in apps.get_app_config('shop').get_models()}
        self.assertEqual(names, {'Category', 'Product', 'Purchase', 'Cart', 'CartItem'})


class SettingsTestCase(SimpleTestCase):
    def test_database_is_postgresql(self):
        self.assertIn('postgresql', settings.DATABASES['default']['ENGINE'])

    def test_shop_app_is_installed(self):
        self.assertIn('shop.apps.ShopConfig', settings.INSTALLED_APPS)

    def test_sessions_are_enabled(self):
        # корзина хранится по идентификатору из сессии
        self.assertIn('django.contrib.sessions', settings.INSTALLED_APPS)
        self.assertIn('django.contrib.sessions.middleware.SessionMiddleware', settings.MIDDLEWARE)

    def test_messages_are_enabled(self):
        self.assertIn('django.contrib.messages', settings.INSTALLED_APPS)
        self.assertIn('django.contrib.messages.middleware.MessageMiddleware', settings.MIDDLEWARE)

    def test_csrf_protection_is_enabled(self):
        self.assertIn('django.middleware.csrf.CsrfViewMiddleware', settings.MIDDLEWARE)

    def test_cart_context_processor_is_registered(self):
        processors = settings.TEMPLATES[0]['OPTIONS']['context_processors']
        self.assertIn('shop.context_processors.cart', processors)
        self.assertIn('django.template.context_processors.request', processors)
