
import requests

API_URL = "https://world.openbeautyfacts.org/api/v2/search"

params = {
    "categories_tags_en": "sunscreens",
    "page_size": 5,
    "json": True
}

headers = {
    "User-Agent": "SkincareAI/1.0 (educational project)"
}

try:
    response = requests.get(
        API_URL,
        params=params,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()
    data = response.json()

    products = data.get("products", [])

    print("API connected successfully!")
    print("Products found:", len(products))
    print("-" * 40)

    for product in products:
        print("Name:", product.get("product_name", "Unknown"))
        print("Brand:", product.get("brands", "Unknown"))
        print("Ingredients:", product.get("ingredients_text", "Not available"))
        print("Image:", product.get("image_url", "Not available"))
        print("-" * 40)

except requests.RequestException as error:
    print("API request failed:", error)

except ValueError:
    print("The API did not return valid JSON.")
