"""Template API endpoints for CRUD operations"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

from app.models.template_models import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListResponse,
    TemplateBulkImport,
    TemplateTestRequest,
    TemplateTestResponse,
    TemplateStatsResponse,
    BulkImportResponse,
    MessageResponse,
)
from app.services.template_manager import get_template_manager
from app.database.init_db import get_database_info

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/templates",
    tags=["Templates"],
    responses={
        404: {"description": "Template not found"},
        400: {"description": "Invalid request"},
    }
)


# ═══════════════════════════════════════════════════════════════
# LIST & SEARCH ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name, content, description")
):
    """
    List all templates.
    
    - **category**: Filter templates by category
    - **search**: Search across template name, content, and description
    
    Returns list of templates with total count and available categories.
    """
    manager = get_template_manager()
    
    if search:
        templates = manager.search_templates(search)
    else:
        templates = manager.list_templates(category=category)
    
    categories = manager.get_categories()
    
    return TemplateListResponse(
        templates=[TemplateResponse(**t) for t in templates],
        total=len(templates),
        categories=categories
    )


@router.get("/categories", response_model=List[str])
async def list_categories():
    """
    Get all template categories.
    
    Returns a list of unique category names used by active templates.
    """
    manager = get_template_manager()
    return manager.get_categories()


@router.get("/stats", response_model=TemplateStatsResponse)
async def get_template_stats():
    """
    Get template statistics.
    
    Returns counts, categories, and database information.
    """
    manager = get_template_manager()
    stats = manager.get_stats()
    db_info = get_database_info()
    
    return TemplateStatsResponse(
        total_templates=stats["total_templates"],
        registered_patterns=stats["registered_patterns"],
        categories=stats["categories"],
        templates_by_category=stats["templates_by_category"],
        database=db_info
    )


@router.get("/triggers")
async def get_all_triggers():
    """
    Get all available voice triggers.
    
    Returns a mapping of template names to their trigger phrases.
    Useful for displaying available commands to users.
    """
    manager = get_template_manager()
    triggers = manager.get_all_triggers()
    
    total_trigger_count = sum(
        len(info["phrases"]) for info in triggers.values()
    )
    
    return {
        "templates": triggers,
        "total_templates": len(triggers),
        "total_triggers": total_trigger_count
    }


# ═══════════════════════════════════════════════════════════════
# CRUD ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/{name}", response_model=TemplateResponse)
async def get_template(name: str):
    """
    Get a specific template by name.
    
    - **name**: Unique template identifier
    """
    manager = get_template_manager()
    template = manager.get_template(name)
    
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{name}' not found"
        )
    
    return TemplateResponse(**template)


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(template: TemplateCreate):
    """
    Create a new custom template.
    
    The template will be immediately available for voice commands.
    
    Example voice triggers after creation:
    - "insert [trigger phrase]"
    - "add [trigger phrase]"
    - "[trigger phrase] template"
    """
    manager = get_template_manager()
    
    try:
        created = manager.create_template(
            name=template.name,
            trigger_phrases=template.trigger_phrases,
            content=template.content,
            category=template.category,
            description=template.description,
            author=template.author
        )
        
        logger.info(f"Created template via API: {template.name}")
        return TemplateResponse(**created)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{name}", response_model=TemplateResponse)
async def update_template(name: str, update: TemplateUpdate):
    """
    Update an existing template.
    
    Only provided fields will be updated. Voice command registration
    is automatically updated.
    """
    manager = get_template_manager()
    
    # Check if exists
    if not manager.get_template(name):
        raise HTTPException(
            status_code=404,
            detail=f"Template '{name}' not found"
        )
    
    try:
        updated = manager.update_template(
            name=name,
            trigger_phrases=update.trigger_phrases,
            content=update.content,
            category=update.category,
            description=update.description,
            author=update.author
        )
        
        logger.info(f"Updated template via API: {name}")
        return TemplateResponse(**updated)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}", response_model=MessageResponse)
async def delete_template(
    name: str,
    hard_delete: bool = Query(
        False, 
        description="Permanently delete (True) or soft delete (False)"
    )
):
    """
    Delete a template.
    
    - **hard_delete**: If True, permanently removes the template.
      If False (default), marks it as inactive for potential recovery.
    """
    manager = get_template_manager()
    
    if not manager.get_template(name):
        raise HTTPException(
            status_code=404,
            detail=f"Template '{name}' not found"
        )
    
    manager.delete_template(name, hard_delete=hard_delete)
    
    action = "permanently deleted" if hard_delete else "deleted"
    logger.info(f"Template {action} via API: {name}")
    
    return MessageResponse(message=f"Template '{name}' {action} successfully")


# ═══════════════════════════════════════════════════════════════
# BULK OPERATIONS
# ═══════════════════════════════════════════════════════════════

@router.post("/bulk-import", response_model=BulkImportResponse)
async def bulk_import_templates(data: TemplateBulkImport):
    """
    Import multiple templates at once.
    
    - **templates**: List of templates to import
    - **overwrite**: If True, existing templates will be updated
    """
    manager = get_template_manager()
    
    created = 0
    updated = 0
    errors = []
    
    for template in data.templates:
        try:
            existing = manager.get_template(template.name)
            
            if existing:
                if data.overwrite:
                    manager.update_template(
                        name=template.name,
                        trigger_phrases=template.trigger_phrases,
                        content=template.content,
                        category=template.category,
                        description=template.description,
                        author=template.author
                    )
                    updated += 1
                else:
                    errors.append({
                        "name": template.name,
                        "error": "Template already exists (use overwrite=true)"
                    })
            else:
                manager.create_template(
                    name=template.name,
                    trigger_phrases=template.trigger_phrases,
                    content=template.content,
                    category=template.category,
                    description=template.description,
                    author=template.author
                )
                created += 1
                
        except Exception as e:
            errors.append({
                "name": template.name,
                "error": str(e)
            })
    
    logger.info(f"Bulk import: {created} created, {updated} updated, {len(errors)} errors")
    
    return BulkImportResponse(
        created=created,
        updated=updated,
        errors=errors
    )


@router.get("/export/all")
async def export_templates():
    """
    Export all templates as JSON.
    
    Can be used to backup templates or transfer to another system.
    """
    manager = get_template_manager()
    templates = manager.list_templates()
    
    from datetime import datetime
    
    return {
        "templates": templates,
        "total": len(templates),
        "exported_at": datetime.now().isoformat()
    }


# ═══════════════════════════════════════════════════════════════
# TESTING & UTILITIES
# ═══════════════════════════════════════════════════════════════

@router.post("/test", response_model=TemplateTestResponse)
async def test_template_processing(request: TemplateTestRequest):
    """
    Test how text would be processed.
    
    Useful for debugging and verifying template triggers work correctly.
    Shows original text, processed text, and commands that were executed.
    """
    manager = get_template_manager()
    result = manager.test_processing(request.text)
    
    return TemplateTestResponse(
        original_text=result["original_text"],
        processed_text=result["processed_text"],
        commands_executed=result["commands_executed"]
    )


@router.post("/refresh", response_model=MessageResponse)
async def refresh_templates():
    """
    Reload all templates from database.
    
    Use this after manual database changes to sync the command processor.
    """
    manager = get_template_manager()
    manager.refresh()
    
    stats = manager.get_stats()
    
    return MessageResponse(
        message=f"Templates refreshed: {stats['total_templates']} loaded, {stats['registered_patterns']} patterns registered"
    )