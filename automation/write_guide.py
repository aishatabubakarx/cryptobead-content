import os
import re
import json
from datetime import datetime, timezone

import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

GUIDES_JSON = "guides/guides.json"


def load_guides():
    if not os.path.exists(GUIDES_JSON):
        return []
    with open(GUIDES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_guides(guides):
    os.makedirs(os.path.dirname(GUIDES_JSON), exist_ok=True)
    with open(GUIDES_JSON, "w", encoding="utf-8") as f:
        json.dump(guides, f, indent=2)


def pick_topic(existing_titles):
    prompt = f"""
You write beginner-friendly educational crypto/blockchain guides for a finance/tech news site.

Guides already published (do not repeat these or anything too similar):
{chr(10).join('- ' + t for t in existing_titles) if existing_titles else '(none yet)'}

Suggest ONE new guide topic that would genuinely help someone understand an important
crypto/blockchain/DeFi concept. Reply with ONLY the topic title, nothing else.
"""
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip().strip('"')


def write_guide(topic):
    prompt = f"""
You write beginner-friendly educational crypto/blockchain guides for a finance/tech news site.

Write a complete guide on this topic: "{topic}"

STRICT RULES:
- Exactly around 3000 words (2800-3200 acceptable).
- Written so a complete beginner can follow it - explain jargon the first time it's used.
- Structured using ### for each major section heading (aim for 6-10 sections).
- Use **bold** sparingly for key terms only.
- Use numbered lists (1. 2. 3.) for step-by-step instructions where relevant.
- Clear, encouraging, plain-English tone. No hype, no vague filler.

Then generate supporting metadata.

Format your entire response EXACTLY like this, with these exact labels on their own lines:
TITLE: [clean guide title]
LEVEL: [choose exactly one of: Beginner, Intermediate, Advanced, Professional]
SUMMARY: [one to two sentence summary of what the reader will learn]
CONTENT:
[the full ~3000 word guide body here, using ### section headings as instructed]
"""
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    text = response.text.strip()

    def extract(label, next_label=None):
        pattern = rf"{label}:\s*(.*?)(?=\n{next_label}:|$)" if next_label else rf"{label}:\s*(.*)"
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    title = extract("TITLE", "LEVEL")
    level = extract("LEVEL", "SUMMARY")
    summary = extract("SUMMARY", "CONTENT")
    content = extract("CONTENT")

    valid_levels = ["Beginner", "Intermediate", "Advanced", "Professional"]
    if level not in valid_levels:
        level = "Beginner"

    word_count = len(content.split())

    return {
        "title": title,
        "seriesLevel": level,
        "summary": summary,
        "content": content,
        "readTime": f"{max(1, round(word_count / 200))} min read",
    }


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70]


def main():
    guides = load_guides()
    existing_titles = [g["title"] for g in guides]

    topic = pick_topic(existing_titles)
    print(f"This week's guide topic: {topic}")

    guide_data = write_guide(topic)
    now = datetime.now(timezone.utc)
    guide_id = slugify(guide_data["title"]) + "-" + now.strftime("%Y%m%d")

    new_guide = {
        "id": guide_id,
        "title": guide_data["title"],
        "seriesLevel": guide_data["seriesLevel"],
        "readTime": guide_data["readTime"],
        "summary": guide_data["summary"],
        "popular": False,
        "content": guide_data["content"],
    }

    guides.insert(0, new_guide)
    save_guides(guides)
    print(f"Published guide: {new_guide['title']} ({new_guide['id']})")


if __name__ == "__main__":
    main()
