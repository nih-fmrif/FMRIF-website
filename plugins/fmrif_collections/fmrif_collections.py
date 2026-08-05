import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path

from pelican import signals
from pelican.readers import MarkdownReader


COLLECTIONS = {
    "facilities": {
        "dir": "facilities",
        "template": "facility",
        "url": "facilities/{slug}/index.html",
    },
    "staff": {
        "dir": "staff",
        "template": "staff_member",
        "url": "staff/{slug}/index.html",
    },
    "summer_course": {
        "dir": "summer-course",
        "template": "course_page",
        "url": "summer-course/{slug}/index.html",
    },
    "recent_publications": {
        "dir": "recent-publications",
        "template": "recent_publication",
        "url": "recent-publications/{slug}/index.html",
    },
}


def _read_collection(generator, collection_name, spec):
    source_dir = Path(generator.settings["PATH"]) / spec["dir"]
    reader = MarkdownReader(generator.settings)
    items = []

    if not source_dir.exists():
        return items

    file_paths = source_dir.rglob("*.md") if collection_name == "summer_course" else source_dir.glob("*.md")

    for path in sorted(file_paths):
        content, metadata = reader.read(str(path))
        slug = str(metadata.get("slug") or path.stem).strip("/")
        output_save_as = spec["url"].format(slug=slug)
        item = {
            **metadata,
            "content": content,
            "slug": slug,
            "collection": collection_name,
            "url": "/" + output_save_as.removesuffix("index.html"),
        }
        items.append(item)

    if collection_name == "recent_publications":
        items.sort(
            key=lambda item: (
                str(item.get("sort_date", "")),
                str(item.get("title", "")).lower(),
            ),
            reverse=True,
        )
    elif collection_name == "staff":
        priority = {
            "peter-bandettini": 0,
            "dorian-van-tassell": 1,
        }
        items.sort(
            key=lambda item: (
                0 if item.get("status") == "Active" else 1,
                priority.get(str(item.get("slug", "")).lower(), 10),
                str(item.get("last_name", "")).lower(),
                str(item.get("title", "")).lower(),
            )
        )
    elif collection_name == "summer_course":
        items.sort(
            key=lambda item: (
                -int(item.get("year", 0)),
                int(item.get("number", 999)),
                str(item.get("title", "")).lower(),
            )
        )
    else:
        items.sort(key=lambda item: (int(item.get("weight", 99)), str(item.get("title", "")).lower()))

    return items


def _write_page(generator, template_name, output_save_as, context):
    output_path = os.path.join(generator.output_path, output_save_as)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    template = generator.get_template(template_name)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(template.render(context))


def _write_json(generator, output_save_as, data):
    output_path = os.path.join(generator.output_path, output_save_as)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return " ".join(self.parts)


def _plain_text(value):
    parser = _TextExtractor()
    parser.feed(str(value or ""))
    return re.sub(r"\s+", " ", parser.text()).strip()


def _summary(value, limit=180):
    text = _plain_text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def _page_search_items(generator):
    source_dir = Path(generator.settings["PATH"]) / "pages"
    reader = MarkdownReader(generator.settings)
    items = []

    if not source_dir.exists():
        return items

    for path in sorted(source_dir.glob("*.md")):
        content, metadata = reader.read(str(path))
        slug = str(metadata.get("slug") or path.stem).strip("/")
        title = str(metadata.get("title") or slug)
        items.append(
            {
                "title": title,
                "url": f"/{slug}/",
                "type": "Page",
                "summary": _summary(content),
                "text": " ".join([title, _plain_text(content)]),
            }
        )
    return items


def _collection_search_items(collections):
    labels = {
        "facilities": "Facility",
        "staff": "Staff",
        "summer_course": "Summer Course",
        "recent_publications": "Publication",
    }
    items = []

    for collection_name, collection_items in collections.items():
        for item in collection_items:
            title = str(item.get("title") or item.get("slug") or "").strip()
            if not title:
                continue
            metadata = " ".join(
                str(item.get(key, ""))
                for key in (
                    "first_name",
                    "last_name",
                    "job_title",
                    "role",
                    "status",
                    "year",
                    "display_authors",
                    "journal",
                    "publication_year",
                    "doi",
                    "pubmed_id",
                    "ic",
                )
            )
            text = " ".join([title, metadata, _plain_text(item.get("content"))])
            items.append(
                {
                    "title": title,
                    "url": item.get("url", "/"),
                    "type": labels.get(collection_name, "Content"),
                    "summary": _summary(item.get("content")),
                    "text": text,
                }
            )
    return items


def _write_search(generator, collections):
    _write_page(
        generator,
        "search",
        "search/index.html",
        {**generator.context, "item": {"title": "Search"}},
    )
    _write_json(
        generator,
        "search-index.json",
        _page_search_items(generator) + _collection_search_items(collections),
    )


def build_collections(generator):
    collections = {
        name: _read_collection(generator, name, spec)
        for name, spec in COLLECTIONS.items()
    }

    generator.context.update(
        {
            "fmrif_collections": collections,
            "facilities": collections["facilities"],
            "staff": collections["staff"],
            "summer_course_pages": collections["summer_course"],
            "summer_course_lectures_by_year": _course_lectures_by_year(collections["summer_course"]),
            "recent_publications": collections["recent_publications"],
            "recent_publication_ic_counts": _ic_counts(collections["recent_publications"]),
            "SITEURL": generator.settings.get("SITEURL", ""),
        }
    )

    for name, spec in COLLECTIONS.items():
        for item in collections[name]:
            context = {**generator.context, **item, "item": item}
            _write_page(generator, spec["template"], spec["url"].format(slug=item["slug"]), context)

    _write_page(
        generator,
        "recent_publications",
        "recent-publications/index.html",
        {**generator.context, "item": {"title": "Recent Publications"}},
    )
    _write_search(generator, collections)


def register():
    signals.article_generator_finalized.connect(build_collections)


def _ic_counts(publications):
    counts = {}
    for publication in publications:
        ic = str(publication.get("ic", "")).strip() or "Unspecified"
        counts[ic] = counts.get(ic, 0) + 1
    return [
        {"ic": ic, "count": count}
        for ic, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _course_lectures_by_year(lectures):
    years = {}
    for lecture in lectures:
        year = str(lecture.get("year", "")).strip()
        if not year:
            continue
        years.setdefault(year, []).append(lecture)

    grouped = []
    for year, year_lectures in years.items():
        grouped.append(
            {
                "year": year,
                "anchor": f"h-{year}",
                "lectures": sorted(
                    year_lectures,
                    key=lambda lecture: (
                        int(lecture.get("number", 999)),
                        str(lecture.get("title", "")).lower(),
                    ),
                ),
            }
        )
    return sorted(grouped, key=lambda group: int(group["year"]), reverse=True)
