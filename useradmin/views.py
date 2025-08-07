from django.shortcuts import render, redirect
from django.db.models import Sum, Q
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from decimal import Decimal

from core.models import CartOrder, CartOrderItems, Product, Category, ProductReview, Vendor
from core.models import CartOrderItems
from userauths.models import Profile, User
from useradmin.forms import AddProductForm
from useradmin.decorators import admin_required
from .models import DashboardAnalytics

import datetime


@admin_required
def dashboard(request):
    vendor = Vendor.objects.get(user=request.user)
    
    products = Product.objects.filter(vendor=vendor)
    order_items = CartOrderItems.objects.filter(product__in=products, order__paid_status=True)
    
    revenue = order_items.aggregate(price=Sum('total'))
    
    this_month = datetime.datetime.now().month
    monthly_order_items = order_items.filter(order__order_date__month=this_month)
    monthly_revenue = monthly_order_items.aggregate(price=Sum('total'))
    
    latest_orders_query = CartOrder.objects.filter(cartorderitems__product__vendor=vendor).distinct().order_by("-id")
    
    for order in latest_orders_query:
        vendor_items = order.cartorderitems_set.filter(product__vendor=vendor)
        order.vendor_total = vendor_items.aggregate(total=Sum('total'))['total'] or 0

    # Get users who have ordered from this vendor, and show the most recently registered ones.
    new_customers = User.objects.filter(cartorder__in=latest_orders_query).distinct().order_by("-id")[:6]
    
    all_categories = Category.objects.all()

    # Save analytics to database - now with vendor-specific data
    analytics = DashboardAnalytics(
        revenue=revenue["price"] if revenue["price"] is not None else Decimal("0.00"),
        orders_count=latest_orders_query.count(),
        products_count=products.count(),
        monthly_earning=monthly_revenue["price"]
        if monthly_revenue["price"] is not None
        else Decimal("0.00"),
    )
    analytics.save()

    context = {
        "monthly_revenue": monthly_revenue,
        "revenue": revenue,
        "all_products": products,
        "all_categories": all_categories,
        "new_customers": new_customers,
        "latest_orders": latest_orders_query,
        "total_orders_count": latest_orders_query,
    }
    return render(request, "useradmin/dashboard.html", context)


@admin_required
def products(request):
    vendor = Vendor.objects.get(user=request.user)
    
    # Start with all products for the vendor
    products_query = Product.objects.filter(vendor=vendor).order_by("-id")
    
    # Get the status from the request
    status = request.GET.get('status')
    
    # Filter by status if provided and valid
    if status in ['draft', 'disabled', 'in_review', 'published', 'rejected']:
        products_query = products_query.filter(product_status=status)

    context = {
        "products": products_query,
        "selected_status": status, # To keep the dropdown on the selected value
    }
    return render(request, "useradmin/products.html", context)


@admin_required
def add_product(request):
    if request.method == "POST":
        form = AddProductForm(request.POST, request.FILES)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.user = request.user
            new_form.vendor = Vendor.objects.get(user=request.user)
            new_form.save()
            form.save_m2m()
            return redirect("useradmin:products")
    else:
        form = AddProductForm()
    context = {"form": form}
    return render(request, "useradmin/add-product.html", context)


@admin_required
def edit_product(request, pid):
    product = Product.objects.get(pid=pid)
    if request.method == "POST":
        form = AddProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.user = request.user
            new_form.vendor = Vendor.objects.get(user=request.user)
            new_form.save()
            form.save_m2m()
            return redirect("useradmin:edit_product", product.pid)
    else:
        form = AddProductForm(instance=product)
    context = {
        "form": form,
        "product": product,
    }
    return render(request, "useradmin/edit-product.html", context)


def delete_product(request, pid):
    product = Product.objects.get(pid=pid)
    product.delete()
    return redirect("useradmin:products")


@admin_required
def orders(request):
    vendor = Vendor.objects.get(user=request.user)
    orders_query = CartOrder.objects.filter(cartorderitems__product__vendor=vendor).distinct().order_by("-id")

    search_query = request.GET.get('q')
    status_query = request.GET.get('status')

    if search_query:
        orders_query = orders_query.filter(
            Q(oid__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        ).distinct()

    if status_query == 'paid':
        orders_query = orders_query.filter(paid_status=True)
    elif status_query == 'not_paid':
        orders_query = orders_query.filter(paid_status=False)

    context = {
        "orders": orders_query,
        "search_query": search_query,
        "selected_status": status_query,
    }
    return render(request, "useradmin/orders.html", context)


def order_detail(request, id):
    order = CartOrder.objects.get(id=id)
    vendor = Vendor.objects.get(user=request.user)
    products = Product.objects.filter(vendor=vendor)
    order_items = CartOrderItems.objects.filter(order=order, product__in=products)
    context = {
        "order": order,
        "order_items": order_items,
    }
    return render(request, "useradmin/order_detail.html", context)


@csrf_exempt
def change_order_status(request, oid):
    order = CartOrder.objects.get(oid=oid)
    if request.method == "POST":
        status = request.POST.get("status")
        print("status =====", status)
        order.product_status = status
        order.save()
        messages.success(request, f"Order status change to {status}")

    return redirect("useradmin:order_detail", order.id)


@admin_required
def shop_page(request):
    vendor = Vendor.objects.get(user=request.user)
    products = Product.objects.filter(vendor=vendor)
    
    # Calculate revenue and sales for this vendor only
    order_items = CartOrderItems.objects.filter(product__in=products, order__paid_status=True)
    revenue = order_items.aggregate(price=Sum('total'))
    total_sales = order_items.aggregate(qty=Sum('qty'))

    context = {
        "products": products,
        "revenue": revenue,
        "total_sales": total_sales,
        "vendor": vendor,
    }
    return render(request, "useradmin/shop_page.html", context)


@admin_required
def reviews(request):
    vendor = Vendor.objects.get(user=request.user)
    products = Product.objects.filter(vendor=vendor)
    reviews = ProductReview.objects.filter(product__in=products)
    context = {
        "reviews": reviews,
    }
    return render(request, "useradmin/reviews.html", context)


@admin_required
def settings(request):
    vendor = Vendor.objects.get(user=request.user)

    if request.method == "POST":
        # Get data from the form
        title = request.POST.get("title")
        description = request.POST.get("description")
        address = request.POST.get("address")
        contact = request.POST.get("contact")
        chat_resp_time = request.POST.get("chat_resp_time")
        shipping_on_time = request.POST.get("shipping_on_time")
        authentic_rating = request.POST.get("authentic_rating")
        days_return = request.POST.get("days_return")
        warranty_period = request.POST.get("warranty_period")
        
        image = request.FILES.get("image")
        cover_image = request.FILES.get("cover_image")

        # Update vendor object
        vendor.title = title
        vendor.description = description
        vendor.address = address
        vendor.contact = contact
        vendor.chat_resp_time = chat_resp_time
        vendor.shipping_on_time = shipping_on_time
        vendor.authentic_rating = authentic_rating
        vendor.days_return = days_return
        vendor.warranty_period = warranty_period

        if image is not None:
            vendor.image = image
        if cover_image is not None:
            vendor.cover_image = cover_image
        
        vendor.save()
        messages.success(request, "Shop Settings Updated Successfully")
        return redirect("useradmin:settings")

    context = {
        "vendor": vendor,
    }
    return render(request, "useradmin/settings.html", context)


@admin_required
def change_password(request):
    user = request.user

    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_new_password = request.POST.get("confirm_new_password")

        if confirm_new_password != new_password:
            messages.error(request, "Confirm Password and New Password Does Not Match")
            return redirect("useradmin:change_password")

        if check_password(old_password, user.password):
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password Changed Successfully")
            return redirect("useradmin:change_password")
        else:
            messages.error(request, "Old password is not correct")
            return redirect("useradmin:change_password")

    return render(request, "useradmin/change_password.html")


# @admin_required
# def edit_product(request, pid):
#     product = Product.objects.get(pid=pid)

#     if request.method == "POST":
#         form = AddProductForm(request.POST, request.FILES, instance=product)
#         if form.is_valid():
#             new_form = form.save(commit=False)
#             new_form.save()
#             form.save_m2m()
#             return redirect("useradmin:dashboard-products")
#     else:
#         form = AddProductForm(instance=product)
#     context = {
#         'form':form,
#         'product':product,
#     }
#     return render(request, "useradmin/edit-products.html", context)

# @admin_required
# def delete_product(request, pid):
#     product = Product.objects.get(pid=pid)
#     product.delete()
#     return redirect("useradmin:dashboard-products")

# @admin_required
# def orders(request):
#     orders = CartOrder.objects.all()
#     context = {
#         'orders':orders,
#     }
#     return render(request, "useradmin/orders.html", context)

# @admin_required
# def order_detail(request, id):
#     order = CartOrder.objects.get(id=id)
#     order_items = CartOrderItems.objects.filter(order=order)
#     context = {
#         'order':order,
#         'order_items':order_items
#     }
#     return render(request, "useradmin/order_detail.html", context)

# @admin_required
# @csrf_exempt
# def change_order_status(request, oid):
#     order = CartOrder.objects.get(oid=oid)
#     if request.method == "POST":
#         status = request.POST.get("status")
#         print("status =======", status)
#         messages.success(request, f"Order status changed to {status}")
#         order.product_status = status
#         order.save()

#     return redirect("useradmin:order_detail", order.id)
