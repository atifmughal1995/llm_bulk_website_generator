from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bulk_website_generator.settings')

application = get_wsgi_application()