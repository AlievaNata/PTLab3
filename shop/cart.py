from .models import Cart

CART_SESSION_KEY = 'cart_id'


def get_cart(request, create=False):
    """
    Возвращает корзину текущего посетителя (id корзины хранится в сессии).

    create=False - не создаёт корзину и возвращает None, если её ещё нет
    (так просмотр каталога не плодит пустые корзины в БД);
    create=True  - создаёт корзину при первом добавлении товара.
    """
    session = getattr(request, 'session', None)
    if session is None:
        return None

    cart = None
    cart_id = session.get(CART_SESSION_KEY)
    if cart_id is not None:
        cart = Cart.objects.filter(pk=cart_id).first()

    if cart is None and create:
        cart = Cart.objects.create()
        session[CART_SESSION_KEY] = cart.pk
    return cart
