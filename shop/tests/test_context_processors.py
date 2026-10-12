from django.test import RequestFactory
from django.urls import reverse

from shop.cart import CART_SESSION_KEY
from shop.context_processors import cart as cart_processor
from shop.models import Cart

from .helpers import ShopTestCase


class CartContextProcessorTestCase(ShopTestCase):
    def make_request(self, session=None):
        request = RequestFactory().get('/')
        if session is not None:
            request.session = session
        return request

    def test_request_without_session(self):
        self.assertEqual(cart_processor(self.make_request()),
                         {'cart_count': 0, 'cart_total': 0})

    def test_no_cart_yet(self):
        self.assertEqual(cart_processor(self.make_request({})),
                         {'cart_count': 0, 'cart_total': 0})

    def test_empty_cart(self):
        cart = Cart.objects.create()
        request = self.make_request({CART_SESSION_KEY: cart.pk})
        self.assertEqual(cart_processor(request), {'cart_count': 0, 'cart_total': 0})

    def test_cart_with_products(self):
        cart = Cart.objects.create()
        cart.add(self.sofa)
        cart.add(self.chair)
        request = self.make_request({CART_SESSION_KEY: cart.pk})
        self.assertEqual(cart_processor(request), {'cart_count': 2, 'cart_total': 60000})

    def test_summary_is_shown_on_every_page(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Корзина: 0 шт. на 0 ₽')
        self.add_to_cart(self.sofa, self.chair)
        for url in (reverse('index'), reverse('cart'), reverse('buy', args=[self.sofa.pk])):
            response = self.client.get(url)
            self.assertContains(response, 'Корзина: 2 шт. на 60000 ₽')
