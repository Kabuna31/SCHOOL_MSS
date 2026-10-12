import os
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school.settings')

# Automatically run migrations on startup for production/Render deployment
try:
    call_command('migrate', interactive=False)
    print("Database migrations applied successfully on startup.")
except Exception as e:
    print(f"Error applying migrations on startup: {e}")

application = get_wsgi_application()