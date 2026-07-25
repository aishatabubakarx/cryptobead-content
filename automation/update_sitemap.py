import os
import json
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_PATH = os.path.join(BASE_DIR, 'news', 'articles.json')
GUIDES_PATH = os.path.join(BASE_DIR, 'guides', 'guides.json')
SITEMAP_PATH = os.path.join(BASE_DIR, 'sitemap.xml')

DOMAIN = "https://cryptobead.com"

def load_json(filepath, fallback):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    return fallback

def update_sitemap():
    articles = load_json(ARTICLES_PATH, [])
    guides = load_json(GUIDES_PATH, [])
    
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    urls = [
        f'  <url><loc>{DOMAIN}/</loc><lastmod>{today_str}</lastmod><changefreq>hourly</changefreq><priority>1.0</priority></url>'
    ]

    for art in articles:
        art_id = art.get('id')
        if art_id:
            pub_date = art.get('publishedAt', today_str)[:10]
            urls.append(f'  <url><loc>{DOMAIN}/article/{art_id}</loc><lastmod>{pub_date}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>')

    for guide in guides:
        guide_id = guide.get('id')
        if guide_id:
            urls.append(f'  <url><loc>{DOMAIN}/guide/{guide_id}</loc><lastmod>{today_str}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>')

    coins = ['BTC', 'ETH', 'SOL', 'LINK', 'ADA', 'DOT', 'UNI', 'AAVE']
    for coin in coins:
        urls.append(f'  <url><loc>{DOMAIN}/coin/{coin}</loc><lastmod>{today_str}</lastmod><changefreq>hourly</changefreq><priority>0.6</priority></url>')

    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml_content += '\n'.join(urls) + '\n'
    xml_content += '</urlset>\n'

    with open(SITEMAP_PATH, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f"Updated sitemap.xml with {len(urls)} URLs.")

    # Cloudflare Cache Purge if credentials exist
    cf_token = os.environ.get('CLOUDFLARE_API_TOKEN')
    cf_zone_id = os.environ.get('CLOUDFLARE_ZONE_ID')

    if cf_token and cf_zone_id:
        try:
            url = f"https://api.cloudflare.com/client/v4/zones/{cf_zone_id}/purge_cache"
            req = urllib.request.Request(
                url,
                data=json.dumps({"purge_everything": True}).encode('utf-8'),
                headers={
                    "Authorization": f"Bearer {cf_token}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                if result.get("success"):
                    print("Cloudflare cache purged successfully.")
                else:
                    print(f"Cloudflare purge warning: {result.get('errors')}")
        except Exception as e:
            print(f"Cloudflare API call failed: {e}")

if __name__ == '__main__':
    update_sitemap()
