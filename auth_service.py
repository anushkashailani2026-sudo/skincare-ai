"""
Authentication, User Management, and Review Service for Skincare AI.
Handles user registration, login, profile management, review submissions,
admin review dashboard, moderation, CSV export, and bottom-right floating notifications.
"""

import os
import re
import csv
import io
import bcrypt
from datetime import datetime
from functools import wraps
from flask import session, request, redirect, url_for, jsonify
from db import execute_query, is_postgres


def clean_text(val, max_len=2000):
    """Sanitize and trim input strings."""
    if not val:
        return ""
    cleaned = str(val).strip()
    return cleaned[:max_len]


def get_user_by_id(user_id):
    """Retrieve user dictionary by integer ID."""
    if not user_id:
        return None
    return execute_query(
        "SELECT id, username, email, full_name, skin_type, created_at FROM users WHERE id = ? LIMIT 1",
        [user_id],
        fetchone=True
    )


def register_user(username, email, password, full_name="", skin_type="", skin_concern=""):
    """Register a new user with secure bcrypt password hashing."""
    username = (username or "").strip()
    email = (email or "").strip().lower()
    full_name = clean_text(full_name or username, max_len=100)
    skin_type = clean_text(skin_type, max_len=50)
    skin_concern = clean_text(skin_concern, max_len=100)

    # Validation
    if not username or len(username) < 3 or len(username) > 30:
        return False, "Username must be between 3 and 30 characters.", None
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores.", None
    
    if not email or "@" not in email or "." not in email:
        return False, "Please enter a valid email address.", None
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    # Check for existing username or email
    existing_user = execute_query(
        "SELECT id FROM users WHERE username = ? OR email = ? LIMIT 1",
        [username, email],
        fetchone=True
    )
    if existing_user:
        return False, "A user with this username or email already exists.", None

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    execute_query("""
        INSERT INTO users (username, email, password_hash, full_name, skin_type)
        VALUES (?, ?, ?, ?, ?)
    """, [username, email, pw_hash, full_name, skin_type])

    # Fetch newly created user
    new_user = execute_query(
        "SELECT id, username, email, full_name, skin_type FROM users WHERE username = ? LIMIT 1",
        [username],
        fetchone=True
    )

    if new_user and (skin_type or skin_concern):
        execute_query("""
            INSERT INTO user_profiles (user_id, skin_type, skin_concern, skin_concerns)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                skin_type = EXCLUDED.skin_type,
                skin_concern = EXCLUDED.skin_concern,
                skin_concerns = EXCLUDED.skin_concerns
        """, [new_user["id"], skin_type, skin_concern, skin_concern])

    return True, "Registration successful!", new_user


def authenticate_user(username_or_email, password):
    """Authenticate user with username or email and bcrypt password check."""
    ident = (username_or_email or "").strip()
    if not ident or not password:
        return False, "Please enter both credentials."

    user = execute_query(
        "SELECT id, username, email, password_hash, full_name, skin_type FROM users WHERE username = ? OR email = ? LIMIT 1",
        [ident, ident.lower()],
        fetchone=True
    )
    if not user:
        return False, "Invalid username/email or password."

    try:
        if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            return True, {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "full_name": user["full_name"],
                "skin_type": user["skin_type"]
            }
    except Exception as exc:
        print("Password check error:", exc)
    
    return False, "Invalid username/email or password."


def login_required(f):
    """Decorator requiring a logged-in regular user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "message": "Authentication required. Please sign in."}), 401
            return redirect(url_for("user_login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


# ========================================================
# USER PRODUCT REVIEWS
# ========================================================

def submit_product_review(*args, **kwargs):
    """
    Submit a real user review for a skincare product.
    Supports flexible arguments:
    submit_product_review(user_id, product_name, rating, review_text, product_id=None, review_title='', ...)
    OR positional:
    submit_product_review(user_id, user_name, user_email, product_id, product_name, rating, title, review_text, ...)
    """
    user_id = None
    user_name = ""
    user_email = ""
    product_id = None
    product_name = ""
    rating = 5
    title = ""
    review_text = ""
    skin_type = ""
    skin_concern = ""
    duration_used = ""

    # Parse positional or keyword arguments
    if len(args) >= 8:
        user_id = args[0]
        user_name = args[1]
        user_email = args[2]
        product_id = args[3]
        product_name = args[4]
        rating = args[5]
        title = args[6]
        review_text = args[7]
        if len(args) > 8: skin_type = args[8]
        if len(args) > 9: skin_concern = args[9]
        if len(args) > 10: duration_used = args[10]
    elif len(args) >= 4:
        user_id = args[0]
        product_name = args[1]
        rating = args[2]
        review_text = args[3]
        if len(args) > 4: product_id = args[4]
        if len(args) > 5: title = args[5]
        if len(args) > 6: skin_type = args[6]
        if len(args) > 7: skin_concern = args[7]
        if len(args) > 8: duration_used = args[8]
    else:
        user_id = kwargs.get("user_id")
        product_name = kwargs.get("product_name", "")
        rating = kwargs.get("rating", 5)
        review_text = kwargs.get("review_text", "")
        product_id = kwargs.get("product_id")
        title = kwargs.get("review_title") or kwargs.get("title", "")
        skin_type = kwargs.get("skin_type", "")
        skin_concern = kwargs.get("skin_concern", "")
        duration_used = kwargs.get("usage_duration") or kwargs.get("duration_used", "")

    # Overwrite from kwargs if present
    if "user_name" in kwargs: user_name = kwargs["user_name"]
    if "user_email" in kwargs: user_email = kwargs["user_email"]
    if "product_id" in kwargs: product_id = kwargs["product_id"]
    if "review_title" in kwargs: title = kwargs["review_title"]
    if "usage_duration" in kwargs: duration_used = kwargs["usage_duration"]

    # Look up user details if missing
    if user_id and (not user_name or not user_email):
        u = get_user_by_id(user_id)
        if u:
            user_name = u.get("username", "Member")
            user_email = u.get("email", "")

    product_name = clean_text(product_name, max_len=150)
    title = clean_text(title or f"Review for {product_name}", max_len=150)
    review_text = clean_text(review_text, max_len=3000)
    skin_type = clean_text(skin_type, max_len=50)
    skin_concern = clean_text(skin_concern, max_len=100)
    duration_used = clean_text(duration_used, max_len=50)
    product_id = str(product_id).strip() if product_id else None

    if not product_name:
        return False, "Product name is required."
    
    try:
        rating_int = int(rating)
        if rating_int < 1 or rating_int > 5:
            return False, "Rating must be between 1 and 5 stars."
    except (ValueError, TypeError):
        return False, "Please choose a valid rating from 1 to 5."

    if not review_text or len(review_text) < 10:
        return False, "Review text must be at least 10 characters long."

    # Insert review with status='pending' and admin_seen=0
    execute_query("""
        INSERT INTO user_reviews (
            user_id, user_name, user_email, product_id, product_name,
            rating, title, review_text, skin_type, skin_concern, duration_used,
            status, admin_seen
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0)
    """, [
        user_id, user_name, user_email, product_id, product_name,
        rating_int, title, review_text, skin_type, skin_concern, duration_used
    ])

    if product_id:
        update_product_rating_cache(product_id)

    return True, "Your review has been successfully submitted! It will appear publicly upon admin moderation."


def update_product_rating_cache(product_id):
    """Update cached average rating and review count on a product."""
    stats = execute_query("""
        SELECT COUNT(*) as cnt, AVG(rating) as avg_r
        FROM user_reviews
        WHERE (product_id = ? OR product_name = ?) AND status = 'approved'
    """, [product_id, product_id], fetchone=True)

    if stats and stats["cnt"]:
        count = stats["cnt"]
        avg_r = round(float(stats["avg_r"]), 1) if stats["avg_r"] else None
        execute_query(
            "UPDATE products SET rating = ?, review_count = ? WHERE id = ? OR barcode = ?",
            [avg_r, count, product_id, product_id]
        )


def get_user_submitted_reviews(user_id):
    """Get all reviews submitted by a specific user for their dashboard."""
    return execute_query("""
        SELECT * FROM user_reviews
        WHERE user_id = ?
        ORDER BY id DESC
    """, [user_id], fetchall=True)


def get_approved_product_reviews(product_id=None, product_name=None, limit=20):
    """Get public approved reviews for a given product."""
    where = ["status = 'approved'"]
    params = []
    if product_id:
        where.append("(product_id = ? OR product_name = ?)")
        params.extend([product_id, product_name or product_id])
    elif product_name:
        where.append("product_name = ?")
        params.append(product_name)
    
    sql = f"SELECT * FROM user_reviews WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return execute_query(sql, params, fetchall=True)


# ========================================================
# ADMIN REVIEW MANAGEMENT & FLOATING NOTIFICATIONS
# ========================================================

def get_admin_reviews_data(rating=None, product=None, status=None, search=None, sort="newest"):
    """Fetch all reviews for the private admin review dashboard."""
    where = []
    params = []

    if rating:
        try:
            r = int(rating)
            if 1 <= r <= 5:
                where.append("rating = ?")
                params.append(r)
        except (ValueError, TypeError):
            pass

    if product and product.strip():
        where.append("product_name LIKE ?")
        params.append(f"%{product.strip()}%")

    if status and status != "all":
        where.append("status = ?")
        params.append(status)

    if search and search.strip():
        q = f"%{search.strip()}%"
        where.append("(title LIKE ? OR review_text LIKE ? OR user_name LIKE ? OR product_name LIKE ?)")
        params.extend([q, q, q, q])

    sql = "SELECT * FROM user_reviews"
    if where:
        sql += " WHERE " + " AND ".join(where)

    if sort == "oldest":
        sql += " ORDER BY id ASC"
    elif sort == "highest":
        sql += " ORDER BY rating DESC, id DESC"
    elif sort == "lowest":
        sql += " ORDER BY rating ASC, id DESC"
    else:
        sql += " ORDER BY id DESC"

    return execute_query(sql, params, fetchall=True)


def get_review_summary_stats():
    """Calculate summary statistics for product reviews."""
    all_revs = execute_query("SELECT id, rating, status, admin_seen FROM user_reviews", fetchall=True)

    total_count = len(all_revs)
    if total_count == 0:
        return {
            "total_count": 0,
            "avg_rating": 0.0,
            "star_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "unseen_count": 0,
            "approved_count": 0,
            "pending_count": 0,
            "flagged_count": 0,
            "positive_percent": 0
        }

    total_sum = 0
    star_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    unseen_count = 0
    approved_count = 0
    pending_count = 0
    flagged_count = 0
    positive_count = 0

    for r in all_revs:
        rating = r["rating"] or 5
        total_sum += rating
        star_counts[rating] = star_counts.get(rating, 0) + 1
        if rating >= 4:
            positive_count += 1
        if r.get("admin_seen") == 0:
            unseen_count += 1
        st = r.get("status")
        if st == "approved":
            approved_count += 1
        elif st == "pending":
            pending_count += 1
        elif st == "flagged":
            flagged_count += 1

    return {
        "total_count": total_count,
        "avg_rating": round(total_sum / total_count, 1),
        "star_counts": star_counts,
        "unseen_count": unseen_count,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "flagged_count": flagged_count,
        "positive_percent": round((positive_count / total_count) * 100)
    }


def update_review_status(review_id, status):
    """Moderate review: approve, reject, or flag."""
    if status not in ["approved", "rejected", "flagged", "pending"]:
        return False, "Invalid status"
    execute_query("UPDATE user_reviews SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", [status, review_id])
    return True, "Status updated"


def delete_user_review(review_id):
    """Permanently delete a user review."""
    execute_query("DELETE FROM user_reviews WHERE id = ?", [review_id])
    return True, "Review deleted"


def mark_review_as_seen(review_id):
    """Mark a review notification as seen by admin."""
    execute_query("UPDATE user_reviews SET admin_seen = 1 WHERE id = ?", [review_id])
    return True


def get_unseen_reviews_for_admin():
    """
    Fetch unseen review notifications for authenticated admin.
    Returns preview cards to show at the bottom-right corner.
    """
    rows = execute_query("""
        SELECT id, product_name, rating, title, review_text, user_name, created_at
        FROM user_reviews
        WHERE admin_seen = 0
        ORDER BY id DESC
        LIMIT 5
    """, fetchall=True)

    notifications = []
    for r in rows:
        stars = "★" * (r["rating"] or 5) + "☆" * (5 - (r["rating"] or 5))
        preview = (r["review_text"] or "")[:90] + ("..." if len(r["review_text"] or "") > 90 else "")
        notifications.append({
            "id": r["id"],
            "product_name": r["product_name"] or "Product Review",
            "rating": r["rating"],
            "stars": stars,
            "title": r["title"],
            "preview": preview,
            "user_name": r["user_name"] or "Member",
            "created_at": str(r["created_at"])[:16]
        })
    return notifications


def export_reviews_csv():
    """Export all product reviews as downloadable CSV data."""
    rows = execute_query("SELECT * FROM user_reviews ORDER BY id DESC", fetchall=True)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "ID", "User ID", "User Name", "User Email", "Product Name",
        "Rating", "Title", "Review Text", "Skin Type", "Skin Concern",
        "Duration Used", "Status", "Created At"
    ])
    for r in rows:
        writer.writerow([
            r.get("id"),
            r.get("user_id"),
            r.get("user_name"),
            r.get("user_email"),
            r.get("product_name"),
            r.get("rating"),
            r.get("title"),
            r.get("review_text"),
            r.get("skin_type"),
            r.get("skin_concern"),
            r.get("duration_used"),
            r.get("status"),
            r.get("created_at")
        ])
    return out.getvalue()


# Function Aliases for flexible import
get_user_reviews = get_user_submitted_reviews
get_admin_reviews = get_admin_reviews_data
get_review_statistics = get_review_summary_stats
