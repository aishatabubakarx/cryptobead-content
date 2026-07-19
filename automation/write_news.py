import os
import re
import json
import hashlib
from datetime import datetime, timezone

import google.generativeai as genai
from generate_article_image import generate_article_cover_image

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

PENDING_PATH = "news/pending_topics.json"
ARTICLES_JSON = "news/articles.json"
IMAGES_DIR = "news/images"
SITE_URL = "https://cryptobead.com"

VALID_CATEGORIES = ["DeFi", "Emerging Tech", "Macro", "Regulation", "Infrastructure"]

AUTHOR = {
    "name": "Aishat Abubakar",
    "role": "Crypto Markets Editor",
    "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&h=150&q=80",
}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70]


def load_pending_topics():
    if not os.path.exists(PENDING_PATH):
        return []
    with open(PENDING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pending_topics(topics):
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(topics, f, indent=2)


def load_articles():
    if not os.path.exists(ARTICLES_JSON):
        return []
    with open(ARTICLES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_articles(articles):
    os.makedirs(os.path.dirname(ARTICLES_JSON), exist_ok=True)
    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2)


def pick_two_internal_links(existing_articles):
    """Pick up to 2 recent articles to link back to, matching the site's own article URLs."""
    picks = existing_articles[:2]
    links = []
    for a in picks:
        url = f"{SITE_URL}/news/{a['id']}"
        links.append(f"[{a['title']}]({url})")
    return links


def write_article(topic, existing_articles):
    internal_links = pick_two_internal_links(existing_articles)
    internal_hint = (
        f"Naturally weave in these {len(internal_links)} internal links somewhere in the body, "
        f"using this exact markdown format: {', '.join(internal_links)}."
        if internal_links else
        "No internal links are available yet (this is one of the first articles) - skip internal links."
    )

    prompt = f"""
You are the crypto markets editor for Cryptobead, a finance/tech news site.

Write a news article about this real, current topic:
TITLE: {topic['title']}
CONTEXT: {topic.get('summary', '')}
SOURCE: {topic.get('source', '')}

STRICT RULES:
- Exactly around 800 words (750-850 acceptable).
- Plain text formatted using ### for subheadings (2-4 subheadings), no markdown bold/asterisks
  except inside links.
- Include 1-2 external links to credible sources using markdown format [anchor text](https://real-url.com) -
  cite real, well-known crypto/finance sources or official sites relevant to the topic (e.g. official
  project blogs, SEC.gov, coindesk.com, cointelegraph.com). Only use a URL you are confident is real
  and correctly formed.
- {internal_hint}
- Be specific: real numbers, named entities, direct analysis. No vague filler.
- Tone: clear, professional, accessible - not academic, not hype-driven.

Then also generate supporting metadata.

Format your entire response EXACTLY like this, with these exact labels on their own lines:
TITLE: [a punchy, SEO-friendly headline, can differ slightly from the source topic title]
SUBTITLE: [one sentence subtitle]
SUMMARY: [one sentence, plain text, no links - used as the meta description, under 155 characters]
CATEGORY: [choose exactly one of: DeFi, Emerging Tech, Macro, Regulation, Infrastructure]
TAGS: [3-5 comma separated tags]
SENTIMENT: [choose exactly one of: bullish, bearish, neutral]
KEY_INSIGHTS: [3 short bullet insights separated by " | "]
CONTENT:
[the full ~800 word article body here, using ### subheadings and markdown links as instructed]
"""

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    text = response.text.strip()

    def extract(label, next_label=None):
        pattern = rf"{label}:\s*(.*?)(?=\n{next_label}:|$)" if next_label else rf"{label}:\s*(.*)"
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    title = extract("TITLE", "SUBTITLE")
    subtitle = extract("SUBTITLE", "SUMMARY")
    summary = extract("SUMMARY", "CATEGORY")
    category = extract("CATEGORY", "TAGS")
    tags_raw = extract("TAGS", "SENTIMENT")
    sentiment = extract("SENTIMENT", "KEY_INSIGHTS").lower()
    insights_raw = extract("KEY_INSIGHTS", "CONTENT")
    content = extract("CONTENT")

    if category not in VALID_CATEGORIES:
        category = "Emerging Tech"
    if sentiment not in ["bullish", "bearish", "neutral"]:
        sentiment = "neutral"

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    key_insights = [k.strip() for k in insights_raw.split("|") if k.strip()]
    word_count = len(content.split())

    return {
        "title": title,
        "subtitle": subtitle,
        "summary": summary,
        "content": content,
        "category": category,
        "tags": tags,
        "sentiment": sentiment,
        "key_insights": key_insights,
        "word_count": word_count,
    }


def main():
    pending = load_pending_topics()
    if not pending:
        print("No pending topics left for today - nothing to publish this run.")
        return

    topic = pending.pop(0)
    save_pending_topics(pending)

    print(f"Writing article for: {topic['title']}")
    existing_articles = load_articles()
    article_data = write_article(topic, existing_articles)

    now = datetime.now(timezone.utc)
    article_id = slugify(article_data["title"]) + "-" + now.strftime("%Y%m%d%H%M")

    image_filename = f"{article_id}.jpg"
    image_path = os.path.join(IMAGES_DIR, image_filename)
    generate_article_cover_image(article_data["title"], image_path)
    image_url = f"{SITE_URL}/{image_path}"

    new_article = {
        "id": article_id,
        "title": article_data["title"],
        "subtitle": article_data["subtitle"],
        "summary": article_data["summary"],
        "content": article_data["content"],
        "category": article_data["category"],
        "date": now.strftime("%b %d, %Y"),
        "publishedAt": now.isoformat(),
        "readTime": f"{max(1, round(article_data['word_count'] / 200))} min read",
        "sentiment": article_data["sentiment"],
        "reliabilityScore": 85,
        "tags": article_data["tags"],
        "image": image_url,
        "featured": False,
        "wordCount": article_data["word_count"],
        "keyInsights": article_data["key_insights"],
        "author": AUTHOR,
    }

    all_articles = load_articles()
    all_articles.insert(0, new_article)  # newest first
    save_articles(all_articles)

    print(f"Published: {new_article['title']} ({new_article['id']})")


if __name__ == "__main__":
    main()
