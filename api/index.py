import os

from django.core.wsgi import get_wsgi_application

# Tell Django which settings module to load when Vercel starts this file.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
# Expose the Django WSGI app as `app` so Vercel can route HTTP requests to it.
app = get_wsgi_application()
