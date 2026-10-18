import os
import sys
import uuid
import asyncio
import aiohttp
import asyncpg
import logging
import logging.config
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from dotenv import load_dotenv
from django.core.cache import cache
import django
from django.conf import settings
from scanner.utils import get_hash,cache_title 

logPath = os.path.join(settings.BASE_DIR, 'logs', 'app.log')
os.makedirs(os.path.dirname(logPath), exist_ok=True)
if hasattr(settings, 'LOGGING'):
    logging.config.dictConfig(settings.LOGGING)
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('scanner')
load_dotenv()

async def getConn():
    return await asyncpg.connect(
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD"),
        database=os.getenv("DATABASE_NAME"),
        host=os.getenv("DATABASE_HOST"),
        port=os.getenv("DATABASE_PORT", "5432"),
    )

async def fetchPage(session, url):
    try:
        async with session.get(url, timeout=15) as res:
            if res.status == 200:
                return await res.text()
            logger.warning(f"[{res.status}] Non-200 response for {url}")
    except Exception as e:
        logger.error(f"FETCH ERROR {url}: {e}")
    return None

def extractLinks(html, baseUrl):
    soup = BeautifulSoup(html, 'html.parser')
    baseHost = urlparse(baseUrl).netloc.lower()
    links = set()
    for tag in soup.find_all('a', href=True):
        href = tag['href'].strip()
        if href.startswith(('#', 'mailto:', 'javascript:', 'tel:', 'ftp:')):
            continue
        absUrl = urljoin(baseUrl, href)
        parsed = urlparse(absUrl)
        if parsed.scheme not in ('http', 'https'):
            continue
        if parsed.netloc.lower() != baseHost:
            continue
        cleanUrl, _ = urldefrag(absUrl)
        links.add(cleanUrl.rstrip('/'))
    return sorted(links)

async def savePage(conn, siteId, url, pageHash, html):
    pageId = str(uuid.uuid4())
    await conn.execute("""
    INSERT INTO scanner_webpage ("uid", "website_id", "url", "pageHash", "html", "createdAt")
    VALUES ($1, $2, $3, $4, $5, NOW())
    """, pageId, uuid.UUID(siteId), url, pageHash, html)
    return pageId, html

async def scrapeSite(baseUrl, siteId):
    visited = set()
    toVisit = [baseUrl.rstrip('/')]
    conn = await getConn()
    count = 0
    async with aiohttp.ClientSession() as session:
        while toVisit:
            url = toVisit.pop(0)
            if url in visited:
                logger.debug(f"Already visited: {url}")
                continue
            visited.add(url)
            html = await fetchPage(session, url)
            if html:
                pageHash = get_hash(html)
                pageId, html = await savePage(conn, siteId, url, pageHash, html)
                cache_title(pageId, html)
                count += 1
                links = extractLinks(html, baseUrl)
                for link in links:
                    if link not in visited and link not in toVisit:
                        logger.debug(f"Adding to queue: {link}")
                        toVisit.append(link)
    await conn.close()

def runScraper(baseUrl, siteId):
    asyncio.run(scrapeSite(baseUrl, siteId))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        logger.error("Usage: python scanner/runner.py <BASE_URL> <WEBSITE_ID>")
    else:
        runScraper(sys.argv[1], sys.argv[2])
