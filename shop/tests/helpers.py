from django.test import TestCase
from django.urls import reverse

from shop.models import Category, Product


class ShopTestCase(TestCase):
    """Общие тестовые данные: две категории и три товара."""

    @classmethod
    def setUpTestData(cls):
        cls.sofas = Category.objects.create(name='Диваны')
        cls.chairs = Category.objects.create(name='Кресла')
        cls.sofa = Product.objects.create(
            name='Диван Лондон', price=50000, category=cls.sofas,
            description='Трёхместный диван')
        cls.sofa2 = Product.objects.create(
            name='Диван Милан', price=20000, category=cls.sofas)
        cls.chair = Product.objects.create(
            name='Кресло Уют', price=10000, category=cls.chairs)

    def add_to_cart(self, *products):
        """Кладёт товары в корзину через настоящий HTTP-запрос (с сессией)."""
        for product in products:
            self.client.post(reverse('cart_add', args=[product.pk]))
