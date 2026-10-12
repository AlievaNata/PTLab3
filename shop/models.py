from django.db import models
from django.db.models import Count, Sum


class Category(models.Model):
    """Категория мягкой мебели: диваны, кресла, пуфы и т.д."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.PositiveIntegerField()
    description = models.TextField(blank=True, default='')
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='products',
    )

    def __str__(self):
        return self.name


class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    person = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.person}: {self.product}'


class Cart(models.Model):
    """
    Корзина покупателя. Привязывается к сессии (см. shop/cart.py),
    поэтому работает и для неавторизованных пользователей.
    """
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Корзина №{self.pk}'

    def add(self, product):
        """
        Кладёт товар в корзину. Возвращает True, если товар был добавлен,
        и False, если он уже лежал в корзине (второй экземпляр не добавляется).
        """
        _, created = CartItem.objects.get_or_create(cart=self, product=product)
        return created

    def remove(self, product):
        """Убирает товар (объект или его pk). True, если товар был в корзине."""
        deleted, _ = self.items.filter(product=product).delete()
        return deleted > 0

    def clear(self):
        self.items.all().delete()

    def contains(self, product):
        return self.items.filter(product=product).exists()

    def product_ids(self):
        return set(self.items.values_list('product_id', flat=True))

    def summary(self):
        """Количество позиций и общая стоимость одним запросом к БД."""
        data = self.items.aggregate(count=Count('id'), total=Sum('product__price'))
        return {'count': data['count'], 'total': data['total'] or 0}

    @property
    def item_count(self):
        return self.summary()['count']

    @property
    def total_price(self):
        return self.summary()['total']


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['added_at', 'id']
        constraints = [
            # Один экземпляр одного товара в корзине - гарантия на уровне БД.
            models.UniqueConstraint(fields=['cart', 'product'], name='unique_product_in_cart'),
        ]

    def __str__(self):
        return f'{self.product} в {self.cart}'
