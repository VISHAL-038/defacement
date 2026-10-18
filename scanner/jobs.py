import json
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .models import MonitoredWebsite

def schedule_scraper_for_site(site: MonitoredWebsite):
    frequency_map = {
        'hourly': (1, IntervalSchedule.HOURS),
        'daily': (1, IntervalSchedule.DAYS),
        'weekly': (7, IntervalSchedule.DAYS),
    }
    if site.frequency not in frequency_map:
        return
    every, period = frequency_map[site.frequency]
    interval, _ = IntervalSchedule.objects.get_or_create(every=every, period=period)
    PeriodicTask.objects.update_or_create(
        name=f"scraper-{site.uid}",
        defaults={
            'interval': interval,
            'task': 'scanner.tasks.run_scraper_task',
            'args': json.dumps([str(site.uid), site.url]),
        }
    )

def delete_scraper_task_for_site(site_uid):
    PeriodicTask.objects.filter(name=f"scraper-{site_uid}").delete()
