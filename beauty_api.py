
import requests

API_URL = "https://world.openbeautyfacts.org/api/v2/search"

HEADERS = {
    "User-Agent": "SkincareAI/1.0 (educational project)"
}


def search_beauty_products(search_term, limit=12):
    """Search Open Beauty Facts and return cleaned product details."""

    if not search_term or not search_term.strip():
        return []

    params = {
        "search_terms": search_term.strip(),
        "page_size": limit,
        "json": True,
        "fields": (
            "product_name,brands,ingredients_text,"
            "image_front_url,url,categories_tags,code"
        )
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            headers=HEADERS,
            timeout=20
        )
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get("products", []):
            name = (item.get("product_name") or "").strip()

            # Skip records without a product name.
            if not name:
                continue

            results.append({
                "name": name,
                "brand": item.get("brands") or "Brand not listed",
                "ingredients": (
                    item.get("ingredients_text")
                    or "Ingredients not available"
                ),
                "image": (
                    item.get("image_front_url")
                    or item.get("image_url")
                    or ""
                ),
                "product_url": item.get("url") or "",
                "barcode": item.get("code") or "",
                "source": "Open Beauty Facts"
            })

        return results

    except (requests.RequestException, ValueError) as error:
        print("OPEN BEAUTY FACTS ERROR:", error)
        return []
