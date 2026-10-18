import hashlib
import difflib
from bs4 import BeautifulSoup
from django.core.cache import cache
import logging

def get_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def generate_diff(old_html, new_html):
    old_lines = old_html.splitlines()
    new_lines = new_html.splitlines()
    diff = difflib.HtmlDiff(wrapcolumn=80).make_table(
        old_lines, new_lines,
        fromdesc="Previous Version", todesc="Current Version",
        context=True, numlines=2
    )
    return diff

logger = logging.getLogger(__name__)

def cache_title(pageId, html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled Page"
    except Exception as e:
        logger.error(f"Title extraction failed for {pageId}: {e}")
        title = ''

    try:
        cacheKey = f"page_title:{pageId}"
        cache.set(cacheKey, title, timeout=60)
    except Exception as e:
        logger.error(f"[UTILS] Failed to cache title for {pageId}: {e}")

