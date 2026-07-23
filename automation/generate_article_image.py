import os
import base64
import requests
from io import BytesIO
from PIL import Image

CLOUDFLARE_API_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CLOUDFLARE_ACCOUNT_ID = os.environ["CLOUDFLARE_ACCOUNT_ID"]
CLOUDFLARE_FLUX_MODEL = "@cf/black-forest-labs/flux-1-schnell"

CATEGORY_VISUAL_HINTS = {
    "Regulation": (
        "legal documents, a gavel, a judge's hand or robed arm resting on a desk (never a full face), "
        "courthouse pillars, official government seals, formal government office settings"
    ),
    "DeFi": (
        "the Ethereum symbol or interlocking geometric shapes representing smart contracts, "
        "flowing liquid light trails, glowing interconnected network nodes"
    ),
    "Macro": (
        "stock exchange facades, financial district architecture, currency and coins together, "
        "trading floor screens with small illegible charts"
    ),
    "Infrastructure": (
        "server racks with glowing blue lighting, data center corridors, circuitry patterns, "
        "fiber optic light trails"
    ),
    "Emerging Tech": (
        "futuristic glowing circuitry, holographic-style interface elements, abstract tech patterns"
    ),
}


def build_image_prompt(topic, category, article_summary=""):
    visual_hint = CATEGORY_VISUAL_HINTS.get(category, "abstract crypto/blockchain visual elements")
    combined = (topic + " " + article_summary).lower()
    bitcoin_note = (
        "If this article is specifically about Bitcoin, feature the physical BTC coin prominently "
        "alongside a creative complementary element tied to this article's specific angle "
        "(e.g. a rising chart line for a price story, a vault/lock for a security story, "
        "a network of connected nodes for an adoption story)."
        if "bitcoin" in combined or "btc" in combined
        else ""
    )

    return (
        f"A photorealistic, cinematic editorial photograph illustrating this specific news story: {topic}. "
        f"Article context: {article_summary[:200]}. "
        f"Shot in the style of professional financial/tech journalism photography (Bloomberg, Reuters, WSJ "
        f"editorial style), realistic lighting, real world objects and settings, shallow depth of field, "
        f"moody atmospheric lighting. Landscape composition, wide 16:9 aspect ratio. "
        f"Visual elements to draw from for this category: {visual_hint}. {bitcoin_note} "
        f"Let the specific details of THIS article (not just its general category) shape exactly what "
        f"objects, screens, or settings appear, avoid generic stock photo sameness between articles. "
        f"Choose color grading that matches this story's mood (gold and amber tones for gains, cold blue "
        f"and red tones for losses, warm neutral tones for regulatory or institutional stories). "
        f"No readable body text, no legible paragraphs, no logos, no watermarks. Small illegible chart "
        f"lines or numbers on background screens are fine for realism. Human figures may appear from "
        f"behind, in silhouette, or out of focus, but no clear identifiable human faces, and never any "
        f"face at all if the subject is a specific real person such as a regulator, judge, or executive."
    )


def generate_article_cover_image(topic, save_path, category="Emerging Tech", article_summary=""):
    """
    Generate a landscape, text-free, creatively topic-specific cover image using
    Cloudflare's free Flux model, and save it directly into the news folder.
    Returns True on success, False on failure (article still publishes without an image).
    """
    image_prompt = build_image_prompt(topic, category, article_summary)

    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_FLUX_MODEL}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"prompt": image_prompt}

    print(f"Requesting article cover image for: {topic}")
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
    except Exception as e:
        print(f"Cloudflare request failed: {e}")
        return False

    if resp.status_code != 200:
        print(f"Cloudflare error: {resp.status_code} | {resp.text[:300]}")
        return False

    content_type = resp.headers.get("Content-Type", "")

    if content_type.startswith("image/"):
        image_bytes = resp.content
    else:
        try:
            data = resp.json()
        except Exception:
            print("Unexpected response format from Cloudflare.")
            return False

        result = data.get("result", data)
        b64_image = None
        if isinstance(result, dict):
            b64_image = result.get("image") or result.get("images", [None])[0]
        elif isinstance(result, str):
            b64_image = result

        if not b64_image:
            print(f"No image found in Cloudflare response: {str(data)[:300]}")
            return False

        if b64_image.startswith("data:"):
            _, b64_image = b64_image.split(",", 1)

        try:
            image_bytes = base64.b64decode(b64_image)
        except Exception as e:
            print(f"Failed to decode base64 image: {e}")
            return False

    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        target_ratio = 16 / 9
        width, height = img.size
        current_ratio = width / height

        if current_ratio > target_ratio:
            # Wider than 16:9 already - crop the sides in
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            img = img.crop((left, 0, left + new_width, height))
        else:
            # Square or taller than 16:9 (the common case) - crop top/bottom
            # so we keep the full width and end up with a true landscape crop
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            img = img.crop((0, top, width, top + new_height))

        img.save(save_path, "JPEG", quality=88)
    except Exception as e:
        print(f"Could not crop image to landscape, saving original: {e}")
        with open(save_path, "wb") as f:
            f.write(image_bytes)

    print(f"Cover image saved: {save_path}")
    return True
