"""
Template Manager Service

Bridges template storage (SQLite) with the command processor.
Loads templates from database and registers them as voice commands.
"""

import re
import logging
from typing import List, Optional, Dict, Any

from app.storage.template_storage import get_template_storage, TemplateStorage
from app.services.command_processor import (
    get_command_processor,
    CommandProcessor,
    VoiceCommand,
    CommandType
)

logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Template Manager Service
    
    Manages the lifecycle of custom templates:
    - Loads templates from SQLite database
    - Registers voice commands with the CommandProcessor
    - Handles CRUD operations with automatic command registration
    
    This is a singleton - use get_template_manager() to get the instance.
    
    Usage:
        manager = get_template_manager()
        
        # Create template (automatically registers voice command)
        manager.create_template(
            name="my_template",
            trigger_phrases=["my template"],
            content="Template content...",
            category="custom"
        )
        
        # Now user can say "insert my template" to insert the content
        
        # Test processing
        result = manager.test_processing("Patient has pain period insert my template")
        print(result["processed_text"])
    """
    
    _instance: Optional['TemplateManager'] = None
    
    def __new__(cls) -> 'TemplateManager':
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize template manager"""
        if self._initialized:
            return
        
        self.storage: TemplateStorage = get_template_storage()
        self.processor: CommandProcessor = get_command_processor()
        
        # Track registered patterns for each template
        self._registered_patterns: Dict[str, str] = {}
        
        # Load and register all existing templates
        self._load_all_templates()
        
        self._initialized = True
        logger.info("TemplateManager initialized")
    
    # ═══════════════════════════════════════════════════════════
    # INITIALIZATION
    # ═══════════════════════════════════════════════════════════
    
    def _load_all_templates(self):
        """Load all templates from database and register with processor"""
        templates = self.storage.get_all()
        
        for template in templates:
            self._register_template(template)
        
        logger.info(f"Loaded and registered {len(templates)} templates")
    
    def _build_pattern(self, trigger_phrases: List[str]) -> str:
        """
        Build regex pattern from trigger phrases.
        
        Creates a pattern that matches:
        - Exact phrase
        - "insert [phrase]"
        - "add [phrase]"
        - "[phrase] template"
        
        Args:
            trigger_phrases: List of trigger phrases
        
        Returns:
            Compiled regex pattern string
        
        Example:
            ["my template", "custom template"]
            → r"\\b(?:insert |add )?(?:my template|custom template)(?: template)?\\b"
        """
        # Escape special regex characters in phrases
        escaped = [re.escape(phrase.lower().strip()) for phrase in trigger_phrases]
        
        # Join with OR
        phrases_pattern = "|".join(escaped)
        
        # Build pattern with optional prefixes/suffixes
        # Matches: "my template", "insert my template", "add my template", "my template template"
        pattern = rf"\b(?:insert |add )?(?:{phrases_pattern})(?: template)?\b"
        
        return pattern
    
    def _register_template(self, template: Dict[str, Any]):
        """
        Register a template with the command processor.
        
        Args:
            template: Template dictionary from storage
        """
        name = template["name"]
        trigger_phrases = template["trigger_phrases"]
        content = template["content"]
        
        # Build regex pattern
        pattern = self._build_pattern(trigger_phrases)
        
        # Create voice command
        command = VoiceCommand(
            command_type=CommandType.TEMPLATE,
            action=name,
            replacement=content
        )
        
        # Register with processor
        self.processor.register_custom_command(pattern, command)
        
        # Store pattern for later unregistration
        self._registered_patterns[name] = pattern
        
        logger.debug(f"Registered template command: {name} ({len(trigger_phrases)} triggers)")
    
    def _unregister_template(self, name: str):
        """
        Unregister a template from the command processor.
        
        Args:
            name: Template name to unregister
        """
        if name in self._registered_patterns:
            pattern = self._registered_patterns[name]
            self.processor.unregister_custom_command(pattern)
            del self._registered_patterns[name]
            logger.debug(f"Unregistered template command: {name}")
    
    # ═══════════════════════════════════════════════════════════
    # CRUD OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def create_template(
        self,
        name: str,
        trigger_phrases: List[str],
        content: str,
        category: str = "general",
        description: str = "",
        author: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new custom template.
        
        The template is saved to the database and immediately registered
        as a voice command.
        
        Args:
            name: Unique template identifier (lowercase, alphanumeric + underscores)
            trigger_phrases: Voice commands to trigger this template
            content: Template content to insert
            category: Category for organization
            description: Brief description
            author: Creator name
        
        Returns:
            Created template dictionary
        
        Raises:
            ValueError: If template name already exists or validation fails
        """
        # Create in storage
        template = self.storage.create({
            "name": name,
            "trigger_phrases": trigger_phrases,
            "content": content,
            "category": category,
            "description": description,
            "author": author
        })
        
        # Register with processor
        self._register_template(template)
        
        logger.info(f"Created template: {name}")
        return template
    
    def update_template(
        self,
        name: str,
        trigger_phrases: Optional[List[str]] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        author: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing template.
        
        Only provided fields are updated. The voice command is re-registered
        with updated trigger phrases if changed.
        
        Args:
            name: Template name to update
            Other args: Fields to update (None = don't update)
        
        Returns:
            Updated template or None if not found
        """
        # Unregister old version first
        self._unregister_template(name)
        
        # Build update data (only non-None values)
        update_data = {}
        if trigger_phrases is not None:
            update_data["trigger_phrases"] = trigger_phrases
        if content is not None:
            update_data["content"] = content
        if category is not None:
            update_data["category"] = category
        if description is not None:
            update_data["description"] = description
        if author is not None:
            update_data["author"] = author
        
        # Update in storage
        template = self.storage.update(name, update_data)
        
        if template:
            # Re-register with new settings
            self._register_template(template)
            logger.info(f"Updated template: {name}")
        
        return template
    
    def delete_template(self, name: str, hard_delete: bool = False) -> bool:
        """
        Delete a template.
        
        The voice command is unregistered immediately.
        
        Args:
            name: Template name to delete
            hard_delete: Permanently delete if True, soft delete if False
        
        Returns:
            True if deleted, False if not found
        """
        # Unregister from processor first
        self._unregister_template(name)
        
        # Delete from storage
        result = self.storage.delete(name, hard_delete=hard_delete)
        
        if result:
            logger.info(f"Deleted template: {name}")
        
        return result
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a template by name.
        
        Args:
            name: Template name
        
        Returns:
            Template dictionary or None
        """
        return self.storage.get_by_name(name)
    
    def list_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all templates.
        
        Args:
            category: Filter by category (optional)
        
        Returns:
            List of template dictionaries
        """
        return self.storage.get_all(category=category)
    
    def get_categories(self) -> List[str]:
        """
        Get all template categories.
        
        Returns:
            List of category names
        """
        return self.storage.get_categories()
    
    def search_templates(self, query: str) -> List[Dict[str, Any]]:
        """
        Search templates by name, content, or description.
        
        Args:
            query: Search term
        
        Returns:
            List of matching templates
        """
        return self.storage.search(query)
    
    # ═══════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════
    
    def refresh(self):
        """
        Reload all templates from database.
        
        Use this after manual database changes or to sync state.
        """
        # Unregister all current templates
        for name in list(self._registered_patterns.keys()):
            self._unregister_template(name)
        
        # Reload from database
        self._load_all_templates()
        
        logger.info("Templates refreshed from database")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get template statistics.
        
        Returns:
            Dictionary with stats including counts and categories
        """
        templates = self.storage.get_all()
        categories = self.storage.get_categories()
        
        # Count by category
        category_counts = {}
        for template in templates:
            cat = template["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "total_templates": len(templates),
            "registered_patterns": len(self._registered_patterns),
            "categories": categories,
            "templates_by_category": category_counts
        }
    
    def test_processing(self, text: str) -> Dict[str, Any]:
        """
        Test how text would be processed with current templates.
        
        Useful for debugging and verifying template triggers work correctly.
        
        Args:
            text: Input text with potential voice commands
        
        Returns:
            Dictionary with original text, processed text, and executed commands
        """
        processed_text, commands = self.processor.process(text)
        
        return {
            "original_text": text,
            "processed_text": processed_text,
            "commands_executed": [
                {
                    "type": cmd.command_type.value if hasattr(cmd.command_type, 'value') else str(cmd.command_type),
                    "action": cmd.action,
                    "original_text": cmd.original_text,
                    "replacement_preview": cmd.replacement[:100] + "..." if len(cmd.replacement) > 100 else cmd.replacement
                }
                for cmd in commands
            ]
        }
    
    def get_all_triggers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available voice triggers grouped by template.
        
        Returns:
            Dictionary mapping template names to their trigger info
        """
        templates = self.storage.get_all()
        
        triggers = {}
        for template in templates:
            triggers[template["name"]] = {
                "phrases": template["trigger_phrases"],
                "category": template["category"],
                "description": template["description"]
            }
        
        return triggers


# ═══════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════

_manager_instance: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """
    Get the template manager singleton instance.
    
    Returns:
        TemplateManager instance
    """
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = TemplateManager()
    
    return _manager_instance