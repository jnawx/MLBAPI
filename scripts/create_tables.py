"""
Create all database tables.

Usage:
    python -m scripts.create_tables
"""

import logging

from app.database import sync_engine
from app.models import Base  # noqa: F401 — import triggers model registration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Creating all tables...")
    Base.metadata.create_all(bind=sync_engine)
    logger.info("Done. All tables created.")


if __name__ == "__main__":
    main()
