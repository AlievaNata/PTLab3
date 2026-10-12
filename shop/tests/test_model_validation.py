from django.core.exceptions import ValidationError
from django.db import models
from django.test import SimpleTestCase, TestCase

from shop.models import Cart, CartItem, Category, Product, Purchase


class ValidationMixin:
    def assert_invalid(self, instance, field):
        with self.assertRaises(ValidationError) as ctx:
            instance.full_clean()
        self.assertIn(field, ctx.exception.message_dict)


class ProductValidationTestCase(ValidationMixin, TestCase):
    def test_minimal_product_is_valid(self):
        Product(name='Диван', price=1).full_clean()

    def test_name_is_required(self):
        self.assert_invalid(Product(name='', price=1), 'name')

    def test_name_length_boundary(self):
        Product(name='а' * 200, price=1).full_clean()
        self.assert_invalid(Product(name='а' * 201, price=1), 'name')

    def test_price_is_required(self):
        self.assert_invalid(Product(name='Диван', price=None), 'price')

    def test_price_cannot_be_negative(self):
        self.assert_invalid(Product(name='Диван', price=-1), 'price')

    def test_price_zero_is_allowed(self):
        Product(name='Диван', price=0).full_clean()

    def test_price_cannot_exceed_database_limit(self):
        # PositiveIntegerField в PostgreSQL: 0 .. 2147483647
        Product(name='Диван', price=2147483647).full_clean()
        self.assert_invalid(Product(name='Диван', price=2147483648), 'price')

    def test_description_may_be_empty(self):
        Product(name='Диван', price=1, description='').full_clean()

    def test_category_must_exist(self):
        self.assert_invalid(Product(name='Диван', price=1, category_id=999999), 'category')


class CategoryValidationTestCase(ValidationMixin, TestCase):
    def test_name_is_required(self):
        self.assert_invalid(Category(name=''), 'name')

    def test_name_length_boundary(self):
        Category(name='а' * 100).full_clean()
        self.assert_invalid(Category(name='а' * 101), 'name')

    def test_name_must_be_unique(self):
        Category.objects.create(name='Диваны')
        self.assert_invalid(Category(name='Диваны'), 'name')


class PurchaseValidationTestCase(ValidationMixin, TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Диван', price=1)

    def test_valid_purchase(self):
        Purchase(product=self.product, person='Иванов', address='ул. Светлая').full_clean(
            exclude=['date'])

    def test_person_is_required(self):
        self.assert_invalid(Purchase(product=self.product, person='', address='a'), 'person')

    def test_address_is_required(self):
        self.assert_invalid(Purchase(product=self.product, person='a', address=''), 'address')

    def test_length_boundaries(self):
        self.assert_invalid(
            Purchase(product=self.product, person='а' * 201, address='a'), 'person')
        self.assert_invalid(
            Purchase(product=self.product, person='a', address='а' * 201), 'address')

    def test_product_is_required(self):
        self.assert_invalid(Purchase(person='a', address='a'), 'product')


class ModelMetaTestCase(SimpleTestCase):
    def test_price_field_type(self):
        self.assertIsInstance(Product._meta.get_field('price'), models.PositiveIntegerField)

    def test_category_is_optional_foreign_key(self):
        field = Product._meta.get_field('category')
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertIs(field.remote_field.on_delete, models.SET_NULL)

    def test_cart_item_uniqueness_constraint(self):
        constraints = CartItem._meta.constraints
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0].name, 'unique_product_in_cart')
        self.assertEqual(tuple(constraints[0].fields), ('cart', 'product'))

    def test_category_meta(self):
        self.assertEqual(Category._meta.ordering, ['name'])
        self.assertEqual(Category._meta.verbose_name_plural, 'категории')

    def test_cart_item_is_deleted_with_cart_and_product(self):
        self.assertIs(CartItem._meta.get_field('cart').remote_field.on_delete, models.CASCADE)
        self.assertIs(CartItem._meta.get_field('product').remote_field.on_delete, models.CASCADE)


class ModelStrWithoutDatabaseTestCase(SimpleTestCase):
    """__str__ не должен обращаться к базе данных."""

    def test_str(self):
        product = Product(name='Стол')
        self.assertEqual(str(Category(name='Диваны')), 'Диваны')
        self.assertEqual(str(product), 'Стол')
        self.assertEqual(str(Purchase(product=product, person='Иван')), 'Иван: Стол')
        self.assertEqual(str(Cart(pk=7)), 'Корзина №7')
        self.assertEqual(str(CartItem(cart=Cart(pk=3), product=product)), 'Стол в Корзина №3')
