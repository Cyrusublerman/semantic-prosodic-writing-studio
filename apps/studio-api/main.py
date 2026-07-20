"""Studio API entry — re-exports the WordRare FastAPI app during migration."""

from app import app

__all__ = ["app"]
