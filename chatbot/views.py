# chatbot/views.py
import json
import re

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from core.models import Product

from .utils.gemini_client import get_enhanced_dish_suggestion, get_grounded_rag_answer
from .utils.rag_engine import (
    MIN_RECIPE_SCORE,
    build_context,
    deterministic_recipe_reply,
    is_alternative_request,
    match_products_for_ingredients,
    retrieve_products,
    retrieve_recipes,
)


def parse_ingredients(text):
    """Extract ingredients from the old Gemini response shape used by chat_endpoint."""
    match = re.search(r"chuẩn bị[:\-]\s*(.+?)(?:\.|$)", text, re.IGNORECASE)
    if not match:
        return []
    return [item.strip() for item in match.group(1).split(",") if item.strip()]


def chatbot_view(request):
    return render(request, "chatbot/chat_interface.html")


def _get_product_image_url(request, product):
    image_path = product.image.url if getattr(product, "image", None) else settings.STATIC_URL + "images/default_product.png"
    return request.build_absolute_uri(image_path)


def _cart_item_from_product(request, product):
    return {
        "title": product.title,
        "qty": 1,
        "price": str(product.price),
        "image": _get_product_image_url(request, product),
        "pid": str(product.pid),
    }


def _add_pending_products_to_cart(request):
    pending_ids = request.session.get("pending_product_ids", [])
    missing = request.session.get("pending_missing_ingredients", [])
    if not pending_ids:
        request.session.pop("pending_ingredients", None)
        request.session.pop("pending_missing_ingredients", None)
        return "Hiện chưa có sản phẩm phù hợp để thêm vào giỏ hàng."

    cart = request.session.get("cart_data_obj", {})
    products = Product.objects.filter(id__in=pending_ids)
    product_by_id = {product.id: product for product in products}
    added = []

    for product_id in pending_ids:
        product = product_by_id.get(product_id)
        if not product:
            continue
        key = str(product.id)
        if key in cart:
            cart[key]["qty"] = int(cart[key].get("qty", 1)) + 1
        else:
            cart[key] = _cart_item_from_product(request, product)
        added.append(product.title)

    request.session["cart_data_obj"] = cart
    request.session.pop("pending_ingredients", None)
    request.session.pop("pending_product_ids", None)
    request.session.pop("pending_missing_ingredients", None)
    request.session.modified = True

    if not added:
        return "Tôi không tìm thấy sản phẩm phù hợp để thêm vào giỏ hàng."

    reply = f"Đã thêm vào giỏ: {', '.join(added)}."
    if missing:
        reply += f" Chưa thêm được: {', '.join(missing[:10])}."
    return reply


def _session_key(session_id, suffix):
    return f"chatbot_{session_id}_{suffix}"


def _generate_rag_reply(user_message, recipe_results, product_results, product_matches, missing):
    recipe_context, product_context = build_context(recipe_results, product_results)
    try:
        return get_grounded_rag_answer(user_message, recipe_context, product_context)
    except Exception as exc:
        print(f"[CHAT] Gemini unavailable, using deterministic RAG fallback: {exc}")
        return deterministic_recipe_reply(
            recipe_results[0].item,
            product_matches=product_matches,
            missing=missing,
        )


@csrf_exempt
def get_chatbot_response(request):
    if request.method != "POST":
        return JsonResponse({"reply": "Yêu cầu không hợp lệ."}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"reply": "Dữ liệu gửi lên không hợp lệ."}, status=400)

    user_message = data.get("message", "").strip()
    clean_response = data.get("clean_response", False)
    session_id = data.get("session_id") or request.session.session_key or "default"

    if not user_message:
        return JsonResponse({"reply": "Bạn muốn hỏi về món ăn nào nhỉ?", "session_id": session_id})

    if user_message.lower() == "ok":
        return JsonResponse({"reply": _add_pending_products_to_cart(request), "session_id": session_id})

    excluded_titles = request.session.get(_session_key(session_id, "suggested_titles"), [])
    original_query = request.session.get(_session_key(session_id, "original_query"), user_message)
    retrieval_query = original_query if is_alternative_request(user_message) else user_message
    exclusions = excluded_titles if is_alternative_request(user_message) else []

    recipe_results = retrieve_recipes(retrieval_query, excluded_titles=exclusions)
    if not recipe_results or recipe_results[0].score < MIN_RECIPE_SCORE:
        reply = "Xin lỗi, tôi chưa có đủ thông tin trong dữ liệu món ăn để trả lời câu hỏi này."
        return JsonResponse({"reply": reply, "session_id": session_id})

    selected_recipe = recipe_results[0].item
    ingredients = selected_recipe.get("ingredients_list", [])
    product_results = retrieve_products(" ".join([retrieval_query, *ingredients]))
    product_matches, missing = match_products_for_ingredients(ingredients)

    request.session["pending_ingredients"] = ingredients
    request.session["pending_product_ids"] = [match["product"]["id"] for match in product_matches]
    request.session["pending_missing_ingredients"] = missing
    request.session[_session_key(session_id, "original_query")] = original_query if is_alternative_request(user_message) else user_message
    request.session[_session_key(session_id, "suggested_titles")] = [*excluded_titles, selected_recipe["title"]][-20:]
    request.session[_session_key(session_id, "last_recipe")] = selected_recipe["title"]
    request.session.modified = True

    reply = _generate_rag_reply(user_message, recipe_results, product_results, product_matches, missing)
    if clean_response and reply:
        reply = re.sub(r"[\[\]\'\"{}()\\]", "", reply)

    return JsonResponse({"reply": reply, "session_id": session_id})


@csrf_exempt
def chat_endpoint(request):
    user_msg = request.POST.get("message", "").strip()
    if request.session.get("pending_product_ids") and user_msg.lower() == "ok":
        return JsonResponse({"reply": _add_pending_products_to_cart(request)})

    dish_name = request.POST.get("dish_name", "")
    ing_str = request.POST.get("ingredients_list_str", "")
    suggestion = get_enhanced_dish_suggestion(user_msg, dish_name, ing_str)
    ingredients = parse_ingredients(suggestion)
    if ingredients:
        product_matches, missing = match_products_for_ingredients(ingredients)
        request.session["pending_ingredients"] = ingredients
        request.session["pending_product_ids"] = [match["product"]["id"] for match in product_matches]
        request.session["pending_missing_ingredients"] = missing
        suggestion += "\n\nBạn có muốn thêm những nguyên liệu này vào giỏ hàng không? (gõ 'ok' để thêm)"
    return JsonResponse({"reply": suggestion})
