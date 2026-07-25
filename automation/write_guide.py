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


def strip_markdown_symbols(text):
    """
    Belt-and-braces cleanup: even with instructions not to use them, models
    can slip in a stray # or * now and then. Strip markdown heading hashes
    and any asterisks (bold/italic/bullets) so the stored content is always
    plain text, regardless of what the model actually returned.
    """
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("*", "")
    return text


def write_guide(topic):
    prompt = f"""
You write in-depth, genuinely useful educational crypto/blockchain guides for a
finance/tech news site. Readers are smart but new to this specific topic - they
are not crypto beginners in general, but they haven't studied this concept before.

Write a complete guide on this topic: "{topic}"

STRICT FORMATTING RULE (non-negotiable): do NOT use the characters # or * anywhere
in your output, for any reason. No markdown headings, no bold, no italics, no bullet
points written with *. Section headings must be plain text on their own line (for
example "Why liquidity pools exist" on its own line, followed by a blank line, then
the paragraph), with no symbols before or after them. If you need a list, write it
as plain numbered lines like "1. First step" rather than markdown bullets.

CONTENT DEPTH AND QUALITY RULES:
- Exactly around 3000 words (2800-3200 acceptable). Do not pad with filler to hit
  the count, every paragraph should teach something.
- Open with a short, concrete hook: a real scenario, number, or question that shows
  why this topic actually matters, before any formal definition.
- Explain jargon the very first time it appears, in plain language, as if talking
  to a smart friend who has never touched this specific corner of crypto.
- Structure into 6-10 clearly separated sections (plain text headings as described
  above), moving from "what is this" to "why it matters" to "how it actually works
  mechanically" to "risks and common mistakes" to "how to actually get started or
  apply this" to "how to evaluate whether it's working/safe."
- Use at least one concrete worked example with realistic numbers (e.g. an actual
  hypothetical trade, fee, or yield calculation), not just abstract description.
- Include a short "common mistakes" or "what goes wrong" section grounded in real
  known failure patterns for this topic, not vague warnings.
- End with a short, honest summary of what the reader should remember and do next.
- Clear, encouraging, plain-English tone. No hype, no vague filler like "revolutionize"
  or "game-changing," no unnecessary superlatives, no false urgency.

Then generate supporting metadata.

Format your entire response EXACTLY like this, with these exact labels on their own
lines (the labels themselves are the only place colons/labels are allowed, everything
else must be plain text with no # or * anywhere):
TITLE: [clean guide title]
LEVEL: [choose exactly one of: Beginner, Intermediate, Advanced, Professional]
SUMMARY: [one to two sentence summary of what the reader will learn]
CONTENT:
[the full ~3000 word guide body here, plain text only, no # or * characters]
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

    title = strip_markdown_symbols(title).strip()
    summary = strip_markdown_symbols(summary).strip()
    content = strip_markdown_symbols(content).strip()

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
