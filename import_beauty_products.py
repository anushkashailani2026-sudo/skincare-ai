
import json
import time
import requests

API_URL = "https://world.openbeautyfacts.org/cgi/search.pl"

SEARCH_TERMS = [
    "sunscreen",
    "face moisturizer",
    "face cream",
    "face cleanser",
    "face wash",
    "face serum",
    "niacinamide",
    "salicylic acid",
    "hyaluronic acid",
    "ceramide"
]

HEADERS = {
    "User-Agent": "SkincareAI/1.0 (educational project)"
}

# These terms help us avoid obvious irrelevant results.
EXCLUDE_TERMS = [
    "tissue", "douchegel", "shower gel", "body wash",
    "lubricant", "toothpaste", "shampoo", "conditioner",
    "deodorant", "perfume", "eye mask"
]

products_by_id = {}


def collect_products(search_term):
    params = {
        "search_terms": search_term,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 100,
        "fields": (
            "code,product_name,brands,ingredients_text,"
            "image_front_url,url,categories_tags"
        )
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        added = 0

        for item in data.get("products", []):
            name = (item.get("product_name") or "").strip()

            if not name:
                continue

            categories = item.get("categories_tags") or []
            searchable_text = (
                name + " " + " ".join(categories)
            ).lower()

            if any(term in searchable_text for term in EXCLUDE_TERMS):
                continue

            # Keep products with skincare-related names or categories.
            relevant_terms = [
                "skin", "face", "sunscreen", "sun screen",
                "sun protection", "moistur", "cream", "serum",
                "cleanser", "face wash", "niacinamide",
                "salicylic", "hyaluronic", "ceramide",
                "acne", "spf", "lotion", "gel"
            ]

            if not any(term in searchable_text for term in relevant_terms):
                continue

            brand = (item.get("brands") or "").strip()
            barcode = (item.get("code") or "").strip()

            product_id = (
                barcode or f"{brand.lower()}|{name.lower()}"
            )

            if product_id in products_by_id:
                continue

            products_by_id[product_id] = {
                "id": product_id,
                "name": name,
                "brand": brand or "Brand not listed",
                "ingredients": item.get("ingredients_text") or "",
                "image": item.get("image_front_url") or "",
                "source_url": item.get("url") or "",
                "categories": categories,
                "barcode": barcode,
                "searched_for": search_term,
                "source": "Open Beauty Facts",
                "price_inr": None,
                "rating": None,
                "skin_types": []
            }

            added += 1

        print(f"{search_term}: added {added} products")

    except (requests.RequestException, ValueError) as error:
        print(f"Could not fetch '{search_term}': {error}")


def main():
    print("Collecting skincare products...\n")

    for term in SEARCH_TERMS:
        collect_products(term)
        time.sleep(1)

    output_file = "external_products_v2.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(
            list(products_by_id.values()),
            file,
            ensure_ascii=False,
            indent=4
        )

    print("\nCollection finished.")
    print("Unique products saved:", len(products_by_id))
    print("Output file:", output_file)


if __name__ == "__main__":
    main()
