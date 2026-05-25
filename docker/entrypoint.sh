#!/bin/sh
set -e

if [ "${RUN_DB_MIGRATIONS:-true}" = "true" ]; then
  python - <<'PY'
import os
import time

from sqlalchemy import text

from app.database import sync_engine

deadline = time.time() + int(os.getenv("DB_WAIT_SECONDS", "90"))
last_error = None

while time.time() < deadline:
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        break
    except Exception as exc:
        last_error = exc
        time.sleep(2)
else:
    raise SystemExit(f"Database did not become ready: {last_error}")
PY

  python -m scripts.create_tables
fi

exec "$@"

