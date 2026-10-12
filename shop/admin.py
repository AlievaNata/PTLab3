from django.contrib import admin

from .models import Cart, CartItem, Category, Product, Purchase


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price')
    list_filter = ('category',)
    search_fields = ('name', 'description')


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('product', 'person', 'address', 'date')
    list_filter = ('date',)
    search_fields = ('person', 'address')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'created', 'items_count', 'total')
    inlines = [CartItemInline]

    @admin.display(description='Товаров')
    def items_count(self, obj):
        return obj.item_count

    @admin.display(description='Стоимость')
    def total(self, obj):
        return obj.total_price
