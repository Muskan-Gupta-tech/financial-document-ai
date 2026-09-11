import re
from typing import Optional, List, Dict, Any


def normalize_text(text: str) -> str:
    """Normalizes whitespace and common OCR artifacts."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_grounding_evidence(
    target_value: Any,
    ocr_lines: List[Dict[str, Any]],
    field_keywords: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Finds evidence (source_text and page_number) for an extracted value from OCR lines.
    If field_keywords are provided, prioritizes lines containing the keywords or near them.
    """
    if target_value is None or not ocr_lines:
        return None

    str_val = str(target_value).strip()
    # If target_value is float, format as string representations
    val_variants = [str_val]
    if isinstance(target_value, (int, float)):
        # e.g. 13125.0 -> '13125', '13,125', '13,125.00'
        num = float(target_value)
        int_part = int(abs(num))
        formatted_with_commas = f"{int_part:,}"
        val_variants.extend([
            f"{num:.2f}",
            f"{int_part}",
            formatted_with_commas,
            f"{formatted_with_commas}.{int(round((abs(num) - int_part) * 100)):02d}",
        ])

    # First pass: look for line that contains a keyword AND the value
    if field_keywords:
        lower_keywords = [k.lower() for k in field_keywords]
        for item in ocr_lines:
            text = item.get("text", "")
            lower_text = text.lower()
            if any(kw in lower_text for kw in lower_keywords):
                for v in val_variants:
                    if v in text:
                        return {
                            "source_text": text,
                            "page_number": item.get("page", 1),
                            "confidence": item.get("score", 0.95),
                        }

    # Second pass: look for any line containing the value
    for item in ocr_lines:
        text = item.get("text", "")
        for v in val_variants:
            if v and v in text:
                return {
                    "source_text": text,
                    "page_number": item.get("page", 1),
                    "confidence": item.get("score", 0.95),
                }

    # Fallback: if field_keyword matches
    if field_keywords:
        lower_keywords = [k.lower() for k in field_keywords]
        for item in ocr_lines:
            text = item.get("text", "")
            lower_text = text.lower()
            if any(kw in lower_text for kw in lower_keywords):
                return {
                    "source_text": text,
                    "page_number": item.get("page", 1),
                    "confidence": item.get("score", 0.95),
                }

    return None
