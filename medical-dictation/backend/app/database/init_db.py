"""Database initialization, migrations, and seeding"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any

from .connection import get_db_connection

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# TABLE SCHEMAS
# ═══════════════════════════════════════════════════════════════

TEMPLATES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    trigger_phrases TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    description TEXT DEFAULT '',
    author TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
)
"""

TEMPLATES_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category)",
    "CREATE INDEX IF NOT EXISTS idx_templates_name ON templates(name)",
    "CREATE INDEX IF NOT EXISTS idx_templates_active ON templates(is_active)",
]


# ═══════════════════════════════════════════════════════════════
# DEFAULT TEMPLATES
# ═══════════════════════════════════════════════════════════════

DEFAULT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "vitals",
        "trigger_phrases": '["vitals", "vital signs", "insert vitals"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        VITAL SIGNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Blood Pressure:    ___/___ mmHg
Heart Rate:        ___ bpm
Respiratory Rate:  ___ /min
Temperature:       ___°F (___°C)
SpO2:              ___%
Weight:            ___ kg (___ lbs)
Height:            ___ cm (___ in)
BMI:               ___

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
        "category": "clinical",
        "description": "Standard vital signs template with all common measurements",
        "author": "System"
    },
    {
        "name": "soap_note",
        "trigger_phrases": '["soap note", "soap", "insert soap"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        SOAP NOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUBJECTIVE:
Chief Complaint: ___
History of Present Illness: ___
Review of Systems: ___

──────────────────────────────────────────────────────────────────

OBJECTIVE:
Vital Signs: ___
Physical Examination: ___
Laboratory/Imaging: ___

──────────────────────────────────────────────────────────────────

ASSESSMENT:
1. ___
2. ___
3. ___

──────────────────────────────────────────────────────────────────

PLAN:
1. ___
2. ___
3. ___

Follow-up: ___

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
        "category": "notes",
        "description": "Standard SOAP note format for clinical documentation",
        "author": "System"
    },
    {
        "name": "hpi",
        "trigger_phrases": '["hpi", "history of present illness", "insert hpi"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                HISTORY OF PRESENT ILLNESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The patient is a ___-year-old [male/female] who presents with ___.

ONSET:              ___
LOCATION:           ___
DURATION:           ___
CHARACTER:          ___
AGGRAVATING:        ___
RELIEVING:          ___
TIMING:             ___
SEVERITY:           ___/10

Associated Symptoms: ___

Previous Episodes:   ___

Current Medications: ___

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
        "category": "clinical",
        "description": "History of Present Illness using OLDCARTS format",
        "author": "System"
    },
    {
        "name": "physical_exam",
        "trigger_phrases": '["physical exam", "pe", "insert physical exam", "examination"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    PHYSICAL EXAMINATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GENERAL:        ___ [Alert, oriented, no acute distress]

HEENT:          
  Head:         ___
  Eyes:         ___ [PERRLA, EOMI]
  Ears:         ___
  Nose:         ___
  Throat:       ___

NECK:           ___ [Supple, no lymphadenopathy, no JVD]

CARDIOVASCULAR: ___ [RRR, no murmurs/rubs/gallops]

RESPIRATORY:    ___ [CTAB, no wheezes/rales/rhonchi]

ABDOMEN:        ___ [Soft, non-tender, non-distended, +BS]

EXTREMITIES:    ___ [No edema, pulses 2+ bilaterally]

NEUROLOGICAL:   ___ [CN II-XII intact, strength 5/5, sensation intact]

SKIN:           ___ [Warm, dry, no rashes]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
        "category": "clinical",
        "description": "Comprehensive physical examination template",
        "author": "System"
    },
    {
        "name": "review_of_systems",
        "trigger_phrases": '["review of systems", "ros", "insert ros", "systems review"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    REVIEW OF SYSTEMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONSTITUTIONAL:   □ Fever  □ Chills  □ Weight loss  □ Fatigue
                  □ Night sweats  □ Malaise

HEENT:            □ Headache  □ Vision changes  □ Hearing loss
                  □ Tinnitus  □ Sore throat  □ Nasal congestion

CARDIOVASCULAR:   □ Chest pain  □ Palpitations  □ Edema
                  □ Dyspnea on exertion  □ Orthopnea  □ PND

RESPIRATORY:      □ Cough  □ Shortness of breath  □ Wheezing
                  □ Hemoptysis  □ Sputum production

GASTROINTESTINAL: □ Nausea  □ Vomiting  □ Diarrhea  □ Constipation
                  □ Abdominal pain  □ Melena  □ Hematochezia

GENITOURINARY:    □ Dysuria  □ Frequency  □ Urgency  □ Hematuria
                  □ Incontinence  □ Nocturia

MUSCULOSKELETAL:  □ Joint pain  □ Muscle weakness  □ Back pain
                  □ Stiffness  □ Swelling

NEUROLOGICAL:     □ Dizziness  □ Numbness  □ Tingling  □ Weakness
                  □ Seizures  □ Syncope  □ Tremor

PSYCHIATRIC:      □ Depression  □ Anxiety  □ Sleep disturbance
                  □ Memory changes

SKIN:             □ Rash  □ Itching  □ Lesions  □ Hair loss
                  □ Nail changes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
        "category": "clinical",
        "description": "Complete 14-point review of systems checklist",
        "author": "System"
    },
    {
        "name": "assessment_plan",
        "trigger_phrases": '["assessment and plan", "a and p", "insert assessment", "assessment plan"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    ASSESSMENT AND PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM #1: ___
  Assessment:  ___
  Plan:
    • ___
    • ___
    • ___

──────────────────────────────────────────────────────────────────

PROBLEM #2: ___
  Assessment:  ___
  Plan:
    • ___
    • ___

──────────────────────────────────────────────────────────────────

PROBLEM #3: ___
  Assessment:  ___
  Plan:
    • ___

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DISPOSITION: ___

FOLLOW-UP: ___

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
        "category": "notes",
        "description": "Problem-oriented assessment and plan template",
        "author": "System"
    },
    {
        "name": "medications",
        "trigger_phrases": '["medication list", "medications", "insert medications", "med list"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    MEDICATION LIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT MEDICATIONS:

1. _______________ ___ mg  ___x daily  (Indication: ___)
2. _______________ ___ mg  ___x daily  (Indication: ___)
3. _______________ ___ mg  ___x daily  (Indication: ___)
4. _______________ ___ mg  ___x daily  (Indication: ___)
5. _______________ ___ mg  ___x daily  (Indication: ___)

──────────────────────────────────────────────────────────────────

PRN MEDICATIONS:

1. _______________ ___ mg  PRN for ___
2. _______________ ___ mg  PRN for ___

──────────────────────────────────────────────────────────────────

ALLERGIES: ___ (Reaction: ___)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
        "category": "clinical",
        "description": "Medication list with dosing and indications",
        "author": "System"
    },
    {
        "name": "discharge_summary",
        "trigger_phrases": '["discharge summary", "dc summary", "insert discharge", "discharge"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    DISCHARGE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATIENT:           _______________
MRN:               _______________
ADMISSION DATE:    _______________
DISCHARGE DATE:    _______________
ATTENDING:         _______________

──────────────────────────────────────────────────────────────────

PRIMARY DIAGNOSIS:
  _______________

SECONDARY DIAGNOSES:
  1. _______________
  2. _______________
  3. _______________

──────────────────────────────────────────────────────────────────

HOSPITAL COURSE:
_______________

PROCEDURES PERFORMED:
  1. _______________
  2. _______________

──────────────────────────────────────────────────────────────────

DISCHARGE MEDICATIONS:
  1. _______________
  2. _______________
  3. _______________

MEDICATIONS STOPPED:
  • _______________

──────────────────────────────────────────────────────────────────

DISCHARGE INSTRUCTIONS:
  • _______________
  • _______________
  • _______________

ACTIVITY:          _______________
DIET:              _______________
WOUND CARE:        _______________

──────────────────────────────────────────────────────────────────

FOLLOW-UP APPOINTMENTS:
  • _______________ in ___ days
  • _______________ in ___ weeks

RETURN TO ED IF:
  • _______________
  • _______________

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
        "category": "notes",
        "description": "Comprehensive hospital discharge summary",
        "author": "System"
    },
    {
        "name": "procedure_note",
        "trigger_phrases": '["procedure note", "insert procedure", "procedure"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    PROCEDURE NOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DATE/TIME:         _______________
PROCEDURE:         _______________
INDICATION:        _______________
CONSENT:           Informed consent obtained

──────────────────────────────────────────────────────────────────

PRE-PROCEDURE:
  Timeout performed: □ Yes  □ No
  Pre-procedure vitals: ___

ANESTHESIA:        _______________
ANTISEPTIC:        _______________

──────────────────────────────────────────────────────────────────

PROCEDURE DETAILS:
_______________

SPECIMENS:         _______________
ESTIMATED BLOOD LOSS: ___ mL
COMPLICATIONS:     □ None  □ _______

──────────────────────────────────────────────────────────────────

POST-PROCEDURE:
  Patient tolerated procedure well
  Vitals stable
  Instructions given to patient

DISPOSITION:       _______________

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ATTENDING:         _______________
""",
        "category": "notes",
        "description": "Standard procedure documentation template",
        "author": "System"
    },
    {
        "name": "consultation",
        "trigger_phrases": '["consultation", "consult note", "insert consult"]',
        "content": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    CONSULTATION NOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DATE:              _______________
REQUESTING PHYSICIAN: _______________
CONSULTING SERVICE:   _______________

REASON FOR CONSULTATION:
_______________

──────────────────────────────────────────────────────────────────

HISTORY OF PRESENT ILLNESS:
_______________

PAST MEDICAL HISTORY:
_______________

CURRENT MEDICATIONS:
_______________

ALLERGIES:
_______________

──────────────────────────────────────────────────────────────────

PHYSICAL EXAMINATION:
_______________

LABORATORY/IMAGING REVIEW:
_______________

──────────────────────────────────────────────────────────────────

ASSESSMENT:
_______________

RECOMMENDATIONS:
1. _______________
2. _______________
3. _______________

──────────────────────────────────────────────────────────────────

Thank you for this consultation. We will follow along with you.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONSULTANT:        _______________
""",
        "category": "consultations",
        "description": "Medical consultation note template",
        "author": "System"
    },
]


# ═══════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ═══════════════════════════════════════════════════════════════

def init_database(seed_defaults: bool = True) -> dict:
    """
    Initialize the database with required tables.
    
    Creates tables if they don't exist and optionally seeds default templates.
    
    Args:
        seed_defaults: Whether to insert default templates
    
    Returns:
        Dictionary with initialization status and counts
    """
    db = get_db_connection()
    result = {
        "tables_created": [],
        "indexes_created": 0,
        "templates_seeded": 0,
        "status": "success"
    }
    
    try:
        with db.get_connection() as conn:
            # ── Create templates table ──
            conn.execute(TEMPLATES_TABLE_SQL)
            result["tables_created"].append("templates")
            logger.info("✓ Created/verified templates table")
            
            # ── Create indexes ──
            for index_sql in TEMPLATES_INDEXES_SQL:
                conn.execute(index_sql)
                result["indexes_created"] += 1
            logger.info(f"✓ Created/verified {result['indexes_created']} indexes")
            
            # ── Seed default templates ──
            if seed_defaults:
                result["templates_seeded"] = _seed_default_templates(conn)
                logger.info(f"✓ Seeded {result['templates_seeded']} default templates")
        
        logger.info("=" * 60)
        logger.info("DATABASE INITIALIZATION COMPLETE")
        logger.info(f"  Tables: {', '.join(result['tables_created'])}")
        logger.info(f"  Indexes: {result['indexes_created']}")
        logger.info(f"  Templates seeded: {result['templates_seeded']}")
        logger.info("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        raise


def _seed_default_templates(conn) -> int:
    """
    Seed default templates into the database.
    
    Args:
        conn: Active database connection
    
    Returns:
        Number of templates inserted
    """
    now = datetime.now().isoformat()
    inserted = 0
    
    for template in DEFAULT_TEMPLATES:
        # Check if template already exists
        existing = conn.execute(
            "SELECT id FROM templates WHERE name = ?",
            (template["name"],)
        ).fetchone()
        
        if existing:
            logger.debug(f"Template '{template['name']}' already exists, skipping")
            continue
        
        # Insert template
        conn.execute("""
            INSERT INTO templates 
            (name, trigger_phrases, content, category, description, author, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template["name"],
            template["trigger_phrases"],
            template["content"],
            template["category"],
            template["description"],
            template["author"],
            now,
            now
        ))
        
        inserted += 1
        logger.debug(f"Seeded template: {template['name']}")
    
    return inserted


def reset_database() -> dict:
    """
    Reset the database by dropping and recreating tables.
    
    WARNING: This will delete ALL data!
    
    Returns:
        Dictionary with reset status
    """
    db = get_db_connection()
    
    logger.warning("=" * 60)
    logger.warning("DATABASE RESET - ALL DATA WILL BE DELETED")
    logger.warning("=" * 60)
    
    try:
        with db.get_connection() as conn:
            # Drop existing table
            conn.execute("DROP TABLE IF EXISTS templates")
            logger.warning("Dropped templates table")
        
        # Reinitialize
        result = init_database(seed_defaults=True)
        result["reset"] = True
        
        return result
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise


def get_database_info() -> dict:
    """
    Get database information and statistics.
    
    Returns:
        Dictionary with database stats
    """
    db = get_db_connection()
    
    with db.get_connection() as conn:
        # Count templates
        total = conn.execute(
            "SELECT COUNT(*) FROM templates"
        ).fetchone()[0]
        
        active = conn.execute(
            "SELECT COUNT(*) FROM templates WHERE is_active = 1"
        ).fetchone()[0]
        
        # Get categories
        categories = conn.execute(
            "SELECT DISTINCT category FROM templates WHERE is_active = 1"
        ).fetchall()
        
        # Get database file size
        db_path = db.settings.absolute_path
        
        if db_path.exists():
            file_size = db_path.stat().st_size
        else:
            file_size = 0
    
    return {
        "database_path": str(db.settings.absolute_path),
        "database_exists": db_path.exists(),
        "total_templates": total,
        "active_templates": active,
        "inactive_templates": total - active,
        "categories": [row[0] for row in categories],
        "file_size_bytes": file_size,
        "file_size_kb": round(file_size / 1024, 2),
        "file_size_mb": round(file_size / (1024 * 1024), 4)
    }