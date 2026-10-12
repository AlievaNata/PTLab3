"""Тесты представлений (шаблонов): отрисовка без БД и без HTTP-сервера."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

SOFAS = SimpleNamespace(id=1, name='Диваны')


def product(pk=1, name='Диван', price=1000, category=SOFAS, description='Мягкий'):
    return SimpleNamespace(id=pk, name=name, price=price, category=category,
                           description=description)


def render(template, context=None, path='/', **request_attrs):
    request = RequestFactory().get(path)
    for key, value in request_attrs.items():
        setattr(request, key, value)
    return render_to_string(template, context or {}, request=request)


class IndexTemplateTestCase(SimpleTestCase):
    def context(self, **extra):
        context = {'products': [product()], 'categories': [SOFAS],
                   'selected_category': None, 'cart_product_ids': set()}
        context.update(extra)
        return context

    def test_product_row(self):
        html = render('shop/index.html', self.context())
        self.assertIn('Диван', html)
        self.assertIn('Мягкий', html)
        self.assertIn('1000 ₽', html)

    def test_product_not_in_cart_has_add_button(self):
        html = render('shop/index.html', self.context())
        self.assertIn('action="/cart/add/1/"', html)
        self.assertIn('В корзину', html)
        self.assertNotIn('В корзине', html)
        self.assertNotIn('/cart/remove/1/', html)

    def test_product_in_cart_has_remove_button(self):
        html = render('shop/index.html', self.context(cart_product_ids={1}))
        self.assertIn('В корзине', html)
        self.assertIn('action="/cart/remove/1/"', html)
        self.assertNotIn('/cart/add/1/', html)

    def test_buy_now_link_is_kept(self):
        self.assertIn('href="/buy/1/"', render('shop/index.html', self.context()))

    def test_forms_are_protected_by_csrf_token(self):
        self.assertIn('csrfmiddlewaretoken', render('shop/index.html', self.context()))

    def test_next_field_keeps_current_page(self):
        html = render('shop/index.html', self.context(), path='/?category=1')
        self.assertIn('name="next" value="/?category=1"', html)

    def test_category_links(self):
        html = render('shop/index.html', self.context())
        self.assertIn('href="/?category=1"', html)
        self.assertIn('Диваны', html)

    def test_selected_category_is_shown(self):
        html = render('shop/index.html', self.context(selected_category=SOFAS))
        self.assertIn('Выбрана категория: Диваны', html)

    def test_selected_category_is_hidden_by_default(self):
        self.assertNotIn('Выбрана категория', render('shop/index.html', self.context()))

    def test_product_without_category(self):
        html = render('shop/index.html', self.context(products=[product(category=None)]))
        self.assertIn('—', html)

    def test_empty_catalog(self):
        self.assertIn('Товаров пока нет', render('shop/index.html', self.context(products=[])))

    def test_html_is_escaped(self):
        html = render('shop/index.html', self.context(products=[product(name='<b>x</b>')]))
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', html)
        self.assertNotIn('<b>x</b>', html)


class CartTemplateTestCase(SimpleTestCase):
    def items(self):
        return [SimpleNamespace(product=product(1, 'Диван', 1000)),
                SimpleNamespace(product=product(2, 'Кресло', 500, category=None))]

    def test_empty_cart(self):
        html = render('shop/cart.html', {'items': [], 'total_price': 0})
        self.assertIn('Корзина пуста.', html)
        self.assertNotIn('Итого', html)
        self.assertNotIn('Очистить корзину', html)

    def test_cart_with_items(self):
        html = render('shop/cart.html', {'items': self.items(), 'total_price': 1500})
        self.assertIn('Диван', html)
        self.assertIn('Кресло', html)
        self.assertIn('1000 ₽', html)
        self.assertIn('500 ₽', html)
        self.assertIn('Итого: 1500 ₽', html)
        self.assertNotIn('Корзина пуста.', html)

    def test_remove_and_clear_forms(self):
        html = render('shop/cart.html', {'items': self.items(), 'total_price': 1500})
        self.assertIn('action="/cart/remove/1/"', html)
        self.assertIn('action="/cart/remove/2/"', html)
        self.assertIn('action="/cart/clear/"', html)
        self.assertIn('csrfmiddlewaretoken', html)

    def test_link_back_to_catalog(self):
        self.assertIn('href="/"', render('shop/cart.html', {'items': [], 'total_price': 0}))


class BaseTemplateTestCase(SimpleTestCase):
    def test_navigation_links(self):
        html = render('shop/cart.html', {'items': [], 'total_price': 0})
        self.assertIn('href="/"', html)
        self.assertIn('href="/cart/"', html)

    def test_header_without_cart(self):
        html = render('shop/cart.html', {'items': [], 'total_price': 0})
        self.assertIn('Корзина: 0 шт. на 0 ₽', html)

    def test_header_shows_cart_summary(self):
        fake_cart = Mock()
        fake_cart.summary.return_value = {'count': 2, 'total': 1500}
        with patch('shop.context_processors.get_cart', return_value=fake_cart):
            html = render('shop/cart.html', {'items': [], 'total_price': 0})
        self.assertIn('Корзина: 2 шт. на 1500 ₽', html)

    def test_messages_are_displayed(self):
        html = render('shop/cart.html', {'items': [], 'total_price': 0},
                      _messages=['Товар добавлен в корзину.', 'Второе сообщение'])
        self.assertIn('Товар добавлен в корзину.', html)
        self.assertIn('Второе сообщение', html)

    def test_no_message_list_without_messages(self):
        html = render('shop/cart.html', {'items': [], 'total_price': 0})
        self.assertNotIn('class="messages"', html)


class PurchaseFormTemplateTestCase(SimpleTestCase):
    def test_form_fields(self):
        html = render('shop/purchase_form.html', {'view': SimpleNamespace(kwargs={'product_id': 7})})
        self.assertIn('name="product"', html)
        self.assertIn('value="7"', html)
        self.assertIn('name="person"', html)
        self.assertIn('name="address"', html)
        self.assertIn('csrfmiddlewaretoken', html)
