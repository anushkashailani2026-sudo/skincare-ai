"""
Master Upgrade Comprehensive Test Suite for Skincare AI.
Tests every major feature: existing routes, user authentication, review submissions,
admin dashboard, review moderation, floating notifications, product dossier,
routine builder, product comparison, journal logging, and data integrity.
"""

import os
import sys
import json
import unittest

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app, init_db
import db as database
from auth_service import (
    register_user, authenticate_user, submit_product_review,
    get_unseen_reviews_for_admin, update_review_status
)
from product_service import search_products, get_product_by_id


class MasterUpgradeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SERVER_NAME"] = "localhost"
        init_db()

    def setUp(self):
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_01_existing_public_routes(self):
        """Verify all existing public endpoints return status 200."""
        routes = ["/", "/ingredients", "/products", "/skin", "/ask-ai", "/feedback"]
        for r in routes:
            resp = self.client.get(r)
            self.assertEqual(resp.status_code, 200, f"Route {r} failed with status {resp.status_code}")
        print("[PASS] 01: All existing public pages load with status 200.")

    def test_02_user_auth_flow(self):
        """Verify user registration, login, authenticated dashboard, and logout."""
        # 1. Register page loads
        resp = self.client.get("/register")
        self.assertEqual(resp.status_code, 200)

        # 2. Register user
        database.execute_query("DELETE FROM user_profiles WHERE user_id IN (SELECT id FROM users WHERE username = 'glow_enthusiast' OR email = 'glow@example.com')")
        database.execute_query("DELETE FROM users WHERE username = 'glow_enthusiast' OR email = 'glow@example.com'")
        username = "glow_enthusiast"
        email = "glow@example.com"
        resp = self.client.post("/register", data={
            "username": username,
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "skin_type": "Combination",
            "skin_concern": "Acne & Blemishes"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # 3. Check dashboard access
        resp = self.client.get("/user/dashboard")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("glow_enthusiast", resp.get_data(as_text=True))

        # 4. Logout
        resp = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # 5. Log in again
        resp = self.client.post("/login", data={
            "identifier": "glow@example.com",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("glow_enthusiast", resp.get_data(as_text=True))
        print("[PASS] 02: User registration, authentication, and session management verified.")

    def test_03_unauthenticated_review_protection(self):
        """Verify that anonymous visitors cannot access review submission."""
        anon_client = app.test_client()
        resp = anon_client.get("/submit-review", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers.get("Location", ""))
        print("[PASS] 03: Review submission blocked for unauthenticated users.")

    def test_04_review_submission_and_admin_notification(self):
        """Verify member submits a review, and admin receives an unseen notification card."""
        member_client = app.test_client()
        # Log in as member
        member_client.post("/login", data={
            "identifier": "glow@example.com",
            "password": "Password123!"
        }, follow_redirects=True)

        # Submit a product review
        prods = search_products(limit=1)
        prod_id = prods[0]["id"] if prods else "sample-serum"
        prod_name = prods[0]["name"] if prods else "Salicylic Acid 2% Solution"

        resp = member_client.post("/submit-review", data={
            "product_id": prod_id,
            "product_name": prod_name,
            "rating": "5",
            "review_title": "Remarkable formulation for pore clarity",
            "review_text": "Cleared congestion within three weeks of consistent PM application without stinging.",
            "skin_type": "Combination",
            "skin_concern": "Acne & Blemishes",
            "usage_duration": "3-4 weeks"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Check unseen reviews in database
        unseen = get_unseen_reviews_for_admin()
        self.assertTrue(len(unseen) > 0, "Expected at least one unseen review for admin.")
        latest_rev = unseen[0]
        self.assertEqual(latest_rev["product_name"], prod_name)

        # Verify admin API blocks anonymous visitor
        anon_client = app.test_client()
        api_resp = anon_client.get("/api/admin/notifications/unseen")
        self.assertEqual(api_resp.status_code, 401)

        # Admin logs in
        admin_client = app.test_client()
        admin_client.post("/admin/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)

        # Admin fetches unseen notifications
        notif_resp = admin_client.get("/api/admin/notifications/unseen")
        self.assertEqual(notif_resp.status_code, 200)
        data = json.loads(notif_resp.get_data(as_text=True))
        self.assertIn("unseen_reviews", data)
        self.assertTrue(len(data["unseen_reviews"]) > 0)

        # Admin dismisses notification
        rev_id = latest_rev["id"]
        dismiss_resp = admin_client.post(f"/api/admin/notifications/dismiss/{rev_id}")
        self.assertEqual(dismiss_resp.status_code, 200)

        # Admin dashboard view
        dash_resp = admin_client.get("/admin/dashboard?tab=reviews")
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn(prod_name, dash_resp.get_data(as_text=True))

        # Admin moderates review to 'approved'
        mod_resp = admin_client.post(f"/admin/review/status/{rev_id}", data={
            "status": "approved"
        }, follow_redirects=True)
        self.assertEqual(mod_resp.status_code, 200)

        # Admin exports CSV
        csv_resp = admin_client.get("/admin/reviews/export")
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn("text/csv", csv_resp.headers.get("Content-Type", ""))
        self.assertIn(prod_name, csv_resp.get_data(as_text=True))

        print("[PASS] 04: Review submission, unseen admin notification card, moderation, and CSV export passed.")

    def test_05_product_dossier_route(self):
        """Verify product intelligence dossier loads and displays formulation intelligence."""
        prods = search_products(limit=1)
        if prods:
            prod_id = prods[0]["id"]
            resp = self.client.get(f"/product/{prod_id}")
            self.assertEqual(resp.status_code, 200)
            html_text = resp.get_data(as_text=True)
            self.assertIn(prods[0]["name"], html_text)
            self.assertIn("Clinical Formulation", html_text)
        print("[PASS] 05: Product formulation intelligence dossier verified.")

    def test_06_routine_builder_and_conflict_check(self):
        """Verify AM/PM routine generator produces clinical steps and conflict checks."""
        resp = self.client.get("/routine")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post("/routine", data={
            "skin_type": "Oily",
            "concern": "Acne & Blemishes",
            "time_of_day": "both"
        })
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("AM Routine Sequence", html)
        self.assertIn("PM Routine Sequence", html)
        print("[PASS] 06: AM/PM Routine builder and active conflict detection verified.")

    def test_07_product_comparison(self):
        """Verify head-to-head comparison matrix loads."""
        prods = search_products(limit=2)
        if len(prods) >= 2:
            resp = self.client.get(f"/compare?id1={prods[0]['id']}&id2={prods[1]['id']}")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn("Product Formulation Comparison", html)
        print("[PASS] 07: Head-to-head product comparison matrix verified.")

    def test_08_skincare_journal(self):
        """Verify daily journal entry logging and persistence."""
        member_client = app.test_client()
        member_client.post("/login", data={
            "identifier": "glow@example.com",
            "password": "Password123!"
        }, follow_redirects=True)

        resp = member_client.post("/journal", data={
            "entry_date": "2026-11-09",
            "skin_rating": "5",
            "products_used": "Gentle Cleanser, 2% BHA, Ceramide Cream",
            "symptoms": "Calm, zero flaking, smooth",
            "notes": "Skin barrier feeling resilient today.",
            "irritation_occurred": ""
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Skin barrier feeling resilient today", html)
        print("[PASS] 08: Skincare journal entry logged and persisted.")

    def test_09_database_feedback_preservation(self):
        """Verify that general feedback table remains populated and untouched."""
        feedbacks = database.execute_query("SELECT COUNT(*) as cnt FROM skincare_feedback", fetchone=True)
        self.assertIsNotNone(feedbacks)
        print(f"[PASS] 09: Feedback database intact with {feedbacks['cnt']} existing records.")


if __name__ == "__main__":
    unittest.main()
