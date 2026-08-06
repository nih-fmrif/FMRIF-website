AUTHOR = "Functional MRI Facility"
SITENAME = "Functional MRI Facility"
SITEURL = ""

PATH = "content"
TIMEZONE = "America/New_York"
DEFAULT_LANG = "en"

THEME = "themes/fmrif"
STATIC_PATHS = ["images", "assets", "pdf"]

PAGE_PATHS = ["pages"]
ARTICLE_PATHS = []
PAGE_URL = "{slug}/"
PAGE_SAVE_AS = "{slug}/index.html"
DISPLAY_PAGES_ON_MENU = False
DEFAULT_PAGINATION = False
RELATIVE_URLS = True

MARKDOWN = {
    "extensions": ["extra", "codehilite", "toc", "meta"],
    "output_format": "html5",
}

PLUGINS = [
    "plugins.google_scholar_publications",
    "plugins.fmrif_collections",
]

SCHOLAR_PUBLICATIONS_CACHE_DIR = "scholar-publications"
SCHOLAR_PUBLICATIONS_LIMIT = 8

FMRIF_NAV = [
    ("Facilities", "/FMRIF_scanners/"),
    ("Staff", "/Staff/"),
    ("Summer Course", "/SummerCourse/"),
    ("Publications", "/recent-publications/"),
    ("Data Download", "https://fmrif-xnat.nimh.nih.gov/"),
    ("Scanner Schedules", "https://oxygen.nimh.nih.gov/internal/schedule/"),
]

FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None
