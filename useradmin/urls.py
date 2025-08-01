from django.urls import path
from useradmin import views

app_name = "useradmin"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("products/", views.products, name="products"),
    path("add-product/", views.add_product, name="add_product"),
    path("edit-product/<pid>/", views.edit_product, name="edit_product"),
    path("delete_product/<pid>/", views.delete_product, name="delete_product"),
    path("orders/", views.orders, name="orders"),
    path("order_detail/<id>/", views.order_detail, name="order_detail"),
    path(
        "change_order_status/<id>/",
        views.change_order_status,
        name="change_order_status",
    ),
    path(
        "shop_page/",
        views.shop_page,
        name="shop_page",
    ),
    path(
        "reviews/",
        views.reviews,
        name="reviews",
    ),
    path(
        "settings/",
        views.settings,
        name="settings",
    ),
    path(
        "change_password/",
        views.change_password,
        name="change_password",
    ),
]
