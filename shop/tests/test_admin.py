from django.contrib import admin
from django.test import TestCase

from shop.admin import CartAdmin
from shop.models import Cart, CartItem, Category, Product, Purchase

from .helpers import ShopTestCase


class AdminRegistrationTestCase(TestCase):
    def test_models_are_registered(self):
        for model in (Category, Product, Purchase, Cart):
            self.assertTrue(admin.site.is_registered(model), model.__name__)

    def test_cart_items_are_edited_inside_cart(self):
        model_admin = admin.site._registry[Cart]
        self.assertEqual([i.model for i in model_admin.inlines], [CartItem])


class CartAdminTestCase(ShopTestCase):
    def test_items_count_and_total(self):
        cart = Cart.objects.create()
        cart.add(self.sofa)
        cart.add(self.chair)
        model_admin = CartAdmin(Cart, admin.site)
        self.assertEqual(model_admin.items_count(cart), 2)
        self.assertEqual(model_admin.total(cart), 60000)
