#!/bin/sh
set -e

# Solo hace falta el directorio local si seguimos en SQLite (disco efimero
# de Render o desarrollo local); con Postgres no se usa para nada, pero
# crearlo no hace daño.
mkdir -p /app/data

# seed.py ya es idempotente (comprueba si ya hay datos antes de sembrar),
# asi que se puede llamar siempre sin condicion de fichero: la primera vez
# que arranca contra una base de datos vacia (SQLite nueva o Postgres recien
# creada) siembra los datos de demo; en cualquier arranque posterior no hace
# nada porque ya hay datos.
echo "Comprobando datos iniciales..."
python seed.py

exec "$@"
