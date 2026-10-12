from django.test import RequestFactory, TestCase

from shop.cart import CART_SESSION_KEY, get_cart
from shop.models import Cart


def make_request(session=None):
    request = RequestFactory().get('/')
    if session is not None:
        request.session = session
    return request


class GetCartTestCase(TestCase):
    def test_request_without_session_gives_none(self):
        request = make_request()
        self.assertIsNone(get_cart(request))
        self.assertIsNone(get_cart(request, create=True))
        self.assertEqual(Cart.objects.count(), 0)

    def test_no_cart_is_created_by_default(self):
        request = make_request({})
        self.assertIsNone(get_cart(request))
        self.assertEqual(Cart.objects.count(), 0)

    def test_create_makes_cart_and_remembers_it_in_session(self):
        request = make_request({})
        cart = get_cart(request, create=True)
        self.assertIsInstance(cart, Cart)
        self.assertEqual(request.session[CART_SESSION_KEY], cart.pk)

    def test_same_cart_is_returned_next_time(self):
        request = make_request({})
        first = get_cart(request, create=True)
        self.assertEqual(get_cart(request), first)
        self.assertEqual(get_cart(request, create=True), first)
        self.assertEqual(Cart.objects.count(), 1)

    def test_existing_cart_is_found_by_session(self):
        cart = Cart.objects.create()
        request = make_request({CART_SESSION_KEY: cart.pk})
        self.assertEqual(get_cart(request), cart)

    def test_stale_cart_id_is_ignored(self):
        request = make_request({CART_SESSION_KEY: 987654})
        self.assertIsNone(get_cart(request))

    def test_stale_cart_id_is_replaced_when_creating(self):
        request = make_request({CART_SESSION_KEY: 987654})
        cart = get_cart(request, create=True)
        self.assertNotEqual(cart.pk, 987654)
        self.assertEqual(request.session[CART_SESSION_KEY], cart.pk)
