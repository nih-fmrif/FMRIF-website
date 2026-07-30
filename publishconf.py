import os
import sys

sys.path.append(os.curdir)
from pelicanconf import *

SITEURL = os.environ.get("SITEURL", "https://fmrif.nimh.nih.gov")
RELATIVE_URLS = False
DELETE_OUTPUT_DIRECTORY = True

FEED_ALL_ATOM = "feeds/all.atom.xml"
CATEGORY_FEED_ATOM = "feeds/{slug}.atom.xml"
