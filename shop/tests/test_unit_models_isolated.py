"""Юнит-тесты методов корзины в изоляции: обращения к БД заменены заглушками (mock)."""
from unittest.mock import PropertyMock, patch

from django.test import SimpleTestCase

from shop.models import Cart


class CartAddUnitTestCase(SimpleTestCase):
    def test_add_creates_item_and_returns_true(self):
        cart, product = Cart(pk=1), object()
        with patch('shop.models.CartItem') as cart_item:
            cart_item.objects.get_or_create.return_value = (object(), True)
            self.assertTrue(cart.add(product))
        cart_item.objects.get_or_create.assert_called_once_with(cart=cart, product=product)

    def test_add_returns_false_if_item_already_exists(self):
        with patch('shop.models.CartItem') as cart_item:
            cart_item.objects.get_or_create.return_value = (object(), False)
            self.assertFalse(Cart(pk=1).add(object()))


class CartItemsUnitTestCase(SimpleTestCase):
    def setUp(self):
        patcher = patch.object(Cart, 'items', new_callable=PropertyMock)
        self.items = patcher.start().return_value
        self.addCleanup(patcher.stop)
        self.cart = Cart(pk=1)

    def test_remove_returns_true_when_something_was_deleted(self):
        self.items.filter.return_value.delete.return_value = (1, {'shop.CartItem': 1})
        self.assertTrue(self.cart.remove(5))
        self.items.filter.assert_called_once_with(product=5)

    def test_remove_returns_false_when_nothing_was_deleted(self):
        self.items.filter.return_value.delete.return_value = (0, {})
        self.assertFalse(self.cart.remove(5))

    def test_clear_deletes_all_items(self):
        self.cart.clear()
        self.items.all.return_value.delete.assert_called_once_with()

    def test_contains(self):
        self.items.filter.return_value.exists.return_value = True
        self.assertTrue(self.cart.contains(5))
        self.items.filter.return_value.exists.return_value = False
        self.assertFalse(self.cart.contains(5))

    def test_product_ids_removes_duplicates(self):
        self.items.values_list.return_value = [1, 2, 2]
        self.assertEqual(self.cart.product_ids(), {1, 2})
        self.items.values_list.assert_called_once_with('product_id', flat=True)

    def test_summary_of_empty_cart(self):
        self.items.aggregate.return_value = {'count': 0, 'total': None}
        self.assertEqual(self.cart.summary(), {'count': 0, 'total': 0})

    def test_summary_uses_single_query(self):
        self.items.aggregate.return_value = {'count': 2, 'total': 1500}
        self.assertEqual(self.cart.summary(), {'count': 2, 'total': 1500})
        self.assertEqual(self.items.aggregate.call_count, 1)


class CartPropertiesUnitTestCase(SimpleTestCase):
    def test_item_count_and_total_price_come_from_summary(self):
        with patch.object(Cart, 'summary', return_value={'count': 3, 'total': 900}):
            cart = Cart(pk=1)
            self.assertEqual(cart.item_count, 3)
            self.assertEqual(cart.total_price, 900)
