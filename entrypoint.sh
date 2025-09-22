#!/bin/bash
set -e

echo "Environment variables:"
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "PYTHONPATH: $PYTHONPATH"

# Add app directory to PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# Wait for MongoDB
echo "Waiting for MongoDB..."
while ! nc -z mongodb 27017; do
  sleep 0.1
done
echo "MongoDB started"

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis started"

# Common tasks: migrations, superuser, static files
if [ "$SERVICE_TYPE" = "web" ]; then
    echo "Applying database migrations..."
    python manage.py makemigrations
    python manage.py migrate

    echo "Creating superuser if it doesn't exist..."
    python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME}').exists():
    User.objects.create_superuser('${DJANGO_SUPERUSER_USERNAME}', '${DJANGO_SUPERUSER_EMAIL}', '${DJANGO_SUPERUSER_PASSWORD}')
    print("Superuser created.")
else:
    print("Superuser already exists.")
EOF

    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

# Decide which service to run
if [ "$SERVICE_TYPE" = "web" ]; then
    echo "Starting Daphne server..."
    exec daphne -b 0.0.0.0 -p 8000 iTech.asgi:application
elif [ "$SERVICE_TYPE" = "worker" ]; then
    echo "Starting Celery worker..."
    exec celery -A iTech worker --loglevel=info
elif [ "$SERVICE_TYPE" = "beat" ]; then
    echo "Starting Celery beat..."
    exec celery -A iTech beat --loglevel=info
else
    echo "Unknown SERVICE_TYPE: $SERVICE_TYPE"
    exit 1
fi
