from .cart import get_cart


def cart(request):
    """Количество товаров и общая стоимость корзины - доступны во всех шаблонах."""
    current = get_cart(request)
    if current is None:
        return {'cart_count': 0, 'cart_total': 0}
    summary = current.summary()
    return {'cart_count': summary['count'], 'cart_total': summary['total']}
