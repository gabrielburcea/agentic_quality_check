"""
This package contains:
- pdf_parser: PDF parsing with headline extraction
- csv_handler: CSV parsing and metadata extraction (agnostic)  # ← NEW!
"""
from .pdf_parser import (
    parse_pdf,
    extract_headlines,
    get_headline_by_page, 
    FONT_SIZE_THRESHOLDS,
    HEADLINE_CRITERIA,
    HEADLINE_PATTERNS
)


from .csv_handler import (
    get_csv_metadata,      # Main function (like parse_pdf)
    infer_column_role,     # Helper (user might want direct access)
    get_sample_values      # Helper (user might want direct access)
)

__all__ = [
    # PDF handler functions
    'parse_pdf',
    'extract_headlines',
    'get_headline_by_page',
    'FONT_SIZE_THRESHOLDS',
    'HEADLINE_CRITERIA',
    'HEADLINE_PATTERNS'
    # CSV handler functions  
    'get_csv_metadata',
    'infer_column_role',
    'get_sample_values'
]
