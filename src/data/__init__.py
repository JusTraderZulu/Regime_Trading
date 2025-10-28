"""
Central Data Access Layer

Provides unified, resilient data access with caching, retry, and fallback logic.
"""

from src.data.manager import DataAccessManager

__all__ = ['DataAccessManager']

