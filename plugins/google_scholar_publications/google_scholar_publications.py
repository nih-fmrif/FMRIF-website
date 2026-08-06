import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEFAULT_CACHE_DIR = "scholar-publications"


def _scholar_user_id(url):
    if not url:
        return ""
    parsed = urlparse(str(url))
    return parse_qs(parsed.query).get("user", [""])[0].strip()


def _publication_sort_key(publication):
    year = str(publication.get("year") or publication.get("publication_year") or "")
    title = str(publication.get("title") or "").lower()
    return (year, title)


def _normalize_publication(publication):
    title = str(publication.get("title") or "").strip()
    if not title:
        return None

    year = publication.get("year") or publication.get("publication_year")
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = str(year or "").strip()

    authors = publication.get("authors") or publication.get("display_authors") or ""
    if isinstance(authors, list):
        authors = ", ".join(str(author) for author in authors)
    venue = publication.get("venue") or publication.get("journal") or publication.get("publication") or ""
    url = publication.get("url") or publication.get("link") or publication.get("scholar_url") or ""
    citations = publication.get("citations") or publication.get("cited_by") or ""
    if isinstance(citations, dict):
        citations = citations.get("value") or ""

    return {
        "title": title,
        "authors": str(authors).strip(),
        "venue": str(venue).strip(),
        "year": year,
        "citations": citations,
        "url": str(url).strip(),
    }


def _read_cache_file(path):
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    profile = payload.get("profile", {}) if isinstance(payload, dict) else {}
    publications = payload.get("publications", payload) if isinstance(payload, dict) else payload
    if not isinstance(publications, list):
        return [], profile

    normalized = []
    seen_titles = set()
    for publication in publications:
        if not isinstance(publication, dict):
            continue
        normalized_publication = _normalize_publication(publication)
        if not normalized_publication:
            continue
        title_key = re.sub(r"\s+", " ", normalized_publication["title"].lower())
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        normalized.append(normalized_publication)

    normalized.sort(key=_publication_sort_key, reverse=True)
    return normalized, profile


def _load_publication_cache(settings):
    content_path = Path(settings["PATH"])
    cache_dir = Path(settings.get("SCHOLAR_PUBLICATIONS_CACHE_DIR", DEFAULT_CACHE_DIR))
    if not cache_dir.is_absolute():
        cache_dir = content_path / cache_dir

    publications_by_slug = {}
    publications_by_user_id = {}

    if not cache_dir.exists():
        return publications_by_slug, publications_by_user_id

    for path in sorted(cache_dir.glob("*.json")):
        publications, profile = _read_cache_file(path)
        publications_by_slug[path.stem] = publications
        publications_by_user_id[path.stem] = publications
        profile_user_id = str(profile.get("scholar_user_id") or "").strip()
        if profile_user_id:
            publications_by_user_id[profile_user_id] = publications

    return publications_by_slug, publications_by_user_id


def augment_staff_publications(settings, staff):
    publications_by_slug, publications_by_user_id = _load_publication_cache(settings)
    max_items = int(settings.get("SCHOLAR_PUBLICATIONS_LIMIT", 8))

    for person in staff:
        slug = str(person.get("slug") or "").strip()
        user_id = _scholar_user_id(person.get("scholar"))
        publications = publications_by_slug.get(slug) or publications_by_user_id.get(user_id) or []
        person["scholar_user_id"] = user_id
        person["scholar_publications"] = publications[:max_items] if max_items > 0 else publications

    return staff


def register():
    return
