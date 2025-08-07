from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from django.db import models

from taggit.models import Tag
from core.models import (
    Coupon,
    Product,
    Category,
    Vendor,
    CartOrder,
    CartOrderItems,
    ProductImages,
    ProductReview,
    Wishlist,
    Address,
)
from userauths.models import ContactUs, Profile  # Thay đổi import

from core.forms import ProductReviewForm
from django.template.loader import render_to_string
from django.contrib import messages


from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from paypal.standard.forms import PayPalPaymentsForm
from django.contrib.auth.decorators import login_required
import calendar
from django.db.models import Count, Avg, Min, Max
from django.db.models.functions import ExtractMonth
from django.core import serializers

import stripe
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm


# Create your views here.
def index(request):
    products = Product.objects.filter(product_status="published", featured=True)
    categories = Category.objects.all()

    # Lấy sản phẩm mới (tạo trong 30 ngày gần đây)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    new_products = Product.objects.filter(
        product_status="published", date__gte=thirty_days_ago
    ).order_by("-date")[:3]

    # Nếu không có sản phẩm mới, lấy 3 sản phẩm mới nhất
    if not new_products:
        new_products = Product.objects.filter(product_status="published").order_by(
            "-date"
        )[:3]

    # Lấy sản phẩm deals (sản phẩm có old_price > price, tức là có giảm giá)
    deals_products = (
        Product.objects.filter(product_status="published", old_price__gt=0)
        .exclude(old_price__lte=models.F("price"))
        .order_by("-date")[:4]
    )

    # Nếu không có deals, lấy 4 sản phẩm featured
    if not deals_products:
        deals_products = Product.objects.filter(
            product_status="published", featured=True
        ).order_by("-date")[:4]

    # Lấy min/max price
    min_max_price = Product.objects.aggregate(Min("price"), Max("price"))
    if not min_max_price["price__min"]:
        min_max_price = {"price__min": 0, "price__max": 1000}

    context = {
        "products": products,
        "categories": categories,
        "new_products": new_products,
        "deals_products": deals_products,
        "min_max_price": min_max_price,
    }
    return render(request, "core/index.html", context)


def product_list_view(request):
    try:
        products = Product.objects.filter(product_status="published")
        categories = Category.objects.all()
        vendors = Vendor.objects.all()

        # Lấy min/max price, xử lý trường hợp không có products
        min_max_price = Product.objects.aggregate(Min("price"), Max("price"))
        if not min_max_price["price__min"]:
            min_max_price = {"price__min": 0, "price__max": 1000}

        context = {
            "products": products,
            "categories": categories,
            "vendors": vendors,
            "min_max_price": min_max_price,
        }
        return render(request, "core/product-list.html", context)

    except Exception as e:
        print("Error in product_list_view:", str(e))
        # Fallback context
        context = {
            "products": Product.objects.none(),
            "categories": Category.objects.all(),
            "vendors": Vendor.objects.all(),
            "min_max_price": {"price__min": 0, "price__max": 1000},
        }
        return render(request, "core/product-list.html", context)


def category_list_view(request):
    categories = Category.objects.all()

    context = {"categories": categories}
    return render(request, "core/category-list.html", context)


def category_product_list_view(request, cid):
    category = Category.objects.get(cid=cid)
    products = Product.objects.filter(product_status="published", category=category)

    context = {
        "category": category,
        "products": products,
    }
    return render(request, "core/category-product-list.html", context)


def vendor_list_view(request):
    vendors = Vendor.objects.all()
    context = {
        "vendors": vendors,
    }
    return render(request, "core/vendor-list.html", context)


def vendor_detail_view(request, vid):
    vendor = Vendor.objects.get(vid=vid)
    products = Product.objects.filter(vendor=vendor, product_status="published")
    context = {
        "vendor": vendor,
        "products": products,
    }
    return render(request, "core/vendor-detail.html", context)


def product_detail_view(request, pid):
    product = Product.objects.get(pid=pid)
    products = Product.objects.filter(category=product.category).exclude(pid=pid)

    # Getting all reviews related to a product
    reviews = ProductReview.objects.filter(product=product).order_by("-date")

    # Getting average review
    average_rating = ProductReview.objects.filter(product=product).aggregate(
        rating=Avg("rating")
    )

    # Product review form
    review_form = ProductReviewForm()

    make_review = True

    if request.user.is_authenticated:
        user_review_count = ProductReview.objects.filter(
            user=request.user, product=product
        ).count()

        if user_review_count > 0:
            make_review = False

    p_image = product.p_images.all()

    address = None
    if request.user.is_authenticated:
        try:
            address = Address.objects.get(status=True, user=request.user)
        except Address.DoesNotExist:
            address = None

    context = {
        "p": product,
        "p_image": p_image,
        "review_form": review_form,
        "make_review": make_review,
        "reviews": reviews,
        "average_rating": average_rating,
        "products": products,
        "address": address,
    }
    return render(request, "core/product-detail.html", context)


def tag_list(request, tag_slug=None):
    products = Product.objects.filter(product_status="published").order_by("-id")

    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        products = products.filter(tags_in=[tag])

    context = {"products": products, "tag": tag}

    return render(request, "core/tag.html", context)


def ajax_add_review(request, pid):
    product = Product.objects.get(pk=pid)
    user = request.user

    review = ProductReview.objects.create(
        user=user,
        product=product,
        review=request.POST.get("review"),
        rating=request.POST.get("rating"),
    )

    context = {
        "user": user.username,
        "review": request.POST.get("review"),
        "rating": request.POST.get("rating"),
    }

    average_reviews = ProductReview.objects.filter(product=product).aggregate(
        rating=Avg("rating")
    )

    return JsonResponse(
        {
            "bool": True,
            "context": context,
            "average_reviews": average_reviews,
        }
    )


def search_view(request):
    query = request.GET.get("q")

    products = Product.objects.filter(title__icontains=query).order_by("-date")

    context = {
        "products": products,
        "query": query,
    }
    return render(request, "core/search.html", context)


def filter_product(request):
    categories = request.GET.getlist("category[]")
    vendors = request.GET.getlist("vendor[]")

    min_price = request.GET["min_price"]
    max_price = request.GET["max_price"]

    products = (
        Product.objects.filter(product_status="published").order_by("-id").distinct()
    )

    products = products.filter(price__gte=min_price)
    products = products.filter(price__lte=max_price)

    if len(categories) > 0:
        products = products.filter(category__id__in=categories).distinct()

    if len(vendors) > 0:
        products = products.filter(vendor__id__in=vendors).distinct()

    data = render_to_string("core/async/product-list.html", {"products": products})
    return JsonResponse({"data": data})


def filter_products(request):
    try:
        categories = request.GET.getlist("category[]") or request.GET.getlist(
            "category"
        )
        vendors = request.GET.getlist("vendor[]") or request.GET.getlist("vendor")
        min_price = request.GET.get("min_price")
        max_price = request.GET.get("max_price")
        conditions = request.GET.getlist("condition[]") or request.GET.getlist(
            "condition"
        )

        print(
            "Filter params:",
            {
                "categories": categories,
                "vendors": vendors,
                "min_price": min_price,
                "max_price": max_price,
                "conditions": conditions,
            },
        )

        products = Product.objects.filter(product_status="published").order_by("-id")

        # Filter by categories
        if categories:
            products = products.filter(category__id__in=categories)

        # Filter by vendors
        if vendors:
            products = products.filter(vendor__id__in=vendors)

        # Filter by price range
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)

        # Filter by conditions
        if conditions:
            if "new" in conditions:
                products = products.filter(
                    date__gte=datetime.now() - timedelta(days=30)
                )
            if "featured" in conditions:
                products = products.filter(featured=True)
            if "published" in conditions:
                products = products.filter(product_status="published")

        print(f"Filtered products count: {products.count()}")

        # Render filtered products HTML
        data = render_to_string("core/async/product-list.html", {"products": products})

        return JsonResponse({"data": data, "count": products.count()})

    except Exception as e:
        print("Error in filter_products:", str(e))
        return JsonResponse(
            {
                "error": str(e),
                "data": "<div class='col-12 text-center text-danger'>Error filtering products</div>",
            },
            status=500,
        )


@csrf_exempt
def add_to_cart(request):
    try:
        print("=== ADD TO CART DEBUG ===")
        print("Method:", request.method)

        # Lấy dữ liệu từ request
        product_id = request.GET.get("id")
        product_title = request.GET.get("title")
        product_qty = request.GET.get("qty", "1")
        product_price = request.GET.get("price")
        product_image = request.GET.get("image", "")
        product_pid = request.GET.get("pid", "")

        print(
            f"Received: id={product_id}, title={product_title}, price={product_price}, qty={product_qty}"
        )

        # Validate required fields
        if not all([product_id, product_title, product_price]):
            return JsonResponse(
                {"error": "Missing required fields", "success": False}, status=400
            )

        # Convert and validate price
        try:
            price_float = float(product_price)
            qty_int = int(product_qty)
        except (ValueError, TypeError):
            return JsonResponse(
                {"error": "Invalid price or quantity format", "success": False},
                status=400,
            )

        # Create cart product
        cart_product = {
            str(product_id): {
                "title": product_title,
                "qty": str(qty_int),
                "price": str(price_float),
                "image": product_image,
                "pid": product_pid,
            }
        }

        # Handle session cart
        if "cart_data_obj" in request.session:
            cart_data = request.session["cart_data_obj"]
            if str(product_id) in cart_data:
                # If product exists, set quantity to the new quantity (don't add to existing)
                cart_data[str(product_id)]["qty"] = str(qty_int)
            else:
                # Add new product
                cart_data.update(cart_product)
            request.session["cart_data_obj"] = cart_data
        else:
            # Create new cart
            request.session["cart_data_obj"] = cart_product

        # Ensure session is saved
        request.session.modified = True

        print("Cart updated successfully")

        return JsonResponse(
            {
                "data": request.session["cart_data_obj"],
                "totalcartitems": len(request.session["cart_data_obj"]),
                "success": True,
            }
        )

    except Exception as e:
        print("ERROR in add_to_cart:", str(e))
        import traceback

        traceback.print_exc()
        return JsonResponse(
            {"error": f"Server error: {str(e)}", "success": False}, status=500
        )


def cart_view(request):
    try:
        cart_total_amount = 0
        if "cart_data_obj" in request.session:
            cart_data = request.session["cart_data_obj"]
            for p_id, item in cart_data.items():
                price = float(item.get("price", 0))
                qty = int(item.get("qty", 1))
                item["subtotal"] = price * qty
                cart_total_amount += price * qty
        else:
            cart_data = {}

        context = {
            "cart_data": cart_data,
            "totalcartitems": len(cart_data) if cart_data else 0,
            "cart_total_amount": cart_total_amount,
        }
        return render(request, "core/cart.html", context)
    except Exception as e:
        print("Error in cart_view:", str(e))
        # Trả về trang cart với data rỗng thay vì lỗi
        context = {
            "cart_data": {},
            "totalcartitems": 0,
            "cart_total_amount": 0,
        }
        return render(request, "core/cart.html", context)


def delete_item_from_cart(request):
    product_id = str(request.GET["id"])
    if "cart_data_obj" in request.session:
        if product_id in request.session["cart_data_obj"]:
            cart_data = request.session["cart_data_obj"]
            del request.session["cart_data_obj"][product_id]
            request.session["cart_data_obj"] = cart_data

    cart_total_amount = 0
    if "cart_data_obj" in request.session:
        for p_id, item in request.session["cart_data_obj"].items():
            cart_total_amount += int(item["qty"]) * float(item["price"])

    context = render_to_string(
        "core/async/cart-list.html",
        {
            "cart_data": request.session["cart_data_obj"],
            "totalcartitems": len(request.session["cart_data_obj"]),
            "cart_total_amount": cart_total_amount,
        },
    )
    return JsonResponse(
        {"data": context, "totalcartitems": len(request.session["cart_data_obj"])}
    )


def update_cart(request):
    product_id = str(request.GET["id"])
    product_qty = str(request.GET["qty"])
    if "cart_data_obj" in request.session:
        if product_id in request.session["cart_data_obj"]:
            cart_data = request.session["cart_data_obj"]
            cart_data[str(request.GET["id"])]["qty"] = product_qty
            request.session["cart_data_obj"] = cart_data

    cart_total_amount = 0
    if "cart_data_obj" in request.session:
        for p_id, item in request.session["cart_data_obj"].items():
            price = float(item.get("price", 0))
            qty = int(item.get("qty", 1))
            item["subtotal"] = price * qty
            cart_total_amount += price * qty

    context = render_to_string(
        "core/async/cart-list.html",
        {
            "cart_data": request.session["cart_data_obj"],
            "totalcartitems": len(request.session["cart_data_obj"]),
            "cart_total_amount": cart_total_amount,
        },
    )
    return JsonResponse(
        {"data": context, "totalcartitems": len(request.session["cart_data_obj"])}
    )


def save_checkout_info(request):
    cart_total_amount = 0
    total_amount = 0

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("mobile")
        address = request.POST.get("address")
        city = request.POST.get("city")
        state = request.POST.get("state")
        country = request.POST.get("country")

        request.session["full_name"] = full_name
        request.session["email"] = email
        request.session["phone"] = phone
        request.session["address"] = address
        request.session["city"] = city
        request.session["state"] = state
        request.session["country"] = country

        # Checking if cart_data_obj session exists
        if "cart_data_obj" in request.session:
            # Getting total amount for Paypal Amount
            for p_id, item in request.session["cart_data_obj"].items():
                total_amount += int(item["qty"]) * float(item["price"])

            # Create ORder Object
            order = CartOrder.objects.create(
                user=request.user,
                price=total_amount,
                full_name=full_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                state=state,
                country=country,
            )

            del request.session["full_name"]
            del request.session["email"]
            del request.session["phone"]
            del request.session["address"]
            del request.session["city"]
            del request.session["state"]
            del request.session["country"]

            # Getting total amount for The Cart
            for p_id, item in request.session["cart_data_obj"].items():
                cart_total_amount += int(item["qty"]) * float(item["price"])

                cart_order_products = CartOrderItems.objects.create(
                    order=order,
                    product=Product.objects.get(pid=item["pid"]),
                    invoice_no="INVOICE_NO-" + str(order.id),  # INVOICE_NO-5,
                    item=item["title"],
                    image=item["image"],
                    qty=item["qty"],
                    price=item["price"],
                    total=float(item["qty"]) * float(item["price"]),
                )

        return redirect("core:checkout", order.oid)
    return redirect("core:checkout", order.oid)


def checkout(request, oid):
    order = CartOrder.objects.get(oid=oid)
    order_items = CartOrderItems.objects.filter(order=order)

    if request.method == "POST":
        code = request.POST.get("code")
        coupon = Coupon.objects.filter(code=code, active=True).first()
        if coupon:
            if coupon in order.coupons.all():
                messages.warning(request, "Coupon already applied")
                return redirect("core:checkout", order.oid)
            else:
                discount = order.price * coupon.discount / 100
                order.coupons.add(coupon)
                order.price -= discount
                order.saved += discount
                order.save()

                messages.success(request, "Coupon applied successfully")
                return redirect("core:checkout", order.oid)
        else:
            messages.error(request, "Coupon does not exist")
            return redirect("core:checkout", order.oid)

    context = {
        "order": order,
        "order_items": order_items,
        "stripe_publishable_key": settings.STRIPE_PUBLIC_KEY,
    }

    return render(request, "core/checkout.html", context)


@csrf_exempt
def create_checkout_session(request, oid):
    order = CartOrder.objects.get(oid=oid)
    stripe.api_key = settings.STRIPE_SECRET_KEY

    checkout_session = stripe.checkout.Session.create(
        customer_email=order.email,
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "USD",
                    "product_data": {
                        "name": order.full_name,
                    },
                    "unit_amount": int(order.price * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=request.build_absolute_uri(
            reverse("core:payment-completed", args=[order.oid])
            + "?session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=request.build_absolute_uri(reverse("core:payment-failed")),
    )

    order.paid_status = False
    order.stripe_payment_intent = checkout_session["id"]
    order.save()

    return JsonResponse({"session_id": checkout_session.id})


@login_required
def payment_completed_view(request, oid):
    order = CartOrder.objects.get(oid=oid)

    # Update order status if needed
    if not order.paid_status:
        order.paid_status = True
        order.save()

    context = {
        "order": order,
    }
    return render(request, "core/payment-completed.html", context)


@login_required
def payment_failed_view(request):
    return render(request, "core/payment-failed.html")


@login_required
def customer_dashboard(request):
    # Tạo profile nếu chưa có
    profile, created = Profile.objects.get_or_create(user=request.user)

    orders_list = CartOrder.objects.filter(user=request.user).order_by("-id")
    address = Address.objects.filter(user=request.user)

    orders = (
        CartOrder.objects.annotate(month=ExtractMonth("order_date"))
        .values("month")
        .annotate(count=Count("id"))
        .values("month", "count")
    )
    month = []
    total_orders = []

    for i in orders:
        month.append(calendar.month_name[i["month"]])
        total_orders.append(i["count"])

    if request.method == "POST":
        # Handle address addition
        if "address" in request.POST and "mobile" in request.POST:
            address_text = request.POST.get("address")
            mobile = request.POST.get("mobile")

            new_address = Address.objects.create(
                user=request.user,
                address=address_text,
                mobile=mobile,
            )
            messages.success(request, "Address added successfully")
            return redirect("core:dashboard")

        # Handle password change
        elif "current_password" in request.POST:
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            # Validate current password
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect("core:dashboard")

            # Validate new passwords match
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect("core:dashboard")

            # Validate password length
            if len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return redirect("core:dashboard")

            # Update password
            request.user.set_password(new_password)
            request.user.save()

            # Keep user logged in after password change
            update_session_auth_hash(request, request.user)

            messages.success(request, "Password changed successfully.")
            return redirect("core:dashboard")

    user_profile = profile

    context = {
        "user_profile": profile,
        "orders": orders,
        "orders_list": orders_list,
        "address": address,
        "month": month,
        "total_orders": total_orders,
    }
    return render(request, "core/dashboard.html", context)


def order_detail(request, id):
    order = CartOrder.objects.get(user=request.user, id=id)
    products = CartOrderItems.objects.filter(order=order)
    context = {
        "products": products,
    }
    return render(request, "core/order-detail.html", context)


def make_address_default(request):
    id = request.GET.get("id")
    Address.objects.update(status=False)
    Address.objects.filter(id=id).update(status=True)
    return JsonResponse({"boolean": True})


@login_required
def wishlist_view(request):
    wishlist = Wishlist.objects.filter(user=request.user)

    context = {
        "wishlist": wishlist,
    }
    return render(request, "core/wishlist.html", context)


def add_to_wishlist(request):
    product_id = request.GET["id"]
    product = Product.objects.get(id=product_id)

    context = {}

    wishlist_count = Wishlist.objects.filter(product=product, user=request.user).count()
    print(wishlist_count)

    if wishlist_count > 0:
        context = {"bool": True}
    else:
        new_wishlist = Wishlist.objects.create(
            user=request.user,
            product=product,
        )
        context = {"bool": True}

    return JsonResponse(context)


def remove_wishlist(request):
    pid = request.GET["id"]
    wishlist_items = Wishlist.objects.filter(user=request.user)
    wishlist_d = Wishlist.objects.get(id=pid)
    delete_product = wishlist_d.delete()

    context = {"bool": True, "w": wishlist_items}

    wishlist_json = serializers.serialize("json", wishlist_items)
    t = render_to_string("core/async/wishlist-list.html", context)
    return JsonResponse({"data": t, "w": wishlist_json})


# Other Pages
def contact(request):
    return render(request, "core/contact.html")


def ajax_contact_form(request):
    full_name = request.GET["full_name"]
    email = request.GET["email"]
    phone = request.GET["phone"]
    subject = request.GET["subject"]
    message = request.GET["message"]

    contact = ContactUs.objects.create(
        full_name=full_name,
        email=email,
        phone=phone,
        subject=subject,
        message=message,
    )

    data = {"bool": True, "message": "Message Sent Successfully"}

    return JsonResponse({"data": data})


def about_us(request):
    return render(request, "core/about_us.html")

def our_story(request):
    return render(request, "core/our_story.html")


def purchase_guide(request):
    return render(request, "core/purchase_guide.html")


def privacy_policy(request):
    return render(request, "core/privacy_policy.html")


def terms_of_service(request):
    return render(request, "core/terms_of_service.html")


@login_required
def checkout_initiate(request):
    """Create order from cart and redirect to checkout page"""
    if "cart_data_obj" not in request.session or not request.session["cart_data_obj"]:
        messages.error(request, "Your cart is empty")
        return redirect("core:cart")

    total_amount = 0

    # Calculate total amount
    for p_id, item in request.session["cart_data_obj"].items():
        total_amount += int(item["qty"]) * float(item["price"])

    # Get user's default address
    user_address = None
    try:
        user_address = Address.objects.get(user=request.user, status=True)
    except Address.DoesNotExist:
        # If no default address, try to get any address
        user_address = Address.objects.filter(user=request.user).first()

    # Create order with basic info
    order = CartOrder.objects.create(
        user=request.user,
        price=total_amount,
        full_name=request.user.get_full_name() or request.user.username,
        email=request.user.email or "",
        phone=user_address.mobile if user_address else "",
        address=user_address.address if user_address else "",
        city="",  # Set default empty values
        state="",
        country="",
    )

    # Create order items
    for p_id, item in request.session["cart_data_obj"].items():
        CartOrderItems.objects.create(
            order=order,
            product=Product.objects.get(pid=item["pid"]),
            invoice_no="INVOICE_NO-" + str(order.id),
            item=item["title"],
            image=item["image"],
            qty=item["qty"],
            price=item["price"],
            total=float(item["qty"]) * float(item["price"]),
        )

    # Clear cart after creating order
    del request.session["cart_data_obj"]
    request.session.modified = True

    return redirect("core:checkout", order.oid)


def clear_cart(request):
    if "cart_data_obj" in request.session:
        del request.session["cart_data_obj"]
        request.session.modified = True

    cart_total_amount = 0
    if "cart_data_obj" in request.session:
        for p_id, item in request.session["cart_data_obj"].items():
            cart_total_amount += int(item["qty"]) * float(item["price"])

    context = render_to_string(
        "core/async/cart-list.html",
        {
            "cart_data": request.session.get("cart_data_obj", {}),
            "totalcartitems": len(request.session.get("cart_data_obj", {})),
            "cart_total_amount": cart_total_amount,
        },
    )
    return JsonResponse(
        {
            "data": context,
            "totalcartitems": len(request.session.get("cart_data_obj", {})),
        }
    )
