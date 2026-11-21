"""
Product Service for Skincare AI.
Handles external product integration with Open Beauty Facts, persistent product caching,
barcode lookup, categorization, and ingredient analysis.
"""

import json
import os
import re
import requests
from datetime import datetime
from db import execute_query, is_postgres

OPEN_BEAUTY_FACTS_SEARCH = "https://world.openbeautyfacts.org/api/v2/search"
OPEN_BEAUTY_FACTS_PRODUCT = "https://world.openbeautyfacts.org/api/v2/product/"

HEADERS = {
    "User-Agent": "SkincareAI/2.0 (Skincare Research Platform; educational-research)"
}


def calculate_completeness(name, brand, ingredients, image, barcode):
    """Calculate data completeness score from 0 to 100%."""
    score = 0
    if name and len(name.strip()) > 2:
        score += 20
    if brand and brand != "Brand not listed":
        score += 20
    if ingredients and len(ingredients.strip()) > 10 and "not listed" not in ingredients.lower():
        score += 35
    if image and image.startswith("http"):
        score += 15
    if barcode:
        score += 10
    return min(100, score)


def categorize_product(name, categories_tags=None, ingredients=""):
    """Accurately categorize a skincare product into standard categories."""
    combined = f"{name} {' '.join(categories_tags or [])} {ingredients}".lower()
    
    if any(k in combined for k in ["sunscreen", "sun protection", "suncare", "spf", "sun block", "uv "]):
        return "Sunscreen"
    elif any(k in combined for k in ["cleanser", "face wash", "cleansing gel", "cleansing foam", "micellar"]):
        return "Cleanser"
    elif any(k in combined for k in ["moisturizer", "moisturiser", "face cream", "hydrating cream", "gel cream", "day cream", "night cream"]):
        return "Moisturizer"
    elif any(k in combined for k in ["serum", "ampoule", "concentrate", "booster", "drop"]):
        return "Serum"
    elif any(k in combined for k in ["toner", "astringent", "essence", "clarifying lotion"]):
        return "Toner"
    elif any(k in combined for k in ["eye cream", "eye serum", "eye gel"]):
        return "Eye Cream"
    elif any(k in combined for k in ["exfoliant", "peel", "scrub", "aha", "bha"]):
        return "Exfoliant"
    elif any(k in combined for k in ["mask", "sheet mask", "clay mask"]):
        return "Face Mask"
    else:
        return "Skincare Treatment"


def deduce_skin_types(ingredients, category):
    """Estimate skin type suitability based on ingredient markers."""
    ing_lower = str(ingredients).lower()
    types = []
    
    # Oily
    if any(k in ing_lower for k in ["salicylic", "niacinamide", "zinc", "tea tree", "witch hazel"]) or category == "Cleanser":
        types.append("Oily")
    # Dry
    if any(k in ing_lower for k in ["hyaluronic", "ceramide", "glycerin", "shea butter", "squalane", "panthenol"]):
        types.append("Dry")
    # Combination
    types.append("Combination")
    # Sensitive
    if any(k in ing_lower for k in ["centella", "cica", "aloe", "allantoin", "colloidal oatmeal"]):
        types.append("Sensitive")
    # Normal
    types.append("Normal")
    
    return types


def seed_products_if_needed():
    """Seed the database from external_products_cleaned.json if products table is empty."""
    res = execute_query("SELECT COUNT(*) as cnt FROM products", fetchone=True)
    count = res["cnt"] if res else 0
    if count >= 50:
        return count

    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "external_products_cleaned.json")
    if not os.path.exists(json_path):
        return count

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_items = json.load(f)
    except Exception as e:
        print("Could not load external_products_cleaned.json:", e)
        return count

    print(f"Seeding {len(raw_items)} external products into database...")
    seeded = 0
    for item in raw_items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        
        brand = (item.get("brand") or "Brand not listed").strip()
        barcode = str(item.get("barcode") or "").strip()
        product_id = barcode or f"{brand.lower().replace(' ', '-')}-{name.lower().replace(' ', '-')}"[:60]
        
        # Clean product_id
        product_id = re.sub(r"[^a-zA-Z0-9_-]", "", product_id) or f"prod-{seeded+1}"
        
        ingredients = item.get("ingredients") or "Not listed"
        categories = item.get("categories") or []
        category = categorize_product(name, categories, ingredients)
        image = item.get("image") or ""
        source_url = item.get("source_url") or ""
        source = item.get("source") or "Open Beauty Facts"
        skin_types = item.get("skin_types") or deduce_skin_types(ingredients, category)
        skin_types_str = ",".join(skin_types) if isinstance(skin_types, list) else str(skin_types)
        price_inr = item.get("price_inr")
        rating = item.get("rating")
        score = calculate_completeness(name, brand, ingredients, image, barcode)

        try:
            execute_query("""
                INSERT INTO products (
                    id, name, brand, category, barcode, product_size, ingredients_text,
                    description, skin_types, image_url, source_url, source_provider,
                    source_product_id, country, price_inr, rating, completeness_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO NOTHING
            """, [
                product_id, name, brand, category, barcode, "", ingredients,
                "", skin_types_str, image, source_url, source,
                barcode, "India/International", price_inr, rating, score
            ])
            seeded += 1
        except Exception as exc:
            pass

    print(f"Successfully seeded {seeded} external products into persistent database.")
    return seeded


def save_or_update_product(data):
    """Save an externally retrieved product record into the database."""
    name = (data.get("name") or "").strip()
    if not name:
        return None
    
    brand = (data.get("brand") or "Brand not listed").strip()
    barcode = str(data.get("barcode") or "").strip()
    product_id = barcode or re.sub(r"[^a-zA-Z0-9_-]", "", f"{brand}-{name}".lower().replace(" ", "-"))[:60]
    
    ingredients = data.get("ingredients") or "Not listed"
    category = data.get("category") or categorize_product(name, data.get("categories_tags"), ingredients)
    image = data.get("image") or ""
    source_url = data.get("source_url") or data.get("product_url") or ""
    source_provider = data.get("source") or data.get("source_provider") or "Open Beauty Facts"
    skin_types = data.get("skin_types") or deduce_skin_types(ingredients, category)
    skin_types_str = ",".join(skin_types) if isinstance(skin_types, list) else str(skin_types)
    price_inr = data.get("price_inr")
    rating = data.get("rating")
    score = calculate_completeness(name, brand, ingredients, image, barcode)

    execute_query("""
        INSERT INTO products (
            id, name, brand, category, barcode, product_size, ingredients_text,
            description, skin_types, image_url, source_url, source_provider,
            source_product_id, country, price_inr, rating, completeness_score,
            last_updated, last_verified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            brand = EXCLUDED.brand,
            category = EXCLUDED.category,
            ingredients_text = EXCLUDED.ingredients_text,
            image_url = CASE WHEN EXCLUDED.image_url != '' THEN EXCLUDED.image_url ELSE products.image_url END,
            source_url = EXCLUDED.source_url,
            completeness_score = EXCLUDED.completeness_score,
            last_updated = CURRENT_TIMESTAMP
    """, [
        product_id, name, brand, category, barcode, data.get("product_size", ""),
        ingredients, data.get("description", ""), skin_types_str, image,
        source_url, source_provider, barcode, data.get("country", "India/International"),
        price_inr, rating, score
    ])
    
    return get_product_by_id(product_id)


def get_product_by_id(product_id):
    """Retrieve a single product by ID or barcode from database."""
    if not product_id:
        return None
    row = execute_query(
        "SELECT * FROM products WHERE id = ? OR barcode = ? LIMIT 1",
        [product_id, product_id],
        fetchone=True
    )
    if row:
        row["skin_types_list"] = [s.strip() for s in (row.get("skin_types") or "").split(",") if s.strip()]
    return row


def search_local_products(query="", category="", brand="", skin_type="", limit=50):
    """Search products already cached in persistent database."""
    where = []
    params = []
    
    if query and query.strip():
        q = f"%{query.strip()}%"
        where.append("(name LIKE ? OR brand LIKE ? OR ingredients_text LIKE ? OR barcode = ?)")
        params.extend([q, q, q, query.strip()])
        
    if category and category.lower() != "all":
        where.append("category = ?")
        params.append(category)
        
    if brand and brand.lower() != "all":
        where.append("brand LIKE ?")
        params.append(f"%{brand}%")
        
    if skin_type and skin_type.lower() != "all":
        where.append("skin_types LIKE ?")
        params.append(f"%{skin_type}%")
        
    sql = "SELECT * FROM products"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY completeness_score DESC, rating DESC NULLS LAST LIMIT ?"
    
    if not is_postgres():
        sql = sql.replace(" NULLS LAST", "")
        
    params.append(limit)
    rows = execute_query(sql, params, fetchall=True)
    for r in rows:
        r["skin_types_list"] = [s.strip() for s in (r.get("skin_types") or "").split(",") if s.strip()]
    return rows


def fetch_open_beauty_facts_by_barcode(barcode):
    """Query Open Beauty Facts API by exact barcode."""
    barcode = str(barcode).strip()
    if not barcode:
        return None
    
    url = f"{OPEN_BEAUTY_FACTS_PRODUCT}{barcode}.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == 1 and "product" in data:
                p = data["product"]
                norm = {
                    "barcode": barcode,
                    "name": p.get("product_name") or p.get("product_name_en") or "Unknown Product",
                    "brand": p.get("brands") or "Brand not listed",
                    "ingredients": p.get("ingredients_text") or p.get("ingredients_text_en") or "Not listed",
                    "categories_tags": p.get("categories_tags") or [],
                    "image": p.get("image_front_url") or p.get("image_url") or "",
                    "source_url": f"https://world.openbeautyfacts.org/product/{barcode}",
                    "source": "Open Beauty Facts",
                    "product_size": p.get("quantity") or ""
                }
                return save_or_update_product(norm)
    except Exception as exc:
        print(f"Open Beauty Facts barcode lookup error for {barcode}: {exc}")
    
    return None


def fetch_open_beauty_facts_search(search_term, limit=10):
    """Live search Open Beauty Facts API and persist results to database."""
    if not search_term or len(search_term.strip()) < 2:
        return []
    
    params = {
        "search_terms": search_term.strip(),
        "page_size": limit,
        "json": True,
        "fields": "code,product_name,brands,ingredients_text,image_front_url,url,categories_tags,quantity"
    }
    
    saved_products = []
    try:
        resp = requests.get(OPEN_BEAUTY_FACTS_SEARCH, params=params, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            for p in data.get("products", []):
                name = (p.get("product_name") or "").strip()
                if not name:
                    continue
                norm = {
                    "barcode": p.get("code") or "",
                    "name": name,
                    "brand": p.get("brands") or "Brand not listed",
                    "ingredients": p.get("ingredients_text") or "Not listed",
                    "categories_tags": p.get("categories_tags") or [],
                    "image": p.get("image_front_url") or "",
                    "source_url": p.get("url") or (f"https://world.openbeautyfacts.org/product/{p.get('code')}" if p.get('code') else ""),
                    "source": "Open Beauty Facts",
                    "product_size": p.get("quantity") or ""
                }
                prod = save_or_update_product(norm)
                if prod:
                    saved_products.append(prod)
    except Exception as exc:
        print(f"Open Beauty Facts live search error for '{search_term}': {exc}")
    
    return saved_products


def get_product_by_barcode(barcode):
    """Retrieve product by barcode from local DB or fetch from Open Beauty Facts."""
    if not barcode:
        return None
    row = execute_query("SELECT * FROM products WHERE barcode = ? LIMIT 1", [str(barcode).strip()], fetchone=True)
    if row:
        row["skin_types_list"] = [s.strip() for s in (row.get("skin_types") or "").split(",") if s.strip()]
        return row
    return fetch_open_beauty_facts_by_barcode(barcode)


# Aliases for unified product access
search_products = search_local_products
