"""
Backfill entry point script.

Usage:
    python -m scripts.run_backfill --start-year 2021
    python -m scripts.run_backfill --start-year 2023 --end-year 2024
"""

from ingestion.backfill import main

if __name__ == "__main__":
    main()
