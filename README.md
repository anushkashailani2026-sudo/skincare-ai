# ✦ Skincare AI — AI-Powered Skincare Product Research & Analysis Platform

> **Live Deployment:** [https://skincare-ai-celq.onrender.com](https://skincare-ai-celq.onrender.com)  
> **Repository:** `https://github.com/anushkashailani2026-sudo/skincare-ai.git`

Skincare AI is an advanced, evidence-based skincare intelligence platform designed to decode cosmetic formulations, detect active conflicts, analyze packaging labels via Vision OCR, build personalized AM/PM regimens, and empower consumers with genuine product reviews and moderation.

---

## 🌟 Core Features & Modules

### 1. 📷 Product Packaging OCR & Barcode Scanner
- **Vision OCR Extraction:** Upload packaging photographs (JPG, PNG, WEBP) to extract Brand Name, Full Product Title, Barcode Number, and Ingredient Text using Ollama Cloud Vision (`gemma4:31b`).
- **Barcode & Catalogue Matcher:** Instant lookup against local database and Open Beauty Facts API.
- **Image Sanitization:** Automatic resizing, format normalization, and memory optimization via Pillow.

### 2. 🔬 Formulation Intelligence & Skin Suitability Analysis
- **Evidence-Based Actives Detection:** Identifies Niacinamide, Salicylic Acid, Hyaluronic Acid, Ceramides, Retinol, Centella Asiatica, Vitamin C, Zinc Oxide, etc.
- **Sensitizer & Irritant Scanning:** Scans for drying alcohols, heavy synthetic fragrances, sulfates, and pore-clogging comedogenic esters.
- **Skin Type Compatibility Meter:** Evaluates suitability percentages across 6 skin profiles (Oily, Dry, Combination, Sensitive, Acne-Prone, Normal).
- **Clinical AI Narrative Synthesis:** Combines algorithmic ingredient analysis with Ollama AI for dermatological summaries.

### 3. ⚖️ Head-to-Head Product Formulation Comparison
- Compare 2 to 3 skincare products side-by-side.
- Inspect shared vs. unique active ingredients, key functional benefits, price per unit, and suitability scores in a unified matrix.

### 4. ✨ Personalized AM / PM Regimen Builder
- **Circadian Step Architecture:** Sequences products in clinical dermatological order (Cleanser → Active Serum → Moisturizer → Broad Spectrum SPF for AM; Double Cleanse → Treatment → Barrier Repair for PM).
- **Automated Conflict Detection:** Warns against hazardous active clashes (e.g. Retinoids + Direct AHA/BHA exfoliants, multiple high-strength peeling acids).
- **Save & Manage Routines:** Registered users can save custom AM/PM regimens to their private profile.

### 5. 📔 Daily Epidermal Progress Journal
- Log daily skincare products applied, skin comfort ratings (1 to 5 stars), symptoms (purging, glow, redness), and environmental notes.
- Flag irritation episodes and severity (mild, moderate, severe) to pinpoint culprit formulations.

### 6. 👤 User Authentication & Community Reviews
- Secure user registration and login with **Bcrypt** password hashing and HTTP-only session cookies.
- Verified members can submit 1-to-5 star product reviews with title, review body, skin type, primary concern, and duration of use.
- Review status tracking (Pending → Approved / Rejected / Flagged).

### 7. 🛡️ Private Admin Dashboard & Moderation Portal
- **Separate Protected Route:** `/admin/login` and `/admin/dashboard` (not linked in public navigation).
- **Product Review Moderation:** Approve, reject, flag, or delete community submissions.
- **Unseen Reviews Badge & Notification Stream:** Real-time visibility into new submissions.
- **CSV Data Export:** One-click CSV download for both product reviews and platform feedback.
- **Admin Settings:** Securely change Admin Username and Password with current password verification and strength enforcement.

### 8. 🔔 Real-time Bottom-Right Floating Notification Cards
- When any user submits a product review, authenticated administrators receive real-time floating notification cards at the bottom-right corner of the website.
- Shows product name, star rating, reviewer name, and review excerpt.
- Dismissible or clickable to navigate directly to the review in the admin moderation dashboard.
- Protected so ordinary site visitors never receive admin alerts.

---

## 🗄️ Database Architecture

The application utilizes a universal database manager (`db.py`) supporting seamless transitions between **SQLite** (local development) and **PostgreSQL** (production on Render / Supabase / Neon):

| Table Name | Description |
| :--- | :--- |
| `products` | 496 seeded products + live Open Beauty Facts API cache |
| `users` | Registered users with bcrypt password hashes |
| `user_profiles` | User skin types, concerns, and sensitivity preferences |
| `user_reviews` | Community product reviews with moderation status & admin_seen flag |
| `skincare_routines` | Saved AM/PM custom skincare regimens |
| `routine_items` | Individual product steps belonging to a routine |
| `skincare_journal` | Daily skin tracking entries and irritation logs |
| `skincare_feedback` | General website feedback entries |
| `skincare_admin` | Hashed administrator account credentials |
| `external_reviews` | Cached external review provider metrics |
| `product_prices` | Multi-retailer reference pricing |

---

## 🚀 Local Installation & Setup (Windows / macOS / Linux)

### 1. Clone the Repository
```powershell
git clone https://github.com/anushkashailani2026-sudo/skincare-ai.git
cd skincare-ai
```

### 2. Set Up Virtual Environment
```powershell
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```ini
# Database (leave blank for automatic local SQLite in instance/feedback.db)
DATABASE_URL=

# Initial Admin Credentials (seeded on first database initialization)
ADMIN_ID=admin
ADMIN_PASSWORD=admin123

# Secret Key for Sessions
SESSION_SECRET=your_super_secret_session_key_here

# Ollama Cloud API Key
OLLAMA_API_KEY=your_ollama_api_key_here
OLLAMA_TEXT_MODEL=gpt-oss:120b
OLLAMA_VISION_MODEL=gemma4:31b

# Environment
NODE_ENV=development
```

### 5. Run the Application
```powershell
# Windows PowerShell
& "venv\Scripts\python.exe" app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🧪 Automated Test Suite

Run the master test suite verifying all 9 core subsystems:
```powershell
& "venv\Scripts\python.exe" test_master_suite.py
```

Run scanner and vision OCR tests:
```powershell
& "venv\Scripts\python.exe" test_scanner_vision.py
```

---

## ☁️ Deployment on Render

The repository is configured for automated zero-downtime deployment on Render:

1. **Build Command:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Start Command:**
   ```bash
   gunicorn app:app
   ```
3. **Required Environment Variables in Render Dashboard:**
   - `ADMIN_ID`: Your chosen administrator login ID
   - `ADMIN_PASSWORD`: Your chosen administrator password
   - `SESSION_SECRET`: A secure random cryptographic secret string
   - `DATABASE_URL`: Hosted PostgreSQL connection string (Render PostgreSQL or Supabase)
   - `OLLAMA_API_KEY`: Your Ollama Cloud API key
   - `OLLAMA_TEXT_MODEL`: `gpt-oss:120b`
   - `OLLAMA_VISION_MODEL`: `gemma4:31b`
   - `NODE_ENV`: `production`

---

## 🔒 Security & Privacy Architecture

- **Zero Plain-Text Passwords:** Bcrypt salt hashing on all admin and member passwords.
- **Session Security:** `httpOnly=True`, `SameSite='Lax'`, and `secure=True` in production.
- **Input Sanitization:** Multi-layer input trimming, type enforcement, and character limits.
- **Security Headers:** Strict Content Security Policy (CSP), `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, and `X-XSS-Protection`.
- **Admin Isolation:** Unauthenticated requests to `/admin/*` or `/api/admin/*` are strictly blocked.
- **Protected Environment:** `.env`, local `.db` files, and uploaded temporary images are ignored via `.gitignore` and never committed.
