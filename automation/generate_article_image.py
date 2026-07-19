import os
import base64
import requests

# --- Pull secrets from environment / GitHub Actions secrets, never hardcode ---
CLOUDFLARE_API_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CLOUDFLARE_ACCOUNT_ID = os.environ["CLOUDFLARE_ACCOUNT_ID"]
CLOUDFLARE_FLUX_MODEL = "@cf/black-forest-labs/flux-1-schnell"


def generate_article_cover_image(topic, save_path):
    """
    Generate a landscape, text-free cover image for a news article using
    Cloudflare's free Flux model, and save it directly into the news folder.

    topic: the article's headline/subject, used to build the visual prompt
    save_path: full file path to save the image, e.g. 'news/images/crypto-bitcoin-etf-20260718.jpg'
    """
    image_prompt = (
        f"A photorealistic, cinematic editorial photograph illustrating the concept of: {topic}. "
        f"Shot in the style of professional financial/tech journalism photography (Bloomberg, "
        f"Reuters, WSJ editorial style) — realistic lighting, real-world objects and settings, "
        f"shallow depth of field, moody atmospheric lighting. Landscape composition, wide 16:9 "
        f"aspect ratio, suitable as a website article cover banner. "
        f"Choose color grading and visual elements that specifically match this topic's mood and "
        f"subject matter — for example: gold/amber tones and coin imagery for gains or Bitcoin "
        f"stories, cold blue and red-chart tones for market downturns or losses, glowing blue "
        f"circuitry/server imagery for blockchain or tech-infrastructure stories, official/political "
        f"settings for regulation or government stories. Let the specific details of the topic "
        f"(price levels, named assets, market direction, institutions involved) directly shape "
        f"what objects, screens, charts, or settings appear in the image. Do not default to a flat "
        f"neutral palette — the color and mood should be earned by the story's content. "
        f"No readable body text, no legible paragraphs, no logos, no watermarks. Small illegible "
        f"chart lines/numbers on background screens are fine for realism. Human figures may appear "
        f"from behind, in silhouette, or out of focus, but no clear identifiable human faces."
    )

    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_FLUX_MODEL}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"prompt": image_prompt}

    print(f"🎨 Requesting article cover image for: {topic}")
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
    except Exception as e:
        print(f"❌ Cloudflare request failed: {e}")
        return None

    if resp.status_code != 200:
        print(f"❌ Cloudflare error: {resp.status_code} | {resp.text[:300]}")
        return None

    content_type = resp.headers.get("Content-Type", "")

    if content_type.startswith("image/"):
        image_bytes = resp.content
    else:
        try:
            data = resp.json()
        except Exception:
            print("❌ Unexpected response format from Cloudflare.")
            return None

        result = data.get("result", data)
        b64_image = None
        if isinstance(result, dict):
            b64_image = result.get("image") or result.get("images", [None])[0]
        elif isinstance(result, str):
            b64_image = result

        if not b64_image:
            print(f"❌ No image found in Cloudflare response: {str(data)[:300]}")
            return None

        if b64_image.startswith("data:"):
            _, b64_image = b64_image.split(",", 1)

        try:
            image_bytes = base64.b64decode(b64_image)
        except Exception as e:
            print(f"❌ Failed to decode base64 image: {e}")
            return None

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(image_bytes)

    print(f"✅ Cover image saved: {save_path}")
    return save_path
