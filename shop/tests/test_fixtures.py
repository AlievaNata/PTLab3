from django.core.management import call_command
from django.test import TestCase

from django.urls import reverse

from shop.models import Cart, Category, Product


class ProductsFixtureTestCase(TestCase):
    fixtures = ['products.yaml']

    def test_categories_are_loaded(self):
        self.assertEqual(
            set(Category.objects.values_list('name', flat=True)),
            {'Диваны', 'Кресла', 'Пуфы и банкетки', 'Кушетки'})

    def test_products_are_loaded(self):
        self.assertEqual(Product.objects.count(), 12)

    def test_every_category_has_products(self):
        for category in Category.objects.all():
            self.assertTrue(category.products.exists(), category.name)

    def test_every_product_is_complete(self):
        for product in Product.objects.all():
            self.assertIsNotNone(product.category, product.name)
            self.assertGreater(product.price, 0, product.name)
            self.assertTrue(product.description, product.name)

    def test_product_names_are_unique(self):
        names = list(Product.objects.values_list('name', flat=True))
        self.assertEqual(len(names), len(set(names)))

    def test_loading_twice_does_not_duplicate_data(self):
        call_command('loaddata', 'products.yaml', verbosity=0)
        self.assertEqual(Product.objects.count(), 12)
        self.assertEqual(Category.objects.count(), 4)


class FixtureCartTestCase(TestCase):
    """Корзина на реальных данных магазина."""
    fixtures = ['products.yaml']

    ALL_PRODUCTS_PRICE = 322100

    def test_total_of_all_products(self):
        cart = Cart.objects.create()
        for product in Product.objects.all():
            self.assertTrue(cart.add(product))
        self.assertEqual(cart.item_count, 12)
        self.assertEqual(cart.total_price, self.ALL_PRODUCTS_PRICE)
        self.assertEqual(cart.total_price, sum(p.price for p in Product.objects.all()))

    def test_second_pass_adds_nothing(self):
        cart = Cart.objects.create()
        for product in Product.objects.all():
            cart.add(product)
        for product in Product.objects.all():
            self.assertFalse(cart.add(product))
        self.assertEqual(cart.item_count, 12)

    def test_catalog_shows_every_product_and_category(self):
        response = self.client.get(reverse('index'))
        for product in Product.objects.all():
            self.assertContains(response, product.name)
        for category in Category.objects.all():
            self.assertContains(response, category.name)

    def test_each_category_page_shows_only_its_products(self):
        for category in Category.objects.all():
            response = self.client.get(reverse('index'), {'category': category.pk})
            shown = {p.pk for p in response.context['products']}
            self.assertEqual(shown, set(category.products.values_list('pk', flat=True)))
