"""One-time setup: create the mlbapi user and database on the PostgreSQL server."""

from __future__ import annotations

import os

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

ADMIN_HOST = os.getenv("POSTGRES_ADMIN_HOST", "192.168.1.3")
ADMIN_PORT = int(os.getenv("POSTGRES_ADMIN_PORT", "5432"))
ADMIN_USER = os.getenv("POSTGRES_ADMIN_USER", "gitlab")
ADMIN_PASSWORD = os.getenv("POSTGRES_ADMIN_PASSWORD", "")
ADMIN_DB = os.getenv("POSTGRES_ADMIN_DB", "gitlabhq_production")

APP_USER = os.getenv("POSTGRES_APP_USER", "mlbapi")
APP_PASSWORD = os.getenv("POSTGRES_APP_PASSWORD", "mlbapi")
APP_DB = os.getenv("POSTGRES_APP_DB", "mlbapi")

conn = psycopg2.connect(
    host=ADMIN_HOST,
    port=ADMIN_PORT,
    user=ADMIN_USER,
    password=ADMIN_PASSWORD,
    dbname=ADMIN_DB,
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# Create mlbapi user
cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_USER,))
if not cur.fetchone():
    cur.execute(
        sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(APP_USER)),
        (APP_PASSWORD,),
    )
    print(f"Created user: {APP_USER}")
else:
    print(f"User {APP_USER} already exists")

# Create mlbapi database
cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (APP_DB,))
if not cur.fetchone():
    cur.execute(
        sql.SQL("CREATE DATABASE {} OWNER {}").format(
            sql.Identifier(APP_DB),
            sql.Identifier(APP_USER),
        )
    )
    print(f"Created database: {APP_DB}")
else:
    print(f"Database {APP_DB} already exists")

# Grant privileges
cur.execute(
    sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
        sql.Identifier(APP_DB),
        sql.Identifier(APP_USER),
    )
)
print(f"Granted privileges to {APP_USER}")

cur.close()
conn.close()
print("Done! You can now run: python -m scripts.create_tables")
