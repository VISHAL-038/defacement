import logging
from celery import shared_task
from scanner.runner import runScraper

logger = logging.getLogger(__name__)

@shared_task
def run_scraper_task(uid, url):
    try:
        runScraper(url, uid)
    except Exception as e:
        logger.error(f" Error scraping {url} ({uid}): {e}")
