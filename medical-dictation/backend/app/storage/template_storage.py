"""SQLite storage implementation for templates"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database.connection import get_db_connection, DatabaseConnection

logger = logging.getLogger(__name__)


class TemplateStorage:
    """
    SQLite storage layer for custom templates.
    
    Provides CRUD operations, search, and bulk operations for templates.
    Uses the DatabaseConnection singleton for all database access.
    
    Usage:
        storage = TemplateStorage()
        
        # Create
        template = storage.create({
            "name": "my_template",
            "trigger_phrases": ["my template"],
            "content": "Template content...",
            "category": "custom"
        })
        
        # Read
        template = storage.get_by_name("my_template")
        all_templates = storage.get_all()
        
        # Update
        storage.update("my_template", {"content": "New content"})
        
        # Delete
        storage.delete("my_template")
    """
    
    def __init__(self):
        """Initialize storage with database connection"""
        self.db: DatabaseConnection = get_db_connection()
        logger.debug("TemplateStorage initialized")
    
    # ═══════════════════════════════════════════════════════════
    # CREATE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def create(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new template.
        
        Args:
            template_data: Dictionary containing:
                - name (required): Unique template name
                - trigger_phrases (required): List of voice triggers
                - content (required): Template content
                - category (optional): Category name
                - description (optional): Template description
                - author (optional): Author name
        
        Returns:
            Created template as dictionary
        
        Raises:
            ValueError: If template with same name exists or required fields missing
        """
        name = template_data.get("name")
        
        if not name:
            raise ValueError("Template name is required")
        
        if not template_data.get("trigger_phrases"):
            raise ValueError("Trigger phrases are required")
        
        if not template_data.get("content"):
            raise ValueError("Template content is required")
        
        # Check if exists
        if self.get_by_name(name):
            raise ValueError(f"Template '{name}' already exists")
        
        # Prepare data
        now = datetime.now().isoformat()
        trigger_phrases = template_data.get("trigger_phrases", [])
        
        # Convert list to JSON string if needed
        if isinstance(trigger_phrases, list):
            trigger_phrases_json = json.dumps(trigger_phrases)
        else:
            trigger_phrases_json = trigger_phrases
        
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO templates 
                (name, trigger_phrases, content, category, description, author, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                trigger_phrases_json,
                template_data.get("content", ""),
                template_data.get("category", "general"),
                template_data.get("description", ""),
                template_data.get("author", ""),
                now,
                now
            ))
            
            template_id = cursor.lastrowid
        
        logger.info(f"Created template: {name} (ID: {template_id})")
        
        # Return created template
        return self.get_by_name(name)
    
    # ═══════════════════════════════════════════════════════════
    # READ OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a template by name.
        
        Args:
            name: Template name
        
        Returns:
            Template dictionary or None if not found
        """
        row = self.db.fetch_one(
            "SELECT * FROM templates WHERE name = ? AND is_active = 1",
            (name,)
        )
        
        if row:
            return self._row_to_dict(row)
        return None
    
    def get_by_id(self, template_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a template by ID.
        
        Args:
            template_id: Template ID
        
        Returns:
            Template dictionary or None if not found
        """
        row = self.db.fetch_one(
            "SELECT * FROM templates WHERE id = ? AND is_active = 1",
            (template_id,)
        )
        
        if row:
            return self._row_to_dict(row)
        return None
    
    def get_all(
        self, 
        category: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all templates.
        
        Args:
            category: Filter by category (optional)
            include_inactive: Include soft-deleted templates
        
        Returns:
            List of template dictionaries
        """
        if include_inactive:
            if category:
                rows = self.db.fetch_all(
                    "SELECT * FROM templates WHERE category = ? ORDER BY name",
                    (category,)
                )
            else:
                rows = self.db.fetch_all(
                    "SELECT * FROM templates ORDER BY name"
                )
        else:
            if category:
                rows = self.db.fetch_all(
                    "SELECT * FROM templates WHERE category = ? AND is_active = 1 ORDER BY name",
                    (category,)
                )
            else:
                rows = self.db.fetch_all(
                    "SELECT * FROM templates WHERE is_active = 1 ORDER BY name"
                )
        
        return [self._row_to_dict(row) for row in rows]
    
    def get_categories(self) -> List[str]:
        """
        Get all unique categories.
        
        Returns:
            List of category names
        """
        rows = self.db.fetch_all(
            "SELECT DISTINCT category FROM templates WHERE is_active = 1 ORDER BY category"
        )
        return [row["category"] for row in rows]
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search templates by name, content, or description.
        
        Args:
            query: Search term
        
        Returns:
            List of matching templates
        """
        search_term = f"%{query}%"
        
        rows = self.db.fetch_all("""
            SELECT * FROM templates 
            WHERE is_active = 1 
            AND (
                name LIKE ? 
                OR content LIKE ? 
                OR description LIKE ?
                OR trigger_phrases LIKE ?
            )
            ORDER BY name
        """, (search_term, search_term, search_term, search_term))
        
        return [self._row_to_dict(row) for row in rows]
    
    def count(self, category: Optional[str] = None) -> int:
        """
        Count templates.
        
        Args:
            category: Filter by category (optional)
        
        Returns:
            Number of templates
        """
        if category:
            row = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM templates WHERE category = ? AND is_active = 1",
                (category,)
            )
        else:
            row = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM templates WHERE is_active = 1"
            )
        
        return row["count"] if row else 0
    
    # ═══════════════════════════════════════════════════════════
    # UPDATE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def update(self, name: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a template.
        
        Args:
            name: Template name to update
            update_data: Dictionary of fields to update
        
        Returns:
            Updated template or None if not found
        """
        # Check if exists
        existing = self.get_by_name(name)
        if not existing:
            return None
        
        # Build update query dynamically
        allowed_fields = ["trigger_phrases", "content", "category", "description", "author"]
        updates = []
        values = []
        
        for field in allowed_fields:
            if field in update_data and update_data[field] is not None:
                value = update_data[field]
                
                # Convert trigger_phrases list to JSON
                if field == "trigger_phrases" and isinstance(value, list):
                    value = json.dumps(value)
                
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            return existing
        
        # Add updated_at
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        
        # Add name to values for WHERE clause
        values.append(name)
        
        query = f"UPDATE templates SET {', '.join(updates)} WHERE name = ?"
        
        with self.db.get_connection() as conn:
            conn.execute(query, tuple(values))
        
        logger.info(f"Updated template: {name}")
        
        return self.get_by_name(name)
    
    # ═══════════════════════════════════════════════════════════
    # DELETE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def delete(self, name: str, hard_delete: bool = False) -> bool:
        """
        Delete a template.
        
        Args:
            name: Template name to delete
            hard_delete: If True, permanently delete. If False, soft delete.
        
        Returns:
            True if deleted, False if not found
        """
        with self.db.get_connection() as conn:
            if hard_delete:
                cursor = conn.execute(
                    "DELETE FROM templates WHERE name = ?",
                    (name,)
                )
            else:
                # Soft delete
                cursor = conn.execute(
                    "UPDATE templates SET is_active = 0, updated_at = ? WHERE name = ?",
                    (datetime.now().isoformat(), name)
                )
            
            deleted = cursor.rowcount > 0
        
        if deleted:
            action = "Hard deleted" if hard_delete else "Soft deleted"
            logger.info(f"{action} template: {name}")
        
        return deleted
    
    def restore(self, name: str) -> bool:
        """
        Restore a soft-deleted template.
        
        Args:
            name: Template name to restore
        
        Returns:
            True if restored, False if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE templates SET is_active = 1, updated_at = ? WHERE name = ?",
                (datetime.now().isoformat(), name)
            )
            restored = cursor.rowcount > 0
        
        if restored:
            logger.info(f"Restored template: {name}")
        
        return restored
    
    # ═══════════════════════════════════════════════════════════
    # BULK OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def bulk_create(self, templates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple templates at once.
        
        Args:
            templates: List of template dictionaries
        
        Returns:
            Dictionary with created count and errors
        """
        created = 0
        errors = []
        
        for template_data in templates:
            try:
                self.create(template_data)
                created += 1
            except ValueError as e:
                errors.append({
                    "name": template_data.get("name", "unknown"),
                    "error": str(e)
                })
        
        return {
            "created": created,
            "errors": errors
        }
    
    def export_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Export all templates as a dictionary.
        
        Returns:
            Dictionary with template names as keys
        """
        templates = self.get_all()
        return {t["name"]: t for t in templates}
    
    def import_templates(
        self, 
        templates: Dict[str, Dict[str, Any]], 
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Import templates from a dictionary.
        
        Args:
            templates: Dictionary of templates {name: template_data}
            overwrite: If True, overwrite existing templates
        
        Returns:
            Dictionary with import stats
        """
        created = 0
        updated = 0
        errors = []
        
        for name, template_data in templates.items():
            try:
                template_data["name"] = name
                existing = self.get_by_name(name)
                
                if existing:
                    if overwrite:
                        self.update(name, template_data)
                        updated += 1
                    else:
                        errors.append({
                            "name": name,
                            "error": "Template already exists"
                        })
                else:
                    self.create(template_data)
                    created += 1
                    
            except Exception as e:
                errors.append({
                    "name": name,
                    "error": str(e)
                })
        
        return {
            "created": created,
            "updated": updated,
            "errors": errors
        }
    
    # ═══════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """
        Convert database row to dictionary.
        
        Args:
            row: sqlite3.Row object
        
        Returns:
            Dictionary representation
        """
        trigger_phrases = row["trigger_phrases"]
        
        # Parse JSON if string
        if isinstance(trigger_phrases, str):
            try:
                trigger_phrases = json.loads(trigger_phrases)
            except json.JSONDecodeError:
                # If not valid JSON, wrap in list
                trigger_phrases = [trigger_phrases]
        
        return {
            "id": row["id"],
            "name": row["name"],
            "trigger_phrases": trigger_phrases,
            "content": row["content"],
            "category": row["category"],
            "description": row["description"],
            "author": row["author"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_active": bool(row["is_active"])
        }


# ═══════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════

_storage_instance: Optional[TemplateStorage] = None


def get_template_storage() -> TemplateStorage:
    """
    Get the template storage singleton instance.
    
    Returns:
        TemplateStorage instance
    """
    global _storage_instance
    
    if _storage_instance is None:
        _storage_instance = TemplateStorage()
    
    return _storage_instance