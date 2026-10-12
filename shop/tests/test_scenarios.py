"""Сквозной сценарий покупателя: от каталога до пустой корзины."""
from django.urls import reverse

from shop.models import Cart, CartItem

from .helpers import ShopTestCase


class ShoppingScenarioTestCase(ShopTestCase):
    def post(self, name, *args, **data):
        return self.client.post(reverse(name, args=args), data, follow=True)

    def test_full_scenario(self):
        # 1. Пустая корзина
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Корзина: 0 шт. на 0 ₽')

        # 2. Кладём диван
        response = self.post('cart_add', self.sofa.pk)
        self.assertContains(response, 'добавлен в корзину')
        self.assertContains(response, 'Корзина: 1 шт. на 50000 ₽')

        # 3. Повторно тот же диван - второй экземпляр не появляется
        response = self.post('cart_add', self.sofa.pk)
        self.assertContains(response, 'уже в корзине')
        self.assertContains(response, 'Корзина: 1 шт. на 50000 ₽')
        self.assertEqual(CartItem.objects.count(), 1)

        # 4. Добавляем кресло - стоимость суммируется
        self.post('cart_add', self.chair.pk)
        response = self.client.get(reverse('cart'))
        self.assertContains(response, 'Итого: 60000 ₽')
        self.assertContains(response, 'Диван Лондон')
        self.assertContains(response, 'Кресло Уют')

        # 5. Убираем диван - остаётся кресло
        response = self.post('cart_remove', self.sofa.pk)
        self.assertContains(response, 'Итого: 10000 ₽')
        self.assertNotContains(response, 'Диван Лондон</p>')

        # 6. Диван можно положить снова
        response = self.post('cart_add', self.sofa.pk)
        self.assertContains(response, 'Корзина: 2 шт. на 60000 ₽')

        # 7. Очищаем корзину
        response = self.post('cart_clear')
        self.assertContains(response, 'Корзина пуста.')
        self.assertContains(response, 'Корзина: 0 шт. на 0 ₽')
        self.assertEqual(Cart.objects.count(), 1)
        self.assertEqual(CartItem.objects.count(), 0)
