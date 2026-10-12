from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView

from .cart import get_cart
from .models import Category, Product, Purchase


def _redirect_back(request, default):
    """Возврат на страницу, откуда пришёл POST (параметр next), если адрес безопасный."""
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()):
        return redirect(next_url)
    return redirect(default)


def index(request):
    products = Product.objects.select_related('category').order_by('category__name', 'name')
    categories = Category.objects.all()

    selected_category = None
    category_id = request.GET.get('category')
    if category_id and category_id.isdigit():
        selected_category = categories.filter(pk=category_id).first()
    if selected_category is not None:
        products = products.filter(category=selected_category)

    cart = get_cart(request)
    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'cart_product_ids': cart.product_ids() if cart else set(),
    }
    return render(request, 'shop/index.html', context)


def cart_detail(request):
    cart = get_cart(request)
    if cart is None:
        items, total_price = [], 0
    else:
        items = cart.items.select_related('product__category')
        total_price = cart.total_price
    return render(request, 'shop/cart.html', {'items': items, 'total_price': total_price})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart = get_cart(request, create=True)
    if cart.add(product):
        messages.success(request, f'Товар «{product.name}» добавлен в корзину.')
    else:
        messages.info(
            request,
            f'Товар «{product.name}» уже в корзине. '
            f'Корзина может содержать только один экземпляр товара.')
    return _redirect_back(request, 'index')


@require_POST
def cart_remove(request, product_id):
    cart = get_cart(request)
    if cart is not None and cart.remove(product_id):
        messages.success(request, 'Товар удалён из корзины.')
    else:
        messages.info(request, 'Этого товара нет в корзине.')
    return _redirect_back(request, 'cart')


@require_POST
def cart_clear(request):
    cart = get_cart(request)
    if cart is not None:
        cart.clear()
    messages.success(request, 'Корзина очищена.')
    return _redirect_back(request, 'cart')


class PurchaseCreate(CreateView):
    model = Purchase
    fields = ['product', 'person', 'address']

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponse(f'Спасибо за покупку, {self.object.person}!')
