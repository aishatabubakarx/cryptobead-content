import os
import json
from datetime import datetime, timezone

SITE_URL = "https://cryptobead.com"
ARTICLES_JSON = "news/articles.json"
GUIDES_JSON = "guides/guides.json"
SITEMAP_PATH = "sitemap.xml"

COINS = ["BTC", "ETH", "SOL", "LINK", "ADA", "DOT", "UNI", "AAVE"]


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def url_entry(loc, changefreq, priority, lastmod=None):
    lastmod_tag = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    return f"  <url><loc>{loc}</loc>{lastmod_tag}<changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>"


def main():
    articles = load_json(ARTICLES_JSON)
    guides = load_json(GUIDES_JSON)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entries = [url_entry(f"{SITE_URL}/", "hourly", "1.0", today)]

    for a in articles:
        lastmod = a.get("publishedAt", today)[:10]
        entries.append(url_entry(f"{SITE_URL}/article/{a['id']}", "daily", "0.8", lastmod))

    for g in guides:
        entries.append(url_entry(f"{SITE_URL}/guide/{g['id']}", "weekly", "0.7", today))

    for symbol in COINS:
        entries.append(url_entry(f"{SITE_URL}/coin/{symbol}", "hourly", "0.6", today))

    xml_entries = "\n".join(entries)
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_entries}
</urlset>
"""
    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write(sitemap)

    print(f"sitemap.xml updated with {len(entries)} URLs.")


if __name__ == "__main__":
    main()
