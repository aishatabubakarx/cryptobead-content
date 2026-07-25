import os
import json
import re
import argparse
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_PATH = os.path.join(BASE_DIR, 'news', 'articles.json')
PENDING_PATH = os.path.join(BASE_DIR, 'news', 'pending_topics.json')
ROTATION_PATH = os.path.join(BASE_DIR, 'news', 'author_rotation.json')

AISHAT_AUTHOR = {
    "name": "Aishat Abubakar",
    "role": "Senior DeFi Journalist & Trader",
    "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&h=150&q=80"
}

ROTATION_PANEL = [
    {
        "name": "Marcus Aurelius",
        "role": "Chief Macro Strategist",
        "avatar": "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=150&h=150&q=80"
    },
    {
        "name": "Sarah Jenkins",
        "role": "Lead Blockchain Architect",
        "avatar": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=150&h=150&q=80"
    },
    {
        "name": "Robert Vance",
        "role": "Chief On-Chain Analyst",
        "avatar": "https://images.unsplash.com/photo-1633332755192-727a05c4013d?auto=format&fit=crop&w=150&h=150&q=80"
    },
    {
        "name": "Elena Rostova",
        "role": "Senior Protocol Analyst",
        "avatar": "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=150&h=150&q=80"
    },
    {
        "name": "Dr. Alistair Sterling",
        "role": "Director of Policy",
        "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&h=150&q=80"
    }
]

def load_json(filepath, fallback):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    return fallback

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_next_author(slot_num=None):
    rotation_data = load_json(ROTATION_PATH, {"rotation_index": 0, "daily_slot": 1})
    
    rot_idx = rotation_data.get("rotation_index", 0)
    current_slot = slot_num or rotation_data.get("daily_slot", 1)

    if current_slot in [1, 4]:
        selected_author = AISHAT_AUTHOR
    else:
        selected_author = ROTATION_PANEL[rot_idx % len(ROTATION_PANEL)]
        rot_idx += 1

    next_slot = (current_slot % 5) + 1
    rotation_data["rotation_index"] = rot_idx
    rotation_data["daily_slot"] = next_slot
    
    save_json(ROTATION_PATH, rotation_data)
    return selected_author

def call_gemini_api(prompt, api_key):
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['candidates'][0]['content']['parts'][0]['text']

def write_news(slot=None):
    api_key = os.environ.get('GEMINI_API_KEY')
    pending_topics = load_json(PENDING_PATH, [])
    articles = load_json(ARTICLES_PATH, [])

    topic_data = None
    if pending_topics:
        topic_data = pending_topics.pop(0)
        save_json(PENDING_PATH, pending_topics)

    topic_title = topic_data.get('title') if topic_data else "Institutional Capital Expands Across On-Chain RWA Protocols"
    category = topic_data.get('category') if topic_data else "DeFi"

    author = get_next_author(slot)
    print(f"Writing article for topic '{topic_title}' under author '{author['name']}'...")

    now = datetime.utcnow()
    timestamp_slug = now.strftime('%Y%m%d%H%M')

    if api_key:
        prompt = f"""You are {author['name']}, {author['role']} for Cryptobead.
Write a comprehensive, highly analytical, and engaging cryptocurrency journalism article on: "{topic_title}".

Category: {category}

Respond strictly in valid JSON format with the following fields:
{{
  "title": "A strong, captivating news headline",
  "subtitle": "A clear 1-sentence analytical subtitle",
  "summary": "A concise 2-sentence executive summary",
  "content": "Full markdown text (600-800 words) with section headings (###), key analysis, data points, and FAQs section at the bottom",
  "sentiment": "bullish" | "bearish" | "neutral",
  "reliabilityScore": integer between 85 and 98,
  "category": "{category}",
  "tags": ["Tag1", "Tag2", "Tag3", "Tag4"],
  "keyInsights": ["Key insight 1", "Key insight 2", "Key insight 3"]
}}
Do not include any code block formatting markdown around the raw JSON object."""

        try:
            raw_text = call_gemini_api(prompt, api_key)
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            parsed = json.loads(json_match.group(0)) if json_match else json.loads(raw_text)
        except Exception as e:
            print(f"Gemini API call failed, using fallback template: {e}")
            parsed = {
                "title": topic_title,
                "subtitle": "Institutional momentum accelerates across decentralized liquidity pools.",
                "summary": "Market telemetry highlights sustained inflows into on-chain yield infrastructure.",
                "content": f"### Market Analysis\n\nRecent protocol data indicates expanding institutional participation in {category}. Network fundamentals remain strong.\n\n### Strategic Takeaways\n\nCross-chain liquidity bridges and decentralized security frameworks continue demonstrating resilience.\n\n### FAQs\n### What is driving this growth?\nSustained institutional interest and clearer regulatory guidelines.",
                "sentiment": "bullish",
                "reliabilityScore": 92,
                "category": category,
                "tags": [category, "Crypto", "Web3"],
                "keyInsights": ["Institutional adoption reaches new highs", "On-chain metrics remain strongly positive"]
            }
    else:
        parsed = {
            "title": topic_title,
            "subtitle": "Institutional momentum accelerates across decentralized liquidity pools.",
            "summary": "Market telemetry highlights sustained inflows into on-chain yield infrastructure.",
            "content": f"### Market Analysis\n\nRecent protocol data indicates expanding institutional participation in {category}. Network fundamentals remain strong.\n\n### Strategic Takeaways\n\nCross-chain liquidity bridges and decentralized security frameworks continue demonstrating resilience.\n\n### FAQs\n### What is driving this growth?\nSustained institutional interest and clearer regulatory guidelines.",
            "sentiment": "bullish",
            "reliabilityScore": 92,
            "category": category,
            "tags": [category, "Crypto", "Web3"],
            "keyInsights": ["Institutional adoption reaches new highs", "On-chain metrics remain strongly positive"]
        }

    slug = re.sub(r'[^a-z0-9]+', '-', parsed.get('title', topic_title).lower()).strip('-')
    article_id = f"{slug[:60]}-{timestamp_slug}"

    cover_images = [
        "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1622979135225-d2ba269bc1bd?auto=format&fit=crop&w=1200&q=80"
    ]
    image_url = cover_images[hash(article_id) % len(cover_images)]

    new_article = {
        "id": article_id,
        "title": parsed.get("title", topic_title),
        "subtitle": parsed.get("subtitle", ""),
        "summary": parsed.get("summary", ""),
        "content": parsed.get("content", ""),
        "category": parsed.get("category", category),
        "date": now.strftime('%b %d, %Y'),
        "publishedAt": now.isoformat() + "Z",
        "readTime": "4 min read",
        "sentiment": parsed.get("sentiment", "bullish"),
        "reliabilityScore": parsed.get("reliabilityScore", 92),
        "tags": parsed.get("tags", [category, "Crypto", "Web3"]),
        "image": image_url,
        "featured": False,
        "wordCount": len(parsed.get("content", "").split()),
        "keyInsights": parsed.get("keyInsights", []),
        "author": author
    }

    articles.insert(0, new_article)
    save_json(ARTICLES_PATH, articles)
    print(f"Successfully published article: {new_article['title']} (ID: {article_id})")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--slot', type=int, choices=[1, 2, 3, 4, 5], help='Daily author rotation slot number (1-5)')
    args = parser.parse_args()
    write_news(slot=args.slot)
