import uuid
import logging
from urllib.parse import urlparse
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest, HttpResponseServerError, JsonResponse
from django.urls import reverse
from django.core.cache import cache
from scanner.models import MonitoredWebsite, WebPage
from scanner.jobs import schedule_scraper_for_site
from scanner.tasks import run_scraper_task
from scanner.utils import generate_diff

logger = logging.getLogger(__name__)

def isValidUrl(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ['http', 'https'] and parsed.netloc
    except Exception:
        logger.warning(f"URL parsing failed: {url}")
        return False

def home(request):
    if request.method == 'POST':
        siteUrl = request.POST.get('url', '').strip()
        freq = request.POST.get('frequency', '').strip()
        if not isValidUrl(siteUrl):
            logger.warning(f"Invalid URL submitted: {siteUrl}")
            return HttpResponseBadRequest("Invalid URL.")
        if freq not in ['hourly', 'daily', 'weekly']:
            logger.warning(f"Invalid frequency submitted: {freq}")
            return HttpResponseBadRequest("Invalid frequency.")
        try:
            site, created = MonitoredWebsite.objects.get_or_create(
                url=siteUrl,
                defaults={'frequency': freq}
            )
            if not created and site.frequency != freq:
                site.frequency = freq
                site.save()
            run_scraper_task.delay(str(site.uid), siteUrl)
            schedule_scraper_for_site(site)
        except Exception as e:
            logger.exception("Error during site creation or job scheduling")
            return HttpResponseServerError(f"Error: {str(e)}")
        return redirect(reverse('scanner:status', kwargs={'uid': site.uid}))
    return render(request, 'home.html')

def getTitle(pageId):
    title = cache.get(f"page_title:{pageId}")
    if title:
        pass
    else:
        logger.warning(f"Title missing in cache for {pageId}")
    return title or "[MISSING TITLE]"

def status(request, uid):
    site = get_object_or_404(MonitoredWebsite, uid=uid)
    pages = WebPage.objects.filter(website=site).order_by('-createdAt')
    err = None
    if request.method == 'POST':
        newUrl = request.POST.get('newPageUrl', '').strip()
        if not isValidUrl(newUrl):
            err = "Invalid URL format."
            logger.warning(f"Invalid manual URL: {newUrl}")
        else:
            siteDomain = urlparse(site.url).netloc
            newDomain = urlparse(newUrl).netloc
            if newDomain != siteDomain:
                err = "Only internal URLs are allowed."
                logger.warning(f" External URL blocked: {newUrl}")
            elif WebPage.objects.filter(url=newUrl, website=site).exists():
                err = "This page has already been scanned."
            else:
                try:
                    run_scraper_task.delay(str(site.uid), newUrl)
                    return redirect(reverse('scanner:status', kwargs={'uid': uid}))
                except Exception:
                    logger.exception("Failed to schedule manual page scrape.")
                    err = "Failed to schedule the page for scanning."
    pageList = []
    for p in pages:
        title = getTitle(p.uid)
        pageList.append({
            'page': p,
            'title': title,
        })
    return render(request, 'status.html', {
        'website': site,
        'pages': pageList,
        'error': err,
    })

def pageDetails(request, uid):
    page = get_object_or_404(WebPage, uid=uid)
    return render(request, 'details.html', {'page': page})

def changes(request, uid):
    site = get_object_or_404(MonitoredWebsite, uid=uid)
    pages = WebPage.objects.filter(website=site).order_by('url', '-createdAt')
    urlVersions = defaultdict(list)
    for p in pages:
        urlVersions[p.url].append(p)
    changed = []
    for url, versions in urlVersions.items():
        if len(versions) >= 2:
            latest, prev = versions[0], versions[1]
            if latest.pageHash != prev.pageHash or latest.html.strip() != prev.html.strip():
                if latest.pageHash == prev.pageHash:
                    logger.warning(f"Same hash, different HTML for {url}")
                diff = generate_diff(prev.html, latest.html)
                changed.append({
                    'url': url,
                    'latest': latest,
                    'previous': prev,
                    'diff': diff
                })
    return render(request, 'changes.html', {
        'website': site,
        'changed_pages': changed,
        'website_id': str(site.uid),
    })