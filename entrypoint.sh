#!/bin/bash

echo "Waiting for PostgreSQL ($POSTGRES_HOST)..."

# Zmieniamy 'db_spc' na zmienną środowiskową, która zawiera adres Azure
while ! pg_isready -h $POSTGRES_HOST -p 5432 -U $POSTGRES_USER -d $POSTGRES_DB; do
    sleep 1
done
echo "PostgreSQL started"

echo "Running migrations..."

python manage.py makemigrations
python manage.py migrate


echo "Creating superuser if needed..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created!')
else:
    print('Superuser already exists')
"

PORT=${PORT:-8000}

echo "Starting server..."
exec gunicorn spc.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120