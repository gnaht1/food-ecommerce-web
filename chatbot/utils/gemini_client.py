# utils/gemini_client.py (ví dụ)
import google.generativeai as genai
from django.conf import settings
import re
from fuzzywuzzy import process

genai.configure(api_key=settings.GOOGLE_API_KEY)

# Khởi tạo model
model = genai.GenerativeModel("gemini-1.5-flash-latest")

# Thêm biến toàn cục để lưu trữ danh sách món ăn
all_dish_names = []


def load_dish_names(dish_names):
    """
    Nạp danh sách tất cả tên món ăn từ database vào bộ nhớ
    """
    global all_dish_names
    all_dish_names = dish_names
    print(f"Đã nạp {len(all_dish_names)} tên món ăn vào bộ nhớ")


def get_gemini_suggestion(prompt_text):
    if not settings.GOOGLE_API_KEY:
        return "Lỗi: API Key của Google chưa được cấu hình."
    try:
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        print(f"Lỗi khi gọi Gemini API: {e}")
        return f"Xin lỗi, đã có lỗi xảy ra khi kết nối với AI: {e}"


def get_enhanced_dish_suggestion(
    user_input, dish_name_from_dataset, ingredients_list_str
):
    """
    Sử dụng Gemini để tạo câu trả lời tự nhiên hơn hoặc xử lý các trường hợp phức tạp.
    """
    if not ingredients_list_str or "không tìm thấy" in ingredients_list_str.lower():
        # Nếu dataset không có, hỏi Gemini xem nó có biết không
        prompt = f"""Người dùng muốn biết nguyên liệu cho món ăn: '{user_input}'.
        Trong bộ dữ liệu của tôi không có món này.
        Dựa trên kiến thức của bạn, bạn có thể gợi ý một vài nguyên liệu phổ biến cho món '{user_input}' được không?
        Nếu không biết, hãy nói rằng bạn không có thông tin."""
    else:
        # Dataset có thông tin, dùng Gemini để làm câu trả lời tự nhiên hơn
        prompt = f"""Người dùng muốn biết nguyên liệu cho món ăn: '{user_input}'.
        Dựa trên dữ liệu được cung cấp, nguyên liệu cho món '{dish_name_from_dataset}' là: {ingredients_list_str}.
        Hãy tạo một câu trả lời thân thiện và tự nhiên để gợi ý các nguyên liệu này cho người dùng.
        Ví dụ: 'Để nấu món {dish_name_from_dataset} thơm ngon, bạn sẽ cần chuẩn bị: [danh sách nguyên liệu]. Chúc bạn vào bếp thành công!'
        """
    return get_gemini_suggestion(prompt)


def find_closest_dish_match(dish_name, min_score=60):
    """
    Tìm món ăn có tên gần giống nhất với tên món được nhập

    Args:
        dish_name: Tên món ăn cần tìm
        min_score: Điểm tương đồng tối thiểu (0-100)

    Returns:
        Tên món ăn gần giống nhất hoặc rỗng nếu không tìm thấy
    """
    global all_dish_names

    if not dish_name or not all_dish_names:
        return ""

    # Tìm kiếm tên món ăn gần giống nhất
    match, score = process.extractOne(dish_name, all_dish_names)

    print(f"Tìm món gần đúng: '{dish_name}' -> '{match}' (score: {score})")

    if score >= min_score:
        return match
    return ""


def extract_dish_name_from_query(user_query, dish_titles_from_dataset=None):
    """
    Trích xuất tên món ăn từ câu truy vấn của người dùng.
    """
    # Cập nhật danh sách món ăn nếu được cung cấp
    global all_dish_names
    if dish_titles_from_dataset and not all_dish_names:
        all_dish_names = dish_titles_from_dataset

    # Làm sạch input
    clean_query = user_query.strip()

    try:
        if not model or not settings.GOOGLE_API_KEY:
            # Gemini không khả dụng, thử tìm trực tiếp từ câu hỏi
            print("Gemini không khả dụng, thử tìm gần đúng...")
            return find_closest_dish_match(clean_query)

        prompt = f"""
        Người dùng đã nhập câu sau: "{clean_query}".
        Hãy trích xuất tên món ăn chính mà người dùng có khả năng đang đề cập đến từ câu trên.
        Chỉ trả về tên món ăn đó, không thêm bất kỳ giải thích nào.
        Ví dụ:
        - Nếu người dùng nhập "tôi muốn ăn phở bò", chỉ trả về "phở bò".
        - Nếu người dùng nhập "cách làm món cá kho tộ", chỉ trả về "cá kho tộ".
        - Nếu người dùng nhập "bún chả", chỉ trả về "bún chả".
        - Nếu người dùng nhập "cho xin công thức món cơm sườn nướng", chỉ trả về "cơm sườn nướng".
        - Nếu không chắc chắn hoặc không thể trích xuất được tên món ăn rõ ràng, hãy trả về lại chính xác câu mà người dùng đã nhập.
        Tên món ăn cần trích xuất là:
        """

        response = model.generate_content(prompt)
        extracted_name = response.text.strip()

        # Xóa các dấu câu không cần thiết có thể Gemini trả về
        extracted_name = re.sub(
            r"[^\w\sàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]",
            "",
            extracted_name,
        )
        extracted_name = extracted_name.strip()

        print(f"Gemini trích xuất từ '{clean_query}' -> '{extracted_name}'")

        if (
            not extracted_name
            or len(extracted_name) < 2
            or extracted_name == clean_query
        ):
            # Gemini không trích xuất được cụ thể, thử tìm gần đúng trực tiếp
            return find_closest_dish_match(clean_query)

        # Tìm món ăn gần đúng từ tên món đã trích xuất
        matched_dish = find_closest_dish_match(extracted_name)
        if matched_dish:
            return matched_dish

        # Nếu vẫn không tìm được, trả về tên đã trích xuất
        return extracted_name

    except Exception as e:
        print(f"Lỗi khi trích xuất tên món ăn: {e}")
        # Thử phương pháp dự phòng
        return find_closest_dish_match(clean_query)


def is_asking_for_alternative(user_query):
    """Kiểm tra xem người dùng có đang yêu cầu món khác không"""
    user_query = user_query.lower()
    alternative_phrases = [
        "món khác",
        "món tương tự",
        "món thay thế",
        "một món khác",
        "món ăn khác",
        "thay thế",
        "gợi ý khác",
        "đổi món",
        "món gì khác",
        "không thích món này",
        "món nào khác",
        "có món nào khác",
    ]

    for phrase in alternative_phrases:
        if phrase in user_query:
            return True

    return False


def extract_keyword_only(user_query):
    """
    Trích xuất TỪ KHÓA chính (tên món/thành phần) từ câu truy vấn,
    không thực hiện fuzzy matching với danh sách món ăn đầy đủ.
    """
    clean_query = user_query.strip().lower()
    try:
        # Giả sử bạn có model và settings được cấu hình
        # Đây là phần gọi Gemini API (bạn có thể giữ nguyên từ bước trước)
        prompt = f"""
        Từ câu sau đây: "{clean_query}", hãy trích xuất TỪ KHÓA chính là tên món ăn hoặc thành phần chính.
        Chỉ trả về TỪ KHÓA đó, ngắn gọn nhất có thể. Ví dụ:
        - "tôi muốn ăn phở bò" -> "phở bò"
        - "cách làm cá kho tộ" -> "cá kho tộ"
        - "chicken" -> "chicken"
        - "cơm sườn" -> "cơm sườn"
        Nếu không chắc, trả về từ chính trong câu.
        Từ khóa:
        """
        response = model.generate_content(prompt)  # Giả sử model đã được khởi tạo
        extracted_keyword = response.text.strip()
        extracted_keyword = re.sub(
            r"[^\w\sàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]",
            "",
            extracted_keyword,
        ).strip()

        print(f"Gemini trích xuất TỪ KHÓA từ '{clean_query}' -> '{extracted_keyword}'")
        return extracted_keyword if extracted_keyword else clean_query

    except Exception as e:
        print(f"Lỗi khi trích xuất từ khóa: {e}")
        return clean_query  # Trả về câu gốc nếu lỗi
