"""Юнит-тесты get_cart и context processor без обращения к БД."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from shop.cart import CART_SESSION_KEY, get_cart
from shop.context_processors import cart as cart_processor


def make_request(session=None):
    request = RequestFactory().get('/')
    if session is not None:
        request.session = session
    return request


class GetCartUnitTestCase(SimpleTestCase):
    def setUp(self):
        patcher = patch('shop.cart.Cart')
        self.cart_model = patcher.start()
        self.addCleanup(patcher.stop)

    def test_no_session_means_no_database_access(self):
        self.assertIsNone(get_cart(make_request(), create=True))
        self.cart_model.objects.filter.assert_not_called()
        self.cart_model.objects.create.assert_not_called()

    def test_empty_session_without_create(self):
        self.assertIsNone(get_cart(make_request({})))
        self.cart_model.objects.filter.assert_not_called()
        self.cart_model.objects.create.assert_not_called()

    def test_empty_session_with_create(self):
        self.cart_model.objects.create.return_value = SimpleNamespace(pk=11)
        session = {}
        cart = get_cart(make_request(session), create=True)
        self.assertEqual(cart.pk, 11)
        self.assertEqual(session[CART_SESSION_KEY], 11)

    def test_cart_is_looked_up_by_id_from_session(self):
        found = SimpleNamespace(pk=5)
        self.cart_model.objects.filter.return_value.first.return_value = found
        self.assertIs(get_cart(make_request({CART_SESSION_KEY: 5})), found)
        self.cart_model.objects.filter.assert_called_once_with(pk=5)
        self.cart_model.objects.create.assert_not_called()

    def test_missing_cart_is_not_created_unless_asked(self):
        self.cart_model.objects.filter.return_value.first.return_value = None
        self.assertIsNone(get_cart(make_request({CART_SESSION_KEY: 5})))
        self.cart_model.objects.create.assert_not_called()

    def test_missing_cart_is_replaced_when_creating(self):
        self.cart_model.objects.filter.return_value.first.return_value = None
        self.cart_model.objects.create.return_value = SimpleNamespace(pk=6)
        session = {CART_SESSION_KEY: 5}
        self.assertEqual(get_cart(make_request(session), create=True).pk, 6)
        self.assertEqual(session[CART_SESSION_KEY], 6)


class CartProcessorUnitTestCase(SimpleTestCase):
    def test_no_cart(self):
        with patch('shop.context_processors.get_cart', return_value=None):
            self.assertEqual(cart_processor(make_request()),
                             {'cart_count': 0, 'cart_total': 0})

    def test_cart_summary_is_used(self):
        fake_cart = Mock()
        fake_cart.summary.return_value = {'count': 3, 'total': 900}
        with patch('shop.context_processors.get_cart', return_value=fake_cart) as get:
            request = make_request()
            self.assertEqual(cart_processor(request), {'cart_count': 3, 'cart_total': 900})
        get.assert_called_once_with(request)
        fake_cart.summary.assert_called_once_with()
