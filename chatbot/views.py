# chatbot/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import re
from fuzzywuzzy import process
from core.models import Product
from django.conf import settings

# Đảm bảo import đầy đủ các hàm cần thiết
from .utils.data_loader import (
    get_dish_details,
    get_alternative_dish,
)
from .utils.gemini_client import (
    get_gemini_suggestion,
    get_enhanced_dish_suggestion,
    extract_dish_name_from_query,
    is_asking_for_alternative,
)

# Biến lưu trữ session của người dùng
user_session_data = {}

MIN_SCORE = 60


def parse_ingredients(text):
    """
    Tìm đoạn chứa danh sách nguyên liệu sau từ 'chuẩn bị' hoặc dấu ':' rồi split bằng dấu phẩy.
    """
    m = re.search(r"chuẩn bị[:\-]\s*(.+?)(?:\.|$)", text, re.IGNORECASE)
    if not m:
        return []
    items = [i.strip() for i in m.group(1).split(",") if i.strip()]
    return items


def chatbot_view(request):
    return render(request, "chatbot/chat_interface.html")


@csrf_exempt
def get_chatbot_response(request):
    if request.method == "POST":
        # Đọc payload JSON trước để lấy message và session_id
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"reply": "Dữ liệu gửi lên không hợp lệ."}, status=400)
        user_msg = data.get("message", "").strip()
        clean_response = data.get("clean_response", False)
        session_id = data.get("session_id", "default")

        # Nếu không có message thì hỏi lại
        if not user_msg:
            return JsonResponse({"reply": "Bạn muốn hỏi về món ăn nào nhỉ?"})

        # 1) Nếu đang chờ 'ok' để thêm nguyên liệu vào cart
        pending = request.session.get("pending_ingredients")
        if pending and user_msg.lower() == "ok":
            cart = request.session.get("cart_data_obj", {})
            all_titles = list(Product.objects.values_list("title", flat=True))
            added = []
            for ing in pending:
                match, score = process.extractOne(ing, all_titles)
                if score >= MIN_SCORE:
                    prod = Product.objects.get(title=match)
                    # dùng URL từ Product.image hoặc fallback placeholder
                    if hasattr(prod, "image") and prod.image:
                        img_path = prod.image.url  # nếu là ImageField
                    else:
                        img_path = settings.STATIC_URL + "images/default_product.png"
                    img_url = request.build_absolute_uri(img_path)
                    cart[str(prod.id)] = {
                        "title": prod.title,
                        "qty": 1,
                        "price": str(prod.price),
                        "image": img_url,
                        "pid": prod.pid,
                    }
                    added.append(match)
            request.session["cart_data_obj"] = cart
            request.session.pop("pending_ingredients")
            return JsonResponse({"reply": f"Đã thêm vào giỏ: {', '.join(added)}."})
        # 2) Mặc định: xử lý gọi Gemini như trước
        try:
            data = json.loads(request.body)
            user_message_original = data.get("message", "").strip()
            clean_response = data.get("clean_response", False)
            session_id = data.get("session_id", "default")  # Lấy session ID
        except json.JSONDecodeError:
            return JsonResponse(
                {"reply": "Lỗi: Dữ liệu gửi lên không hợp lệ."}, status=400
            )

        if not user_message_original:
            return JsonResponse({"reply": "Bạn muốn hỏi về món ăn nào nhỉ?"})

        bot_reply = ""

        # In ra log để debug
        print(f"[CHAT] Câu hỏi người dùng: '{user_message_original}'")

        # Kiểm tra xem người dùng có yêu cầu món khác không
        if is_asking_for_alternative(user_message_original):
            # Lấy thông tin món trước đó và query gốc từ session
            previous_dish = user_session_data.get(session_id, {}).get("last_dish")
            original_query = user_session_data.get(session_id, {}).get("original_query")

            if previous_dish and original_query:
                print(f"[CHAT] Người dùng yêu cầu món khác thay cho '{previous_dish}'")
                print(f"[CHAT] Query gốc: '{original_query}'")

                # Tìm món thay thế với độ tương đồng thấp hơn
                dish_details = get_alternative_dish(
                    previous_dish=previous_dish,
                    original_query=original_query,
                    min_similarity=40,  # Độ tương đồng tối thiểu
                    max_similarity=75,  # Độ tương đồng tối đa
                )

                if "error" in dish_details:
                    bot_reply = dish_details["error"]
                    print(f"[CHAT] Lỗi khi tìm món thay thế: {bot_reply}")
                elif "not_found" in dish_details:
                    bot_reply = "Xin lỗi, tôi không tìm được món thay thế phù hợp."
                    print(f"[CHAT] Không tìm thấy món thay thế")
                elif "title" in dish_details:
                    print(f"[CHAT] Đã tìm thấy món thay thế: {dish_details['title']}")

                    # Lưu món ăn mới vào session
                    user_session_data[session_id]["last_dish"] = dish_details["title"]

                    # Xử lý format nguyên liệu và hướng dẫn giống như món thông thường
                    ingredients_text = ""
                    if "ingredients" in dish_details and dish_details["ingredients"]:
                        # Clean up the ingredients string
                        ingredients = str(dish_details["ingredients"])
                        ingredients = ingredients.replace("[", "").replace("]", "")
                        ingredients = ingredients.replace('"', "").replace("'", "")

                        ingredients_list = [
                            i.strip() for i in ingredients.replace(";", ",").split(",")
                        ]
                        ingredients_text = "\n".join(
                            [
                                f"• {ingredient.strip()}"
                                for ingredient in ingredients_list
                                if ingredient.strip()
                            ]
                        )

                    # Format instructions
                    instructions_text = ""
                    if "instructions" in dish_details and dish_details["instructions"]:
                        if isinstance(dish_details["instructions"], list):
                            instructions_text = "\n".join(
                                [
                                    f"{i + 1}. {step}"
                                    for i, step in enumerate(
                                        dish_details["instructions"]
                                    )
                                ]
                            )
                        else:
                            instructions = str(dish_details["instructions"])
                            for indicator in ["Bước ", "bước "]:
                                instructions = instructions.replace(
                                    indicator, "\n" + indicator
                                )
                            instructions_text = instructions

                    # Construct reply
                    bot_reply = (
                        f"Tôi đề xuất món **{dish_details['title']}** thay thế. Để nấu món này, bạn cần:\n\n"
                        f"**Nguyên liệu:**\n{ingredients_text}\n\n"
                        f"**Hướng dẫn thực hiện:**\n{instructions_text}"
                    )
            else:
                bot_reply = (
                    "Bạn muốn tôi gợi ý món gì? Hãy cho tôi biết loại món ăn bạn thích."
                )
        else:
            # Xử lý câu hỏi thông thường
            dish_to_search = extract_dish_name_from_query(user_message_original)

            if not dish_to_search:
                print(f"Không trích xuất được tên món ăn từ '{user_message_original}'.")
                bot_reply = "Xin lỗi, tôi chưa hiểu rõ bạn muốn hỏi về món ăn nào. Bạn có thể vui lòng cho biết tên món ăn cụ thể được không?"
            else:
                print(f"[CHAT] Tìm kiếm món: '{dish_to_search}'")
                dish_details = get_dish_details(dish_to_search)
                print(f"[CHAT] Kết quả tìm kiếm: {dish_details.keys()}")

                if "error" in dish_details:
                    bot_reply = dish_details["error"]
                    print(f"[CHAT] Lỗi: {bot_reply}")
                elif "not_found" in dish_details:
                    if dish_to_search.lower() == user_message_original.lower():
                        bot_reply = f"Xin lỗi, tôi không tìm thấy thông tin cho món '{dish_to_search}' trong cơ sở dữ liệu của mình."
                    else:
                        bot_reply = f"Xin lỗi, tôi không tìm thấy thông tin cho món '{dish_to_search}' (được hiểu từ câu '{user_message_original}') trong cơ sở dữ liệu của mình."
                    print(f"[CHAT] Không tìm thấy món: {bot_reply}")
                elif "title" in dish_details:
                    print(f"[CHAT] Tìm thấy món ăn: {dish_details['title']}")

                    # Lưu món ăn và truy vấn gốc vào session
                    if session_id not in user_session_data:
                        user_session_data[session_id] = {}
                    user_session_data[session_id]["last_dish"] = dish_details["title"]
                    user_session_data[session_id]["original_query"] = (
                        user_message_original
                    )

                    # Format ingredients với line breaks và lưu thẳng list vào session
                    ingredients_list = []
                    ingredients_text = ""
                    if "ingredients" in dish_details and dish_details["ingredients"]:
                        raw = str(dish_details["ingredients"])
                        raw = raw.strip("[]").replace("'", "").replace('"', "")
                        ingredients_list = [
                            i.strip()
                            for i in raw.replace(";", ",").split(",")
                            if i.strip()
                        ]
                        ingredients_text = "\n".join(
                            [f"• {i}" for i in ingredients_list]
                        )

                    # LƯU thẳng danh sách vào session để đợi 'ok'
                    if ingredients_list:
                        request.session["pending_ingredients"] = ingredients_list

                    # Format instructions với line breaks
                    instructions_text = ""
                    if "instructions" in dish_details and dish_details["instructions"]:
                        if isinstance(dish_details["instructions"], list):
                            instructions_text = "\n".join(
                                [
                                    f"{i + 1}. {step}"
                                    for i, step in enumerate(
                                        dish_details["instructions"]
                                    )
                                ]
                            )
                        else:
                            instructions = str(dish_details["instructions"])
                            for indicator in ["Bước ", "bước "]:
                                instructions = instructions.replace(
                                    indicator, "\n" + indicator
                                )
                            instructions_text = instructions

                    # Construct the final formatted reply
                    bot_reply = (
                        f"OK bạn! Để nấu món **{dish_details['title']}**, bạn cần:\n\n"
                        f"**Nguyên liệu:**\n{ingredients_text}\n\n"
                        f"**Hướng dẫn thực hiện:**\n{instructions_text}"
                    )
                    # hỏi user có muốn thêm cart không
                    if ingredients_list:
                        bot_reply += "\n\nBạn có muốn thêm những nguyên liệu này vào giỏ hàng không? (gõ 'ok' để thêm)"
                else:
                    bot_reply = f"Đã có lỗi xảy ra khi tìm thông tin món '{dish_to_search}'. Vui lòng thử lại."

        # Làm sạch kết quả trả về nếu được yêu cầu
        if clean_response and bot_reply:
            bot_reply = re.sub(r"[\[\]\'\"\{\}\(\)\\]", "", bot_reply)

        return JsonResponse({"reply": bot_reply, "session_id": session_id})

    return JsonResponse({"reply": "Yêu cầu không hợp lệ."}, status=400)


@csrf_exempt
def chat_endpoint(request):
    user_msg = request.POST.get("message", "").strip()
    # bước 1: nếu đang chờ 'ok' để add cart
    pending = request.session.get("pending_ingredients")
    if pending and user_msg.lower() == "ok":
        added = []
        cart = request.session.get("cart_data_obj", {})
        # lấy toàn bộ title product để fuzzy match
        all_titles = list(Product.objects.values_list("title", flat=True))
        for ing in pending:
            match, score = process.extractOne(ing, all_titles)
            if score >= MIN_SCORE:
                prod = Product.objects.get(title=match)
                # dùng URL từ Product.image hoặc fallback placeholder
                if hasattr(prod, "image") and prod.image:
                    img_path = prod.image.url
                else:
                    img_path = settings.STATIC_URL + "images/default_product.png"
                img_url = request.build_absolute_uri(img_path)
                cart[str(prod.id)] = {
                    "title": prod.title,
                    "qty": 1,
                    "price": str(prod.price),
                    "image": img_url,
                    "pid": prod.pid,
                }
                added.append(match)
        request.session["cart_data_obj"] = cart
        # xóa pending
        request.session.pop("pending_ingredients")
        return JsonResponse({"reply": f"Đã thêm vào giỏ: {', '.join(added)}."})
    # bước 2: gọi Gemini để trả lời bình thường
    # giả sử bạn có 2 param dish_name_from_dataset, ingredients_list_str từ bước tìm dataset
    dish_name = request.POST.get("dish_name", "")
    ing_str = request.POST.get("ingredients_list_str", "")
    suggestion = get_enhanced_dish_suggestion(user_msg, dish_name, ing_str)
    # tách nguyên liệu
    ings = parse_ingredients(suggestion)
    if ings:
        # lưu vào session và hỏi thêm
        request.session["pending_ingredients"] = ings
        suggestion += "\n\nBạn có muốn thêm những nguyên liệu này vào giỏ hàng không? (gõ 'ok' để thêm)"
    return JsonResponse({"reply": suggestion})
