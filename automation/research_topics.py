import os
import json
import re
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENDING_TOPICS_PATH = os.path.join(BASE_DIR, 'news', 'pending_topics.json')
ARTICLES_PATH = os.path.join(BASE_DIR, 'news', 'articles.json')

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
    # Try SDK first
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception:
        # Fallback to direct HTTP request using standard library
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['candidates'][0]['content']['parts'][0]['text']

def research_topics():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("GEMINI_API_KEY not found in environment. Skipping AI research.")
        return

    existing_articles = load_json(ARTICLES_PATH, [])
    existing_pending = load_json(PENDING_TOPICS_PATH, [])

    existing_titles = set(
        [a.get('title', '').lower() for a in existing_articles] +
        [p.get('title', '').lower() for p in existing_pending]
    )

    prompt = """You are a senior Web3 and crypto news researcher for Cryptobead.
Research and generate 5 highly relevant, breaking or trending cryptocurrency, DeFi, Macro, or Blockchain infrastructure news topics for today.

Provide the output strictly as a JSON array of objects with the following schema:
[
  {
    "title": "Clear, compelling news topic title",
    "summary": "Brief 1-2 sentence background summary",
    "category": "DeFi" | "Emerging Tech" | "Macro" | "Regulation" | "Infrastructure",
    "tags": ["Tag1", "Tag2", "Tag3"],
    "sourceUrl": "https://cryptobead.com"
  }
]
Do not wrap in markdown code blocks or additional explanation."""

    try:
        text = call_gemini_api(prompt, api_key)
        json_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if json_match:
            new_topics = json.loads(json_match.group(0))
        else:
            new_topics = json.loads(text)

        added_count = 0
        for topic in new_topics:
            title = topic.get('title', '').strip()
            if title and title.lower() not in existing_titles:
                existing_pending.append(topic)
                existing_titles.add(title.lower())
                added_count += 1

        save_json(PENDING_TOPICS_PATH, existing_pending)
        print(f"Successfully researched and added {added_count} new topics to pending_topics.json.")

    except Exception as e:
        print(f"Error during topic research: {e}")

if __name__ == '__main__':
    research_topics()
