release: python manage.py migrate_deployment
web: gunicorn school.wsgi:application --bind 0.0.0.0:$PORT
