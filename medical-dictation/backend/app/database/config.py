"""Database configuration settings"""

import os
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseSettings:
    """
    SQLite database configuration.
    
    Attributes:
        db_path: Relative path to database file from backend directory
        timeout: Connection timeout in seconds
        check_same_thread: SQLite thread safety setting
        foreign_keys: Enable foreign key constraints
        wal_mode: Enable Write-Ahead Logging for better concurrency
    """
    
    db_path: str = "data/templates.db"
    timeout: float = 30.0
    check_same_thread: bool = False
    foreign_keys: bool = True
    wal_mode: bool = True
    
    @property
    def db_url(self) -> str:
        """Get SQLite connection URL"""
        return f"sqlite:///{self.db_path}"
    
    @property
    def absolute_path(self) -> Path:
        """
        Get absolute path to database file.
        Resolves relative to the backend directory.
        """
        # Get the backend directory (parent of app directory)
        # Structure: backend/app/database/config.py
        # So we go up 3 levels to get to backend/
        current_file = Path(__file__)
        backend_dir = current_file.parent.parent.parent
        
        return backend_dir / self.db_path
    
    def ensure_directory(self) -> Path:
        """
        Create database directory if it doesn't exist.
        
        Returns:
            Path to the database directory
        """
        db_dir = self.absolute_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Database directory ensured: {db_dir}")
        return db_dir


@lru_cache()
def get_db_settings() -> DatabaseSettings:
    """
    Get cached database settings from environment.
    
    Returns:
        DatabaseSettings instance configured from environment variables
    """
    settings = DatabaseSettings(
        db_path=os.getenv("DATABASE_PATH", "data/templates.db"),
        timeout=float(os.getenv("DATABASE_TIMEOUT", "30.0")),
    )
    
    # Ensure directory exists
    settings.ensure_directory()
    
    logger.info(f"Database settings loaded: {settings.absolute_path}")
    
    return settings