from django.contrib import admin
from core.models import (
    Category,
    Product,
    Vendor,
    CartOrder,
    CartOrderItems,
    Wishlist,
    ProductImages,
    ProductReview,
    Address,
    Coupon,
)


class ProductImagesAdmin(admin.TabularInline):
    model = ProductImages


class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImagesAdmin]
    list_display = [
        "user",
        "title",
        "product_image",
        "price",
        "category",
        "vendor",
        "featured",
        "product_status",
        "pid",
    ]
    search_fields = [
        "title",
        "description",
        "pid",
        "user__username",
        "category__title",
        "vendor__title",
    ]
    list_filter = ["category", "vendor", "featured", "product_status"]


class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category_image",
    ]


class VendorAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "vendor_image",
    ]
    search_fields = ["title", "description", "address"]


class CartOrderAdmin(admin.ModelAdmin):
    list_editable = ["paid_status", "product_status"]
    list_display = [
        "user",
        "price",
        "paid_status",
        "order_date",
        "product_status",
    ]
    search_fields = [
        "user__username",
        "user__email",
        "oid",
        "full_name",
        "email",
        "phone",
    ]
    list_filter = ["paid_status", "product_status", "order_date"]


class CartOrderItemsAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "invoice_no",
        "item",
        "image",
        "qty",
        "price",
        "total",
    ]
    search_fields = ["invoice_no", "item", "order__oid", "order__user__username"]
    list_filter = ["order__product_status"]


class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "review", "rating"]


class wishlistAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "product",
        "date",
    ]


class AdressAdmin(admin.ModelAdmin):
    list_editable = ["address", "status"]
    list_display = [
        "user",
        "address",
        "status",
    ]


admin.site.register(Product, ProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(CartOrder, CartOrderAdmin)
admin.site.register(CartOrderItems, CartOrderItemsAdmin)
admin.site.register(ProductReview, ProductReviewAdmin)
admin.site.register(Wishlist, wishlistAdmin)
admin.site.register(Address, AdressAdmin)
admin.site.register(Coupon)
