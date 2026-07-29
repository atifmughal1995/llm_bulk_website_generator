from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bulk_website_generator.settings')

app = Celery('bulk_website_generator')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()