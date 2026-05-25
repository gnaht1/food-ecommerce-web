import ast
import csv
import os
import re
from dataclasses import dataclass
from functools import lru_cache

from django.conf import settings
from fuzzywuzzy import process

from core.models import Product

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:  # pragma: no cover - handled at runtime for misconfigured envs.
    TfidfVectorizer = None
    cosine_similarity = None


RECIPE_TOP_K = 5
PRODUCT_TOP_K = 10
MIN_RECIPE_SCORE = 0.08
MIN_PRODUCT_SCORE = 0.05
MIN_FUZZY_SCORE = 60


@dataclass
class SearchResult:
    item: dict
    score: float


def _clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _parse_ingredients(value):
    text = _clean_text(value)
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (list, tuple)):
            return [_clean_text(item) for item in parsed if _clean_text(item)]
    except (ValueError, SyntaxError):
        pass
    return [item.strip(" -•") for item in re.split(r";|,\s+(?=[A-Za-z0-9¼½¾⅓⅔])", text) if item.strip()]


def _recipe_document(recipe):
    return " ".join(
        [
            recipe.get("title", ""),
            " ".join(recipe.get("ingredients_list", [])),
            recipe.get("ingredients", ""),
            recipe.get("instructions", ""),
        ]
    )


def _product_document(product):
    return " ".join(
        [
            product.get("title", ""),
            product.get("description", ""),
            product.get("category", ""),
            product.get("vendor", ""),
            product.get("type", ""),
        ]
    )


class TfidfIndex:
    def __init__(self, items, document_builder):
        self.items = items
        self.ready = bool(items) and TfidfVectorizer is not None and cosine_similarity is not None
        self.vectorizer = None
        self.matrix = None
        if self.ready:
            self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
            self.matrix = self.vectorizer.fit_transform([document_builder(item) for item in items])

    def search(self, query, limit, exclude_titles=None):
        if not self.ready or not query:
            return []
        excluded = {title.lower() for title in (exclude_titles or [])}
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix).flatten()
        ranked_indexes = scores.argsort()[::-1]
        results = []
        for idx in ranked_indexes:
            item = self.items[idx]
            if item.get("title", "").lower() in excluded:
                continue
            score = float(scores[idx])
            if score <= 0:
                break
            results.append(SearchResult(item=item, score=score))
            if len(results) >= limit:
                break
        return results


@lru_cache(maxsize=1)
def get_recipe_index():
    path = os.path.join(settings.BASE_DIR, "data", "recipes.csv")
    recipes = []
    with open(path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            title = _clean_text(row.get("Title") or row.get("title"))
            if not title:
                continue
            ingredients = _clean_text(row.get("Cleaned_Ingredients") or row.get("Ingredients"))
            recipes.append(
                {
                    "title": title,
                    "ingredients": ingredients,
                    "ingredients_list": _parse_ingredients(ingredients),
                    "instructions": _clean_text(row.get("Instructions")),
                }
            )
    return TfidfIndex(recipes, _recipe_document)


@lru_cache(maxsize=1)
def get_product_index():
    products = []
    queryset = (
        Product.objects.filter(product_status="published", status=True, in_stock=True)
        .select_related("category", "vendor")
        .only("id", "pid", "title", "description", "price", "image", "category__title", "vendor__title", "type")
    )
    for product in queryset:
        products.append(
            {
                "id": product.id,
                "pid": str(product.pid),
                "title": product.title,
                "description": _clean_text(product.description),
                "category": product.category.title if product.category else "",
                "vendor": product.vendor.title if product.vendor else "",
                "type": product.type or "",
                "price": str(product.price),
                "image": product.image.url if product.image else "",
            }
        )
    return TfidfIndex(products, _product_document)


def is_alternative_request(message):
    text = message.lower()
    phrases = [
        "another dish",
        "different dish",
        "something else",
        "other recipe",
        "món khác",
        "món tương tự",
        "món thay thế",
        "gợi ý khác",
        "đổi món",
        "món nào khác",
    ]
    return any(phrase in text for phrase in phrases)


def retrieve_recipes(query, excluded_titles=None, limit=RECIPE_TOP_K):
    return get_recipe_index().search(query, limit=limit, exclude_titles=excluded_titles)


def retrieve_products(query, limit=PRODUCT_TOP_K):
    return get_product_index().search(query, limit=limit)


def match_products_for_ingredients(ingredients):
    product_index = get_product_index()
    all_titles = [item["title"] for item in product_index.items]
    matches = []
    missing = []
    for ingredient in ingredients:
        result = product_index.search(ingredient, limit=1)
        if result and result[0].score >= MIN_PRODUCT_SCORE:
            matches.append({"ingredient": ingredient, "product": result[0].item, "score": result[0].score})
            continue
        fuzzy_match = process.extractOne(ingredient, all_titles) if all_titles else None
        if fuzzy_match and fuzzy_match[1] >= MIN_FUZZY_SCORE:
            product = product_index.items[all_titles.index(fuzzy_match[0])]
            matches.append({"ingredient": ingredient, "product": product, "score": fuzzy_match[1] / 100})
        else:
            missing.append(ingredient)
    return matches, missing


def build_context(recipe_results, product_results):
    recipe_lines = []
    for index, result in enumerate(recipe_results, start=1):
        recipe = result.item
        recipe_lines.append(
            "\n".join(
                [
                    f"Recipe {index}: {recipe['title']}",
                    f"Score: {result.score:.3f}",
                    f"Ingredients: {recipe['ingredients']}",
                    f"Instructions: {recipe['instructions']}",
                ]
            )
        )
    product_lines = [
        f"- {result.item['title']} (id={result.item['id']}, category={result.item.get('category', '')}, score={result.score:.3f})"
        for result in product_results
    ]
    return "\n\n".join(recipe_lines), "\n".join(product_lines)


def deterministic_recipe_reply(recipe, product_matches=None, missing=None, prefix="OK bạn!"):
    ingredients = recipe.get("ingredients_list") or _parse_ingredients(recipe.get("ingredients"))
    ingredients_text = "\n".join(f"• {ingredient}" for ingredient in ingredients) or recipe.get("ingredients", "")
    instructions = recipe.get("instructions", "")
    reply = (
        f"{prefix} Để nấu món **{recipe['title']}**, bạn cần:\n\n"
        f"**Nguyên liệu:**\n{ingredients_text}\n\n"
        f"**Hướng dẫn thực hiện:**\n{instructions}"
    )
    if product_matches:
        names = ", ".join(match["product"]["title"] for match in product_matches[:10])
        reply += f"\n\nTôi tìm thấy sản phẩm phù hợp trong cửa hàng: {names}."
    if missing:
        reply += f"\nMột số nguyên liệu chưa có sản phẩm phù hợp: {', '.join(missing[:10])}."
    if product_matches:
        reply += "\n\nBạn có muốn thêm các sản phẩm phù hợp vào giỏ hàng không? (gõ 'ok' để thêm)"
    return reply
