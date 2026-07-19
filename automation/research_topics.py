import os
import json
import feedparser
from datetime import datetime, timezone

PENDING_PATH = "news/pending_topics.json"

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
]


def collect_todays_headlines():
    """Pull today's entries from each feed, newest first, deduplicated by title."""
    seen_titles = set()
    headlines = []
    today = datetime.now(timezone.utc).date()

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if not title or title.lower() in seen_titles:
                continue

            # Keep only genuinely recent items where we can tell the date;
            # if a feed doesn't provide one, keep it anyway rather than lose a story.
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
    Simple relevance ranking: prioritize headlines mentioning major assets/topics,
    then fill remaining slots with whatever's left. Good enough starting point -
    can be swapped for a smarter Gemini-based ranking later if desired.
    """
    priority_terms = ["bitcoin", "btc", "ethereum", "eth", "sec", "etf", "regulation",
                       "stablecoin", "solana", "hack", "fed", "interest rate"]

    def score(item):
        text = (item["title"] + " " + item["summary"]).lower()
        return sum(1 for term in priority_terms if term in text)

    ranked = sorted(headlines, key=score, reverse=True)
    return ranked[:5]


def main():
    headlines = collect_todays_headlines()
    if not headlines:
        print("No headlines found today - leaving pending_topics.json untouched.")
        return

    top_five = pick_best_five(headlines)

    os.makedirs(os.path.dirname(PENDING_PATH), exist_ok=True)
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(top_five, f, indent=2)

    print(f"Saved {len(top_five)} topics for today:")
    for t in top_five:
        print(f" - {t['title']}")


if __name__ == "__main__":
    main()
