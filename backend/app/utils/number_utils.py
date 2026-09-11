import re
from typing import Optional, Any


def parse_financial_number(raw_str: Any) -> Optional[float]:
    """
    Parses financial string representation into a float.
    Handles:
    - Negative parentheses: '(102,477.54)' -> -102477.54
    - Commas and spaces: '1,250.00' or '1 250,00'
    - Currency symbols: '$', '₹', '€', '£'
    - Dashes / hyphens representing nil/zero: '-' or '—' -> 0.0
    - European decimal comma vs thousands separator: '126,27' -> 126.27
    """
    if raw_str is None:
        return None
    if isinstance(raw_str, (int, float)):
        return float(raw_str)

    s = str(raw_str).strip()
    if not s or s in ("-", "—", "–", "N/A", "NA", "nil", "null"):
        return 0.0

    is_negative = False
    # Check for parentheses: (123.45)
    if (s.startswith("(") and s.endswith(")")) or (s.startswith("[") and s.endswith("]")):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        is_negative = True
        s = s[1:].strip()
    elif s.endswith("-"):
        is_negative = True
        s = s[:-1].strip()

    # Strip currency signs, quotes, and non-numeric except , and .
    s = re.sub(r"[^\d,\.]", "", s)
    if not s:
        return 0.0

    # Handle comma as decimal separator if there's only one comma and 2 digits after it, e.g. 126,27
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            s = f"{parts[0]}.{parts[1]}"
        else:
            s = s.replace(",", "")
    elif "," in s and "." in s:
        # Standard format 12,345.67
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            # European format 12.345,67
            s = s.replace(".", "").replace(",", ".")

    try:
        val = float(s)
        return -val if is_negative else val
    except ValueError:
        return None


def approx_equal(val1: Optional[float], val2: Optional[float], tolerance: float = 0.05) -> bool:
    """Checks if two values are equal within tolerance."""
    if val1 is None or val2 is None:
        return False
    return abs(val1 - val2) <= tolerance


def calculate_variance(calculated: Optional[float], reported: Optional[float]) -> Optional[float]:
    """Calculates variance: |calculated - reported| rounded to 4 decimals."""
    if calculated is None or reported is None:
        return None
    return round(abs(calculated - reported), 4)
