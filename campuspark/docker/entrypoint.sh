#!/bin/sh
# entrypoint.sh
# Preenche os valores que faltarem no .env, aplica as migrations e sobe o servidor.
set -e

# ${VAR:-padrao} cobre tanto a variavel ausente quanto vazia (ex.: .env copiado do .env.example)
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"
export DJANGO_DEBUG="${DJANGO_DEBUG:-True}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-localhost,127.0.0.1,0.0.0.0}"
# Sem DATABASE_URL no .env, usa o PostgreSQL local do docker-compose (servico "db")
export DATABASE_URL="${DATABASE_URL:-postgresql://campuspark:campuspark@db:5432/campuspark}"

echo "Aplicando migrations..."
python manage.py migrate --noinput

exec "$@"
