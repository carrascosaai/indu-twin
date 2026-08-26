#!/bin/sh
set -e

DB_PATH="/app/data/indu_twin.db"
mkdir -p /app/data

if [ ! -f "$DB_PATH" ]; then
  echo "No hay base de datos en $DB_PATH, generando datos de demo..."
  python seed.py
fi

exec "$@"
