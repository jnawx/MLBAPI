"""One-time setup: create the mlbapi user and database on the PostgreSQL server."""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

conn = psycopg2.connect(
    host="192.168.1.3",
    port=5432,
    user="gitlab",
    password="your_secure_password_here_please_change",
    dbname="gitlabhq_production",
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# Create mlbapi user
cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'mlbapi'")
if not cur.fetchone():
    cur.execute("CREATE USER mlbapi WITH PASSWORD 'mlbapi'")
    print("Created user: mlbapi")
else:
    print("User mlbapi already exists")

# Create mlbapi database
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'mlbapi'")
if not cur.fetchone():
    cur.execute("CREATE DATABASE mlbapi OWNER mlbapi")
    print("Created database: mlbapi")
else:
    print("Database mlbapi already exists")

# Grant privileges
cur.execute("GRANT ALL PRIVILEGES ON DATABASE mlbapi TO mlbapi")
print("Granted privileges to mlbapi")

cur.close()
conn.close()
print("Done! You can now run: python -m scripts.create_tables")
