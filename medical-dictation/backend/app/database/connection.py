"""Database connection management for SQLite"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Generator, Any, List

from .config import get_db_settings, DatabaseSettings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    SQLite database connection manager.
    
    Implements singleton pattern to ensure single connection manager instance.
    Provides context manager for safe connection handling with automatic
    commit/rollback.
    
    Usage:
        db = DatabaseConnection()
        
        # Using context manager (recommended)
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM templates")
            results = cursor.fetchall()
        
        # Using helper methods
        row = db.fetch_one("SELECT * FROM templates WHERE name = ?", ("my_template",))
        rows = db.fetch_all("SELECT * FROM templates")
    """
    
    _instance: Optional['DatabaseConnection'] = None
    
    def __new__(cls) -> 'DatabaseConnection':
        """Singleton pattern - only one instance allowed"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize connection manager (only runs once due to singleton)"""
        if self._initialized:
            return
        
        self.settings: DatabaseSettings = get_db_settings()
        self._initialized = True
        
        logger.info(f"Database connection manager initialized")
        logger.info(f"  Path: {self.settings.absolute_path}")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections.
        
        Automatically commits on success, rolls back on error,
        and closes connection when done.
        
        Yields:
            sqlite3.Connection: Active database connection
        
        Example:
            with db.get_connection() as conn:
                conn.execute("INSERT INTO templates ...")
                # Auto-commits here if no error
        """
        conn = sqlite3.connect(
            str(self.settings.absolute_path),
            timeout=self.settings.timeout,
            check_same_thread=self.settings.check_same_thread
        )
        
        # Enable dict-like row access (row["column_name"])
        conn.row_factory = sqlite3.Row
        
        # Enable foreign key constraints
        if self.settings.foreign_keys:
            conn.execute("PRAGMA foreign_keys = ON")
        
        # Enable WAL mode for better concurrent access
        if self.settings.wal_mode:
            conn.execute("PRAGMA journal_mode = WAL")
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error, rolled back: {e}")
            raise
        finally:
            conn.close()
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query and return the cursor.
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            sqlite3.Cursor: Query cursor
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute a query with multiple parameter sets.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
        
        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params_list)
            return cursor.rowcount
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Fetch a single row.
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            Single row or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        Fetch all rows.
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            List of rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
        
        Returns:
            True if table exists
        """
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = self.fetch_one(query, (table_name,))
        return result is not None
    
    def get_table_info(self, table_name: str) -> List[dict]:
        """
        Get column information for a table.
        
        Args:
            table_name: Name of the table
        
        Returns:
            List of column info dicts
        """
        rows = self.fetch_all(f"PRAGMA table_info({table_name})")
        return [
            {
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "default": row["dflt_value"],
                "pk": bool(row["pk"])
            }
            for row in rows
        ]


# ═══════════════════════════════════════════════════════════════
# GLOBAL INSTANCE GETTER
# ═══════════════════════════════════════════════════════════════

def get_db_connection() -> DatabaseConnection:
    """
    Get the database connection manager instance.
    
    Returns:
        DatabaseConnection singleton instance
    """
    return DatabaseConnection()