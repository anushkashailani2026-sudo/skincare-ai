from flask import Flask, render_template, request
from dotenv import load_dotenv
import os
import re
from ollama import Client

from products_data import PRODUCTS


# ========================================
# LOAD ENVIRONMENT VARIABLES
# ========================================

load_dotenv()


# ========================================
# FLASK APP
# ========================================

app = Flask(__name__)


# ========================================
# OLLAMA CLOUD
# ========================================

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

client = Client(
    host="https://ollama.com",
    headers={
        "Authorization": f"Bearer {OLLAMA_API_KEY}"
    }
)


# ========================================
# MARKDOWN / FORMATTING CLEANUP
# ========================================

def clean_markdown(text):
    """
    Converts AI output into clean plain text.
    This prevents Markdown symbols and literal HTML
    from appearing in the browser.
    """

    if not text:
        return ""

    # Remove fenced code blocks but keep their contents.
    text = re.sub(
        r"```(?:text|markdown|md|html)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )
    text = text.replace("```", "")

    # Convert common HTML line breaks to normal new lines.
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    # Remove common HTML tags.
    text = re.sub(r"<[^>]+>", "", text)

    # Remove Markdown bold / italic markers.
    text = re.sub(
        r"\*\*\*(.*?)\*\*\*",
        r"\1",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"\1",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"__(.*?)__",
        r"\1",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"(?<!\w)\*([^*\n]+)\*(?!\w)",
        r"\1",
        text
    )

    text = re.sub(
        r"(?<!\w)_([^_\n]+)_(?!\w)",
        r"\1",
        text
    )

    # Remove Markdown heading symbols.
    text = re.sub(
        r"^\s*#{1,6}\s*",
        "",
        text,
        flags=re.MULTILINE
    )

    # Remove Markdown blockquote symbols.
    text = re.sub(
        r"^\s*>\s?",
        "",
        text,
        flags=re.MULTILINE
    )

    # Remove horizontal rules.
    text = re.sub(
        r"^\s*[-_=]{3,}\s*$",
        "",
        text,
        flags=re.MULTILINE
    )

    # Clean Markdown bullet markers while keeping list text.
    text = re.sub(
        r"^\s*[-•]\s+",
        "• ",
        text,
        flags=re.MULTILINE
    )

    # Remove accidental repeated spaces.
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines.
    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()


# ========================================
# HOME PAGE
# ========================================

@app.route("/")
def home():
    return render_template("index.html")


# ========================================
# INGREDIENTS PAGE
# ========================================

@app.route("/ingredients")
def ingredients():
    return render_template("ingredient.html")


# ========================================
# INGREDIENT RESULT
# ========================================

@app.route("/ingredient/<ingredient_name>")
def ingredient_result(ingredient_name):

    display_name = ingredient_name.replace("-", " ").title()

    prompt = f"""
You are Skincare AI, a skincare education assistant.

Explain the skincare ingredient: {display_name}

Use simple, beginner-friendly language.

IMPORTANT:

- Give useful and reasonably detailed information.
- Do not make a medical diagnosis.
- Do not claim that an ingredient will definitely cure a condition.
- Use cautious language such as "may help", "is commonly used", or "can be helpful".
- Do not use Markdown formatting.
- Do not use asterisks.
- Do not use hashtags.
- Do not use backticks.
- Do not use HTML tags.
- Do not use <br>.
- Keep headings on their own lines.
- Leave a blank line between sections.
- Use numbered lists where useful.

Use exactly these sections:

1. What is it?

2. What does it do?

3. Who commonly uses it?

4. Main skincare benefits

5. How it is generally used

6. Possible side effects or irritation

7. Important precautions

8. Ingredients or products that may need extra caution when combined

9. Simple beginner tips

10. Bottom line
"""

    try:

        response = client.chat(
            model="gpt-oss:120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        result = response["message"]["content"]
        result = clean_markdown(result)

    except Exception as e:

        result = (
            "Unable to generate the ingredient information right now.\n\n"
            f"Error: {e}"
        )

    return render_template(
        "ingredient_result.html",
        ingredient=display_name,
        result=result,
        explanation=result
    )


# ========================================
# SKIN PAGE
# ========================================

@app.route("/skin")
def skin():
    return render_template("skin.html")


# ========================================
# SKIN ANALYSIS
# ========================================

@app.route("/analyze-skin", methods=["POST"])
def analyze_skin():

    skin_type = request.form.get("skin_type", "").strip()

    concerns = request.form.getlist("concerns")
    concerns_text = (
        ", ".join(concerns)
        if concerns
        else "No specific concerns selected"
    )

    frequency = request.form.get("frequency", "").strip()

    routine = request.form.get("routine", "").strip()

    goals = request.form.getlist("goals")
    goals_text = (
        ", ".join(goals)
        if goals
        else "General skincare guidance"
    )

    prompt = f"""
You are Skincare AI, a skincare education assistant.

Create a detailed but beginner-friendly personalized skincare guide
based ONLY on the information provided below.

USER PROFILE

Skin type: {skin_type}
Main concerns: {concerns_text}
Frequency of concerns: {frequency}
Current routine: {routine}
Goals: {goals_text}

IMPORTANT SAFETY RULES

- Do not make a medical diagnosis.
- Do not claim certainty about the cause of a skin concern.
- Use phrases such as "may", "can", "often", and "commonly".
- Do not prescribe medication.
- If a concern is severe, painful, persistent, rapidly worsening, infected-looking,
  or causing significant distress, recommend speaking with a qualified dermatologist.
- Keep recommendations general and skincare-education focused.
- Do not invent personal information that the user did not provide.

CONTENT REQUIREMENTS

Give a useful response rather than a very short summary.

Use EXACTLY these sections:

1. YOUR SKIN PROFILE

Briefly summarize the user's skin type, concerns, frequency,
current routine, and goals.

2. WHAT YOUR ANSWERS SUGGEST

Explain what these answers may indicate about the user's skincare needs.
Clearly separate likely skincare needs from things that cannot be determined
from a questionnaire.

3. MAIN CONCERNS

Discuss each selected concern separately.
Explain what the user can generally focus on.

4. MORNING ROUTINE

Give a simple step-by-step morning routine.
Include product TYPES rather than forcing specific brands.

5. NIGHT ROUTINE

Give a simple step-by-step night routine.
Keep it beginner-friendly.

6. WEEKLY OR OCCASIONAL CARE

Explain whether any occasional exfoliation or other care may be useful.
Do not recommend excessive exfoliation.

7. INGREDIENTS TO CONSIDER

List useful ingredient options and explain briefly what each is commonly used for.

8. INGREDIENTS TO USE CAREFULLY

Mention ingredients or combinations that may cause irritation or require
slow introduction depending on the user's profile.

9. PRODUCT TYPES TO LOOK FOR

Suggest cleanser, moisturizer, sunscreen, treatment, or other relevant
product categories based on the user's answers.

10. HOW TO INTRODUCE NEW PRODUCTS

Give a simple beginner-friendly method for introducing new products
one at a time and monitoring irritation.

11. COMMON MISTAKES TO AVOID

Give practical mistakes relevant to this user's profile.

12. GENERAL SKINCARE HABITS

Give simple non-medical habits that may support a consistent skincare routine.

13. WHEN TO CONSIDER PROFESSIONAL HELP

Explain general situations where a dermatologist or qualified healthcare
professional may be appropriate.

14. PERSONALIZED BOTTOM LINE

Give a short final summary of the most important priorities for this user.

FORMATTING RULES

- Plain text only.
- No Markdown.
- No asterisks.
- No hashtags.
- No backticks.
- No HTML.
- No <br>.
- No decorative symbols.
- Keep every heading on its own line.
- Leave a blank line between sections.
- Use numbered lists when helpful.
- Keep language simple and clear.
"""

    try:

        response = client.chat(
            model="gpt-oss:120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        result = response["message"]["content"]
        result = clean_markdown(result)

    except Exception as e:

        result = (
            "Unable to analyze the skin profile right now.\n\n"
            f"Error: {e}"
        )

    return render_template(
        "skin_result.html",
        result=result,
        skin_type=skin_type,
        concerns=concerns_text,
        frequency=frequency,
        routine=routine,
        goals=goals_text
    )


# ========================================
# PRODUCT FINDER
# ========================================

@app.route("/products", methods=["GET", "POST"])
def products():

    if request.method == "GET":
        return render_template("products.html")

    # ------------------------------------
    # GET USER SELECTIONS
    # ------------------------------------

    product_type = request.form.get(
        "product_type",
        ""
    ).strip()

    ingredient = request.form.get(
        "ingredient",
        ""
    ).strip()

    skin_type = request.form.get(
        "skin_type",
        ""
    ).strip()

    price_range = request.form.get(
        "price_range",
        ""
    ).strip()

    rating = request.form.get(
        "rating",
        ""
    ).strip()

    sort_by = request.form.get(
        "sort_by",
        ""
    ).strip()


    # ====================================
    # FILTER PRODUCTS
    # ====================================

    filtered_products = PRODUCTS.copy()


    # ------------------------------------
    # PRODUCT TYPE FILTER
    # ------------------------------------

    if product_type:

        filtered_products = [
            product
            for product in filtered_products
            if product.get(
                "category",
                ""
            ).strip().lower()
            == product_type.lower()
        ]


    # ------------------------------------
    # INGREDIENT FILTER
    # ------------------------------------

    if ingredient:

        filtered_products = [
            product
            for product in filtered_products
            if product.get(
                "ingredient",
                ""
            ).strip().lower()
            == ingredient.lower()
        ]


    # ------------------------------------
    # SKIN TYPE FILTER
    # ------------------------------------

    if skin_type and skin_type.lower() != "not sure":

        filtered_products = [
            product
            for product in filtered_products
            if any(
                skin_type.lower().strip()
                == skin.strip().lower()
                for skin in product.get(
                    "skin_types",
                    []
                )
            )
        ]


    # ====================================
    # PRICE FILTER
    # ====================================

    if price_range == "under_500":

        filtered_products = [
            product
            for product in filtered_products
            if product.get("price", 0) < 500
        ]

    elif price_range == "500_1000":

        filtered_products = [
            product
            for product in filtered_products
            if 500 <= product.get("price", 0) <= 1000
        ]

    elif price_range == "1000_1500":

        filtered_products = [
            product
            for product in filtered_products
            if 1000 <= product.get("price", 0) <= 1500
        ]

    elif price_range == "1500_plus":

        filtered_products = [
            product
            for product in filtered_products
            if product.get("price", 0) >= 1500
        ]


    # ====================================
    # RATING FILTER
    # ====================================

    if rating:

        try:

            minimum_rating = float(rating)

            filtered_products = [
                product
                for product in filtered_products
                if product.get("rating", 0) >= minimum_rating
            ]

        except ValueError:

            pass


    # ====================================
    # SORTING
    # ====================================

    if sort_by == "rating":

        filtered_products.sort(
            key=lambda product: product.get(
                "rating",
                0
            ),
            reverse=True
        )

    elif sort_by == "popularity":

        filtered_products.sort(
            key=lambda product: product.get(
                "popularity",
                0
            ),
            reverse=True
        )

    elif sort_by == "price_low":

        filtered_products.sort(
            key=lambda product: product.get(
                "price",
                0
            )
        )

    elif sort_by == "price_high":

        filtered_products.sort(
            key=lambda product: product.get(
                "price",
                0
            ),
            reverse=True
        )


   

    # ====================================
    # CREATE PRODUCT INFORMATION FOR AI
    # ====================================

    if filtered_products:

        product_information = ""

        for number, product in enumerate(
            filtered_products,
            start=1
        ):

            product_information += f"""
Product {number}:

Name: {product["name"]}
Brand: {product["brand"]}
Category: {product["category"]}
Ingredient: {product["ingredient"]}
Suitable for: {", ".join(product["skin_types"])}
Price: ₹{product["price"]}
Rating: {product["rating"]}
Popularity score: {product["popularity"]}

"""

    else:

        product_information = """
No products matched all of the selected filters.
"""


    # ====================================
    # OLLAMA PRODUCT PROMPT
    # ====================================

    prompt = f"""
You are Skincare AI, a skincare product recommendation assistant.

The user selected:

Product type:
{product_type}

Ingredient:
{ingredient}

Skin type:
{skin_type}

Budget:
{price_range}

Minimum rating:
{rating}

Sort preference:
{sort_by}

Here is the product information available in our database:

{product_information}

IMPORTANT:

Only discuss products that appear in the database above.

Do not invent additional products.

Do not change the prices.

Do not change the ratings.

Do not change the ingredients.

Do not invent availability or stock information.

Do not invent shopping links.

If no products matched, clearly say that no products matched
the selected filters and suggest relaxing one filter.

Use this structure:

YOUR MATCH

Briefly explain what the user's selections mean.

RECOMMENDED PRODUCTS

For every matching product, explain:

Product name
Brand
Price
Rating
Why it matches

WHY THESE PRODUCTS

Explain why these products fit the user's selected skin type,
ingredient and category.

WHAT TO BE CAREFUL WITH

Mention relevant precautions.

HOW TO CHOOSE

Give a short checklist for comparing the products.

BOTTOM LINE

Give a short personalized conclusion.

FORMATTING:

Do not use Markdown.

Do not use asterisks.

Do not use hashtags.

Do not use backticks.

Do not use HTML.

Do not use <br>.

Do not use bold or italic formatting.

Keep headings clearly separated.

Use short paragraphs.

Use numbered lists where appropriate.

Keep the language simple and beginner-friendly.

Do not make medical diagnoses.
"""


    # ====================================
    # ASK OLLAMA
    # ====================================

    try:

        response = client.chat(
            model="gpt-oss:120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        result = response["message"]["content"]
        result = clean_markdown(result)

    except Exception as e:

        result = (
            "The products were filtered successfully, "
            "but the AI explanation could not be generated.\n\n"
            f"Error: {e}"
        )


    # ====================================
    # SHOW RESULT PAGE
    # ====================================

    return render_template(
        "product_result.html",
        result=result,
        products=filtered_products,
        product_type=product_type,
        ingredient=ingredient,
        skin_type=skin_type,
        price_range=price_range,
        rating=rating,
        sort_by=sort_by
    )


# ========================================
# ASK AI
# ========================================

@app.route("/ask-ai", methods=["GET", "POST"])
def ask_ai():

    # ------------------------------------
    # OPEN ASK AI PAGE
    # ------------------------------------

    if request.method == "GET":
        return render_template("ask_ai.html")


    # ------------------------------------
    # GET USER QUESTION
    # ------------------------------------

    question = request.form.get(
        "question",
        ""
    ).strip()


    # ------------------------------------
    # EMPTY QUESTION
    # ------------------------------------

    if not question:

        return render_template(
            "ask_ai.html",
            answer="Please enter a skincare question first."
        )


    # ====================================
    # ASK AI PROMPT
    # ====================================

    prompt = f"""
You are Skincare AI, a skincare education assistant.

The user has asked:

{question}

Answer the question in simple, beginner-friendly language.

IMPORTANT RULES:

- Give educational skincare information.
- Do not make medical diagnoses.
- Do not claim certainty when the information is uncertain.
- Do not invent products, prices, ratings, shopping links, or availability.
- If the question involves a serious, painful, persistent, rapidly worsening,
  or unusual skin problem, recommend consulting a qualified dermatologist.
- Keep the answer practical and easy to understand.
- Explain skincare terms in simple language.
- Do not prescribe medication.

FORMATTING RULES:

- Plain text only.
- Do not use Markdown.
- Do not use asterisks.
- Do not use hashtags.
- Do not use backticks.
- Do not use HTML.
- Do not use <br>.
- Do not use bold or italic formatting.
- Keep headings on their own lines.
- Leave a blank line between sections.
- Use numbered lists where appropriate.
- Keep paragraphs short.
"""


    # ====================================
    # ASK OLLAMA
    # ====================================

    try:

        response = client.chat(
            model="gpt-oss:120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        answer = response["message"]["content"]

        answer = clean_markdown(answer)

    except Exception as e:

        answer = (
            "The AI assistant could not generate an answer right now.\n\n"
            "Please try again."
        )

        print("ASK AI ERROR:", e)


    # ====================================
    # SHOW ASK AI PAGE
    # ====================================

    return render_template(
        "ask_ai.html",
        answer=answer,
        question=question
    )


# ========================================
# RUN APPLICATION
# ========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )