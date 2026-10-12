from django.test import SimpleTestCase
from django.urls import Resolver404, resolve, reverse

from shop import views


class UrlReverseTestCase(SimpleTestCase):
    def test_reverse(self):
        self.assertEqual(reverse('index'), '/')
        self.assertEqual(reverse('cart'), '/cart/')
        self.assertEqual(reverse('cart_clear'), '/cart/clear/')
        self.assertEqual(reverse('cart_add', args=[5]), '/cart/add/5/')
        self.assertEqual(reverse('cart_remove', args=[5]), '/cart/remove/5/')
        self.assertEqual(reverse('buy', args=[3]), '/buy/3/')

    def test_admin_url(self):
        self.assertEqual(reverse('admin:index'), '/admin/')


class UrlResolveTestCase(SimpleTestCase):
    def test_functions_views(self):
        self.assertIs(resolve('/').func, views.index)
        self.assertIs(resolve('/cart/').func, views.cart_detail)
        self.assertIs(resolve('/cart/add/1/').func, views.cart_add)
        self.assertIs(resolve('/cart/remove/1/').func, views.cart_remove)
        self.assertIs(resolve('/cart/clear/').func, views.cart_clear)

    def test_class_based_view(self):
        match = resolve('/buy/3/')
        self.assertIs(match.func.view_class, views.PurchaseCreate)
        self.assertEqual(match.kwargs, {'product_id': 3})

    def test_product_id_is_converted_to_int(self):
        self.assertEqual(resolve('/cart/add/12/').kwargs, {'product_id': 12})

    def test_non_numeric_product_id_is_not_routed(self):
        for path in ('/cart/add/abc/', '/cart/remove/abc/', '/buy/abc/', '/cart/add/-1/'):
            with self.assertRaises(Resolver404, msg=path):
                resolve(path)

    def test_unknown_path_is_not_routed(self):
        with self.assertRaises(Resolver404):
            resolve('/no/such/page/')
