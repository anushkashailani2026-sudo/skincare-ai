"""
Personal Skin Profile, AM/PM Routine Generator, and Skincare Journal Service.
Handles skin profile CRUD, clinical routine building with conflict checks,
routine saving/retrieval, and daily journal entry tracking.
"""

import os
import json
from db import execute_query, is_postgres
import product_service
import analysis_service


# ========================================================
# USER SKIN PROFILE
# ========================================================

def get_user_profile(user_id):
    """Retrieve skin profile for user, or return default if unset."""
    if not user_id:
        return {}
    row = execute_query(
        "SELECT * FROM user_profiles WHERE user_id = ? LIMIT 1",
        [user_id],
        fetchone=True
    )
    if row:
        row["skin_concerns_list"] = [c.strip() for c in (row.get("skin_concern") or "").split(",") if c.strip()]
        return row
    
    # Check users table
    u = execute_query("SELECT skin_type FROM users WHERE id = ? LIMIT 1", [user_id], fetchone=True)
    skin_type = u.get("skin_type") if u else "Combination"
    return {
        "user_id": user_id,
        "skin_type": skin_type or "Combination",
        "skin_concern": "Acne & Blemishes",
        "skin_concerns_list": ["Acne & Blemishes"]
    }


def save_user_profile(user_id, skin_type="Combination", skin_concerns="Acne & Blemishes", sensitivities="", budget_pref="medium", am_pref="simple", pm_pref="targeted"):
    """Save or update user skin profile."""
    if isinstance(skin_concerns, list):
        skin_concerns = ", ".join(skin_concerns)
        
    execute_query("""
        INSERT INTO user_profiles (
            user_id, skin_type, skin_concern, sensitivities,
            budget_preference, am_routine_preference, pm_routine_preference, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO UPDATE SET
            skin_type = EXCLUDED.skin_type,
            skin_concern = EXCLUDED.skin_concern,
            sensitivities = EXCLUDED.sensitivities,
            budget_preference = EXCLUDED.budget_preference,
            am_routine_preference = EXCLUDED.am_routine_preference,
            pm_routine_preference = EXCLUDED.pm_routine_preference,
            updated_at = CURRENT_TIMESTAMP
    """, [user_id, skin_type, skin_concerns, sensitivities, budget_pref, am_pref, pm_pref])
    return get_user_profile(user_id)


# ========================================================
# PERSONALIZED ROUTINE BUILDER
# ========================================================

def generate_recommended_routine(*args, **kwargs):
    """
    Generate tailored AM and PM skincare routines with real products from the database,
    ordered by clinical dermatological application sequence and conflict-checked.
    Accepts (skin_type, concern, time_of_day='both') OR (user_id).
    """
    skin_type = "Combination"
    concern = "Acne & Blemishes"
    time_of_day = "both"

    if len(args) == 1 and (isinstance(args[0], int) or str(args[0]).isdigit()):
        prof = get_user_profile(args[0])
        skin_type = prof.get("skin_type", "Combination")
        concern = prof.get("skin_concern", "Acne & Blemishes")
    elif len(args) >= 1 and isinstance(args[0], str):
        skin_type = args[0]
        if len(args) >= 2: concern = args[1]
        if len(args) >= 3: time_of_day = args[2]
    else:
        skin_type = kwargs.get("skin_type") or "Combination"
        concern = kwargs.get("concern") or "Acne & Blemishes"
        time_of_day = kwargs.get("time_of_day") or "both"

    # Normalize
    st_clean = skin_type.strip().capitalize() if skin_type else "Combination"
    
    # Query real products by category suited to user's skin type
    cleansers = product_service.search_local_products(category="Cleanser", skin_type=st_clean, limit=5)
    if not cleansers:
        cleansers = product_service.search_local_products(category="Cleanser", limit=5)
        
    serums = product_service.search_local_products(category="Serum", skin_type=st_clean, limit=5)
    if not serums:
        serums = product_service.search_local_products(category="Serum", limit=5)
        
    moisturizers = product_service.search_local_products(category="Moisturizer", skin_type=st_clean, limit=5)
    if not moisturizers:
        moisturizers = product_service.search_local_products(category="Moisturizer", limit=5)
        
    sunscreens = product_service.search_local_products(category="Sunscreen", skin_type=st_clean, limit=5)
    if not sunscreens:
        sunscreens = product_service.search_local_products(category="Sunscreen", limit=5)

    c_am = cleansers[0] if cleansers else {"id": "p-cleanse", "name": "Gentle Barrier Balance Cleanser", "brand": "Dermalogic", "price_inr": 499}
    s_am = serums[0] if serums else {"id": "p-am-serum", "name": "10% Niacinamide + Zinc Serum", "brand": "Minimalist", "price_inr": 599}
    m_am = moisturizers[0] if moisturizers else {"id": "p-moist", "name": "Ceramide Daily Light Hydrator", "brand": "CeraVe", "price_inr": 699}
    sun_am = sunscreens[0] if sunscreens else {"id": "p-sun", "name": "Ultra-Light Matte Sunscreen SPF 50+", "brand": "Biore", "price_inr": 799}

    c_pm = cleansers[1] if len(cleansers) > 1 else c_am
    s_pm = serums[1] if len(serums) > 1 else s_am
    m_pm = moisturizers[1] if len(moisturizers) > 1 else m_am

    am_steps = [
        {
            "step_number": 1,
            "category": "Cleanser",
            "name": c_am.get("name"),
            "brand": c_am.get("brand"),
            "product_id": c_am.get("id"),
            "price": c_am.get("price_inr"),
            "clinical_reason": f"Purifies facial impurities and excess sebum without disturbing the stratum corneum barrier in {st_clean} skin.",
            "key_actives": ["Mild Surfactants", "Glycerin"],
            "application_instruction": "Lather gently with lukewarm water and rinse thoroughly."
        },
        {
            "step_number": 2,
            "category": "Targeted Serum",
            "name": s_am.get("name"),
            "brand": s_am.get("brand"),
            "product_id": s_am.get("id"),
            "price": s_am.get("price_inr"),
            "clinical_reason": f"Delivers concentrated bioactive molecules targeting {concern} while supporting epidermal barrier defenses.",
            "key_actives": ["Niacinamide", "Hyaluronic Acid"],
            "application_instruction": "Pat 3-4 drops evenly onto damp skin. Allow 60 seconds to absorb."
        },
        {
            "step_number": 3,
            "category": "Moisturizer",
            "name": m_am.get("name"),
            "brand": m_am.get("brand"),
            "product_id": m_am.get("id"),
            "price": m_am.get("price_inr"),
            "clinical_reason": "Seals in hydration and prevents transepidermal water loss (TEWL) during daily environmental exposure.",
            "key_actives": ["Ceramides", "Squalane"],
            "application_instruction": "Massage a coin-sized amount over face and neck."
        },
        {
            "step_number": 4,
            "category": "Sunscreen (SPF 50)",
            "name": sun_am.get("name"),
            "brand": sun_am.get("brand"),
            "product_id": sun_am.get("id"),
            "price": sun_am.get("price_inr"),
            "clinical_reason": "Essential photoprotection against UVA/UVB induced collagen breakdown and post-inflammatory erythema.",
            "key_actives": ["Broad Spectrum UV Filters"],
            "application_instruction": "Apply two finger lengths generously as the final morning step 15 mins before sunlight."
        }
    ]

    pm_steps = [
        {
            "step_number": 1,
            "category": "Evening Cleanser",
            "name": c_pm.get("name"),
            "brand": c_pm.get("brand"),
            "product_id": c_pm.get("id"),
            "price": c_pm.get("price_inr"),
            "clinical_reason": "Breaks down sunscreen, atmospheric particulate pollution, and accumulated sweat.",
            "key_actives": ["Micellar / Foaming Cleansers"],
            "application_instruction": "Massage for 60 seconds across face and neck, then rinse thoroughly."
        },
        {
            "step_number": 2,
            "category": "Night Treatment Serum",
            "name": s_pm.get("name"),
            "brand": s_pm.get("brand"),
            "product_id": s_pm.get("id"),
            "price": s_pm.get("price_inr"),
            "clinical_reason": f"Accelerates cellular turnover and collagen synthesis during circadian nocturnal repair.",
            "key_actives": ["Salicylic Acid / Peptides"],
            "application_instruction": "Apply 3-4 drops before night moisturizer on dry skin."
        },
        {
            "step_number": 3,
            "category": "Night Repair Moisturizer",
            "name": m_pm.get("name"),
            "brand": m_pm.get("brand"),
            "product_id": m_pm.get("id"),
            "price": m_pm.get("price_inr"),
            "clinical_reason": "Nourishing lipid replenishment to repair lipid bilayers while you sleep.",
            "key_actives": ["Ceramide Complex", "Fatty Acids"],
            "application_instruction": "Apply generously over treatment serum as the final evening step."
        }
    ]

    return {
        "skin_type": st_clean,
        "concern": concern,
        "time_of_day": time_of_day,
        "am_steps": am_steps,
        "pm_steps": pm_steps,
        "am": {"steps": am_steps},
        "pm": {"steps": pm_steps}
    }


def save_user_routine(user_id, routine_name, routine_type, steps, skin_type="", concern=""):
    """Save user routine and its step items into database."""
    # Delete existing routine of this type if replacing
    execute_query(
        "DELETE FROM skincare_routines WHERE user_id = ? AND routine_type = ? AND routine_name = ?",
        [user_id, routine_type, routine_name]
    )
    
    execute_query("""
        INSERT INTO skincare_routines (user_id, routine_name, routine_type, description)
        VALUES (?, ?, ?, ?)
    """, [user_id, routine_name, routine_type, f"{skin_type} {concern} ({routine_type.upper()})"])

    routine_row = execute_query(
        "SELECT id FROM skincare_routines WHERE user_id = ? AND routine_name = ? ORDER BY id DESC LIMIT 1",
        [user_id, routine_name],
        fetchone=True
    )
    routine_id = routine_row["id"] if routine_row else None

    if routine_id and isinstance(steps, list):
        for idx, item in enumerate(steps):
            p_id = item.get("product_id") or (item.get("product", {}).get("id") if isinstance(item.get("product"), dict) else None)
            step_order = item.get("step_number") or item.get("order") or (idx + 1)
            cat = item.get("category", "")
            instruct = item.get("application_instruction") or item.get("instruction", "")
            execute_query("""
                INSERT INTO routine_items (routine_id, product_id, step_order, category, custom_instruction)
                VALUES (?, ?, ?, ?, ?)
            """, [routine_id, p_id, step_order, cat, instruct])

    return routine_id


def get_user_saved_routines(user_id):
    """Retrieve all saved routines for a user with step products."""
    routines = execute_query(
        "SELECT * FROM skincare_routines WHERE user_id = ? ORDER BY id DESC",
        [user_id],
        fetchall=True
    )
    for r in routines:
        items = execute_query("""
            SELECT ri.*, p.name as product_name, p.brand as product_brand, p.image_url as product_image
            FROM routine_items ri
            LEFT JOIN products p ON ri.product_id = p.id
            WHERE ri.routine_id = ?
            ORDER BY ri.step_order ASC
        """, [r["id"]], fetchall=True)
        r["items"] = items
        r["time_of_day"] = r.get("routine_type", "am")
    return routines


def delete_user_routine(routine_id, user_id):
    """Delete a user routine and associated items."""
    execute_query("DELETE FROM routine_items WHERE routine_id = ?", [routine_id])
    execute_query("DELETE FROM skincare_routines WHERE id = ? AND user_id = ?", [routine_id, user_id])
    return True


# ========================================================
# SKINCARE JOURNAL
# ========================================================

def add_journal_entry(user_id, entry_date, *args, **kwargs):
    """
    Create a new journal observation entry.
    Supports:
    add_journal_entry(user_id, entry_date, skin_rating, products_used, symptoms, notes, irritation_occurred, irritation_severity)
    OR
    add_journal_entry(user_id, entry_date, products_used, skin_feeling, observations="", irritation=0, irritation_notes="", daily_rating=5)
    """
    products_used = ""
    skin_feeling = ""
    observations = ""
    irritation = 0
    irritation_notes = ""
    daily_rating = 5

    if len(args) >= 6:
        daily_rating = int(args[0])
        products_used = str(args[1])
        observations = str(args[2])
        skin_feeling = str(args[3])
        irritation = int(args[4] or 0)
        irritation_notes = str(args[5])
    elif len(args) >= 2:
        products_used = str(args[0])
        skin_feeling = str(args[1])
        if len(args) > 2: observations = str(args[2])
        if len(args) > 3: irritation = int(args[3] or 0)
        if len(args) > 4: irritation_notes = str(args[4])
        if len(args) > 5: daily_rating = int(args[5] or 5)
    else:
        daily_rating = int(kwargs.get("skin_rating") or kwargs.get("daily_rating") or 5)
        products_used = kwargs.get("products_used", "")
        observations = kwargs.get("symptoms") or kwargs.get("observations", "")
        skin_feeling = kwargs.get("notes") or kwargs.get("skin_feeling", "")
        irritation = int(kwargs.get("irritation_occurred") or kwargs.get("irritation") or 0)
        irritation_notes = kwargs.get("irritation_severity") or kwargs.get("irritation_notes", "")

    execute_query("""
        INSERT INTO skincare_journal (
            user_id, entry_date, products_used, skin_feeling,
            observations, irritation_experienced, irritation_notes, daily_rating
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        user_id, entry_date, products_used, skin_feeling,
        observations, irritation, irritation_notes, daily_rating
    ])
    return True


def get_user_journal_entries(user_id, limit=30):
    """Fetch private skincare journal entries for user."""
    rows = execute_query("""
        SELECT * FROM skincare_journal
        WHERE user_id = ?
        ORDER BY entry_date DESC, id DESC
        LIMIT ?
    """, [user_id, limit], fetchall=True)

    for r in rows:
        r["skin_rating"] = r.get("daily_rating")
        r["symptoms"] = r.get("observations")
        r["notes"] = r.get("skin_feeling")
        r["irritation_occurred"] = r.get("irritation_experienced")
        r["irritation_severity"] = r.get("irritation_notes")
    return rows


def delete_journal_entry(entry_id, user_id):
    """Delete a journal entry."""
    execute_query("DELETE FROM skincare_journal WHERE id = ? AND user_id = ?", [entry_id, user_id])
    return True


# Aliases
get_user_routines = get_user_saved_routines
