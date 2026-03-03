"""Medical text formatting and post-processing for clinical documentation"""

import logging
import re
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class MedicalFormatter:
    """
    Formats raw Whisper transcription into proper medical documentation.
    Handles number-to-digit conversion, medical acronyms, drug names,
    capitalization, and SOAP note formatting.
    """

    # ─── WORD-TO-NUMBER MAPPING ───
    WORD_NUMBERS: Dict[str, int] = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90,
        "hundred": 100,
        "thousand": 1000,
        "million": 1000000,
    }

    # ─── UNIT CONVERSIONS ───
    UNIT_CONVERSIONS: Dict[str, str] = {
        "milligrams": "mg",
        "milligram": "mg",
        "milliliters": "ml",
        "milliliter": "ml",
        "micrograms": "mcg",
        "microgram": "mcg",
        "kilograms": "kg",
        "kilogram": "kg",
        "grams": "g",
        "gram": "g",
        "centimeters": "cm",
        "centimeter": "cm",
        "millimeters": "mm",
        "millimeter": "mm",
        "inches": "in",
        "inch": "in",
        "percent": "%",
        "degrees": "°",
        "degree": "°",
    }

    # ─── MEDICAL ACRONYMS (must be uppercase) ───
    MEDICAL_ACRONYMS: Set[str] = {
        "COPD",
        "CHF",
        "DVT",
        "PE",
        "MI",
        "CVA",
        "TIA",
        "UTI",
        "GERD",
        "BPH",
        "CABG",
        "PCI",
        "ECG",
        "EKG",
        "MRI",
        "CT",
        "CBC",
        "CMP",
        "BMP",
        "TSH",
        "HbA1c",
        "LDL",
        "HDL",
        "BP",
        "HR",
        "RR",
        "SpO2",
        "BMI",
        "IV",
        "IM",
        "PO",
        "PRN",
        "BID",
        "TID",
        "QID",
        "QHS",
        "AC",
        "PC",
        "STAT",
        "NPO",
        "DNR",
        "ICU",
        "ER",
        "OR",
        "OTC",
        "HIV",
        "AIDS",
        "NSAID",
        "ACE",
        "ARB",
        "SSRI",
        "SNRI",
    }

    # ─── DRUG NAMES (will be capitalized) ───
    DRUG_NAMES: Set[str] = {
        "acetaminophen",
        "amoxicillin",
        "metformin",
        "lisinopril",
        "atorvastatin",
        "omeprazole",
        "ibuprofen",
        "clopidogrel",
        "warfarin",
        "aspirin",
        "prednisone",
        "levothyroxine",
        "amlodipine",
        "hydrochlorothiazide",
        "gabapentin",
        "losartan",
        "albuterol",
        "fluticasone",
        "pantoprazole",
        "sertraline",
        "escitalopram",
        "duloxetine",
        "tramadol",
        "oxycodone",
        "hydrocodone",
        "diazepam",
        "lorazepam",
        "clonazepam",
    }

    # ─── SOAP SECTION HEADERS ───
    SOAP_SECTIONS: Dict[str, str] = {
        "subjective": "SUBJECTIVE",
        "objective": "OBJECTIVE",
        "assessment": "ASSESSMENT",
        "plan": "PLAN",
    }

    def __init__(self):
        """Initialize the medical formatter"""
        self.word_numbers = self.WORD_NUMBERS.copy()
        self.unit_conversions = self.UNIT_CONVERSIONS.copy()
        self.medical_acronyms = self.MEDICAL_ACRONYMS.copy()
        self.drug_names = self.DRUG_NAMES.copy()

    def format(self, raw_text: str) -> str:
        """
        Apply all formatting transformations to raw transcribed text.

        Pipeline (in order):
        1. NUMBER-UNIT CONVERSION: word numbers -> digits, units -> abbreviations
        2. MEDICAL ACRONYM CAPITALIZATION: force uppercase
        3. DRUG NAME CAPITALIZATION: capitalize first letter
        4. SENTENCE CAPITALIZATION: capitalize after periods
        5. WHITESPACE CLEANUP: fix spacing

        Args:
            raw_text: Raw transcribed text from Whisper

        Returns:
            Formatted medical text
        """
        if not raw_text or not raw_text.strip():
            return ""

        text = raw_text.strip()

        # ── 1. NUMBER-UNIT CONVERSION ──
        text = self._convert_numbers(text)
        text = self._convert_units(text)

        # ── 2. MEDICAL ACRONYM CAPITALIZATION ──
        text = self._capitalize_acronyms(text)

        # ── 3. DRUG NAME CAPITALIZATION ──
        text = self._capitalize_drug_names(text)

        # ── 4. SENTENCE CAPITALIZATION ──
        text = self._capitalize_sentences(text)

        # ── 5. WHITESPACE CLEANUP ──
        text = self._cleanup_whitespace(text)

        return text.strip()

    def _convert_numbers(self, text: str) -> str:
        """
        Convert word numbers to digits.
        Examples: "one" -> "1", "twenty five" -> "25", "one hundred" -> "100"

        Args:
            text: Text with word numbers

        Returns:
            Text with digit numbers
        """
        # Split into words, process locally to avoid changing context
        words = text.split()
        result = []
        i = 0

        while i < len(words):
            word = words[i]
            word_lower = word.lower().rstrip(".,;:")
            trailing_punct = word[len(word_lower) :]

            # Check if this word is a number
            if word_lower in self.word_numbers:
                # Look ahead for compound numbers (e.g., "twenty five" -> "25")
                num_value = self.word_numbers[word_lower]

                # Check for next word (compound like "twenty five")
                if (
                    i + 1 < len(words)
                    and words[i + 1].lower().rstrip(".,;:") in self.word_numbers
                    and word_lower in ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
                ):
                    next_word = words[i + 1].lower().rstrip(".,;:")
                    next_punct = words[i + 1][len(next_word) :]
                    next_value = self.word_numbers[next_word]

                    # Combine (e.g., 20+5=25)
                    if next_value < 10:
                        num_value += next_value
                        result.append(str(num_value) + next_punct)
                        i += 2
                        continue

                result.append(str(num_value) + trailing_punct)
                i += 1
            else:
                result.append(word)
                i += 1

        return " ".join(result)

    def _convert_units(self, text: str) -> str:
        """
        Convert unit words to abbreviations.
        Examples: "50 milligrams" -> "50mg", "100 milliliters" -> "100ml"

        Args:
            text: Text with unit words

        Returns:
            Text with unit abbreviations
        """
        # Create regex patterns for each unit
        for unit_word, abbreviation in self.unit_conversions.items():
            # Match with word boundaries and optional trailing punctuation
            # Pattern: number + space + unit word
            pattern = rf"(\d+)\s+{unit_word}\b"
            replacement = rf"\1{abbreviation}"
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _capitalize_acronyms(self, text: str) -> str:
        """
        Capitalize medical acronyms to uppercase.
        Case-insensitive matching, ensures output is uppercase.

        Args:
            text: Text with medical acronyms (possibly lowercase)

        Returns:
            Text with acronyms in uppercase
        """
        for acronym in self.medical_acronyms:
            # Match case-insensitively, replace with uppercase
            # Use word boundaries to avoid partial matches
            pattern = rf"\b{re.escape(acronym)}\b"
            text = re.sub(pattern, acronym, text, flags=re.IGNORECASE)

        return text

    def _capitalize_drug_names(self, text: str) -> str:
        """
        Capitalize drug names (first letter uppercase, rest lowercase).

        Args:
            text: Text with drug names (possibly lowercase)

        Returns:
            Text with drug names capitalized
        """
        for drug_name in self.drug_names:
            # Match case-insensitively, replace with capitalized version
            capitalized = drug_name.capitalize()
            pattern = rf"\b{re.escape(drug_name)}\b"
            text = re.sub(pattern, capitalized, text, flags=re.IGNORECASE)

        return text

    def _capitalize_sentences(self, text: str) -> str:
        """
        Capitalize first letter after periods and at start of text.

        Args:
            text: Text to capitalize

        Returns:
            Text with sentence capitalization
        """
        # Capitalize first letter of text
        if text:
            text = text[0].upper() + text[1:]

        # Capitalize after period + space
        text = re.sub(r"(\.\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)

        return text

    def _cleanup_whitespace(self, text: str) -> str:
        """
        Clean up whitespace:
        1. Remove double spaces
        2. One space after . , : ;
        3. No space before . , : ;

        Args:
            text: Text with whitespace issues

        Returns:
            Cleaned text
        """
        # Remove double spaces
        text = re.sub(r"\s{2,}", " ", text)

        # No space before . , : ;
        text = re.sub(r"\s+([.,;:])", r"\1", text)

        # One space after . , : ; (unless followed by space already or end of text)
        text = re.sub(r"([.,;:])(?!=\s)(?!=\s*$)", r"\1 ", text)

        # Fix multiple spaces that may have been introduced
        text = re.sub(r"\s{2,}", " ", text)

        return text

    def format_soap_note(self, raw_text: str) -> str:
        """
        Format raw text as SOAP note with section headers.

        Detects "Subjective", "Objective", "Assessment", "Plan" sections
        and formats them as uppercase headers with proper spacing.

        Args:
            raw_text: Raw text that may contain SOAP sections

        Returns:
            Formatted SOAP note
        """
        if not raw_text or not raw_text.strip():
            return ""

        text = raw_text.strip()

        # Find and format SOAP sections
        for section_key, section_header in self.SOAP_SECTIONS.items():
            # Case-insensitive match for section keywords
            pattern = rf"\b{section_key}\b"

            # Replace with formatted header
            def replace_func(match):
                return f"\n{section_header}:\n"

            text = re.sub(pattern, replace_func, text, flags=re.IGNORECASE)

        # Apply standard formatting
        text = self.format(text)

        # Clean up excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()


# ─────────────────────────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    formatter = MedicalFormatter()

    logger.info("=== Medical Formatter Tests ===\n")

    # Test 1: Number conversion
    test1 = "patient is twenty five years old with fifty milligrams of medication"
    result1 = formatter.format(test1)
    logger.info(f"Test 1 (Numbers):\n  Input:  {test1}\n  Output: {result1}\n")

    # Test 2: Units
    test2 = "take one hundred milliliters three times daily"
    result2 = formatter.format(test2)
    logger.info(f"Test 2 (Units):\n  Input:  {test2}\n  Output: {result2}\n")

    # Test 3: Acronyms
    test3 = "patient has copd and chf. ecg shows normal sinus rhythm."
    result3 = formatter.format(test3)
    logger.info(f"Test 3 (Acronyms):\n  Input:  {test3}\n  Output: {result3}\n")

    # Test 4: Drug names
    test4 = "prescribed amoxicillin and metformin daily"
    result4 = formatter.format(test4)
    logger.info(f"Test 4 (Drugs):\n  Input:  {test4}\n  Output: {result4}\n")

    # Test 5: SOAP note
    test5 = "subjective: patient reports fatigue. objective: vital signs stable. assessment: acute bronchitis. plan: prescribe amoxicillin"
    result5 = formatter.format_soap_note(test5)
    logger.info(f"Test 5 (SOAP):\n  Input:  {test5}\n  Output:\n{result5}\n")

    logger.info("=== Tests Complete ===")
