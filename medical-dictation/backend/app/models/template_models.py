"""Pydantic models for template API endpoints"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator
import re


# ═══════════════════════════════════════════════════════════════
# BASE MODELS
# ═══════════════════════════════════════════════════════════════

class TemplateBase(BaseModel):
    """Base template model with common fields"""
    trigger_phrases: List[str] = Field(
        ..., 
        min_length=1,
        description="Voice trigger phrases for this template"
    )
    content: str = Field(
        ..., 
        min_length=1,
        description="Template content to insert"
    )
    category: str = Field(
        default="general",
        description="Template category for organization"
    )
    description: str = Field(
        default="",
        description="Brief description of the template"
    )
    author: str = Field(
        default="",
        description="Template creator name"
    )


# ═══════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════

class TemplateCreate(TemplateBase):
    """Model for creating a new template"""
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Unique template identifier (lowercase, underscores allowed)"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is lowercase with only alphanumeric and underscores"""
        v = v.lower().strip()
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(
                "Name must start with a letter and contain only lowercase letters, numbers, and underscores"
            )
        return v
    
    @field_validator("trigger_phrases")
    @classmethod
    def validate_trigger_phrases(cls, v: List[str]) -> List[str]:
        """Clean and validate trigger phrases"""
        # Remove empty strings, strip whitespace, lowercase
        phrases = list(set([p.strip().lower() for p in v if p.strip()]))
        if not phrases:
            raise ValueError("At least one trigger phrase is required")
        return phrases
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "my_custom_template",
                "trigger_phrases": ["my template", "custom template", "insert my template"],
                "content": "━━━━━━━━━━━━━━━━━━━━\nMY CUSTOM TEMPLATE\n━━━━━━━━━━━━━━━━━━━━\n\nContent here: ___\n",
                "category": "custom",
                "description": "A custom template for demonstration",
                "author": "Dr. Smith"
            }
        }
    }


class TemplateUpdate(BaseModel):
    """Model for updating an existing template"""
    trigger_phrases: Optional[List[str]] = None
    content: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    
    @field_validator("trigger_phrases")
    @classmethod
    def validate_trigger_phrases(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Clean and validate trigger phrases if provided"""
        if v is not None:
            phrases = list(set([p.strip().lower() for p in v if p.strip()]))
            if not phrases:
                raise ValueError("At least one trigger phrase is required")
            return phrases
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "trigger_phrases": ["updated trigger", "new trigger phrase"],
                "content": "Updated template content...",
                "category": "updated_category"
            }
        }
    }


class TemplateBulkImport(BaseModel):
    """Model for bulk importing templates"""
    templates: List[TemplateCreate] = Field(
        ...,
        description="List of templates to import"
    )
    overwrite: bool = Field(
        default=False,
        description="Overwrite existing templates with same name"
    )


class TemplateTestRequest(BaseModel):
    """Model for testing template processing"""
    text: str = Field(
        ..., 
        min_length=1,
        description="Text to process for voice commands"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Patient presents with chest pain period insert vitals new paragraph"
            }
        }
    }


# ═══════════════════════════════════════════════════════════════
# RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class TemplateResponse(BaseModel):
    """Model for template response"""
    id: int
    name: str
    trigger_phrases: List[str]
    content: str
    category: str
    description: str
    author: str
    created_at: str
    updated_at: str
    is_active: bool = True
    
    model_config = {
        "from_attributes": True
    }


class TemplateListResponse(BaseModel):
    """Model for listing templates"""
    templates: List[TemplateResponse]
    total: int
    categories: List[str]


class TemplateTestResponse(BaseModel):
    """Response for template test"""
    original_text: str
    processed_text: str
    commands_executed: List[dict]


class TemplateStatsResponse(BaseModel):
    """Response for template statistics"""
    total_templates: int
    registered_patterns: int
    categories: List[str]
    templates_by_category: dict
    database: dict


class BulkImportResponse(BaseModel):
    """Response for bulk import operation"""
    created: int
    updated: int
    errors: List[dict]


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Operation completed successfully"
            }
        }
    }