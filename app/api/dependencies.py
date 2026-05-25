"""FastAPI dependencies shared across API endpoints."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

# Re-export for use in endpoint Depends()
__all__ = ["get_db"]
