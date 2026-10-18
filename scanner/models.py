import uuid
from django.db import models
from django.utils import timezone

class MonitoredWebsite(models.Model):
    FREQUENCY_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ]
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(unique=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='daily')
    def __str__(self):
        return self.url

class WebPage(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey('MonitoredWebsite', on_delete=models.CASCADE)
    url = models.URLField()
    pageHash = models.CharField(max_length=64)
    html = models.TextField()
    createdAt = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.website.url} → {self.url}"
     