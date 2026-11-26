"""
Test suite for Product Scanner, Vision OCR, and Barcode lookup.
"""

import os
import sys
import time
import unittest
from io import BytesIO
from PIL import Image
import barcode
from barcode.writer import ImageWriter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from vision_service import (
    allowed_file, save_and_optimize_image, match_ocr_to_products,
    decode_physical_barcode, cleanup_temp_scans, UPLOAD_FOLDER
)
from product_service import search_products, get_product_by_barcode


class ScannerVisionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_allowed_extensions(self):
        """Verify allowed file extensions."""
        self.assertTrue(allowed_file("cream.jpg"))
        self.assertTrue(allowed_file("serum.jpeg"))
        self.assertTrue(allowed_file("lotion.png"))
        self.assertTrue(allowed_file("sunscreen.webp"))
        self.assertFalse(allowed_file("malicious.exe"))
        self.assertFalse(allowed_file("script.py"))

    def test_barcode_lookup_endpoint(self):
        """Verify barcode lookup routes to product detail."""
        prods = search_products(limit=1)
        if prods and prods[0].get("barcode"):
            barcode_num = prods[0]["barcode"]
            resp = self.client.post("/scan", data={"barcode": barcode_num}, follow_redirects=False)
            self.assertEqual(resp.status_code, 302)
            self.assertIn(f"/product/{prods[0]['id']}", resp.headers.get("Location", ""))
            print(f"[PASS] Barcode search correctly routes to product #{prods[0]['id']}.")

    def test_matcher_logic(self):
        """Verify match_ocr_to_products matches known keywords."""
        sample_ocr = {
            "brand": "CeraVe",
            "product_name": "Moisturizing Cream",
            "ingredients_text": "Ceramides, Hyaluronic Acid, Glycerin, Dimethicone",
            "barcode": ""
        }
        matches = match_ocr_to_products(sample_ocr)
        self.assertIsInstance(matches, list)
        print(f"[PASS] Product OCR matcher returned {len(matches)} potential catalogue candidates.")

    def test_physical_barcode_detection_ean13(self):
        """Verify physical EAN-13 barcode decoding from image."""
        test_code = "366236100214"
        ean = barcode.get("ean13", test_code, writer=ImageWriter())
        fp = BytesIO()
        ean.write(fp)
        fp.seek(0)
        img = Image.open(fp)

        decoded = decode_physical_barcode(img)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["barcode"], "3662361002146")
        self.assertIn("EAN", decoded["format"])
        print(f"[PASS] Physical EAN-13 decoded: {decoded['barcode']} ({decoded['format']}).")

    def test_physical_barcode_non_barcode_image(self):
        """Verify non-barcode image returns None gracefully."""
        blank_img = Image.new("RGB", (200, 200), color="white")
        decoded = decode_physical_barcode(blank_img)
        self.assertIsNone(decoded)
        print("[PASS] Non-barcode image correctly returned None.")

    def test_temp_scan_cleanup(self):
        """Verify cleanup_temp_scans removes expired temporary images."""
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        test_file = os.path.join(UPLOAD_FOLDER, "scan_test_cleanup.jpg")
        with open(test_file, "w") as f:
            f.write("test")

        # Artificially age the file
        old_time = time.time() - 7200
        os.utime(test_file, (old_time, old_time))

        deleted = cleanup_temp_scans(max_age_seconds=3600)
        self.assertGreaterEqual(deleted, 1)
        self.assertFalse(os.path.exists(test_file))
        print(f"[PASS] Cleanup removed {deleted} expired temporary scan file(s).")

    def test_scan_post_image_upload(self):
        """Verify image upload via POST with product_image field."""
        # Create a small valid test image
        img = Image.new("RGB", (100, 100), color="pink")
        buf = BytesIO()
        img.save(buf, "JPEG")
        buf.seek(0)

        data = {
            "product_image": (buf, "test_cream.jpg")
        }
        resp = self.client.post("/scan", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Scan Analysis Dossier", html)
        print("[PASS] POST /scan with image processed successfully.")


if __name__ == "__main__":
    unittest.main()
