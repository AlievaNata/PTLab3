"""
Юнит-тесты контроллеров (views) в изоляции: модели, корзина, сообщения и render
заменены заглушками. SimpleTestCase запрещает любые запросы к БД, поэтому
тесты гарантированно не зависят от PostgreSQL.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from shop import views


class RedirectBackUnitTestCase(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def redirect(self, data=None, **extra):
        return views._redirect_back(self.factory.post('/', data or {}, **extra), 'index')

    def test_without_next_goes_to_default(self):
        response = self.redirect()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

    def test_relative_next_is_used(self):
        self.assertEqual(self.redirect({'next': '/cart/'}).url, '/cart/')

    def test_next_with_query_string_is_used(self):
        self.assertEqual(self.redirect({'next': '/?category=2'}).url, '/?category=2')

    def test_absolute_url_of_same_host_is_allowed(self):
        self.assertEqual(self.redirect({'next': 'http://testserver/cart/'}).url,
                         'http://testserver/cart/')

    def test_foreign_host_is_rejected(self):
        for evil in ('https://evil.example.com/', '//evil.example.com/', 'javascript:alert(1)'):
            self.assertEqual(self.redirect({'next': evil}).url, '/', evil)

    def test_http_url_is_rejected_for_https_request(self):
        response = self.redirect({'next': 'http://testserver/cart/'}, secure=True)
        self.assertEqual(response.url, '/')

    def test_empty_next_goes_to_default(self):
        self.assertEqual(self.redirect({'next': ''}).url, '/')


class ViewTestBase(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        for target in ('shop.views.messages', 'shop.views.get_cart'):
            patcher = patch(target)
            setattr(self, target.split('.')[-1], patcher.start())
            self.addCleanup(patcher.stop)


class CartAddUnitTestCase(ViewTestBase):
    def setUp(self):
        super().setUp()
        patcher = patch('shop.views.get_object_or_404')
        self.get_product = patcher.start()
        self.addCleanup(patcher.stop)
        self.product = SimpleNamespace(name='Диван')
        self.get_product.return_value = self.product
        self.cart = self.get_cart.return_value

    def test_new_product_is_added(self):
        self.cart.add.return_value = True
        request = self.factory.post('/cart/add/1/')
        response = views.cart_add(request, product_id=1)

        self.get_product.assert_called_once_with(views.Product, pk=1)
        self.get_cart.assert_called_once_with(request, create=True)
        self.cart.add.assert_called_once_with(self.product)
        self.messages.success.assert_called_once()
        self.assertIn('Диван', self.messages.success.call_args[0][1])
        self.messages.info.assert_not_called()
        self.assertEqual((response.status_code, response.url), (302, '/'))

    def test_duplicate_product_gives_info_message(self):
        self.cart.add.return_value = False
        views.cart_add(self.factory.post('/cart/add/1/'), product_id=1)
        self.messages.info.assert_called_once()
        self.assertIn('уже в корзине', self.messages.info.call_args[0][1])
        self.messages.success.assert_not_called()

    def test_get_request_is_rejected(self):
        response = views.cart_add(self.factory.get('/cart/add/1/'), product_id=1)
        self.assertEqual(response.status_code, 405)
        self.get_cart.assert_not_called()
        self.cart.add.assert_not_called()

    def test_redirects_to_next(self):
        self.cart.add.return_value = True
        response = views.cart_add(self.factory.post('/', {'next': '/cart/'}), product_id=1)
        self.assertEqual(response.url, '/cart/')


class CartRemoveUnitTestCase(ViewTestBase):
    def test_removes_product(self):
        cart = self.get_cart.return_value
        cart.remove.return_value = True
        response = views.cart_remove(self.factory.post('/'), product_id=5)
        cart.remove.assert_called_once_with(5)
        self.messages.success.assert_called_once()
        self.assertEqual(response.url, '/cart/')

    def test_product_not_in_cart(self):
        self.get_cart.return_value.remove.return_value = False
        views.cart_remove(self.factory.post('/'), product_id=5)
        self.messages.info.assert_called_once()
        self.messages.success.assert_not_called()

    def test_no_cart(self):
        self.get_cart.return_value = None
        response = views.cart_remove(self.factory.post('/'), product_id=5)
        self.messages.info.assert_called_once()
        self.assertEqual(response.status_code, 302)

    def test_get_request_is_rejected(self):
        self.assertEqual(views.cart_remove(self.factory.get('/'), product_id=5).status_code, 405)


class CartClearUnitTestCase(ViewTestBase):
    def test_clears_cart(self):
        cart = self.get_cart.return_value
        response = views.cart_clear(self.factory.post('/'))
        cart.clear.assert_called_once_with()
        self.messages.success.assert_called_once()
        self.assertEqual(response.url, '/cart/')

    def test_no_cart(self):
        self.get_cart.return_value = None
        response = views.cart_clear(self.factory.post('/'))
        self.assertEqual(response.status_code, 302)

    def test_get_request_is_rejected(self):
        self.assertEqual(views.cart_clear(self.factory.get('/')).status_code, 405)


class CartDetailUnitTestCase(ViewTestBase):
    def setUp(self):
        super().setUp()
        patcher = patch('shop.views.render')
        self.render = patcher.start()
        self.addCleanup(patcher.stop)

    @patch('shop.views.get_cart', return_value=None)
    def test_no_cart(self, get_cart_mock):
        request = self.factory.get('/cart/')
        views.cart_detail(request)
        self.render.assert_called_once_with(
            request, 'shop/cart.html', {'items': [], 'total_price': 0})

    def test_cart_with_items(self):
        cart = self.get_cart.return_value
        cart.items.select_related.return_value = ['item']
        cart.total_price = 500
        request = self.factory.get('/cart/')
        views.cart_detail(request)
        cart.items.select_related.assert_called_once_with('product__category')
        self.render.assert_called_once_with(
            request, 'shop/cart.html', {'items': ['item'], 'total_price': 500})


class IndexUnitTestCase(ViewTestBase):
    def setUp(self):
        super().setUp()
        for target in ('render', 'Product', 'Category'):
            patcher = patch(f'shop.views.{target}')
            setattr(self, f'mock_{target}', patcher.start())
            self.addCleanup(patcher.stop)
        self.products = self.mock_Product.objects.select_related.return_value.order_by.return_value
        self.categories = self.mock_Category.objects.all.return_value
        self.get_cart.return_value = None

    def context(self):
        return self.mock_render.call_args[0][2]

    def call(self, params=None):
        request = self.factory.get('/', params or {})
        views.index(request)
        self.assertEqual(self.mock_render.call_args[0][:2], (request, 'shop/index.html'))
        return self.context()

    def test_products_are_selected_with_category_and_ordered(self):
        self.call()
        self.mock_Product.objects.select_related.assert_called_once_with('category')
        self.mock_Product.objects.select_related.return_value.order_by.assert_called_once_with(
            'category__name', 'name')

    def test_without_filter(self):
        context = self.call()
        self.assertIs(context['products'], self.products)
        self.assertIs(context['categories'], self.categories)
        self.assertIsNone(context['selected_category'])
        self.assertEqual(context['cart_product_ids'], set())
        self.categories.filter.assert_not_called()
        self.products.filter.assert_not_called()

    def test_filter_by_existing_category(self):
        category = SimpleNamespace(name='Диваны')
        self.categories.filter.return_value.first.return_value = category
        context = self.call({'category': '5'})
        self.categories.filter.assert_called_once_with(pk='5')
        self.products.filter.assert_called_once_with(category=category)
        self.assertIs(context['products'], self.products.filter.return_value)
        self.assertIs(context['selected_category'], category)

    def test_filter_by_missing_category(self):
        self.categories.filter.return_value.first.return_value = None
        context = self.call({'category': '5'})
        self.products.filter.assert_not_called()
        self.assertIs(context['products'], self.products)
        self.assertIsNone(context['selected_category'])

    def test_non_numeric_category_is_ignored(self):
        for value in ('abc', '-1', '1.5', ''):
            self.call({'category': value})
        self.categories.filter.assert_not_called()

    def test_products_in_cart_are_passed_to_template(self):
        cart = Mock()
        cart.product_ids.return_value = {1, 2}
        self.get_cart.return_value = cart
        self.assertEqual(self.call()['cart_product_ids'], {1, 2})
