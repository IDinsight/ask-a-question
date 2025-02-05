"""Package initialization for the FastAPI application.

This module imports and exposes key components required for API routing, including the
main FastAPI router.

Exports:
    - `router`: The main FastAPI APIRouter instance containing all route definitions.

These components can be imported directly from the package for use in the application.
"""

from .routers import router

__all__ = ["router"]
