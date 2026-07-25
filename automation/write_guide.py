import os
import json
import re
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDES_PATH = os.path.join(BASE_DIR, 'guides', 'guides.json')

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

def write_guide(topic="DeFi Yield Farming & Automated Market Makers"):
    api_key = os.environ.get('GEMINI_API_KEY')
    guides = load_json(GUIDES_PATH, [])

    if api_key:
        prompt = f"""You are a Lead Blockchain Architect writing an in-depth educational guide for Cryptobead Academy.
Topic: "{topic}"

Respond strictly in valid JSON format:
{{
  "title": "Clear educational guide title",
  "seriesLevel": "Beginner" | "Intermediate" | "Advanced",
  "readTime": "10 min read",
  "summary": "Clear executive summary of what readers will learn",
  "popular": true,
  "content": "Comprehensive markdown tutorial with detailed technical sections, architecture diagrams, and best practice rules."
}}
Do not wrap in markdown code blocks."""

        try:
            raw_text = call_gemini_api(prompt, api_key)
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            parsed = json.loads(json_match.group(0)) if json_match else json.loads(raw_text)
        except Exception as e:
            print(f"Gemini API call failed, using template: {e}")
            parsed = {
                "title": topic,
                "seriesLevel": "Intermediate",
                "readTime": "10 min read",
                "summary": "Master automated market makers and decentralized yield strategies.",
                "popular": True,
                "content": f"# {topic}\n\n## Overview\nUnderstanding liquidity pools and smart contract interaction."
            }
    else:
        parsed = {
            "title": topic,
            "seriesLevel": "Intermediate",
            "readTime": "10 min read",
            "summary": "Master automated market makers and decentralized yield strategies.",
            "popular": True,
            "content": f"# {topic}\n\n## Overview\nUnderstanding liquidity pools and smart contract interaction."
        }

    slug = re.sub(r'[^a-z0-9]+', '-', parsed.get('title', topic).lower()).strip('-')
    guide_id = f"{slug}-{datetime.utcnow().strftime('%Y%m%d')}"

    new_guide = {
        "id": guide_id,
        "title": parsed.get("title", topic),
        "seriesLevel": parsed.get("seriesLevel", "Intermediate"),
        "readTime": parsed.get("readTime", "8 min read"),
        "summary": parsed.get("summary", ""),
        "popular": parsed.get("popular", True),
        "content": parsed.get("content", "")
    }

    updated = False
    for idx, g in enumerate(guides):
        if g.get('id') == guide_id or g.get('title') == new_guide['title']:
            guides[idx] = new_guide
            updated = True
            break

    if not updated:
        guides.insert(0, new_guide)

    save_json(GUIDES_PATH, guides)
    print(f"Successfully saved guide: {new_guide['title']}")

if __name__ == '__main__':
    write_guide()
