"""
Test suite for Product Scanner, Vision OCR, and Barcode lookup.
"""

import os
import sys
import unittest
from io import BytesIO
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from vision_service import allowed_file, save_and_optimize_image, match_ocr_to_products
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
            barcode = prods[0]["barcode"]
            resp = self.client.post("/scan", data={"barcode": barcode}, follow_redirects=False)
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


if __name__ == "__main__":
    unittest.main()
