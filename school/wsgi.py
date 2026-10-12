import os
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school.settings')

# Automatically run migrations and ensure columns exist on startup for Render
try:
    call_command('migrate', interactive=False)
    print("Database migrations applied successfully on startup.")
except Exception as e:
    print(f"Error applying migrations on startup: {e}")

# Fallback safety check: ensure school_id exists on users_customuser table in PostgreSQL
try:
    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE users_customuser 
            ADD COLUMN IF NOT EXISTS school_id INTEGER 
            REFERENCES administration_school(id) ON DELETE SET NULL;
        """)
    print("Checked and ensured school_id column exists on users_customuser.")
except Exception as ex:
    print(f"Safe column check note: {ex}")

application = get_wsgi_application()