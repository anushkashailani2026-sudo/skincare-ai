# Skincare AI — AI-Powered Skincare Product Research & Analysis

Skincare AI is a skincare research and analysis platform powered by Groq AI. It helps users understand skincare ingredients, compare products, assess skin suitability, build routines, and explore skincare-related concerns.

**Live Website:** https://skincare-ai-celq.onrender.com
**GitHub Repository:** https://github.com/anushkashailani2026-sudo/skincare-ai

---

## Core Features

### 1. Product Packaging Scanner
- Extracts product names, brands, barcodes, and ingredient information from packaging images.
- Supports image uploads in JPG, PNG, and WEBP formats.
- Uses barcode lookup and product catalogue matching.
- Processes images using Pillow.

### 2. Ingredient and Skin Analysis
- Identifies common skincare ingredients such as Niacinamide, Salicylic Acid, Hyaluronic Acid, Ceramides, Retinol, and Vitamin C.
- Highlights potential irritants and sensitizers.
- Provides skin-type compatibility information.
- Generates AI-assisted ingredient explanations and skin analysis.

### 3. Product Comparison
- Compare two or more skincare products.
- Review common and different ingredients.
- Examine product benefits, prices, and suitability information.

### 4. Personalized Skincare Routines
- Build AM and PM skincare routines.
- Organize products into skincare steps.
- Identify potential ingredient conflicts.
- Save and manage routines through user accounts.

### 5. Skincare Journal
- Record daily skincare activities.
- Track skin comfort, symptoms, and irritation.
- Maintain a personal skincare progress history.

### 6. User Accounts and Reviews
- User registration and login.
- Password hashing using Bcrypt.
- Product reviews with ratings and written feedback.
- Review moderation and status tracking.

### 7. Admin Dashboard
- Separate administrator login and dashboard.
- Approve, reject, flag, and manage reviews.
- View notifications for new submissions.
- Export review and feedback data as CSV.
- Manage administrator credentials.

### 8. Admin Notifications
- Floating notification cards for new product reviews.
- Display reviewer and product information.
- Allow administrators to navigate to submitted reviews.

---

## AI Architecture

AI operations are centralized through `groq_service.py`.

| Feature | Configured Groq Model |
|---|---|
| Ask AI Assistant | `openai/gpt-oss-120b` |
| Ingredient Analysis | `openai/gpt-oss-120b` |
| Skin Assessment | `openai/gpt-oss-120b` |
| Product Assistant | `openai/gpt-oss-120b` |
| Formulation Analysis | `openai/gpt-oss-120b` |
| Packaging Vision OCR | `qwen/qwen3.8-27b` |

The models can be configured through environment variables.

---

## Database

The application supports:

- **SQLite:** Used for local development.
- **PostgreSQL:** Supported through the database configuration for hosted deployments.

The database includes tables for:

- Products
- Users
- User profiles
- Product reviews
- Skincare routines
- Routine items
- Skincare journal entries
- Website feedback
- Administrator accounts
- External reviews
- Product prices

**Important deployment note:** If Render is using SQLite without a persistent disk, database data may not survive service restarts or redeployments. PostgreSQL migration and persistent production storage are separate setup tasks and should be completed before relying on permanent user data.

---

## Local Installation

### 1. Clone the Repository

```bash
git clone https://github.com/anushkashailani2026-sudo/skincare-ai.git
cd skincare-ai
```

### 2. Create a Virtual Environment

**Windows:**

```powershell
python -m venv venv
```

**macOS / Linux:**

```bash
python3 -m venv venv
```

### 3. Install Dependencies

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root.

You can use `.env.example` as the template.

Configure the following variables:

```ini
# Database
DATABASE_URL=

# Initial Administrator Credentials
ADMIN_ID=admin
ADMIN_PASSWORD=replace_with_a_strong_password

# Session Security
SESSION_SECRET=replace_with_a_long_random_secret

# Groq API
GROQ_API_KEY=your_groq_api_key_here
GROQ_TEXT_MODEL=openai/gpt-oss-120b
GROQ_VISION_MODEL=qwen/qwen3.8-27b

# Environment
NODE_ENV=development
```

Keep your actual `.env` file private. Never upload API keys, passwords, or secret values to GitHub.

### 5. Run the Application

**Windows PowerShell:**

```powershell
& ".\venv\Scripts\python.exe" app.py
```

Open the application at:

http://127.0.0.1:5000

---

## Testing

Run the Groq integration and AI tests:

```powershell
& ".\venv\Scripts\python.exe" test_groq.py
```

Run the master test suite:

```powershell
& ".\venv\Scripts\python.exe" test_master_suite.py
```

Run scanner and vision tests:

```powershell
& ".\venv\Scripts\python.exe" test_scanner_vision.py
```

Run beauty API tests:

```powershell
& ".\venv\Scripts\python.exe" test_beauty_api.py
```

---

## Render Deployment

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
gunicorn app:app
```

### Environment Variables

Configure the required variables in the Render service dashboard:

| Variable | Value |
|---|---|
| `GROQ_API_KEY` | Your private Groq API key |
| `GROQ_TEXT_MODEL` | `openai/gpt-oss-120b` |
| `GROQ_VISION_MODEL` | `qwen/qwen3.8-27b` |
| `ADMIN_ID` | Your chosen administrator ID |
| `ADMIN_PASSWORD` | A strong administrator password |
| `SESSION_SECRET` | A long, random secret |
| `NODE_ENV` | `production` |

`DATABASE_URL` should only be configured when a PostgreSQL database is available and the application is ready to use it.

---

## Security and Privacy

- Passwords are hashed using Bcrypt.
- Session cookies use secure settings in production.
- Input validation and sanitization are applied.
- Security headers help protect against common web vulnerabilities.
- Administrator routes are protected.
- API keys and environment secrets are kept outside the Git repository.
- Local database files and temporary files are excluded through `.gitignore`.

---

## Technologies Used

- Python
- Flask
- Groq API
- SQLite
- PostgreSQL support
- HTML
- CSS
- JavaScript
- Pillow
- Bcrypt
- Gunicorn

---

**Project:** Skincare AI
**Repository:** https://github.com/anushkashailani2026-sudo/skincare-ai
**Deployment:** https://skincare-ai-celq.onrender.com