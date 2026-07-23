import os
import re
import json
from datetime import datetime, timezone

import google.generativeai as genai
from generate_article_image import generate_article_cover_image

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

PENDING_PATH = "news/pending_topics.json"
ARTICLES_JSON = "news/articles.json"
ROTATION_STATE_PATH = "news/author_rotation.json"
IMAGES_DIR = "news/images"

JSDELIVR_BASE = "https://cdn.jsdelivr.net/gh/aishatabubakarx/cryptobead-content@main"

VALID_CATEGORIES = ["DeFi", "Emerging Tech", "Macro", "Regulation", "Infrastructure"]

AISHAT = {"name": "Aishat Abubakar", "role": "Senior DeFi Journalist & Trader",
          "avatar": "/aishat_profile.jpg"}

OTHER_AUTHORS = [
    {"name": "Marcus Aurelius", "role": "Chief Macro Strategist",
     "avatar": "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=150&h=150&q=80"},
    {"name": "Sarah Jenkins", "role": "Lead Blockchain Architect",
     "avatar": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=150&h=150&q=80"},
    {"name": "Robert Vance", "role": "Chief On-Chain Analyst",
     "avatar": "https://images.unsplash.com/photo-1633332755192-727a05c4013d?auto=format&fit=crop&w=150&h=150&q=80"},
    {"name": "Elena Rostova", "role": "Senior Protocol Analyst",
     "avatar": "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=150&h=150&q=80"},
    {"name": "Dr. Alistair Sterling", "role": "Director of Policy",
     "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&h=150&q=80"},
]

AISHAT_SLOTS = {1, 4}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_todays_slot_and_author(existing_articles):
    """
    Determines which of the 5 daily slots this run is by counting how many
    articles have already been published today, rather than relying on a
    separate counter file that could fail to persist and silently reset to
    slot 1 (always Aishat) every run.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    todays_count = sum(
        1 for a in existing_articles
        if a.get("publishedAt", "").startswith(today)
    )
    slot = todays_count + 1

    state = load_json(ROTATION_STATE_PATH, {"rotation_index": 0})

    if slot in AISHAT_SLOTS:
        author = AISHAT
    else:
        author = OTHER_AUTHORS[state["rotation_index"] % len(OTHER_AUTHORS)]
        state["rotation_index"] += 1
        save_json(ROTATION_STATE_PATH, state)

    return slot, author


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70]


def pick_internal_links(existing_articles, count=2):
    picks = existing_articles[:count]
    return [f"[{a['title']}](https://cryptobead.com/article/{a['id']})" for a in picks]


def strip_fabricated_internal_links(content, existing_articles):
    """
    Gemini was asked to use only real internal links, but models can still
    fabricate a plausible-looking one. Rather than trust that, verify every
    cryptobead.com/article/:id link against real article IDs afterward, and
    demote any fake one to plain text so it can never point to a dead page.
    """
    real_ids = {a["id"] for a in existing_articles}

    def replace_if_fake(match):
        link_text, article_id = match.group(1), match.group(2)
        if article_id in real_ids:
            return match.group(0)  # real link, keep as-is
        return link_text  # fabricated - drop the link, keep just the text

    pattern = r"\[([^\]]+)\]\(https://cryptobead\.com/article/([^\)]+)\)"
    return re.sub(pattern, replace_if_fake, content)


def write_article(topic, existing_articles):
    source_text = topic.get("full_text") or topic.get("summary", "")
    internal_links = pick_internal_links(existing_articles)
    internal_hint = (
        f"If it fits naturally, you may weave in one of these internal links using this exact "
        f"markdown format: {internal_links[0]}. Do not force it if it doesn't fit. Do NOT invent, "
        f"combine, or paraphrase a different link, headline, or URL of your own, use this exact "
        f"one verbatim or omit internal links entirely."
        if internal_links else
        "No internal links are available yet, skip internal links entirely."
    )

    prompt = f"""
You are a crypto news writer. Write ONE news article based only on the real source
material below. Do not fabricate quotes, sources, names, or figures not present in
this material. If a specific detail is missing, either omit it or state that it is
unconfirmed, never invent it.

SOURCE HEADLINE: {topic['title']}
SOURCE TEXT: {source_text}
SOURCE LINK: {topic.get('link', '')}
SOURCE OUTLET: {topic.get('source', '')}

STRUCTURE (follow exactly):
- Headline: specific entity plus a specific number or action, not generic.
- Exactly 3 bold TL;DR bullet points right under the headline, each a complete
  factual sentence, styled as markdown bullets starting with "- **" and ending "**".
- Opening paragraph: restates the headline claim with one added concrete detail
  (a number, date, or name). Do not just repeat the bullets.
- One short bridge sentence connecting the lede to the body.
- Body organized under exactly 2 to 3 section headers written as questions, using
  markdown ### (for example "### What is the significance of this ruling?"). Never
  use statement headers.
- Each section: short paragraphs of 1 to 3 sentences, ends on a forward looking or
  consequence oriented line, never a flat summary.
- {internal_hint}
- Do NOT write a conclusion. When the news ends, stop. Do not tie it up, do not
  summarize, do not add a closing thought.
- After the body, add a line containing exactly "### FAQs" and then 2 to 3 FAQ
  entries as markdown ### question headers. Fully answer only the FIRST question
  (1 to 2 sentences). For the remaining questions, write ONLY the question header
  with no answer text beneath it at all.
- After the FAQs, add one line starting with "Tickers:" followed by 1 to 3 relevant
  ticker symbols separated by spaces (for example "Tickers: BTC ETH").
- After that, add one line starting with "Disclaimer:" with a short one sentence
  factual disclaimer (not investment advice).

VOICE (follow exactly):
- Flat, declarative, just the facts. No adjectives doing emotional work (never
  "shocking," "massive," "stunning").
- Every claim attributed to a named person, account, firm, or filing using phrasing
  like "according to," "X wrote," "Y said in a statement," "data from Z shows."
- Numbers over adjectives: exact dollar figures, percentages, dates, named sources.
- Quotes are short, sourced, and used sparingly, mostly paraphrase.
- No first person. No reader address except none at all.
- Neutral framing for contested claims: "observers allege," "critics say," "the
  company has not responded."
- NEVER use an em dash or en dash. Use a comma, period, or restructure the sentence
  instead. Do not use a colon or semicolon unless strictly necessary.

LENGTH: the article body (not counting TL;DR bullets, FAQs, tickers, or disclaimer)
must be between 650 and 750 words. This is a hard requirement.

CATEGORY: choose exactly one of: DeFi, Emerging Tech, Macro, Regulation, Infrastructure.

Then provide optional enrichment. Only include a tweet URL if you are genuinely
confident a real, correctly formatted tweet exists that is directly relevant. If
you are not fully confident, write NONE. Never guess or invent a plausible looking
URL.

Only include chart data if the source material contains real, specific numeric
data worth charting. If no such real data exists, write NONE. Never invent numbers.

If you do include chart data, also choose the chart type that best fits the shape
of that specific data:
- "bar": comparing distinct separate things (e.g. sentence lengths across cases,
  fees across different protocols).
- "line" or "area": a trend changing over time (e.g. price history, adoption
  growth over months).
- "pie": a share-of-total breakdown (e.g. market dominance split, vote results).
- "radial": a single percentage or progress-toward-target metric (e.g. "96% of
  target reached"). For radial, provide exactly ONE data point, its value must
  be a number from 0 to 100.

Format your entire response EXACTLY like this, with these exact labels on their
own lines:
TITLE: [headline]
SUBTITLE: [one sentence subtitle]
SUMMARY: [one sentence, plain text, under 140 characters]
CATEGORY: [one of the 5 categories]
TAGS: [3-5 comma separated tags]
SENTIMENT: [bullish, bearish, or neutral]
KEY_INSIGHTS: [3 short direct factual sentences separated by " | "]
TWEET_URL: [a real tweet URL, or NONE]
CHART_TITLE: [chart title, or NONE]
CHART_SUBTITLE: [chart subtitle, or NONE]
CHART_TYPE: [bar, line, area, pie, or radial - or NONE]
CHART_YAXIS: [y axis label, or NONE]
CHART_SOURCE: [source line, or NONE]
CHART_DATA: [comma separated label:value pairs, or NONE]
CONTENT:
[the full article following the structure and voice rules above]
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
    insights_raw = extract("KEY_INSIGHTS", "TWEET_URL")
    tweet_url = extract("TWEET_URL", "CHART_TITLE")
    chart_title = extract("CHART_TITLE", "CHART_SUBTITLE")
    chart_subtitle = extract("CHART_SUBTITLE", "CHART_TYPE")
    chart_type = extract("CHART_TYPE", "CHART_YAXIS").lower()
    chart_yaxis = extract("CHART_YAXIS", "CHART_SOURCE")
    chart_source = extract("CHART_SOURCE", "CHART_DATA")
    chart_data_raw = extract("CHART_DATA", "CONTENT")
    content = extract("CONTENT")
    content = strip_fabricated_internal_links(content, existing_articles)

    if chart_type not in ["bar", "line", "area", "pie", "radial"]:
        chart_type = "bar"

    if category not in VALID_CATEGORIES:
        category = "Emerging Tech"
    if sentiment not in ["bullish", "bearish", "neutral"]:
        sentiment = "neutral"

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    key_insights = [k.strip() for k in insights_raw.split("|") if k.strip()]
    word_count = len(content.split())

    result = {
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

    if tweet_url and tweet_url.upper() != "NONE" and tweet_url.startswith("http"):
        result["tweet_url"] = tweet_url

    if chart_data_raw and chart_data_raw.upper() != "NONE" and chart_title.upper() != "NONE":
        pairs = []
        for pair in chart_data_raw.split(","):
            if ":" in pair:
                label, _, value = pair.partition(":")
                try:
                    pairs.append({"label": label.strip(), "value": float(value.strip())})
                except ValueError:
                    continue
        if pairs:
            result["chart_data"] = {
                "title": chart_title,
                "subtitle": chart_subtitle,
                "yAxisLabel": chart_yaxis,
                "sourceLabel": chart_source,
                "chartType": chart_type,
                "data": pairs,
            }

    return result


def main():
    pending = load_json(PENDING_PATH, [])
    if not pending:
        print("No pending topics left for today, nothing to publish this run.")
        return

    topic = pending.pop(0)
    save_json(PENDING_PATH, pending)

    existing_articles = load_json(ARTICLES_JSON, [])

    slot, author = get_todays_slot_and_author(existing_articles)
    print(f"Slot {slot} today, assigned to {author['name']}")
    print(f"Writing article for: {topic['title']}")

    article_data = write_article(topic, existing_articles)

    now = datetime.now(timezone.utc)
    article_id = slugify(article_data["title"]) + "-" + now.strftime("%Y%m%d%H%M")

    image_filename = f"{article_id}.jpg"
    image_path = os.path.join(IMAGES_DIR, image_filename)
    image_ok = generate_article_cover_image(
        article_data["title"], image_path,
        category=article_data["category"], article_summary=article_data["summary"]
    )
    image_url = f"{JSDELIVR_BASE}/{image_path}" if image_ok else ""

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
        "author": author,
    }

    if "tweet_url" in article_data:
        new_article["tweetUrl"] = article_data["tweet_url"]
    if "chart_data" in article_data:
        new_article["chartData"] = article_data["chart_data"]

    all_articles = load_json(ARTICLES_JSON, [])
    all_articles.insert(0, new_article)
    save_json(ARTICLES_JSON, all_articles)

    print(f"Published: {new_article['title']} ({new_article['id']}) by {author['name']}")
    print(f"Word count: {article_data['word_count']}")


if __name__ == "__main__":
    main()
