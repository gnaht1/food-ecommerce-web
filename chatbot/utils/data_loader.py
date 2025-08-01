# utils/data_loader.py
import os
import pandas as pd
import re
from django.conf import settings
from .gemini_client import load_dish_names, extract_keyword_only
from fuzzywuzzy import process


DATASET_PATH = os.path.join(settings.BASE_DIR, "data", "recipes.csv")
df_recipes = None


def load_recipes_data():
    """Tải dữ liệu từ file CSV"""
    global df_recipes
    try:
        # Log the file path being used
        print(f"Attempting to load CSV from: {DATASET_PATH}")

        # Verify if file exists
        if not os.path.exists(DATASET_PATH):
            print(f"Error: File not found at {DATASET_PATH}")
            return None

        # Check file size to ensure it's not empty
        if os.path.getsize(DATASET_PATH) == 0:
            print(f"Error: File at {DATASET_PATH} is empty")
            return None

        # Try loading CSV with multiple encoding options
        encodings = ["utf-8", "utf-8-sig", "latin1", "iso-8859-1"]
        for encoding in encodings:
            try:
                df_recipes = pd.read_csv(DATASET_PATH, encoding=encoding)
                print(f"Successfully loaded CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                print(f"Failed to load CSV with {encoding} encoding, trying next...")
            except pd.errors.EmptyDataError:
                print(f"Error: CSV file at {DATASET_PATH} is empty")
                return None
            except pd.errors.ParserError:
                print(f"Error: CSV file at {DATASET_PATH} is malformed or corrupted")
                return None
        else:
            print(f"Error: Could not load CSV with any encoding: {DATASET_PATH}")
            return None

        if df_recipes is None or df_recipes.empty:
            print(f"Error: Loaded DataFrame is empty or None")
            return None

        print(f"Đã tải dữ liệu từ {DATASET_PATH}: {len(df_recipes)} món ăn")
        print(f"Columns in CSV: {', '.join(df_recipes.columns)}")

        # Map column names to standardized names (case insensitive)
        column_mapping = {
            "title": [
                "Title",
                "title",
                "TÊN MÓN",
                "name",
                "dish_name",
                "ten",
            ],
            "ingredients": [
                "Cleaned_Ingredients",  # Prioritize Cleaned_Ingredients
                "Ingredients",
                "ingredients",
                "NGUYÊN LIỆU",
            ],
            "instructions": [
                "Instructions",
                "instructions",
                "CÁCH LÀM",
                "steps",
            ],
        }

        # Find the appropriate columns in the dataset
        actual_columns = {}
        for std_col, possible_names in column_mapping.items():
            for col_name in possible_names:
                if col_name in df_recipes.columns:
                    actual_columns[std_col] = col_name
                    print(f"Đã tìm thấy cột {std_col}: {col_name}")
                    break
            else:
                print(f"Cảnh báo: Không tìm thấy cột {std_col} trong CSV")

        # Check if we found the title column
        if "title" not in actual_columns:
            print("Lỗi: Không tìm được cột tên món ăn. Không thể tiếp tục.")
            return None

        # Rename columns for easier access
        df_recipes = df_recipes.rename(
            columns={
                actual_columns.get("title"): "title",
                actual_columns.get("ingredients", "ingredients"): "ingredients",
                actual_columns.get("instructions", "instructions"): "instructions",
            }
        )

        # Drop any empty rows in the title column
        df_recipes = df_recipes.dropna(subset=["title"])
        df_recipes = df_recipes[df_recipes["title"].astype(str).str.strip() != ""]

        # Ensure all columns are strings
        for col in ["title", "ingredients", "instructions"]:
            if col in df_recipes.columns:
                df_recipes[col] = df_recipes[col].astype(str)

        # Create a list of dish names
        all_dish_names = df_recipes["title"].tolist()

        # Show some sample data
        print(f"Sample dish names: {all_dish_names[:5]}")
        print(f"Total dishes after cleaning: {len(all_dish_names)}")

        # Load dish names into memory
        load_dish_names(all_dish_names)
        return df_recipes

    except Exception as e:
        print(f"Lỗi khi tải dữ liệu: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return None


def get_recipes_data():
    """Lazy loading - chỉ tải dữ liệu khi cần thiết"""
    global df_recipes
    if df_recipes is None:
        print("Dữ liệu chưa được tải, đang tải...")
        df_recipes = load_recipes_data()
    return df_recipes


def get_dish_details(dish_name):
    """Lấy thông tin chi tiết về món ăn từ tên món"""
    df_recipes = get_recipes_data()
    
    if df_recipes is None:
        return {"error": "Không thể tải dữ liệu món ăn"}

    try:
        # Clean input dish name
        dish_name_lower = dish_name.lower().strip()

        # Direct matching (không phân biệt hoa thường)
        matching_dishes = df_recipes[df_recipes["title"].str.lower() == dish_name_lower]

        # If direct match failed, try fuzzy matching
        if matching_dishes.empty:
            print(
                f"Không tìm thấy món '{dish_name_lower}' bằng so khớp chính xác, thử fuzzy matching"
            )
            return find_dish_fuzzy(dish_name)

        # Lấy thông tin của món đầu tiên tìm thấy
        dish = matching_dishes.iloc[0]

        result = {"title": dish["title"]}

        if "ingredients" in df_recipes.columns:
            result["ingredients"] = dish["ingredients"]

        if "instructions" in df_recipes.columns:
            result["instructions"] = dish["instructions"]

        return result

    except Exception as e:
        import traceback

        print(f"Lỗi khi tìm thông tin món ăn: {str(e)}")
        print(traceback.format_exc())
        return {"error": f"Lỗi khi tìm thông tin món ăn: {str(e)}"}


def find_dish_fuzzy(dish_name, threshold=70):
    """
    Tìm món ăn bằng fuzzy matching
    """
    df_recipes = get_recipes_data()
    
    if df_recipes is None:
        return None

    try:
        # Clean input dish name
        dish_name_clean = dish_name.lower().strip()

        # Get all dish names
        all_dishes = df_recipes["title"].tolist()

        # Find the best match
        match_result = process.extractOne(
            dish_name_clean, [d.lower() for d in all_dishes]
        )
        if not match_result:
            return {"not_found": True}

        match, score = match_result

        print(f"Fuzzy match: '{dish_name}' -> '{match}' (score: {score})")

        if score >= threshold:
            # Find the index of the match in our list
            match_index = [d.lower() for d in all_dishes].index(match)
            # Get the original dish name with proper casing
            original_match = all_dishes[match_index]

            # Find this dish in the dataframe
            dish = df_recipes.iloc[match_index]

            result = {"title": original_match}

            if "ingredients" in df_recipes.columns:
                result["ingredients"] = dish["ingredients"]

            if "instructions" in df_recipes.columns:
                result["instructions"] = dish["instructions"]

            return result
        else:
            return {"not_found": True}
    except Exception as e:
        import traceback

        print(f"Lỗi trong fuzzy matching: {str(e)}")
        print(traceback.format_exc())
        return {"error": f"Lỗi trong fuzzy matching: {str(e)}"}


def preview_data():
    df_recipes = get_recipes_data()
    
    if df_recipes is None:
        print("Không thể tải dữ liệu để xem trước")
        return

    print("\n=== PREVIEW OF RECIPE DATA ===")
    cols_to_show = ["title"]
    cols_to_show.extend(
        [c for c in ["ingredients", "instructions"] if c in df_recipes.columns]
    )

    sample_data = df_recipes[cols_to_show].head()
    for idx, row in sample_data.iterrows():
        print(f"\nMón #{idx + 1}: {row['title']}")
        if "ingredients" in cols_to_show:
            print(
                f"Nguyên liệu: {row['ingredients'][:100]}..."
                if len(row["ingredients"]) > 100
                else row["ingredients"]
            )
        if "instructions" in cols_to_show:
            print(
                f"Hướng dẫn: {row['instructions'][:100]}..."
                if len(row["instructions"]) > 100
                else row["instructions"]
            )


def get_alternative_dish(
    previous_dish=None,
    original_query=None,
    limit=10,
    min_similarity=40,
    max_similarity=75,
):
    """
    Tìm món ăn thay thế: Ưu tiên Fuzzy Match với TỪ KHÓA,
    sau đó là 'contains', cuối cùng là ngẫu nhiên.
    """
    df_recipes = get_recipes_data()
    
    if df_recipes is None:
        return {"error": "Không thể tải dữ liệu món ăn"}

    try:
        print(f"Query gốc: '{original_query}'")
        print(f"Món đã gợi ý trước đó: '{previous_dish}'")

        # 1. Trích xuất TỪ KHÓA chính từ query gốc
        keyword = extract_keyword_only(original_query)
        print(f"Từ khóa tìm kiếm (món khác): '{keyword}'")

        # 2. Lấy danh sách các món khả dụng (loại trừ món cũ)
        available_dishes_df = df_recipes[
            df_recipes["title"].str.lower() != previous_dish.lower()
        ]
        available_titles = available_dishes_df["title"].tolist()

        if not available_titles:
            return {"not_found": True}  # Không còn món nào khác

        chosen_dish_df = None

        # 3. Thử Fuzzy Matching (ưu tiên)
        # Sử dụng extractBests để tìm các món có tên tương tự từ khóa.
        # score_cutoff=75 nghĩa là chỉ lấy các món có độ tương đồng >= 75
        fuzzy_matches = process.extractBests(
            keyword, available_titles, score_cutoff=75, limit=15
        )
        print(f"Fuzzy matches (score >= 75): {fuzzy_matches}")

        potential_dishes_titles = [match[0] for match in fuzzy_matches]

        if potential_dishes_titles:
            print(f"Sử dụng Fuzzy matches.")
            # Lấy DataFrame tương ứng với các món tìm thấy
            chosen_dish_df = available_dishes_df[
                available_dishes_df["title"].isin(potential_dishes_titles)
            ]

        # 4. Nếu Fuzzy không có, thử str.contains
        if chosen_dish_df is None or chosen_dish_df.empty:
            print("Fuzzy không có kết quả phù hợp, thử str.contains.")
            filtered_dishes = available_dishes_df[
                available_dishes_df["title"]
                .str.lower()
                .str.contains(keyword.lower(), na=False)
            ]
            if filtered_dishes.empty and "ingredients" in available_dishes_df.columns:
                filtered_dishes = available_dishes_df[
                    available_dishes_df["ingredients"]
                    .str.lower()
                    .str.contains(keyword.lower(), na=False)
                ]
            if not filtered_dishes.empty:
                print("Sử dụng str.contains matches.")
                chosen_dish_df = filtered_dishes

        # 5. Nếu vẫn không có, chọn ngẫu nhiên
        if chosen_dish_df is None or chosen_dish_df.empty:
            print("str.contains không có kết quả, chọn ngẫu nhiên.")
            chosen_dish_df = available_dishes_df  # Dùng tất cả món còn lại

        # 6. Chọn một món từ danh sách đã lọc (hoặc ngẫu nhiên)
        dish = chosen_dish_df.sample(1).iloc[0]

        # 7. Trả về kết quả
        result = {"title": dish["title"]}
        if "ingredients" in df_recipes.columns:
            result["ingredients"] = str(dish["ingredients"])
        if "instructions" in df_recipes.columns:
            result["instructions"] = str(dish["instructions"])

        print(f"Đã chọn món thay thế: '{result['title']}'")
        return result

    except Exception as e:
        import traceback

        print(f"Lỗi khi tìm món ăn thay thế: {str(e)}")
        print(traceback.format_exc())
        return {"error": f"Lỗi khi tìm món ăn thay thế: {str(e)}"}


# Dữ liệu sẽ được tải khi cần thiết (lazy loading)
# để tránh làm chậm quá trình khởi động Django
