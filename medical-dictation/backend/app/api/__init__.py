"""API module - REST endpoints"""

from .template_routes import router as template_router

__all__ = [
    "template_router",
]