"""Voice command processing for dictation control"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    """Types of voice commands"""
    FORMATTING = "formatting"      # Bold, italic, underline
    NAVIGATION = "navigation"      # Move cursor, select text
    TEMPLATE = "template"          # Insert templates
    EDITING = "editing"            # Delete, replace, insert
    PUNCTUATION = "punctuation"    # Period, comma, new line
    CONTROL = "control"            # Start, stop, pause dictation
    CUSTOM = "custom"              # Custom macros


@dataclass
class VoiceCommand:
    """Represents a recognized voice command"""
    command_type: CommandType
    action: str
    args: List = field(default_factory=list)
    original_text: str = ""  # The text that triggered the command
    replacement: str = ""    # What to replace the command with (if any)


@dataclass
class CommandResult:
    """Result of command processing"""
    command: Optional[VoiceCommand]
    remaining_text: str
    was_command: bool


class CommandProcessor:
    """
    Processes voice commands for dictation control.
    Recognizes patterns like "bold", "new line", "undo", etc.
    
    Usage:
        processor = CommandProcessor()
        result = processor.process("Patient has period new paragraph Next section")
        # result.command = VoiceCommand for "period"
        # result.remaining_text = "Patient has. \n\nNext section"
    """
    
    def __init__(self):
        """Initialize the command processor with default commands"""
        self.custom_commands: Dict[str, VoiceCommand] = {}
        self.command_history: List[VoiceCommand] = []
        self.enabled = True
        
        # Build command patterns
        self._build_command_patterns()
    
    def _build_command_patterns(self):
        """Build regex patterns for command recognition"""
        
        # ══════════════════════════════════════════════════════════
        # PUNCTUATION COMMANDS (most common, processed first)
        # ══════════════════════════════════════════════════════════
        self.punctuation_commands = {
            # Basic punctuation
            r"\b(?:period|full stop)\b": (".", ""),
            r"\bcomma\b": (",", ""),
            r"\b(?:question mark|question)\b": ("?", ""),
            r"\b(?:exclamation mark|exclamation point|exclamation)\b": ("!", ""),
            r"\bcolon\b": (":", ""),
            r"\bsemicolon\b": (";", ""),
            r"\bhyphen\b": ("-", ""),
            r"\bdash\b": (" — ", ""),
            r"\bellipsis\b": ("...", ""),
            
            # Quotes
            r"\b(?:open quote|begin quote|quote)\b": ('"', ""),
            r"\b(?:close quote|end quote|unquote)\b": ('"', ""),
            r"\b(?:open parenthesis|open paren|left paren)\b": ("(", ""),
            r"\b(?:close parenthesis|close paren|right paren)\b": (")", ""),
            
            # New lines and paragraphs
            r"\bnew line\b": ("\n", ""),
            r"\bnew paragraph\b": ("\n\n", ""),
            r"\bnext line\b": ("\n", ""),
            r"\bnext paragraph\b": ("\n\n", ""),
            
            # Special
            r"\btab\b": ("\t", ""),
            r"\bspace\b": (" ", ""),
        }
        
        # ══════════════════════════════════════════════════════════
        # FORMATTING COMMANDS
        # ══════════════════════════════════════════════════════════
        self.formatting_commands = {
            r"\b(?:bold|make bold)\b": VoiceCommand(
                CommandType.FORMATTING, "bold", replacement="**"
            ),
            r"\b(?:italic|italics|make italic)\b": VoiceCommand(
                CommandType.FORMATTING, "italic", replacement="*"
            ),
            r"\b(?:underline|make underline)\b": VoiceCommand(
                CommandType.FORMATTING, "underline", replacement="__"
            ),
            r"\b(?:strikethrough|strike through)\b": VoiceCommand(
                CommandType.FORMATTING, "strikethrough", replacement="~~"
            ),
            r"\b(?:heading|header) (?:one|1)\b": VoiceCommand(
                CommandType.FORMATTING, "heading1", replacement="# "
            ),
            r"\b(?:heading|header) (?:two|2)\b": VoiceCommand(
                CommandType.FORMATTING, "heading2", replacement="## "
            ),
            r"\b(?:heading|header) (?:three|3)\b": VoiceCommand(
                CommandType.FORMATTING, "heading3", replacement="### "
            ),
            r"\bbullet point\b": VoiceCommand(
                CommandType.FORMATTING, "bullet", replacement="\n• "
            ),
            r"\bnumbered list\b": VoiceCommand(
                CommandType.FORMATTING, "numbered", replacement="\n1. "
            ),
        }
        
        # ══════════════════════════════════════════════════════════
        # EDITING COMMANDS
        # ══════════════════════════════════════════════════════════
        self.editing_commands = {
            r"\b(?:undo|undo that)\b": VoiceCommand(
                CommandType.EDITING, "undo"
            ),
            r"\b(?:redo|redo that)\b": VoiceCommand(
                CommandType.EDITING, "redo"
            ),
            r"\b(?:delete|remove) (?:that|last word)\b": VoiceCommand(
                CommandType.EDITING, "delete_last_word"
            ),
            r"\b(?:delete|remove) last sentence\b": VoiceCommand(
                CommandType.EDITING, "delete_last_sentence"
            ),
            r"\b(?:delete|remove) last paragraph\b": VoiceCommand(
                CommandType.EDITING, "delete_last_paragraph"
            ),
            r"\bclear all\b": VoiceCommand(
                CommandType.EDITING, "clear_all"
            ),
            r"\bselect all\b": VoiceCommand(
                CommandType.EDITING, "select_all"
            ),
            r"\bcopy that\b": VoiceCommand(
                CommandType.EDITING, "copy"
            ),
            r"\bcut that\b": VoiceCommand(
                CommandType.EDITING, "cut"
            ),
            r"\bpaste\b": VoiceCommand(
                CommandType.EDITING, "paste"
            ),
        }
        
        # ══════════════════════════════════════════════════════════
        # NAVIGATION COMMANDS
        # ══════════════════════════════════════════════════════════
        self.navigation_commands = {
            r"\bgo to (?:start|beginning)\b": VoiceCommand(
                CommandType.NAVIGATION, "go_to_start"
            ),
            r"\bgo to end\b": VoiceCommand(
                CommandType.NAVIGATION, "go_to_end"
            ),
            r"\bscroll up\b": VoiceCommand(
                CommandType.NAVIGATION, "scroll_up"
            ),
            r"\bscroll down\b": VoiceCommand(
                CommandType.NAVIGATION, "scroll_down"
            ),
            r"\bnew section\b": VoiceCommand(
                CommandType.NAVIGATION, "new_section", replacement="\n\n---\n\n"
            ),
        }
        
        # ══════════════════════════════════════════════════════════
        # CONTROL COMMANDS
        # ══════════════════════════════════════════════════════════
        self.control_commands = {
            r"\b(?:stop|pause) (?:dictation|listening|recording)\b": VoiceCommand(
                CommandType.CONTROL, "pause"
            ),
            r"\b(?:start|resume) (?:dictation|listening|recording)\b": VoiceCommand(
                CommandType.CONTROL, "resume"
            ),
            r"\bsave (?:document|note|file)\b": VoiceCommand(
                CommandType.CONTROL, "save"
            ),
        }
        
        # ══════════════════════════════════════════════════════════
        # MEDICAL TEMPLATE COMMANDS
        # ══════════════════════════════════════════════════════════
        self.template_commands = {
            r"\b(?:insert|add) (?:vitals|vital signs)(?: template)?\b": VoiceCommand(
                CommandType.TEMPLATE, "vitals",
                replacement="\n\nVital Signs:\n• BP: ___/___\n• HR: ___\n• RR: ___\n• Temp: ___\n• SpO2: ___%\n\n"
            ),
            r"\b(?:insert|add) (?:soap|soap note)(?: template)?\b": VoiceCommand(
                CommandType.TEMPLATE, "soap_note",
                replacement="\n\nSOAP Note:\n\nSubjective:\n\n\nObjective:\n\n\nAssessment:\n\n\nPlan:\n\n"
            ),
            r"\b(?:insert|add) (?:hpi|history of present illness)(?: template)?\b": VoiceCommand(
                CommandType.TEMPLATE, "hpi",
                replacement="\n\nHistory of Present Illness:\nThe patient is a ___-year-old ___ who presents with ___. "
                           "Onset was ___. Duration is ___. Location is ___. Character is ___. "
                           "Severity is ___/10. Aggravating factors include ___. "
                           "Relieving factors include ___. Associated symptoms include ___.\n\n"
            ),
            r"\b(?:insert|add) (?:ros|review of systems)(?: template)?\b": VoiceCommand(
                CommandType.TEMPLATE, "ros",
                replacement="\n\nReview of Systems:\n• Constitutional: ___\n• HEENT: ___\n• Cardiovascular: ___\n"
                           "• Respiratory: ___\n• GI: ___\n• GU: ___\n• Musculoskeletal: ___\n"
                           "• Neurological: ___\n• Psychiatric: ___\n• Skin: ___\n\n"
            ),
            r"\b(?:insert|add) (?:physical exam|pe)(?: template)?\b": VoiceCommand(
                CommandType.TEMPLATE, "physical_exam",
                replacement="\n\nPhysical Examination:\n• General: ___\n• HEENT: ___\n• Neck: ___\n"
                           "• Lungs: ___\n• Heart: ___\n• Abdomen: ___\n• Extremities: ___\n"
                           "• Neurological: ___\n• Skin: ___\n\n"
            ),
            r"\b(?:insert|add) (?:assessment and plan|a and p)(?: template)?\b": VoiceCommand(
                CommandType.TEMPLATE, "assessment_plan",
                replacement="\n\nAssessment and Plan:\n\n1. Problem #1: ___\n   • Assessment: ___\n   • Plan: ___\n\n"
                           "2. Problem #2: ___\n   • Assessment: ___\n   • Plan: ___\n\n"
            ),
            r"\b(?:insert|add) (?:medication list|medications)(?: template)?\b": VoiceCommand(
                CommandType.TEMPLATE, "medications",
                replacement="\n\nMedications:\n1. ___ ___ mg ___ times daily\n2. ___ ___ mg ___ times daily\n"
                           "3. ___ ___ mg ___ times daily\n\n"
            ),
            r"\b(?:insert|add) (?:allergy list|allergies)(?: template)?\b": VoiceCommand(
                CommandType.TEMPLATE, "allergies",
                replacement="\n\nAllergies:\n• ___: ___\n• NKDA: ☐\n\n"
            ),
        }
        
        # Compile all patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for faster matching"""
        self.compiled_punctuation = {
            re.compile(pattern, re.IGNORECASE): replacement
            for pattern, replacement in self.punctuation_commands.items()
        }
        
        self.compiled_formatting = {
            re.compile(pattern, re.IGNORECASE): cmd
            for pattern, cmd in self.formatting_commands.items()
        }
        
        self.compiled_editing = {
            re.compile(pattern, re.IGNORECASE): cmd
            for pattern, cmd in self.editing_commands.items()
        }
        
        self.compiled_navigation = {
            re.compile(pattern, re.IGNORECASE): cmd
            for pattern, cmd in self.navigation_commands.items()
        }
        
        self.compiled_control = {
            re.compile(pattern, re.IGNORECASE): cmd
            for pattern, cmd in self.control_commands.items()
        }
        
        self.compiled_templates = {
            re.compile(pattern, re.IGNORECASE): cmd
            for pattern, cmd in self.template_commands.items()
        }
    
    def process(self, text: str) -> Tuple[str, List[VoiceCommand]]:
        """
        Process text for voice commands.
        
        Args:
            text: Transcribed text that may contain commands
        
        Returns:
            Tuple of (processed_text, list_of_commands_executed)
        
        Example:
            >>> processor.process("Patient has diabetes period new paragraph Next")
            ("Patient has diabetes.\n\nNext", [VoiceCommand(...), VoiceCommand(...)])
        """
        if not self.enabled or not text:
            return text, []
        
        commands_executed = []
        processed_text = text
        
        # ── 1. PROCESS PUNCTUATION COMMANDS (inline replacement) ──
        for pattern, (replacement, _) in self.compiled_punctuation.items():
            match = pattern.search(processed_text)
            if match:
                # Create command record
                cmd = VoiceCommand(
                    command_type=CommandType.PUNCTUATION,
                    action="punctuation",
                    original_text=match.group(),
                    replacement=replacement
                )
                commands_executed.append(cmd)
                
                # Replace command with punctuation
                processed_text = pattern.sub(replacement, processed_text)
        
        # ── 2. PROCESS FORMATTING COMMANDS ──
        for pattern, cmd in self.compiled_formatting.items():
            match = pattern.search(processed_text)
            if match:
                new_cmd = VoiceCommand(
                    command_type=cmd.command_type,
                    action=cmd.action,
                    original_text=match.group(),
                    replacement=cmd.replacement
                )
                commands_executed.append(new_cmd)
                
                # Replace command with formatting marker
                processed_text = pattern.sub(cmd.replacement, processed_text)
        
        # ── 3. PROCESS TEMPLATE COMMANDS ──
        for pattern, cmd in self.compiled_templates.items():
            match = pattern.search(processed_text)
            if match:
                new_cmd = VoiceCommand(
                    command_type=cmd.command_type,
                    action=cmd.action,
                    original_text=match.group(),
                    replacement=cmd.replacement
                )
                commands_executed.append(new_cmd)
                
                # Replace command with template
                processed_text = pattern.sub(cmd.replacement, processed_text)
        
        # ── 4. PROCESS NAVIGATION COMMANDS ──
        for pattern, cmd in self.compiled_navigation.items():
            match = pattern.search(processed_text)
            if match:
                new_cmd = VoiceCommand(
                    command_type=cmd.command_type,
                    action=cmd.action,
                    original_text=match.group(),
                    replacement=cmd.replacement if cmd.replacement else ""
                )
                commands_executed.append(new_cmd)
                
                # Remove command from text (or replace if has replacement)
                if cmd.replacement:
                    processed_text = pattern.sub(cmd.replacement, processed_text)
                else:
                    processed_text = pattern.sub("", processed_text)
        
        # ── 5. PROCESS EDITING COMMANDS (action only, no text replacement) ──
        for pattern, cmd in self.compiled_editing.items():
            match = pattern.search(processed_text)
            if match:
                new_cmd = VoiceCommand(
                    command_type=cmd.command_type,
                    action=cmd.action,
                    original_text=match.group(),
                )
                commands_executed.append(new_cmd)
                
                # Remove command from text
                processed_text = pattern.sub("", processed_text)
        
        # ── 6. PROCESS CONTROL COMMANDS (action only) ──
        for pattern, cmd in self.compiled_control.items():
            match = pattern.search(processed_text)
            if match:
                new_cmd = VoiceCommand(
                    command_type=cmd.command_type,
                    action=cmd.action,
                    original_text=match.group(),
                )
                commands_executed.append(new_cmd)
                
                # Remove command from text
                processed_text = pattern.sub("", processed_text)
        
        # ── 7. PROCESS CUSTOM COMMANDS ──
        for pattern_str, cmd in self.custom_commands.items():
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(processed_text)
            if match:
                new_cmd = VoiceCommand(
                    command_type=cmd.command_type,
                    action=cmd.action,
                    args=cmd.args,
                    original_text=match.group(),
                    replacement=cmd.replacement
                )
                commands_executed.append(new_cmd)
                
                if cmd.replacement:
                    processed_text = pattern.sub(cmd.replacement, processed_text)
                else:
                    processed_text = pattern.sub("", processed_text)
        
        # ── CLEAN UP ──
        # Remove extra spaces
        processed_text = re.sub(r' +', ' ', processed_text)
        processed_text = processed_text.strip()
        
        # Log commands
        if commands_executed:
            logger.debug(f"Processed {len(commands_executed)} commands: {[c.action for c in commands_executed]}")
            self.command_history.extend(commands_executed)
        
        return processed_text, commands_executed
    
    def register_custom_command(self, pattern: str, command: VoiceCommand):
        """
        Register a custom voice command pattern.
        
        Args:
            pattern: Regex pattern to match
            command: VoiceCommand to execute when pattern matches
        
        Example:
            processor.register_custom_command(
                r"\bmy signature\b",
                VoiceCommand(CommandType.TEMPLATE, "signature", 
                           replacement="\n\nDr. John Smith, MD\nInternal Medicine\n")
            )
        """
        self.custom_commands[pattern] = command
        logger.info(f"Registered custom command: {command.action}")
    
    def unregister_custom_command(self, pattern: str):
        """Remove a custom command"""
        if pattern in self.custom_commands:
            del self.custom_commands[pattern]
            logger.info(f"Unregistered custom command pattern: {pattern}")
    
    def enable(self):
        """Enable command processing"""
        self.enabled = True
        logger.info("Command processing enabled")
    
    def disable(self):
        """Disable command processing"""
        self.enabled = False
        logger.info("Command processing disabled")
    
    def get_available_commands(self) -> Dict[str, List[str]]:
        """
        Get all available commands grouped by type.
        Useful for help/documentation.
        
        Returns:
            Dictionary with command types as keys and lists of command phrases
        """
        return {
            "punctuation": [
                "period", "comma", "question mark", "exclamation",
                "colon", "semicolon", "hyphen", "dash", "ellipsis",
                "open quote", "close quote", "open parenthesis", "close parenthesis",
                "new line", "new paragraph", "tab", "space"
            ],
            "formatting": [
                "bold", "italic", "underline", "strikethrough",
                "heading one", "heading two", "heading three",
                "bullet point", "numbered list"
            ],
            "editing": [
                "undo", "redo", "delete last word", "delete last sentence",
                "delete last paragraph", "clear all", "select all",
                "copy that", "cut that", "paste"
            ],
            "navigation": [
                "go to start", "go to end", "scroll up", "scroll down",
                "new section"
            ],
            "control": [
                "stop dictation", "start dictation", "pause dictation",
                "resume dictation", "save document"
            ],
            "templates": [
                "insert vitals", "insert soap note", "insert hpi",
                "insert review of systems", "insert physical exam",
                "insert assessment and plan", "insert medications",
                "insert allergies"
            ],
        }
    
    def get_command_history(self, limit: int = 50) -> List[Dict]:
        """Get recent command history"""
        history = self.command_history[-limit:]
        return [
            {
                "type": cmd.command_type.value,
                "action": cmd.action,
                "original_text": cmd.original_text,
            }
            for cmd in history
        ]
    
    def clear_history(self):
        """Clear command history"""
        self.command_history.clear()


# ─────────────────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────────────────

# Global command processor instance
command_processor: CommandProcessor = CommandProcessor()


def get_command_processor() -> CommandProcessor:
    """Get the global command processor instance"""
    return command_processor


# ─────────────────────────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    processor = CommandProcessor()
    
    # Test cases
    test_cases = [
        "Patient has diabetes period new paragraph Next section",
        "The patient is a 45 year old male comma presenting with chest pain period",
        "Insert vitals template",
        "Bold this is important",
        "Delete last word",
        "Insert soap note template",
        "Blood pressure is 120 over 80 comma heart rate 72 period",
    ]
    
    print("=" * 60)
    print("COMMAND PROCESSOR TEST")
    print("=" * 60)
    
    for test in test_cases:
        print(f"\nInput:  '{test}'")
        result, commands = processor.process(test)
        print(f"Output: '{result}'")
        print(f"Commands: {[c.action for c in commands]}")
        print("-" * 60)