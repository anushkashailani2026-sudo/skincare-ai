"""
Groq AI Service for Skincare AI.

Centralized service for text generation, skincare explanations, product
recommendation narratives, image analysis, and packaging OCR.
"""

import os
import re
import json
import time
import base64
import logging
from typing import Dict, Any, Tuple, Optional, List

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("skincare_ai.groq")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [GroqService] %(levelname)s: %(message)s"
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ========================================================
# MODEL AND CONFIGURATION SETTINGS
# ========================================================

# Current Groq text models. The second model is used if the first fails.
DEFAULT_TEXT_MODEL = os.getenv(
    "GROQ_TEXT_MODEL", "openai/gpt-oss-120b"
).strip()

FALLBACK_TEXT_MODELS = [
    "openai/gpt-oss-20b",
]

# Qwen 3.8 is the current multimodal model configured for image input.
# It is a preview model, so keep the model name configurable in .env.
DEFAULT_VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL", "qwen/qwen3.8-27b"
).strip()

# Do not add text-only models as vision fallbacks.
FALLBACK_VISION_MODELS: List[str] = []

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.5
MAX_IMAGE_BYTES = 20 * 1024 * 1024


def get_groq_api_key() -> str:
    """Retrieve the Groq API key from the environment."""
    return os.getenv("GROQ_API_KEY", "").strip()


def get_groq_client():
    """Create the official Groq client, or return None if unavailable."""
    key = get_groq_api_key()
    if not key:
        return None

    try:
        from groq import Groq
        return Groq(api_key=key, timeout=35.0)
    except Exception as exc:
        logger.error("Failed to initialize Groq client: %s", exc)
        return None


def clean_markdown_text(text: str) -> str:
    """Remove common Markdown markers for clean display in the app."""
    if not text:
        return ""

    cleaned = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"^>\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# ========================================================
# CORE COMPLETION FUNCTIONS
# ========================================================

def generate_chat_completion(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1000,
    is_vision: bool = False
) -> Tuple[Optional[str], Optional[str]]:
    """
    Send a chat completion request to Groq.

    Returns:
        (response_text, None) on success
        (None, error_message) on failure
    """
    client = get_groq_client()
    if not client:
        return None, (
            "Groq client is unavailable. Check GROQ_API_KEY and "
            "ensure the groq package is installed."
        )

    candidate_models: List[str] = []
    if model:
        candidate_models.append(model)

    fallbacks = FALLBACK_VISION_MODELS if is_vision else FALLBACK_TEXT_MODELS
    for fallback in fallbacks:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    if not candidate_models:
        return None, "No Groq model is configured."

    try:
        from groq import (
            RateLimitError,
            APITimeoutError,
            APIConnectionError,
            APIError,
        )
    except ImportError as exc:
        logger.error("Groq SDK imports failed: %s", exc)
        return None, "The Groq package is not installed. Run: pip install groq"

    last_error = None

    for candidate in candidate_models:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(
                    "Sending Groq request (model=%s, attempt=%s)",
                    candidate,
                    attempt,
                )

                response = client.chat.completions.create(
                    model=candidate,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_tokens,
                )

                if response and response.choices:
                    content = response.choices[0].message.content or ""
                    if content.strip():
                        return content.strip(), None
                    return None, "Groq returned an empty response."

                return None, "Groq returned an unexpected empty response."

            except RateLimitError as exc:
                last_error = f"Rate limit reached on {candidate}: {exc}"
                logger.warning("%s", last_error)
                if attempt < MAX_RETRIES:
                    delay = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    time.sleep(delay)
                else:
                    break

            except (APITimeoutError, APIConnectionError) as exc:
                last_error = f"Network connection issue with Groq: {exc}"
                logger.warning("%s", last_error)
                if attempt < MAX_RETRIES:
                    time.sleep(INITIAL_BACKOFF_SECONDS)
                else:
                    break

            except APIError as exc:
                last_error = f"Groq API error on model {candidate}: {exc}"
                logger.error("%s", last_error)
                # Try the next configured model for model/API errors.
                break

            except Exception as exc:
                last_error = f"Unexpected error during Groq completion: {exc}"
                logger.exception("%s", last_error)
                return None, last_error

    return None, last_error or "Failed to obtain a completion from Groq."


def generate_text_completion(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1000
) -> Tuple[Optional[str], Optional[str]]:
    """Helper for standard text prompt completions."""
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    return generate_chat_completion(
        messages=messages,
        model=model or DEFAULT_TEXT_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        is_vision=False,
    )


def _read_image_input(image_path_or_bytes: Any) -> Tuple[Optional[bytes], str, Optional[str]]:
    """
    Read an image from a filesystem path, bytes, or an uploaded file object.
    Returns (image_bytes, mime_type, error_message).
    """
    try:
        if isinstance(image_path_or_bytes, (str, os.PathLike)):
            path = os.fspath(image_path_or_bytes)

            if not os.path.isfile(path):
                return None, "image/jpeg", f"Image file was not found: {path}"

            extension = os.path.splitext(path)[1].lower()
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }.get(extension, "image/jpeg")

            with open(path, "rb") as image_file:
                image_data = image_file.read()

        elif isinstance(image_path_or_bytes, bytes):
            image_data = image_path_or_bytes
            mime_type = "image/jpeg"

        elif hasattr(image_path_or_bytes, "read"):
            image_data = image_path_or_bytes.read()
            mime_type = "image/jpeg"

            # Restore the upload stream so another part of the app can read it.
            if hasattr(image_path_or_bytes, "seek"):
                image_path_or_bytes.seek(0)

        else:
            return None, "image/jpeg", "Unsupported image input format."

        if not image_data:
            return None, mime_type, "The uploaded image is empty."

        if len(image_data) > MAX_IMAGE_BYTES:
            return (
                None,
                mime_type,
                "The image is larger than 20 MB. Please upload a smaller image.",
            )

        # Detect common image formats from their file signatures when possible.
        if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_type = "image/png"
        elif image_data.startswith(b"RIFF") and image_data[8:12] == b"WEBP":
            mime_type = "image/webp"
        elif image_data.startswith(b"\xff\xd8\xff"):
            mime_type = "image/jpeg"

        return image_data, mime_type, None

    except Exception as exc:
        return None, "image/jpeg", f"Failed to read image data: {exc}"


def generate_vision_analysis(
    image_path_or_bytes: Any,
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 1500
) -> Tuple[Optional[str], Optional[str]]:
    """
    Analyze an image using Groq's multimodal model.

    Accepts a file path, raw image bytes, or an uploaded file object
    such as Flask/Werkzeug FileStorage.
    """
    image_data, mime_type, read_error = _read_image_input(image_path_or_bytes)
    if read_error:
        return None, read_error

    client = get_groq_client()
    if not client:
        return None, (
            "Groq client is unavailable. Check GROQ_API_KEY and "
            "ensure the groq package is installed."
        )

    encoded_image = base64.b64encode(image_data).decode("utf-8")

    user_content = [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{encoded_image}"
            },
        },
    ]

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": user_content})

    return generate_chat_completion(
        messages=messages,
        model=model or DEFAULT_VISION_MODEL,
        temperature=0.1,
        max_tokens=max_tokens,
        is_vision=True,
    )


# ========================================================
# DOMAIN-SPECIFIC SKINCARE AI CAPABILITIES
# ========================================================

def ask_skincare_assistant(question: str) -> str:
    """Answer user skincare questions using Groq."""
    system_prompt = (
        "You are an evidence-based skincare educational assistant. "
        "Provide helpful, scientifically grounded, beginner-friendly explanations. "
        "Do not diagnose conditions or prescribe medications. "
        "Recommend consulting a qualified dermatologist for persistent, severe, "
        "or painful skin conditions. "
        "Write in clean, readable plain text with short paragraphs and spacing "
        "between sections. Do not use Markdown formatting, asterisks, hashtags, "
        "or Markdown tables."
    )

    content, error = generate_text_completion(
        prompt=question,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=700,
    )

    if error or not content:
        logger.warning("ask_skincare_assistant note: %s", error)
        return (
            "I could not reach the AI assistant right now. "
            "Please verify your GROQ_API_KEY environment variable or try again "
            "in a few moments."
        )

    return clean_markdown_text(content)


def explain_ingredient(ingredient_name: str) -> str:
    """Generate a structured 10-section breakdown for the ingredient explorer."""
    prompt = f"""
Provide a clear, evidence-based skincare guide for the ingredient:
{ingredient_name}

Use simple, beginner-friendly language.

IMPORTANT:
- Give useful and reasonably detailed information.
- Do not make a medical diagnosis.
- Do not claim an ingredient will definitely cure a condition.
- Use cautious language such as "may help" and "is commonly used".
- Do not invent scientific facts.
- Use plain text without Markdown or HTML.
- Keep headings on their own lines.
- Leave a blank line between sections.
- Use numbered lists where useful.

Use these sections:
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

    system_prompt = (
        "You provide careful, beginner-friendly skincare education. "
        "Do not diagnose or prescribe medication."
    )

    content, error = generate_text_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=1000,
    )

    if error or not content:
        logger.warning("explain_ingredient note: %s", error)
        return (
            f"Unable to generate detailed ingredient information for "
            f"'{ingredient_name}' right now. Please check your Groq API configuration."
        )

    return clean_markdown_text(content)


def analyze_skin_profile(prompt: str) -> str:
    """Generate a cautious skin profile analysis and routine advice."""
    system_prompt = (
        "You provide cautious skincare education. "
        "Do not diagnose, prescribe medication, or invent personal information."
    )

    content, error = generate_text_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=1200,
    )

    if error or not content:
        logger.warning("analyze_skin_profile note: %s", error)
        return (
            "Unable to analyze the skin profile right now. "
            "Please ensure your GROQ_API_KEY is configured in your environment."
        )

    return clean_markdown_text(content)


def explain_products_selection(prompt: str) -> str:
    """Generate an explanation based only on products supplied by the app."""
    system_prompt = (
        "You are a careful skincare product assistant. "
        "Use only the product details supplied in the prompt. "
        "Never invent product information or claim unknown skin suitability."
    )

    content, error = generate_text_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=800,
    )

    if error or not content:
        logger.warning("explain_products_selection note: %s", error)
        return (
            "Your product results were processed, but the AI explanation "
            "could not be generated at this moment. Please check your Groq API credentials."
        )

    return clean_markdown_text(content)


def generate_formulation_narrative(
    name: str,
    brand: str,
    category: str,
    ingredients: str,
    actives: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Generate a balanced formulation report for a product dossier."""

    def fallback_narrative() -> str:
        active_names = [
            item.get("name", "")
            for item in (actives or [])
            if isinstance(item, dict) and item.get("name")
        ]

        return (
            f"**{name}** by **{brand}** is formulated as a "
            f"{(category or 'skincare product').lower()} designed to support skin health. "
            f"Based on the ingredient profile, this formulation features "
            f"{', '.join(active_names) if active_names else 'supportive emollients and humectants'}. "
            "Individual results can vary, and the full ingredient list should be "
            "checked before use."
        )

    if not ingredients:
        return fallback_narrative()

    prompt = (
        "Provide a concise, evidence-based cosmetic formulation analysis for this product:\n"
        f"Product: {name} by {brand}\n"
        f"Category: {category}\n"
        f"Ingredients: {ingredients[:1200]}\n\n"
        "Include:\n"
        "1. Formulation summary\n"
        "2. Who may benefit most\n"
        "3. Who should exercise caution\n"
        "4. Realistic expectations versus marketing claims\n"
        "Use a scientific, balanced, clear, reassuring tone. "
        "Do not make medical diagnoses. Do not claim benefits that cannot be "
        "reasonably inferred from the supplied ingredients."
    )

    system_prompt = (
        "You are a careful cosmetic formulation analyst providing general "
        "skincare education. Do not diagnose medical conditions."
    )

    content, error = generate_text_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=700,
    )

    if error or not content:
        logger.warning("generate_formulation_narrative note: %s", error)
        return fallback_narrative()

    return clean_markdown_text(content)


def extract_packaging_ocr(
    image_path: Any
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Extract product details and readable ingredient text from a product image.

    Returns a dictionary and None on success, or None and an error message
    if the image could not be analyzed.
    """
    prompt = (
        "You are a careful skincare product identification and OCR assistant. "
        "Analyze this skincare product image. Extract only information that is "
        "actually readable. Do not guess missing text.\n"
        "Return these fields:\n"
        "1. Brand name\n"
        "2. Full product name\n"
        "3. Category (for example Cleanser, Moisturizer, Serum, Sunscreen, Toner)\n"
        "4. Ingredients text, preserving the visible ingredient list as accurately as possible\n"
        "5. Barcode number, only if readable\n"
        "6. Clarity (clear or blurry)\n"
        "7. Confidence (high, medium, or low)\n\n"
        "Respond with strict JSON only, using exactly these keys:\n"
        '{"brand":"","product_name":"","category":"","ingredients_text":"","barcode":"","clarity":"clear","confidence":"low"}'
    )

    system_prompt = (
        "You are an OCR and product-label recognition assistant. "
        "Return valid JSON only. Do not wrap the JSON in Markdown code fences. "
        "Never invent unreadable product details."
    )

    content, error = generate_vision_analysis(
        image_path_or_bytes=image_path,
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=1000,
    )

    if error or not content:
        return None, error or "Failed to extract text from the product image."

    # First try parsing the entire response.
    try:
        parsed = json.loads(content.strip())
    except json.JSONDecodeError:
        # If the model added text around the JSON, extract the JSON object.
        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            logger.warning("Groq vision did not return a JSON object.")
            return {
                "brand": "",
                "product_name": "",
                "category": "Skincare",
                "ingredients_text": content.strip(),
                "barcode": "",
                "clarity": "blurry",
                "confidence": "low",
            }, None

        try:
            parsed = json.loads(json_match.group(0))
        except json.JSONDecodeError as json_error:
            logger.warning("JSON parsing error from Groq vision: %s", json_error)
            return None, "The AI could not format the scanned product details correctly."

    if not isinstance(parsed, dict):
        return None, "The AI returned an unexpected format for the scanned product."

    # Ensure all fields expected by the rest of the app are present.
    defaults = {
        "brand": "",
        "product_name": "",
        "category": "Skincare",
        "ingredients_text": "",
        "barcode": "",
        "clarity": "blurry",
        "confidence": "low",
    }

    result = defaults.copy()
    for key in defaults:
        value = parsed.get(key, defaults[key])
        result[key] = value if isinstance(value, str) else str(value)

    return result, None
