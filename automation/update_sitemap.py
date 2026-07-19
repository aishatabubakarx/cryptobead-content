import os
import json

SITE_URL = "https://cryptobead.com"
ARTICLES_JSON = "news/articles.json"
GUIDES_JSON = "guides/guides.json"
SITEMAP_PATH = "sitemap.xml"


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    articles = load_json(ARTICLES_JSON)
    guides = load_json(GUIDES_JSON)

    urls = [f"{SITE_URL}/"]
    urls += [f"{SITE_URL}/news/{a['id']}" for a in articles]
    urls += [f"{SITE_URL}/guides/{g['id']}" for g in guides]

    xml_entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_entries}
</urlset>
"""
    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write(sitemap)

    print(f"sitemap.xml updated with {len(urls)} URLs.")


if __name__ == "__main__":
    main()
