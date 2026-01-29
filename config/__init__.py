"""
Configuration package for the cleaning service email automation system.

Provides centralized settings management via environment variables.
"""

from .settings import settings, Settings

__all__ = ["settings", "Settings"]
