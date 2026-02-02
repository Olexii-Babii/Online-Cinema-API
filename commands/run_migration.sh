#!/bin/sh
set -e


ALEMBIC_CONFIG="/usr/src/fastapi/alembic.ini"

echo "Waiting for PostgreSQL to be ready..."

while ! nc -z $POSTGRES_HOST 5432; do
  sleep 0.1
done
echo "PostgreSQL is up!"

echo "Applying migrations to database: $POSTGRES_DB..."

alembic -c "$ALEMBIC_CONFIG" upgrade head

echo "Migrations applied successfully!"

echo "Running database populate script..."
python -m database.populate_db
echo "Database populate script completed."
