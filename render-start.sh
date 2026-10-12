#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

python manage.py migrate --noinput
exec daphne -b 0.0.0.0 -p "${PORT:?PORT not set}" managementProject.asgi:application
