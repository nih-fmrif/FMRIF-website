#!/usr/bin/env python3
import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen


SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
DEFAULT_ENV_FILE = ".env"


def load_env_file(path):
    env_path = Path(path)
    if not env_path.exists():
        return {}

    values = {}
    with env_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def read_metadata(path):
    metadata = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                break
            match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line.rstrip())
            if match:
                metadata[match.group(1).lower()] = match.group(2).strip()
    return metadata


def scholar_user_id(url):
    return parse_qs(urlparse(str(url)).query).get("user", [""])[0].strip()


def normalize_serpapi_article(article):
    cited_by = article.get("cited_by") or {}
    authors = article.get("authors", "")
    if isinstance(authors, list):
        authors = ", ".join(str(author) for author in authors)
    return {
        "title": article.get("title", "").strip(),
        "authors": str(authors).strip(),
        "venue": article.get("publication", "").strip(),
        "year": article.get("year", ""),
        "citations": cited_by.get("value", ""),
        "url": article.get("link", ""),
    }


def fetch_serpapi_author_publications(author_id, api_key, limit):
    params = {
        "engine": "google_scholar_author",
        "author_id": author_id,
        "api_key": api_key,
        "sort": "pubdate",
        "num": min(limit, 100),
    }
    with urlopen(f"{SERPAPI_ENDPOINT}?{urlencode(params)}", timeout=30) as response:
        payload = json.load(response)
    articles = payload.get("articles", [])
    return [normalize_serpapi_article(article) for article in articles[:limit]]


def harvest(content_dir, cache_dir, api_key, limit):
    staff_dir = content_dir / "staff"
    cache_dir.mkdir(parents=True, exist_ok=True)

    harvested = []
    for path in sorted(staff_dir.glob("*.md")):
        metadata = read_metadata(path)
        author_id = scholar_user_id(metadata.get("scholar", ""))
        if not author_id:
            continue

        publications = fetch_serpapi_author_publications(author_id, api_key, limit)
        output_path = cache_dir / f"{path.stem}.json"
        payload = {
            "profile": {
                "title": metadata.get("title", path.stem),
                "slug": metadata.get("slug", path.stem),
                "scholar_user_id": author_id,
                "scholar": metadata.get("scholar", ""),
            },
            "publications": publications,
        }
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        harvested.append((metadata.get("title", path.stem), len(publications), output_path))

    return harvested


def main():
    parser = argparse.ArgumentParser(
        description="Refresh cached Google Scholar publications for staff profiles."
    )
    parser.add_argument("--content-dir", default="content", type=Path)
    parser.add_argument("--cache-dir", default=None, type=Path)
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, type=Path)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--limit", default=12, type=int)
    args = parser.parse_args()

    env_values = load_env_file(args.env_file)
    api_key = args.api_key or os.environ.get("SERPAPI_KEY") or env_values.get("SERPAPI_KEY")

    if not api_key:
        raise SystemExit("Set SERPAPI_KEY in .env, export it, or pass --api-key.")

    content_dir = args.content_dir
    cache_dir = args.cache_dir or content_dir / "scholar-publications"
    harvested = harvest(content_dir, cache_dir, api_key, args.limit)

    for title, count, output_path in harvested:
        print(f"{title}: {count} publications -> {output_path}")


if __name__ == "__main__":
    main()
