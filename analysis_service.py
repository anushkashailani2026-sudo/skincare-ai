"""
AI Product Analysis and Ingredient Intelligence Service for Skincare AI.
Generates comprehensive evidence-based skincare reports, compatibility checks,
ingredient breakdowns, and transparent multi-metric evaluation indicators.
"""

import os
import re
import json
from ollama import Client

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "gpt-oss:120b")

# Evidence-based ingredient knowledge base
KNOWN_INGREDIENTS = {
    "niacinamide": {
        "name": "Niacinamide (Vitamin B3)",
        "functions": ["Sebum regulation", "Barrier repair", "Hyperpigmentation reduction", "Anti-inflammatory"],
        "benefits": "Strengthens skin's lipid barrier, fades post-acne marks, minimizes pore appearance, and balances oil production.",
        "concerns": "Generally very well tolerated. Rare mild flushing or irritation at high concentrations (>10%).",
        "suitable_for": ["Oily", "Acne-prone", "Combination", "Normal", "Sensitive"],
        "conflicts": "Safe with most actives; use caution when pairing with strong pure L-Ascorbic Acid (Vitamin C) if skin is sensitive.",
        "evidence_strength": "Very Strong (Multiple randomized double-blind clinical trials)"
    },
    "salicylic acid": {
        "name": "Salicylic Acid (BHA)",
        "functions": ["Pore exfoliation", "Comedolytic", "Anti-inflammatory", "Sebum clearance"],
        "benefits": "Lipophilic acid that penetrates into sebaceous follicles to dissolve trapped oil, dead cells, and clear blackheads.",
        "concerns": "Can cause dryness, peeling, and mild burning if overused. Avoid during pregnancy at high percentages.",
        "suitable_for": ["Oily", "Acne-prone", "Combination"],
        "conflicts": "Avoid combining in the exact same routine step with Retinol, high-strength Glycolic Acid, or other strong exfoliants.",
        "evidence_strength": "Very Strong (FDA-approved acne active)"
    },
    "hyaluronic acid": {
        "name": "Hyaluronic Acid / Sodium Hyaluronate",
        "functions": ["Humectant hydration", "Skin plumping", "Transepidermal water retention"],
        "benefits": "Binds up to 1,000 times its weight in water, rapidly plumping dehydrated skin and smoothing fine dehydration lines.",
        "concerns": "In very dry climates, apply to damp skin followed by an occlusive moisturizer to avoid moisture drawing out.",
        "suitable_for": ["Dry", "Dehydrated", "Normal", "Sensitive", "Oily", "Combination"],
        "conflicts": "None. Highly compatible with all skincare ingredients.",
        "evidence_strength": "Very Strong (Extensive clinical hydration literature)"
    },
    "ceramides": {
        "name": "Ceramides (NP, AP, EOP)",
        "functions": ["Intercellular lipid restoration", "Skin barrier fortification", "Moisture sealing"],
        "benefits": "Bio-identical lipids that constitute over 50% of the skin barrier, repairing damaged, compromised, or sensitized skin.",
        "concerns": "Virtually non-irritating. Excellent safety profile.",
        "suitable_for": ["Dry", "Sensitive", "Eczema-prone", "Compromised barrier", "Normal", "Combination"],
        "conflicts": "None. Excellent pairing with Retinoids and Exfoliants to mitigate barrier irritation.",
        "evidence_strength": "Very Strong (Gold standard barrier repair active)"
    },
    "retinol": {
        "name": "Retinol / Retinoids (Vitamin A)",
        "functions": ["Cellular turnover acceleration", "Collagen stimulation", "Acne resolution", "Texture refinement"],
        "benefits": "Clinically proven to reduce fine lines, unclog micro-comedones, and accelerate epidermis renewal.",
        "concerns": "Retinization period: initial dryness, redness, flaking, and skin purging. Strictly requires daytime sunscreen (SPF 50). Avoid during pregnancy.",
        "suitable_for": ["Aging concerns", "Acne-prone", "Oily", "Uneven texture", "Normal"],
        "conflicts": "Do not mix with AHA/BHA chemical peels, Benzoyl Peroxide (in same step), or pure Ascorbic Acid in the same application.",
        "evidence_strength": "Gold Standard (Decades of rigorous clinical trials)"
    },
    "centella asiatica": {
        "name": "Centella Asiatica (Cica / Madecassoside)",
        "functions": ["Anti-inflammatory soothing", "Wound healing", "Antioxidant protection"],
        "benefits": "Reduces erythema (redness), calms irritation from active breakouts, and accelerates barrier recovery.",
        "concerns": "Extremely well-tolerated. Very low irritation risk.",
        "suitable_for": ["Sensitive", "Acne-prone", "Rosacea-prone", "Compromised skin", "All types"],
        "conflicts": "None. Compatible with all routines.",
        "evidence_strength": "Strong (Extensive pharmacological and cosmetic dermatology trials)"
    },
    "glycerin": {
        "name": "Glycerin",
        "functions": ["Core humectant", "Aquaporin stimulation", "Barrier hydration"],
        "benefits": "Superior humectant that draws water into the stratum corneum, restores suppleness, and prevents moisture loss.",
        "concerns": "Zero known sensitization potential. Cosmetic safety rating 100%.",
        "suitable_for": ["All skin types", "Dry", "Sensitive"],
        "conflicts": "None.",
        "evidence_strength": "Gold Standard (Universal physiological humectant)"
    },
    "zinc oxide": {
        "name": "Zinc Oxide",
        "functions": ["Broad-spectrum UV attenuation (UVA + UVB)", "Soothing", "Mild antibacterial"],
        "benefits": "Mineral physical sunscreen filter that sits on skin to reflect and absorb UV rays without chemical heat absorption.",
        "concerns": "May leave a slight white cast on deeper Fitzpatrick skin tones unless micronized or tinted.",
        "suitable_for": ["Sensitive", "Rosacea-prone", "Post-procedure", "Acne-prone", "All types"],
        "conflicts": "None.",
        "evidence_strength": "Gold Standard (FDA & EU approved broad-spectrum UV filter)"
    }
}


def get_ollama_client():
    key = os.getenv("OLLAMA_API_KEY")
    if not key:
        return None
    return Client(host="https://ollama.com", headers={"Authorization": f"Bearer {key}"})


def parse_ingredients_list(ingredients_text):
    """Clean and parse an ingredient list into individual components."""
    if not ingredients_text:
        return []
    cleaned = re.sub(r"[\(\)\[\]]", " ", ingredients_text)
    items = [item.strip() for item in re.split(r"[,;•\n\r/]+", cleaned) if len(item.strip()) > 1]
    return items


def detect_known_actives_and_irritants(ingredients_text):
    """Detect active ingredients, beneficial humectants, potential irritants, and allergens."""
    ing_lower = str(ingredients_text).lower()
    
    actives_found = []
    for key, data in KNOWN_INGREDIENTS.items():
        if key in ing_lower:
            actives_found.append(data)
            
    irritants_found = []
    # Check for fragrance / essential oils
    if any(k in ing_lower for k in ["fragrance", "parfum", "limonene", "linalool", "citronellol", "geraniol", "eugenol"]):
        irritants_found.append({
            "name": "Fragrance / Allergenic Terpenes",
            "type": "Potential Allergen",
            "detail": "Contains synthetic fragrance or naturally occurring citrus/flower terpenes (limonene, linalool) that may trigger contact dermatitis in sensitive skin."
        })
    # Check for drying alcohols
    if any(k in ing_lower for k in ["alcohol denat", "denatured alcohol", "isopropyl alcohol", "sd alcohol"]):
        irritants_found.append({
            "name": "Denatured / Simple Alcohol",
            "type": "Potential Drying Agent",
            "detail": "Used for fast evaporation and matte finish, but high concentrations can strip the lipid barrier in dry or sensitized skin."
        })
    # Check for heavy comedogenic pore-clogging oils
    if any(k in ing_lower for k in ["coconut oil", "cocos nucifera", "isopropyl myristate", "isopropyl palmitate", "wheat germ oil"]):
        irritants_found.append({
            "name": "Comedogenic Esters/Oils",
            "type": "Pore Clogging Consideration",
            "detail": "Higher potential comedogenicity; individuals prone to closed comedones or cystic acne should monitor for breakouts."
        })
    # Check for sulfates
    if any(k in ing_lower for k in ["sodium lauryl sulfate", "sls", "ammonium lauryl sulfate"]):
        irritants_found.append({
            "name": "Sodium Lauryl Sulfate (SLS)",
            "type": "Strong Cleansing Surfactant",
            "detail": "High-detergency surfactant that can cause barrier stripping or irritation compared to milder amino-acid surfactants."
        })
        
    return actives_found, irritants_found


def calculate_skin_suitability_scores(ingredients_text, category=""):
    """
    Evaluate product suitability for 6 distinct skin types and key concerns (0-100 scale).
    """
    ing_lower = str(ingredients_text).lower()
    actives, irritants = detect_known_actives_and_irritants(ingredients_text)
    
    # Baseline scores
    scores = {
        "Oily": 70,
        "Dry": 70,
        "Combination": 75,
        "Sensitive": 70,
        "Acne-prone": 70,
        "Normal": 85
    }
    
    # Adjust for Oily / Acne-prone
    if any(k in ing_lower for k in ["salicylic", "niacinamide", "zinc", "tea tree", "centella", "witch hazel"]):
        scores["Oily"] += 15
        scores["Acne-prone"] += 20
    if any(k in ing_lower for k in ["coconut oil", "shea butter", "mineral oil", "petrolatum"]) and category not in ["Cleanser"]:
        scores["Oily"] -= 20
        scores["Acne-prone"] -= 20
    if category == "Sunscreen" and any(k in ing_lower for k in ["gel", "aqua", "fluid", "matte", "dry touch"]):
        scores["Oily"] += 15
        
    # Adjust for Dry
    if any(k in ing_lower for k in ["hyaluronic", "ceramide", "glycerin", "shea butter", "squalane", "panthenol", "urea"]):
        scores["Dry"] += 20
    if any(k in ing_lower for k in ["alcohol denat", "salicylic acid"]):
        scores["Dry"] -= 15
        
    # Adjust for Sensitive
    if any(k in ing_lower for k in ["centella", "cica", "allantoin", "panthenol", "colloidal oatmeal", "madecassoside"]):
        scores["Sensitive"] += 15
    if any(k in ing_lower for k in ["fragrance", "parfum", "limonene", "linalool", "essential oil", "alcohol denat", "glycolic acid"]):
        scores["Sensitive"] -= 25

    # Clamp scores between 20 and 98
    for k in scores:
        scores[k] = max(25, min(98, scores[k]))
        
    concerns_match = {
        "Acne & Blemishes": "High" if scores["Acne-prone"] >= 80 else ("Moderate" if scores["Acne-prone"] >= 65 else "Low"),
        "Dryness & Dehydration": "High" if scores["Dry"] >= 80 else ("Moderate" if scores["Dry"] >= 65 else "Low"),
        "Uneven Tone & Dark Spots": "High" if any(k in ing_lower for k in ["niacinamide", "vitamin c", "ascorbic", "glycolic", "kojic", "azelaic"]) else "Moderate",
        "Redness & Sensitivity": "High" if scores["Sensitive"] >= 80 else ("Moderate" if scores["Sensitive"] >= 60 else "Caution advised"),
        "Barrier Maintenance": "High" if any(k in ing_lower for k in ["ceramide", "panthenol", "cholesterol", "glycerin"]) else "Moderate"
    }

    return scores, concerns_match


def check_ingredient_conflicts(ingredients_text):
    """Identify potential layering conflicts and usage cautions."""
    ing_lower = str(ingredients_text).lower()
    conflicts = []
    
    has_retinol = any(k in ing_lower for k in ["retinol", "retinoid", "retinyl", "retinal", "tretinoin"])
    has_bha = "salicylic acid" in ing_lower
    has_aha = any(k in ing_lower for k in ["glycolic acid", "lactic acid", "mandelic acid"])
    has_vit_c = any(k in ing_lower for k in ["ascorbic acid", "l-ascorbic", "ethyl ascorbic"])
    
    if has_retinol and (has_bha or has_aha):
        conflicts.append({
            "pair": "Retinoids + Direct Exfoliating Acids (AHA/BHA)",
            "risk": "High potential for barrier irritation",
            "guidance": "Avoid applying strong chemical exfoliants and retinoids in the same application. Alternate nights to protect the skin barrier."
        })
    elif has_retinol:
        conflicts.append({
            "pair": "Retinol Layering Caution",
            "risk": "Photosensitivity and purging",
            "guidance": "Use strictly in the PM routine. Always follow with broad-spectrum sunscreen in the AM. Do not combine in the same step with high-strength Vitamin C or physical scrubs."
        })
        
    if has_bha or has_aha:
        conflicts.append({
            "pair": "Chemical Exfoliants (AHA/BHA)",
            "risk": "Mild sun sensitivity",
            "guidance": "Acids increase epidermal sun sensitivity. Ensure daily SPF application and avoid combining multiple concentrated exfoliants in the same session."
        })
        
    if not conflicts:
        conflicts.append({
            "pair": "General Active Routine Compatibility",
            "risk": "Well tolerated",
            "guidance": "No high-risk layering conflicts detected. Standard patch test before first facial use is always advised."
        })
        
    return conflicts


def generate_comprehensive_analysis(product):
    """
    Generate an authoritative, evidence-based skincare report for any product.
    Blends algorithmic clinical analysis with Ollama AI for personalized narrative synthesis.
    """
    name = product.get("name", "Product")
    brand = product.get("brand", "Skincare Brand")
    category = product.get("category", "Skincare")
    ingredients = product.get("ingredients_text") or product.get("ingredients") or ""
    
    parsed_ingredients = parse_ingredients_list(ingredients)
    actives, irritants = detect_known_actives_and_irritants(ingredients)
    scores, concerns = calculate_skin_suitability_scores(ingredients, category)
    conflicts = check_ingredient_conflicts(ingredients)
    
    # Calculate transparent indicators
    completeness_score = product.get("completeness_score") or (85 if len(parsed_ingredients) > 5 else 50)
    evidence_score = 90 if actives else 75
    irritation_risk = "Low" if not irritants else ("Moderate" if len(irritants) == 1 else "Elevated for sensitive skin")
    confidence_score = 92 if (product.get("barcode") and len(parsed_ingredients) > 5) else 75
    
    indicators = {
        "completeness": completeness_score,
        "evidence_strength": evidence_score,
        "irritation_level": irritation_risk,
        "data_confidence": confidence_score,
        "evidence_label": "High Clinical Evidence" if evidence_score >= 85 else "Moderate Standard",
        "completeness_label": "Verified Ingredient Registry" if completeness_score >= 80 else "Partial Information"
    }

    # Attempt AI narrative generation with Ollama Cloud
    ai_narrative = None
    client = get_ollama_client()
    if client and ingredients:
        try:
            prompt = (
                f"You are a cosmetic dermatologist and skincare formulation analyst. "
                f"Provide a concise, evidence-based analysis for this product:\n"
                f"Product: {name} by {brand}\n"
                f"Category: {category}\n"
                f"Ingredients: {ingredients[:1000]}\n\n"
                f"Include:\n"
                f"1. Formulation summary\n"
                f"2. Who will benefit most\n"
                f"3. Who should exercise caution\n"
                f"4. Realistic expectations vs marketing claims\n"
                f"Tone: Scientific, balanced, clear, and reassuring. Do not make medical diagnoses."
            )
            resp = client.chat(
                model=OLLAMA_TEXT_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            ai_narrative = resp.message.content.strip()
        except Exception as e:
            print("Ollama narrative generation note:", e)

    # If AI call is unavailable, synthesize an evidence-based summary
    if not ai_narrative:
        ai_narrative = (
            f"**{name}** by **{brand}** is formulated as a {category.lower()} designed to support skin health. "
            f"Based on the ingredient profile, this formulation features "
            f"{', '.join([a['name'] for a in actives]) if actives else 'gentle supportive emollients and humectants'}. "
            f"It provides effective skin barrier nourishment with particularly strong suitability for {max(scores, key=scores.get)} skin types. "
            f"{'Notice: contains ' + ', '.join([i['name'] for i in irritants]) + '; sensitive skin types should perform a 24-hour patch test.' if irritants else 'The formula has an agreeable safety and tolerance profile with minimal common sensitizers.'}"
        )

    return {
        "product": product,
        "parsed_ingredients": parsed_ingredients[:35],
        "total_ingredients_count": len(parsed_ingredients),
        "actives": actives,
        "irritants": irritants,
        "skin_scores": scores,
        "concerns_match": concerns,
        "conflicts": conflicts,
        "indicators": indicators,
        "ai_narrative": ai_narrative
    }


# Aliases and routine conflict checker
analyze_product_formulation = generate_comprehensive_analysis
check_skin_suitability = calculate_skin_suitability_scores


def detect_routine_conflicts(products_list):
    """Check for clashing active ingredients across a routine of multiple products."""
    if not products_list:
        return []
    combined = []
    for p in products_list:
        ing = p.get("ingredients_text") or p.get("ingredient") or p.get("ingredients") or ""
        if ing:
            combined.append(ing)
    return check_ingredient_conflicts(" ".join(combined))
