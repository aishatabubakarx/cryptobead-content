import os
import json
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

PENDING_PATH = "news/pending_topics.json"

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
]


def collect_todays_headlines():
    seen_titles = set()
    headlines = []
    today = datetime.now(timezone.utc).date()

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if not title or title.lower() in seen_titles:
                continue

            published = entry.get("published_parsed")
            if published:
                entry_date = datetime(*published[:6], tzinfo=timezone.utc).date()
                if entry_date != today:
                    continue

            seen_titles.add(title.lower())
            headlines.append({
                "title": title,
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "source": feed.feed.get("title", feed_url),
            })

    return headlines


def pick_best_five(headlines):
    """
    Ranks headlines by relevance, but caps how many can come from the same topic
    bucket so Bitcoin (which often overlaps with multiple keywords like ETF/SEC/Fed
    at once) doesn't systematically crowd out Ethereum, Solana, DeFi, or general
    industry stories.
    """
    priority_terms = ["bitcoin", "btc", "ethereum", "eth", "sec", "etf", "regulation",
                       "stablecoin", "solana", "hack", "fed", "interest rate", "lawsuit", "sentenced"]

    topic_buckets = {
        "bitcoin": ["bitcoin", "btc"],
        "ethereum": ["ethereum", "eth"],
        "regulation_legal": ["sec", "regulation", "lawsuit", "sentenced", "court", "doj", "irs"],
        "defi_altcoins": ["solana", "defi", "stablecoin", "uniswap", "chainlink", "cardano", "polkadot"],
        "macro": ["fed", "interest rate", "inflation"],
        "security": ["hack", "exploit", "drained", "stolen"],
    }

    def score(item):
        text = (item["title"] + " " + item["summary"]).lower()
        return sum(1 for term in priority_terms if term in text)

    def get_bucket(item):
        text = (item["title"] + " " + item["summary"]).lower()
        for bucket_name, terms in topic_buckets.items():
            if any(term in text for term in terms):
                return bucket_name
        return "other"

    ranked = sorted(headlines, key=score, reverse=True)

    MAX_PER_BUCKET = 2
    bucket_counts = {}
    selected = []

    for item in ranked:
        if len(selected) >= 5:
            break
        bucket = get_bucket(item)
        if bucket_counts.get(bucket, 0) >= MAX_PER_BUCKET:
            continue
        selected.append(item)
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    # If the cap left us short of 5 (not enough topic variety today), fill
    # remaining slots with the next-best headlines regardless of bucket.
    if len(selected) < 5:
        for item in ranked:
            if len(selected) >= 5:
                break
            if item not in selected:
                selected.append(item)

    return selected[:5]


def fetch_full_article_text(url, max_chars=6000):
    """
    Fetch the real source article text so the writer has actual quotes, numbers,
    and names to work with instead of a one-line RSS summary. Returns empty string
    on failure, in which case write_news.py falls back to the RSS summary alone.
    """
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; CryptobeadBot/1.0)"})
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join(p for p in paragraphs if len(p) > 40)
        return text[:max_chars]
    except Exception as e:
        print(f"Could not fetch full article text from {url}: {e}")
        return ""


def main():
    headlines = collect_todays_headlines()
    if not headlines:
        print("No headlines found today, leaving pending_topics.json untouched.")
        return

    top_five = pick_best_five(headlines)

    for item in top_five:
        print(f"Fetching full source text for: {item['title']}")
        item["full_text"] = fetch_full_article_text(item["link"])

    os.makedirs(os.path.dirname(PENDING_PATH), exist_ok=True)
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(top_five, f, indent=2)

    print(f"Saved {len(top_five)} topics for today:")
    for t in top_five:
        has_text = "yes" if t.get("full_text") else "no (will use RSS summary only)"
        print(f" - {t['title']} | full source text: {has_text}")


if __name__ == "__main__":
    main()
