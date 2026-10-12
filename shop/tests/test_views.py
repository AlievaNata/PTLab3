from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from django.views.generic.edit import CreateView

from shop.models import Cart, CartItem, Product, Purchase
from shop.views import PurchaseCreate

from .helpers import ShopTestCase


def last_message(response):
    """
    Последнее сообщение django.contrib.messages, добавленное во время запроса.
    (Непрочитанные сообщения прошлых запросов тоже лежат в хранилище,
    поэтому сравниваем именно последнее.)
    """
    return str(list(get_messages(response.wsgi_request))[-1])


class PurchaseCreateTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_webpage_accessibility(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_view_class(self):
        self.assertTrue(issubclass(PurchaseCreate, CreateView))
        self.assertEqual(PurchaseCreate.model, Purchase)


class IndexViewTestCase(ShopTestCase):
    def test_status_and_templates(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/index.html')
        self.assertTemplateUsed(response, 'shop/base.html')

    def test_all_products_are_listed(self):
        response = self.client.get(reverse('index'))
        for product in (self.sofa, self.sofa2, self.chair):
            self.assertContains(response, product.name)
            self.assertContains(response, f'{product.price} ₽')
        self.assertContains(response, self.sofa.description)

    def test_categories_are_listed(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(list(response.context['categories']), [self.sofas, self.chairs])
        self.assertIsNone(response.context['selected_category'])

    def test_filter_by_category(self):
        response = self.client.get(reverse('index'), {'category': self.chairs.pk})
        self.assertEqual(response.context['selected_category'], self.chairs)
        self.assertEqual([p.name for p in response.context['products']], ['Кресло Уют'])
        self.assertContains(response, 'Кресло Уют')
        self.assertNotContains(response, 'Диван Лондон')

    def test_invalid_category_shows_everything(self):
        for value in ('abc', '999999', '-1', ''):
            response = self.client.get(reverse('index'), {'category': value})
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.context['selected_category'])
            self.assertEqual(len(response.context['products']), 3)

    def test_product_without_category(self):
        Product.objects.create(name='Пуф Без Категории', price=100)
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Пуф Без Категории')

    def test_empty_catalog(self):
        Product.objects.all().delete()
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Товаров пока нет')

    def test_buttons_reflect_cart_contents(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'В корзину', count=3)
        self.assertNotContains(response, 'В корзине')
        self.assertEqual(response.context['cart_product_ids'], set())

        self.add_to_cart(self.sofa)
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'В корзине', count=1)
        self.assertContains(response, 'В корзину', count=2)
        self.assertEqual(response.context['cart_product_ids'], {self.sofa.pk})

    def test_viewing_catalog_does_not_create_cart(self):
        self.client.get(reverse('index'))
        self.assertEqual(Cart.objects.count(), 0)


class PurchaseCreateViewTestCase(ShopTestCase):
    def test_form_page(self):
        response = self.client.get(reverse('buy', args=[self.sofa.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/purchase_form.html')
        self.assertContains(response, f'value="{self.sofa.pk}"')

    def test_successful_purchase(self):
        response = self.client.post(reverse('buy', args=[self.sofa.pk]), {
            'product': self.sofa.pk,
            'person': 'Ivanov',
            'address': 'Svetlaya St.',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Спасибо за покупку, Ivanov!')
        purchase = Purchase.objects.get()
        self.assertEqual(purchase.product, self.sofa)
        self.assertEqual(purchase.person, 'Ivanov')
        self.assertEqual(purchase.address, 'Svetlaya St.')

    def test_invalid_purchase_shows_form_again(self):
        response = self.client.post(reverse('buy', args=[self.sofa.pk]), {
            'product': self.sofa.pk,
            'person': '',
            'address': 'Svetlaya St.',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('person', response.context['form'].errors)
        self.assertEqual(Purchase.objects.count(), 0)


class CartAddViewTestCase(ShopTestCase):
    def test_add_product(self):
        response = self.client.post(reverse('cart_add', args=[self.sofa.pk]))
        self.assertRedirects(response, reverse('index'))
        cart = Cart.objects.get()
        self.assertEqual(cart.product_ids(), {self.sofa.pk})
        self.assertEqual(last_message(response), 'Товар «Диван Лондон» добавлен в корзину.')

    def test_same_product_is_not_added_twice(self):
        self.client.post(reverse('cart_add', args=[self.sofa.pk]))
        response = self.client.post(reverse('cart_add', args=[self.sofa.pk]))
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(Cart.objects.count(), 1)
        self.assertIn('уже в корзине', last_message(response))
        self.assertIn('только один экземпляр', last_message(response))

    def test_different_products_share_one_cart(self):
        self.add_to_cart(self.sofa, self.chair)
        self.assertEqual(Cart.objects.count(), 1)
        self.assertEqual(CartItem.objects.count(), 2)

    def test_unknown_product(self):
        response = self.client.post(reverse('cart_add', args=[999999]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Cart.objects.count(), 0)

    def test_get_is_not_allowed(self):
        response = self.client.get(reverse('cart_add', args=[self.sofa.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_post_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('cart_add', args=[self.sofa.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_redirect_to_safe_next_url(self):
        response = self.client.post(reverse('cart_add', args=[self.sofa.pk]),
                                    {'next': reverse('cart')})
        self.assertRedirects(response, reverse('cart'))

    def test_redirect_keeps_category_filter(self):
        next_url = f"{reverse('index')}?category={self.sofas.pk}"
        response = self.client.post(reverse('cart_add', args=[self.sofa.pk]),
                                    {'next': next_url})
        self.assertRedirects(response, next_url)

    def test_unsafe_next_url_is_ignored(self):
        for evil in ('https://evil.example.com/', '//evil.example.com/'):
            response = self.client.post(reverse('cart_add', args=[self.sofa.pk]),
                                        {'next': evil})
            self.assertRedirects(response, reverse('index'))

    def test_carts_of_different_visitors_are_separate(self):
        self.add_to_cart(self.sofa)
        other_client = Client()
        other_client.post(reverse('cart_add', args=[self.sofa.pk]))
        self.assertEqual(Cart.objects.count(), 2)
        self.assertEqual(CartItem.objects.count(), 2)


class CartRemoveViewTestCase(ShopTestCase):
    def test_remove_product(self):
        self.add_to_cart(self.sofa, self.chair)
        response = self.client.post(reverse('cart_remove', args=[self.sofa.pk]))
        self.assertRedirects(response, reverse('cart'))
        self.assertEqual(Cart.objects.get().product_ids(), {self.chair.pk})
        self.assertEqual(last_message(response), 'Товар удалён из корзины.')

    def test_remove_product_that_is_not_in_cart(self):
        self.add_to_cart(self.sofa)
        response = self.client.post(reverse('cart_remove', args=[self.chair.pk]))
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(last_message(response), 'Этого товара нет в корзине.')

    def test_remove_when_there_is_no_cart(self):
        response = self.client.post(reverse('cart_remove', args=[self.sofa.pk]))
        self.assertRedirects(response, reverse('cart'))
        self.assertEqual(last_message(response), 'Этого товара нет в корзине.')

    def test_remove_redirects_to_next_url(self):
        self.add_to_cart(self.sofa)
        response = self.client.post(reverse('cart_remove', args=[self.sofa.pk]),
                                    {'next': reverse('index')})
        self.assertRedirects(response, reverse('index'))

    def test_get_is_not_allowed(self):
        response = self.client.get(reverse('cart_remove', args=[self.sofa.pk]))
        self.assertEqual(response.status_code, 405)


class CartClearViewTestCase(ShopTestCase):
    def test_clear_cart(self):
        self.add_to_cart(self.sofa, self.chair)
        response = self.client.post(reverse('cart_clear'))
        self.assertRedirects(response, reverse('cart'))
        self.assertEqual(CartItem.objects.count(), 0)
        self.assertEqual(last_message(response), 'Корзина очищена.')

    def test_clear_when_there_is_no_cart(self):
        response = self.client.post(reverse('cart_clear'))
        self.assertRedirects(response, reverse('cart'))

    def test_get_is_not_allowed(self):
        response = self.client.get(reverse('cart_clear'))
        self.assertEqual(response.status_code, 405)


class CartDetailViewTestCase(ShopTestCase):
    def test_empty_cart(self):
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/cart.html')
        self.assertContains(response, 'Корзина пуста.')
        self.assertEqual(response.context['total_price'], 0)
        self.assertNotContains(response, 'Итого')

    def test_cart_shows_products_and_total_price(self):
        self.add_to_cart(self.sofa, self.chair)
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Диван Лондон')
        self.assertContains(response, 'Кресло Уют')
        self.assertNotContains(response, 'Диван Милан')
        self.assertContains(response, 'Итого: 60000 ₽')
        self.assertEqual(response.context['total_price'], 60000)
        self.assertEqual(len(response.context['items']), 2)

    def test_total_changes_when_cart_changes(self):
        self.add_to_cart(self.sofa, self.sofa2)
        self.assertContains(self.client.get(reverse('cart')), 'Итого: 70000 ₽')
        self.client.post(reverse('cart_remove', args=[self.sofa.pk]))
        self.assertContains(self.client.get(reverse('cart')), 'Итого: 20000 ₽')
        self.client.post(reverse('cart_clear'))
        self.assertContains(self.client.get(reverse('cart')), 'Корзина пуста.')

    def test_duplicate_click_does_not_change_total(self):
        self.add_to_cart(self.sofa, self.sofa, self.sofa)
        response = self.client.get(reverse('cart'))
        self.assertContains(response, 'Итого: 50000 ₽')
        self.assertEqual(len(response.context['items']), 1)

    def test_product_without_category_in_cart(self):
        product = Product.objects.create(name='Пуф Без Категории', price=100)
        self.add_to_cart(product)
        self.assertContains(self.client.get(reverse('cart')), 'Пуф Без Категории')
