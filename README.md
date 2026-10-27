# Skincare AI 🧴

Hey! This is **Skincare AI**, a project I made to make skincare a little less confusing. There are so many ingredients and products out there, and sometimes it's hard to know where to start. So, I wanted to bring some useful skincare information and product discovery options together in one place.

## 🌐 Try it out

👉 **Live website:** [Click here to open Skincare AI](https://skincare-ai-celq.onrender.com)

*I'll replace this with my actual live link once the deployment is ready.*

## ✨ What can you do here?

- **Ask AI:** Ask skincare-related questions and get easy-to-understand answers.
- **Learn about ingredients:** Explore common ingredients and what they're generally used for.
- **My Skin:** Share your skin type and concerns to get general skincare guidance.
- **Find products:** Browse the product catalog and look for options that match your needs.
- **Filter and sort:** Narrow products by category, ingredient, skin type, budget, and rating. You can also sort by price, rating, or popularity.
- **Share feedback:** Leave a rating or feedback about the app.

## 🛠️ What I used to build it

- Python
- Flask
- HTML and CSS
- Ollama Cloud (`gpt-oss:120b`) for AI features
- `python-dotenv` for environment variables
- SQLite for local feedback storage, with PostgreSQL support that can be configured for deployment

## 📂 Project structure

```text
skincare_ai/
├── app.py
├── products_data.py
├── requirements.txt
├── test_ollama.py
├── templates/
├── static/
├── instance/
├── .env
└── .gitignore
```

The `templates` folder contains the HTML pages, while `static` contains the styling and other static files.

## 💻 Want to run it on your computer?

### 1. Get the project

Download or clone this repository, then open a terminal in the project folder (the folder containing `app.py`).

### 2. Create a virtual environment

**Windows:**

```bat
py -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install the required packages

```bash
python -m pip install -r requirements.txt
```

### 4. Set up the API key

Create a `.env` file in the main project folder and add your own Ollama Cloud API key:

```env
OLLAMA_API_KEY=your_ollama_cloud_api_key
```

Keep your real API key private. Don't upload the `.env` file to GitHub.

### 5. Run the app

```bash
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The AI features need an internet connection and a valid Ollama Cloud API key.

## 🚀 Deployment

This project can be deployed as a web service on Render.

Typical settings:

**Build command**
```bash
pip install -r requirements.txt
```

**Start command**
```bash
gunicorn app:app
```

Add `OLLAMA_API_KEY` in the hosting service's environment variables. Once the deployment is working, update the live link at the top of this README.

If you collect feedback in production, configure persistent database storage. A local SQLite file may not persist across deployments on some hosting platforms.

## ⚠️ A small note

This project is for learning and general skincare information. It isn't a medical tool and can't diagnose skin conditions. If you have a persistent or serious skin concern, it's best to consult a qualified dermatologist. Product prices, ratings, and other catalog details may be demo information, so please check the seller or brand website before buying anything.

## 💗 Thanks for checking out my project!

I'm still learning and improving things, so feedback and suggestions are always welcome.
