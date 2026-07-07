"""
Solution: Extract characters with metadata, group into lines, then identify
    headlines based on predominant font size per line.

Architecture Alignment:
    - Layer 1: Document Ingestion
    - Feeds into: Layer 2 (semantic chunking) and Layer 3 (mapping UI)

Parsing Strategies:
    1. **pdfplumber (FREE)**: Character-level font-based headline detection
    2. **ai_parse_document (DATABRICKS)**: AI-powered semantic parsing (paid) - for later use if needed

"""
import pdfplumber 
import re
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict

################
##### Configuration: Headline Detection Rules
################
# These thresholds determine what counts as a "headline" vs "body text"
# Based on analysis of statistical reports:
# - Headlines: 14-18pt font
# - Body text: 10-12pt font
# - Footnotes: 8-9pt font

FONT_SIZE_THRESHOLDS = {
    'h1_min': 16.0,  # Main headlines anything >= 16pt might be a headline
    'h2_min': 12.0,  # Sub-headlines (12-16pt) - LOWERED to capture 12pt bold
    'h3_min': 10.0,  # Smaller subheadlines (10-12pt) - for edge cases
    'body_max': 12.5,  # Body text is usually <= 12.5pt
    'min_headline': 11.5,  # Minimum font size for headlines - LOWERED TO 11.5
    'max_body_sentence': 15.0  # Text 14-15pt that's not bold is body text
}

# A phrase must meet these criteria to be considered
HEADLINE_CRITERIA = {
    'min_words': 2,  # Executive Summary = 2 words 
    'max_words': 10,  # REDUCED from 20 to 10 - real headlines are short
    'min_chars': 5,  # Minimum length to avoid noise like "A" or "1"
    'max_consecutive_lines': 100,  # Headlines rarely span more than 3 lines
    'min_spacing': 25.0  # Minimum spacing before line to be considered headline
}

# Common patterns in statistical report headlines:

# Common headline patterns in statistical reports
# These patterns are GENERIC and work across different report types:
# - Government stats, research papers, surveys, economic indicators, etc.
# - Avoid domain-specific terms (e.g., "attainment", "facts and figures")

HEADLINE_PATTERNS = [
    r'^[A-Z].*',                    # Starts with capital letter (universal)
    r'^\d+\..*',                  # Numbered sections: "1. Introduction"
    r'^(Chapter|Section|Part)\s+\d+', # Chapter markers
    r'.*Summary$',              # Ends with "Summary"
    r'.*Results$',                  # Ends with "Results"
    r'.*Analysis$',           # Ends with "Analysis"
    r'.*Methodology$',         # Ends with "Methodology"
    r'.*Introduction$',       # Ends with "Introduction"
    r'.*Conclusion$',        # Ends with "Conclusion"
    r'.*Overview$',           # Ends with "Overview"
    r'.*Discussion$',            # Ends with "Discussion"
    r'.*Findings$',          # Ends with "Findings"
    r'.*Background.*',         # Contains "Background" (common in gov reports)
    r'.*Key.*',              # Starts with "Key" (e.g., "Key findings")
    r'About\s+the.*',     # "About the [topic]" (common in gov reports)
]

##################################
###### Main parsing function #####
##################################
def parse_pdf(
    pdf_path: str,
    parser: str = 'pdfplumber', 
    extract_tables: bool = False, 
    use_databricks: bool = False
) -> Dict: 
    """
    Parse a PDF an extract headlines, text and tables.

    Parameters:
        pdf_path(str): Full path to PDF file
        parser(str): 'pdfplumber' or databricks extract_tables (bool): Whether to databricks extract_tables
        use_databricks(bool): Shortcut for parser = 'databricks'
    Returns:
        dict: Parse document with unified structure
    """
    if use_databricks or parser == 'databricks':
        return _parse_with_databricks_ai(pdf_path)
    elif parser == 'pdfplumber':
        return _parse_with_pdfplumber(pdf_path, extract_tables)
    else:
        raise ValueError(f"Invalid parser: {parser}") 

###################################################################
########## PDFPLUMBER IMPLEMENTATION (Character-level extraction) #
###################################################################

def _parse_with_pdfplumber(pdf_path: str, extract_tables: bool = False) -> Dict:

    """
    Parse PDF using pdfplumber with CHARACTER-LEVEL font detection.

    Key Learning:
        Some PDF's (esp Microsoft Word) don't expose font metadata via page.extract_words(), 
        but expose it via page.chars(). We extract characters, reconstruct lines, and identify headlines by predominant font size per line. 

    Process:
        1. Extract characters with font metadata (size, position, font name)
        2. Group characters into lines (same y-position)
        3. Calculate average font size per line
        4. Lines with font >= 11.5pt = headline candidates
        5. Validate and rank headlines by size
        6. Extract body text and tables
    """
    try:
        result = {
            'document_id': _generate_document_id(pdf_path), 
            'filename': pdf_path.split('/')[-1],
            'headlines': [],
            'body_text': '', 
            'tables': [], 
            'metadata': {
                'parser_used': 'pdfplumber', 
                'parse_timestamp': datetime.now().isoformat(), 
                'total_pages': 0 
            }
        }

        with pdfplumber.open(pdf_path) as pdf: 
            result['metadata']['total_pages'] = len(pdf.pages)

            all_text = []
            page_headlines = []

            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract plain text for body_text field
                page_text = page.extract_text()
                if page_text:
                    all_text.append(page_text)
                # Extract headlines using character-level font data
                headlines_on_page = _extract_headlines_from_page_chars(page, page_num)
                page_headlines.extend(headlines_on_page)

                # Extract tables
                if extract_tables:
                    tables_on_page = page.extract_tables()
                    if tables_on_page:
                        for table in tables_on_page:
                            result['tables'].append({'page': page_num,
                                                     'data': table})

            # Join all text into a single string
            result['body_text'] = '\n'.join(all_text)

            # Process headline: assign levels and extract paragraphs
            result['headlines'] = _process_and_rank_headlines(page_headlines, result['body_text'])
        return result
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    except Exception as e:
        raise RuntimeError(f"Error parsing PDF: {e}")


def _extract_headlines_from_page_chars(page, page_num: int) -> List[Dict]:
    """
    Extract headlines using CHARACTER-LEVEL font metadata.
    
    ALGORITHM:
        1. Get all characters with font size and position
        2. Group characters by line (same y-position ± 2px)
        3. Reconstruct text for each line
        4. Calculate average font size per line
        5. Lines with avg_size >= 11.5pt = headline candidates
        6. Validate and return
    
    WHY THIS WORKS:
        Microsoft Word PDFs store font data per character, not per word.
        By grouping characters into lines and checking the predominant size,
        we can reliably identify headlines even when extract_words() fails.
    
    """
    chars = page.chars

    if not chars:
        return []
    
    # Group characters by line (y-position)
    lines_by_y = defaultdict(list)

    for char in chars:
        # Round y-position to group chars on same line (+- 2px tolerance)
        y = round(char.get('top', 0) / 2) * 2

        lines_by_y[y].append({
            'text': char.get('text', ''), 
            'size': char.get('size', 0), 
            'font': char.get('fontname', ''),
            'x': char.get('x0', 0)
        })
    
    headlines = []
    prev_y = None  # Initialize before loop

    for y in sorted(lines_by_y.keys()):
        line_chars = sorted(lines_by_y[y], key=lambda c: c['x'])  # Sort left-to-right

        # Reconstruct text
        line_text = ''.join([c['text'] for c in line_chars]).strip()

        if not line_text or len(line_text) < HEADLINE_CRITERIA['min_chars']:
            continue
                          
        # Calculate average font size for this line
        sizes = [c['size'] for c in line_chars if c['size'] > 0]

        if not sizes:
            continue
            
        avg_size = sum(sizes) / len(sizes)

        # Calculate spacing from previous line (for isolation check)
        spacing = y - prev_y if prev_y else 0

        # Get most common font name to check if bold
        font_counts = {}
        for c in line_chars:
            font = c['font']
            font_counts[font] = font_counts.get(font, 0) + 1
        most_common_font = max(font_counts, key=font_counts.get) if font_counts else ""
        is_bold = 'Bold' in most_common_font or 'bold' in most_common_font.lower()

        # Check if this line is a headline
        if avg_size >= FONT_SIZE_THRESHOLDS['min_headline']:
            # REJECT: 14-15pt non-bold text (body text in special sections)
            if 14.0 <= avg_size <= FONT_SIZE_THRESHOLDS['max_body_sentence'] and not is_bold:
                prev_y = y
                continue

            # REJECT: 12pt text that's NOT bold (regular body text)
            if avg_size < 13.0 and not is_bold:
                prev_y = y
                continue

            # REJECT: 12pt bold with >10 words (emphasized body sentences)
            word_count = len(line_text.split())
            if avg_size < 13.0 and is_bold and word_count > HEADLINE_CRITERIA['max_words']:
                prev_y = y
                continue

            # REJECT: Lines without enough spacing above (not isolated)
            if spacing > 0 and spacing < HEADLINE_CRITERIA['min_spacing']:
                prev_y = y
                continue

            # Validate as a headline
            if _is_valid_headline(line_text):
                headlines.append({
                    'text': line_text,
                    'page': page_num,
                    'font_size': avg_size,
                    'is_bold': is_bold, 
                    'spacing': spacing, 
                    'raw_confidence': _calculate_headline_confidence(line_text, avg_size, is_bold, spacing)
                })
        
        prev_y = y
    return headlines

def _is_valid_headline(text: str) -> bool:
    """
    Validate whether text is a true headline. 

    Checks: 
    1. Word count: 2-10 words (REDUCED from 20)
    2. Character count: >= 5 chars
    3. Patterns matching (capital start, numbered, etc)
    4. Not all caps (usually emphasis)
    5. Not all lowercase
    6. Not ending with incomplete sentence markers
    """
    if not text or not text.strip():
        return False

    words = text.split()
    if len(words) < HEADLINE_CRITERIA['min_words']:
        return False
    if len(words) > HEADLINE_CRITERIA['max_words']:
        return False
    if len(text) < HEADLINE_CRITERIA['min_chars']:
        return False
    
    # REJECT: Incomplete sentences (end with conjunctions, prepositions, etc.)
    incomplete_endings = [
        ', with an',  # "London was highest, with an"
        'and key',
        'in the', 
        'by the', 
        'of the', 
        'for the', 
        'to the',
        'from the',
        ', and', 
        ', followed'
    ]

    text_lower = text.strip().lower()
    for ending in incomplete_endings:
        if text_lower.endswith(ending):
            return False

    # Pattern matching 
    matches_pattern = any(
        re.match(pattern, text.strip())
        for pattern in HEADLINE_PATTERNS
    )

    # Additional checks
    is_all_caps = text.isupper()
    is_all_lower = text.islower()
    starts_with_capital = text[0].isupper()

    return (matches_pattern or starts_with_capital) and not is_all_caps and not is_all_lower

def _calculate_headline_confidence(text: str, font_size: float, is_bold: bool = False, spacing: float = 0) -> float:
    """
    Calculate confidence score (0.0 to 1.0)

    Scoring:
        Base: 0.5
        + 0.3 if font >= 16pt (H1)
        + 0.2 if font >= 12pt (H2) - UPDATED
        + 0.1 if 2-8 words (ideal length)
        + 0.1 if matches pattern
        + 0.15 if bold
        + 0.15 if large spacing (>30pt)
        Max: 1.0
    
    """
    confidence = 0.5

    # Font size scoring
    if font_size >= FONT_SIZE_THRESHOLDS['h1_min']: 
        confidence += 0.3
    elif font_size >= FONT_SIZE_THRESHOLDS['h2_min']:
        confidence += 0.2

    # Word count scoring
    word_count = len(text.split())
    if 2 <= word_count <= 8:
        confidence += 0.1

    # Pattern matching scoring
    if any(re.match(pattern, text.strip()) for pattern in HEADLINE_PATTERNS):
        confidence += 0.1
    
    # Bold font scoring (NEW)
    if is_bold: 
        confidence += 0.15
    
    # Spacing scoring (NEW) - isolated headlines have large spacing
    if spacing >= 30:
        confidence += 0.15
    elif spacing >= 25:
        confidence += 0.10

    return min(confidence, 1.0)

def _process_and_rank_headlines(headlines: List[Dict], full_text: str) -> List[Dict]:
    """
    Assign hierarchy levels (H1, H2, H3) and extract paragraphs.
    
    Hierarchy:
        - Font >= 16pt → Level 1 (H1)
        - Font 12-16pt → Level 2 (H2)
        - Font < 12pt → Level 3 (H3)
    """
    if not headlines:
        return []

    processed = []

    for idx, headline in enumerate(headlines):
        # Assign level based on font size
        if headline['font_size'] >= FONT_SIZE_THRESHOLDS['h1_min']:
            level = 1  # H1

        elif headline['font_size'] >= FONT_SIZE_THRESHOLDS['h2_min']:
            level = 2  # H2
        else:
            level = 3  # H3

        # Extract paragraphs between this headline and next 

        next_headline = headlines[idx + 1] if idx + 1 < len(headlines) else None
        paragraphs = _extract_paragraphs_for_headline(
            headline['text'], 
            next_headline['text'] if next_headline else None, 
            full_text
        )

        processed.append({
            'id': f"h{idx + 1}",
            'text': headline['text'], 
            'level': level, 
            'page': headline['page'], 
            'confidence': headline['raw_confidence'],
            'is_bold': headline.get('is_bold', False),  # NEW
            'spacing': headline.get('spacing', 0),  # NEW
            'paragraphs': paragraphs
        })
    
    return processed

def _extract_paragraphs_for_headline(
    headline_text: str,
    next_headline_text: Optional[str], 
    full_text: str
) -> List[str]:
    
    """
    Extract paragraphs between headline and the next.
    
    Finds content after current headline up to next headline (or end of doc), then splits into paragraphs (separated by double newlines).
    
    """
    try: 
        start_idx = full_text.find(headline_text)
        if start_idx == -1:
            return []
        
        start_idx += len(headline_text)

        if next_headline_text:
            end_idx = full_text.find(next_headline_text, start_idx)
            if end_idx == -1:
                end_idx = len(full_text)
        else: 
            end_idx = len(full_text)

        section_text = full_text[start_idx:end_idx].strip()
        paragraphs = re.split(r'\n\n+', section_text)
        cleaned = [p.strip() for p in paragraphs if p.strip()]

        return cleaned
    except Exception:
        return []


###############################################
### DATABRICKS AI PARSER (Placeholder) #######
##############################################

def _parse_with_databricks_ai(pdf_path: str) -> Dict:
    """
    Parse PDF using Databricks ai_parse_document [AI-powered paid]. 

    Placeholder for future implementation.
    """
    raise NotImplementedError(
        "Databricks ai_parse_document not yet implemented. "
        "Use parser='pdfplumber' for now."
    )
    
#### UTILITY FUNCTIONS #######

def _generate_document_id(pdf_path: str) -> str:
    """ Generate unique document ID from path + timestamp"""
    filename = pdf_path.split("/")[-1].replace(".pdf", "")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{filename}_{timestamp}"

######################
#### PUBLIC API ######
######################

def extract_headlines(pdf_path: str, parser: str = 'pdfplumber') -> List[Dict]:
    """
    Extract only headlines (no body text, no tables).
    
    """
    result = parse_pdf(pdf_path, parser=parser, extract_tables=False)
    return result['headlines']

def get_headline_by_page(pdf_path: str, page_num: int) -> List[Dict]:
    """
    Get headlines from specific page
    """
    result = parse_pdf(pdf_path, extract_tables=False)
    return [h for h in result['headlines'] if h['page'] == page_num]

###############################
######## EXAMPLE USAGE ########
###############################

if __name__ == '__main__': 
    sample_pdf = '/Volumes/my_catalog/agentic_quality_check_dev/pdfs_volume/Multiplication_check.pdf'

    result = parse_pdf(sample_pdf)

    print(f"Document: {result['filename']}")
    print(f"Pages: {result['metadata']['total_pages']}")
    print(f"Headlines: {len(result['headlines'])}")

    for h in result['headlines']:
        print(f" [H{h['level']}] Page {h['page']}: {h['text']}")
