"""
Diagnostic and automated verification test suite for Groq AI integration.
Tests text completion, skincare assistant, ingredient analysis, product explanations,
and multimodal packaging OCR.
"""

import os
import sys
import unittest
from io import BytesIO
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import groq_service


class GroqServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.api_key = groq_service.get_groq_api_key()

    def test_01_configuration_defaults(self):
        """Verify text and vision model defaults are properly configured."""
        self.assertIsInstance(groq_service.DEFAULT_TEXT_MODEL, str)
        self.assertTrue(len(groq_service.DEFAULT_TEXT_MODEL) > 0)
        self.assertIsInstance(groq_service.DEFAULT_VISION_MODEL, str)
        self.assertTrue(len(groq_service.DEFAULT_VISION_MODEL) > 0)
        print(f"[PASS] Text model: {groq_service.DEFAULT_TEXT_MODEL}")
        print(f"[PASS] Vision model: {groq_service.DEFAULT_VISION_MODEL}")

    def test_02_clean_markdown_utility(self):
        """Verify markdown cleanup removes hashes, bold markers, and excessive lines."""
        raw = "### Heading\n\n**Bold Text** and *italic*.\n\n\n\n> Quote line."
        cleaned = groq_service.clean_markdown_text(raw)
        self.assertNotIn("###", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertIn("Bold Text", cleaned)
        self.assertIn("Quote line.", cleaned)
        print("[PASS] Markdown sanitization utility verified.")

    def test_03_ask_skincare_assistant(self):
        """Verify ask_skincare_assistant handles requests gracefully."""
        question = "What is the primary function of hyaluronic acid?"
        answer = groq_service.ask_skincare_assistant(question)
        self.assertIsInstance(answer, str)
        self.assertTrue(len(answer) > 10)
        if self.api_key:
            print(f"[PASS] Live Groq response received for Ask AI: '{answer[:80]}...'")
        else:
            print(f"[PASS] Handled unconfigured API key gracefully: '{answer[:80]}...'")

    def test_04_ingredient_explanation(self):
        """Verify explain_ingredient generates structured advice."""
        result = groq_service.explain_ingredient("Niacinamide")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 10)
        print("[PASS] Ingredient explanation pipeline verified.")

    def test_05_formulation_narrative(self):
        """Verify product dossier formulation narrative synthesis."""
        narrative = groq_service.generate_formulation_narrative(
            name="Daily Moisturizing Lotion",
            brand="CeraVe",
            category="Moisturizer",
            ingredients="Aqua, Glycerin, Caprylic/Capric Triglyceride, Cetearyl Alcohol, Ceramide NP, Ceramide AP, Hyaluronic Acid",
            actives=[{"name": "Ceramide Complex"}, {"name": "Hyaluronic Acid"}]
        )
        self.assertIsInstance(narrative, str)
        self.assertIn("CeraVe", narrative)
        print("[PASS] Formulation narrative synthesis verified.")

    def test_06_vision_packaging_ocr(self):
        """Verify multimodal packaging OCR pipeline with image data."""
        # Generate a synthetic test label image
        img = Image.new("RGB", (300, 150), color=(255, 255, 255))
        test_img_path = os.path.join(BASE_DIR, "test_label_temp.jpg")
        img.save(test_img_path, "JPEG")

        try:
            data, err = groq_service.extract_packaging_ocr(test_img_path)
            if self.api_key:
                self.assertIsNone(err)
                self.assertIsInstance(data, dict)
                self.assertIn("product_name", data)
                print("[PASS] Live Groq Vision OCR executed successfully.")
            else:
                self.assertIsNotNone(err)
                print(f"[PASS] Vision error handled gracefully without crash: '{err}'")
        finally:
            if os.path.exists(test_img_path):
                os.remove(test_img_path)


if __name__ == "__main__":
    unittest.main()
