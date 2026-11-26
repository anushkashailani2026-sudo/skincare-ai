"""
Vision and Image Analysis Service for Skincare AI.
Handles product packaging photo uploads, ingredient label OCR,
physical barcode decoding (EAN-13, EAN-8, UPC-A, UPC-E via zxing-cpp),
and product identification using Groq Vision model.
"""

import os
import io
import re
import time
import json
import base64
import uuid
import logging
from PIL import Image
import product_service
import groq_service

logger = logging.getLogger("skincare_ai.vision")

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads", "temp_analysis")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_temp_scans(max_age_seconds=3600):
    """
    Safely delete temporary scan images older than max_age_seconds (default 1 hour).
    Only targets files prefixed with 'scan_' in the temp analysis directory.
    Never touches permanent product images or user content.
    """
    try:
        if not os.path.isdir(UPLOAD_FOLDER):
            return 0
        now = time.time()
        deleted = 0
        for fname in os.listdir(UPLOAD_FOLDER):
            if fname.startswith("scan_") and fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                fpath = os.path.join(UPLOAD_FOLDER, fname)
                if os.path.isfile(fpath):
                    try:
                        if now - os.path.getmtime(fpath) > max_age_seconds:
                            os.remove(fpath)
                            deleted += 1
                    except Exception:
                        pass
        return deleted
    except Exception as exc:
        logger.warning("Cleanup temp scans notice: %s", exc)
        return 0


def save_and_optimize_image(file_storage):
    """
    Validate, sanitize, and optimize uploaded product image.
    Enforces format validation, size limit, and safe PIL conversion.
    Returns relative web path and absolute disk path.
    """
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    cleanup_temp_scans()

    if not file_storage or not file_storage.filename:
        return None, "No file provided. Please choose a packaging photo to upload."

    if not allowed_file(file_storage.filename):
        return None, "Unsupported file format. Please upload a JPG, JPEG, PNG, or WEBP image."

    try:
        # Check size if available
        file_storage.stream.seek(0, os.SEEK_END)
        size = file_storage.stream.tell()
        file_storage.stream.seek(0)
        if size > MAX_FILE_SIZE:
            return None, "Image exceeds the 10 MB size limit. Please upload a smaller photo."

        image = Image.open(file_storage.stream)
        image.verify()  # Verify image integrity

        # Re-open after verify()
        file_storage.stream.seek(0)
        image = Image.open(file_storage.stream)

        # Convert RGBA or Palette to RGB for JPEG compatibility
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
            "height": image.height,
            "filename": filename
        }, None
    except Exception as exc:
        return None, f"Invalid or corrupted image file: {str(exc)}"


def decode_physical_barcode(image_path_or_pil):
    """
    Scan an image using zxing-cpp to decode physical 1D/2D barcodes (EAN-13, EAN-8, UPC-A, UPC-E).
    Returns dict with barcode, format, and valid=True, or None if no barcode detected.
    """
    try:
        import zxingcpp
        if isinstance(image_path_or_pil, Image.Image):
            pil_img = image_path_or_pil
        else:
            pil_img = Image.open(image_path_or_pil)

        result = zxingcpp.read_barcode(pil_img, try_rotate=True, try_downscale=True, try_invert=True)
        if result and getattr(result, "valid", False) and getattr(result, "text", ""):
            raw_text = str(result.text).strip()
            # Clean up leading zeroes if 13-digit EAN-13 from UPC-A
            clean_text = raw_text
            fmt = str(result.format).replace("BarcodeFormat.", "")
            return {
                "barcode": clean_text,
                "format": fmt,
                "valid": True
            }
        return None
    except Exception as exc:
        logger.info("Physical barcode decode info: %s", exc)
        return None


def extract_product_text_from_image(image_path):
    """
    Use Groq multimodal vision model to extract brand, product name,
    ingredients text, and barcode numbers from packaging photograph.
    """
    return groq_service.extract_packaging_ocr(image_path)


def identify_and_match_product(extracted_data):
    """
    Match extracted vision/OCR data against local database and Open Beauty Facts.
    Returns matched products with confidence scores.
    """
    if not extracted_data:
        return []

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


def process_full_scan(file_storage_or_bytes, filename="upload.jpg"):
    """
    End-to-end scanner processing pipeline:
    1. Validates and optimizes uploaded image
    2. Decodes physical 1D/2D barcodes via zxing-cpp
    3. Runs Groq multimodal Vision OCR for packaging text
    4. Matches against catalog & Open Beauty Facts
    5. Returns unified scan result dictionary:
       {
           'barcode_info': dict or None,
           'ocr_data': dict or None,
           'matches': list,
           'image_url': str,
           'error': str or None
       }
    """
    if hasattr(file_storage_or_bytes, "filename"):
        saved, err = save_and_optimize_image(file_storage_or_bytes)
    else:
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        fs = FileStorage(stream=BytesIO(file_storage_or_bytes), filename=filename)
        saved, err = save_and_optimize_image(fs)

    if err or not saved:
        return None, err or "Failed to process packaging photo."

    save_path = saved["save_path"]
    image_url = saved.get("relative_url", "")

    # Step 1: Decode physical barcode
    barcode_info = decode_physical_barcode(save_path)

    # Step 2: Groq multimodal vision OCR for packaging text
    ocr_data, ocr_err = extract_product_text_from_image(save_path)
    if not ocr_data:
        ocr_data = {
            "brand": "",
            "product_name": "",
            "category": "Skincare",
            "ingredients_text": "",
            "barcode": "",
            "clarity": "clear",
            "confidence": "low"
        }

    ocr_data["image_url"] = image_url

    # Step 3: If physical barcode was decoded, prioritize it
    if barcode_info and barcode_info.get("barcode"):
        ocr_data["barcode"] = barcode_info["barcode"]

    # Step 4: Product matching against database & Open Beauty Facts
    matches = identify_and_match_product(ocr_data)

    return {
        "barcode_info": barcode_info,
        "ocr_data": ocr_data,
        "matches": matches,
        "image_url": image_url,
        "error": None
    }, None


def analyze_product_image_ocr(image_bytes_or_storage, filename="upload.jpg"):
    """
    Backward-compatible entry point for image scanning:
    Validates, saves/optimizes, and runs Groq vision OCR extraction.
    """
    res, err = process_full_scan(image_bytes_or_storage, filename=filename)
    if err or not res:
        return None, err or "Failed to process image."
    return res.get("ocr_data"), None


# Alias for matching
match_ocr_to_products = identify_and_match_product
