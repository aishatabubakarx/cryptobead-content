"""
Removes the broken Bitkub article (the one with the mangled TITLE field
and missing image) from news/articles.json and sitemap.xml.

Usage:
    python3 remove_bitkub_article.py

Run this from the root of your cryptobead-content project (the folder
that contains news/articles.json and sitemap.xml).
"""

import json
import os

ARTICLE_ID = "bitkub-faces-thai-sec-criminal-complaint-over-47m-undisclosed-hack-tha-202607272110"

ARTICLES_JSON = "news/articles.json"
SITEMAP = "sitemap.xml"


def remove_from_articles_json():
    if not os.path.exists(ARTICLES_JSON):
        print(f"Skipping: {ARTICLES_JSON} not found here.")
        return
    with open(ARTICLES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    before = len(data)
    data = [a for a in data if a.get("id") != ARTICLE_ID]
    after = len(data)
    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"{ARTICLES_JSON}: {before} -> {after} articles "
          f"({'removed' if before != after else 'not found, nothing removed'})")


def remove_from_sitemap():
    if not os.path.exists(SITEMAP):
        print(f"Skipping: {SITEMAP} not found here.")
        return
    with open(SITEMAP, "r", encoding="utf-8") as f:
        lines = f.readlines()
    before = len(lines)
    lines = [line for line in lines if ARTICLE_ID not in line]
    after = len(lines)
    with open(SITEMAP, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"{SITEMAP}: {before} -> {after} lines "
          f"({'removed' if before != after else 'not found, nothing removed'})")


if __name__ == "__main__":
    remove_from_articles_json()
    remove_from_sitemap()
