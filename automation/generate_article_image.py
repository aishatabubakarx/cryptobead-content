import os
import json
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_PATH = os.path.join(BASE_DIR, 'news', 'articles.json')
IMAGES_DIR = os.path.join(BASE_DIR, 'news', 'images')

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

def ensure_article_image():
    articles = load_json(ARTICLES_PATH, [])
    if not articles:
        print("No articles found.")
        return

    latest = articles[0]
    art_id = latest.get('id', 'default')
    current_img = latest.get('image', '')

    os.makedirs(IMAGES_DIR, exist_ok=True)
    local_filename = f"{art_id}.jpg"
    local_path = os.path.join(IMAGES_DIR, local_filename)

    # If already pointing to a local relative path and file exists, done
    if current_img.startswith('/news/images/') or current_img.startswith('news/images/'):
        print(f"Article {art_id} already has local image: {current_img}")
        return

    # If it's a remote URL, download it locally to news/images/
    if current_img.startswith('http'):
        try:
            req = urllib.request.Request(
                current_img,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp, open(local_path, 'wb') as out_file:
                out_file.write(resp.read())
            
            latest['image'] = f"/news/images/{local_filename}"
            save_json(ARTICLES_PATH, articles)
            print(f"Downloaded cover image for article {art_id} to /news/images/{local_filename}")
        except Exception as e:
            print(f"Warning: Could not download remote image: {e}")

if __name__ == '__main__':
    ensure_article_image()
