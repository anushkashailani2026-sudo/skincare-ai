"""
Vision and Image Analysis Service for Skincare AI.
Handles product packaging photo uploads, ingredient label OCR,
and product identification using Ollama Cloud vision model (gemma4:31b).
"""

import os
import io
import re
import json
import base64
import uuid
from PIL import Image
from ollama import Client
import product_service

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads", "temp_analysis")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "gemma4:31b")


def get_ollama_client():
    key = os.getenv("OLLAMA_API_KEY")
    if not key:
        return None
    return Client(host="https://ollama.com", headers={"Authorization": f"Bearer {key}"})


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_and_optimize_image(file_storage):
    """
    Validate, sanitize, and optimize uploaded product image.
    Returns relative web path and absolute disk path.
    """
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    if not file_storage or not file_storage.filename:
        return None, "No file provided"
    
    if not allowed_file(file_storage.filename):
        return None, "Unsupported file format. Please upload JPG, PNG, or WEBP."
    
    try:
        image = Image.open(file_storage.stream)
        image.verify()  # Verify image integrity
        
        # Re-open after verify()
        file_storage.stream.seek(0)
        image = Image.open(file_storage.stream)
        
        # Convert RGBA to RGB for JPEG compatibility
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        # Resize if overly large for vision model efficiency (max 1600x1600)
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        
        filename = f"scan_{uuid.uuid4().hex[:12]}.jpg"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        image.save(save_path, "JPEG", quality=88, optimize=True)
        
        relative_url = f"/static/uploads/temp_analysis/{filename}"
        return {
            "save_path": save_path,
            "relative_url": relative_url,
            "width": image.width,
            "height": image.height
        }, None
    except Exception as exc:
        return None, f"Invalid or corrupted image file: {str(exc)}"


def extract_product_text_from_image(image_path):
    """
    Use vision model to extract brand, product name, ingredients text, and barcode numbers.
    """
    client = get_ollama_client()
    if not client:
        return None, "Ollama Cloud API key is not configured in .env."

    try:
        with open(image_path, "rb") as img_file:
            b64_image = base64.b64encode(img_file.read()).decode("utf-8")
        
        prompt = (
            "You are an expert skincare product identification and OCR assistant. "
            "Analyze this skincare product image carefully. "
            "Extract all readable information: "
            "1. Brand name "
            "2. Full product name "
            "3. Category (e.g. Cleanser, Moisturizer, Serum, Sunscreen, Toner, etc.) "
            "4. Ingredients text (exact list of ingredients if visible on the label) "
            "5. Barcode number (the 8, 12, or 13-digit number beneath the barcode lines if visible) "
            "6. Data quality assessment (Is text clear or blurry? Confidence high, medium, or low?) "
            "Format your response strictly as valid JSON with keys: "
            '{"brand": "...", "product_name": "...", "category": "...", "ingredients_text": "...", "barcode": "...", "clarity": "clear|blurry", "confidence": "high|medium|low"}'
        )
        
        resp = client.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[{"role": "user", "content": prompt, "images": [b64_image]}]
        )
        
        content = resp.message.content.strip()
        # Parse JSON from model response
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            parsed = json.loads(json_match.group(0))
            return parsed, None
        else:
            return {
                "brand": "",
                "product_name": "",
                "category": "Skincare",
                "ingredients_text": content,
                "barcode": "",
                "clarity": "medium",
                "confidence": "low"
            }, None
    except Exception as exc:
        return None, f"Image vision processing error: {str(exc)}"


def identify_and_match_product(extracted_data):
    """
    Match extracted vision/OCR data against local database and Open Beauty Facts.
    Returns matched products with confidence scores.
    """
    barcode = str(extracted_data.get("barcode") or "").strip()
    brand = str(extracted_data.get("brand") or "").strip()
    name = str(extracted_data.get("product_name") or "").strip()
    ingredients = str(extracted_data.get("ingredients_text") or "").strip()

    matches = []

    # 1. Barcode direct lookup
    if barcode and len(barcode) >= 6:
        # Check local DB
        local_p = product_service.get_product_by_id(barcode)
        if local_p:
            matches.append({
                "product": local_p,
                "confidence": 98,
                "match_reason": f"Exact barcode match ({barcode})"
            })
        else:
            # Check Open Beauty Facts
            ext_p = product_service.fetch_open_beauty_facts_by_barcode(barcode)
            if ext_p:
                matches.append({
                    "product": ext_p,
                    "confidence": 95,
                    "match_reason": f"Verified barcode match from Open Beauty Facts ({barcode})"
                })

    # 2. Search local database by product name and brand
    search_query = f"{brand} {name}".strip() if brand else name
    if search_query:
        local_results = product_service.search_local_products(query=search_query, limit=5)
        for lp in local_results:
            if any(m["product"]["id"] == lp["id"] for m in matches):
                continue
            
            # Calculate match score based on name and brand similarity
            score = 60
            lp_name = lp["name"].lower()
            if name.lower() in lp_name or lp_name in name.lower():
                score += 25
            if brand and brand.lower() in lp["brand"].lower():
                score += 10
            
            matches.append({
                "product": lp,
                "confidence": min(95, score),
                "match_reason": "High name and brand similarity in product database"
            })

    # 3. If no high-confidence match found, search Open Beauty Facts API live
    if not matches or max(m["confidence"] for m in matches) < 80:
        if search_query:
            live_results = product_service.fetch_open_beauty_facts_search(search_query, limit=5)
            for ep in live_results:
                if any(m["product"]["id"] == ep["id"] for m in matches):
                    continue
                matches.append({
                    "product": ep,
                    "confidence": 75,
                    "match_reason": "Matched from Open Beauty Facts live catalogue"
                })

    # Sort matches by confidence descending
    matches.sort(key=lambda x: x["confidence"], reverse=True)

    # If no database match could be found, construct an ad-hoc unverified product record
    # so the user can still proceed with AI ingredient analysis of their photo!
    if not matches and (name or ingredients):
        custom_id = f"custom-{uuid.uuid4().hex[:8]}"
        custom_product = {
            "id": custom_id,
            "name": name or "Extracted Product from Photo",
            "brand": brand or "Unspecified Brand",
            "category": extracted_data.get("category") or "Skincare",
            "ingredients_text": ingredients or "Ingredients extracted from photo",
            "image_url": "",
            "source_provider": "Photo OCR Extraction",
            "source_url": "",
            "barcode": barcode,
            "completeness_score": 50,
            "rating": None,
            "review_count": 0,
            "skin_types_list": ["Normal", "Combination"]
        }
        matches.append({
            "product": custom_product,
            "confidence": 50,
            "match_reason": "Identified directly from packaging label photo (not yet catalogued in external database)"
        })

    return matches


def analyze_product_image_ocr(image_bytes_or_storage, filename="upload.jpg"):
    """
    Unified entry point for image scanning:
    Validates, saves/optimizes, and runs Ollama vision OCR extraction.
    """
    if hasattr(image_bytes_or_storage, "filename"):
        saved, err = save_and_optimize_image(image_bytes_or_storage)
    else:
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        fs = FileStorage(stream=BytesIO(image_bytes_or_storage), filename=filename)
        saved, err = save_and_optimize_image(fs)
        
    if err or not saved:
        return None, err or "Failed to process image."
    
    ocr_result, ocr_err = extract_product_text_from_image(saved["save_path"])
    if ocr_result:
        ocr_result["image_url"] = saved.get("relative_url", "")
    return ocr_result, ocr_err


# Alias for matching
match_ocr_to_products = identify_and_match_product
