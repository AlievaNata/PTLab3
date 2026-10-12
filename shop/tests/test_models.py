from django.db import IntegrityError, transaction
from django.test import TestCase
from shop.models import Cart, CartItem, Category, Product, Purchase
from datetime import datetime

from .helpers import ShopTestCase


class ProductTestCase(TestCase):
    def setUp(self):
        Product.objects.create(name="book", price="740")
        Product.objects.create(name="pencil", price="50")

    def test_correctness_types(self):
        self.assertIsInstance(Product.objects.get(name="book").name, str)
        self.assertIsInstance(Product.objects.get(name="book").price, int)
        self.assertIsInstance(Product.objects.get(name="pencil").name, str)
        self.assertIsInstance(Product.objects.get(name="pencil").price, int)

    def test_correctness_data(self):
        self.assertTrue(Product.objects.get(name="book").price == 740)
        self.assertTrue(Product.objects.get(name="pencil").price == 50)


class PurchaseTestCase(TestCase):
    def setUp(self):
        self.product_book = Product.objects.create(name="book", price="740")
        self.datetime = datetime.now()
        Purchase.objects.create(product=self.product_book,
                                person="Ivanov",
                                address="Svetlaya St.")

    def test_correctness_types(self):
        self.assertIsInstance(Purchase.objects.get(product=self.product_book).person, str)
        self.assertIsInstance(Purchase.objects.get(product=self.product_book).address, str)
        self.assertIsInstance(Purchase.objects.get(product=self.product_book).date, datetime)

    def test_correctness_data(self):
        self.assertTrue(Purchase.objects.get(product=self.product_book).person == "Ivanov")
        self.assertTrue(Purchase.objects.get(product=self.product_book).address == "Svetlaya St.")
        self.assertTrue(Purchase.objects.get(product=self.product_book).date.replace(microsecond=0) == \
            self.datetime.replace(microsecond=0))

    def test_str(self):
        purchase = Purchase.objects.get(product=self.product_book)
        self.assertEqual(str(purchase), "Ivanov: book")


class CategoryTestCase(TestCase):
    def test_str(self):
        self.assertEqual(str(Category.objects.create(name='Диваны')), 'Диваны')

    def test_name_is_unique(self):
        Category.objects.create(name='Диваны')
        # На PostgreSQL после IntegrityError транзакция теста "ломается",
        # поэтому ошибку нужно изолировать во вложенном atomic().
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name='Диваны')

    def test_ordering_by_name(self):
        Category.objects.create(name='Пуфы')
        Category.objects.create(name='Диваны')
        Category.objects.create(name='Кресла')
        names = list(Category.objects.values_list('name', flat=True))
        self.assertEqual(names, ['Диваны', 'Кресла', 'Пуфы'])


class FurnitureProductTestCase(TestCase):
    def test_str(self):
        self.assertEqual(str(Product.objects.create(name='Диван', price=1)), 'Диван')

    def test_description_is_optional_and_empty_by_default(self):
        product = Product.objects.create(name='Диван', price=1)
        self.assertEqual(product.description, '')

    def test_category_is_optional(self):
        product = Product.objects.create(name='Диван', price=1)
        self.assertIsNone(product.category)

    def test_category_related_name(self):
        category = Category.objects.create(name='Диваны')
        product = Product.objects.create(name='Диван', price=1, category=category)
        self.assertEqual(list(category.products.all()), [product])

    def test_deleting_category_keeps_product(self):
        category = Category.objects.create(name='Диваны')
        product = Product.objects.create(name='Диван', price=1, category=category)
        category.delete()
        product.refresh_from_db()
        self.assertIsNone(product.category)


class CartModelTestCase(ShopTestCase):
    def setUp(self):
        self.cart = Cart.objects.create()

    def test_str(self):
        self.assertEqual(str(self.cart), f'Корзина №{self.cart.pk}')

    def test_new_cart_is_empty(self):
        self.assertEqual(self.cart.item_count, 0)
        self.assertEqual(self.cart.total_price, 0)
        self.assertEqual(self.cart.product_ids(), set())

    def test_add_returns_true_for_new_product(self):
        self.assertTrue(self.cart.add(self.sofa))
        self.assertTrue(self.cart.contains(self.sofa))
        self.assertEqual(self.cart.item_count, 1)

    def test_same_product_cannot_be_added_twice(self):
        self.assertTrue(self.cart.add(self.sofa))
        self.assertFalse(self.cart.add(self.sofa))
        self.assertEqual(self.cart.item_count, 1)
        self.assertEqual(self.cart.total_price, self.sofa.price)

    def test_database_rejects_duplicate_item(self):
        CartItem.objects.create(cart=self.cart, product=self.sofa)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartItem.objects.create(cart=self.cart, product=self.sofa)
        self.assertEqual(self.cart.items.count(), 1)

    def test_total_price_is_sum_of_product_prices(self):
        self.cart.add(self.sofa)
        self.cart.add(self.sofa2)
        self.cart.add(self.chair)
        self.assertEqual(self.cart.item_count, 3)
        self.assertEqual(self.cart.total_price, 50000 + 20000 + 10000)

    def test_summary(self):
        self.cart.add(self.sofa)
        self.cart.add(self.chair)
        self.assertEqual(self.cart.summary(), {'count': 2, 'total': 60000})

    def test_remove_updates_total(self):
        self.cart.add(self.sofa)
        self.cart.add(self.chair)
        self.assertTrue(self.cart.remove(self.sofa))
        self.assertFalse(self.cart.contains(self.sofa))
        self.assertEqual(self.cart.total_price, self.chair.price)

    def test_remove_accepts_primary_key(self):
        self.cart.add(self.sofa)
        self.assertTrue(self.cart.remove(self.sofa.pk))
        self.assertEqual(self.cart.item_count, 0)

    def test_remove_missing_product_returns_false(self):
        self.cart.add(self.sofa)
        self.assertFalse(self.cart.remove(self.chair))
        self.assertEqual(self.cart.item_count, 1)

    def test_removed_product_can_be_added_again(self):
        self.cart.add(self.sofa)
        self.cart.remove(self.sofa)
        self.assertTrue(self.cart.add(self.sofa))

    def test_clear(self):
        self.cart.add(self.sofa)
        self.cart.add(self.chair)
        self.cart.clear()
        self.assertEqual(self.cart.item_count, 0)
        self.assertEqual(self.cart.total_price, 0)

    def test_product_ids(self):
        self.cart.add(self.sofa)
        self.cart.add(self.chair)
        self.assertEqual(self.cart.product_ids(), {self.sofa.pk, self.chair.pk})

    def test_items_are_ordered_by_time_added(self):
        self.cart.add(self.chair)
        self.cart.add(self.sofa)
        self.assertEqual([i.product for i in self.cart.items.all()], [self.chair, self.sofa])

    def test_carts_are_independent(self):
        other = Cart.objects.create()
        self.cart.add(self.sofa)
        self.assertTrue(other.add(self.sofa))
        other.clear()
        self.assertTrue(self.cart.contains(self.sofa))
        self.assertEqual(other.total_price, 0)

    def test_deleting_product_removes_it_from_cart(self):
        self.cart.add(self.sofa)
        self.cart.add(self.chair)
        self.sofa.delete()
        self.assertEqual(self.cart.product_ids(), {self.chair.pk})
        self.assertEqual(self.cart.total_price, self.chair.price)

    def test_deleting_cart_removes_items(self):
        self.cart.add(self.sofa)
        self.cart.delete()
        self.assertFalse(CartItem.objects.exists())


class CartItemTestCase(ShopTestCase):
    def test_str(self):
        cart = Cart.objects.create()
        item = CartItem.objects.create(cart=cart, product=self.sofa)
        self.assertEqual(str(item), f'Диван Лондон в Корзина №{cart.pk}')
