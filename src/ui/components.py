"""
UI Components - Reusable Streamlit Widgets

Purpose:   
    - Provide reusable UI components for the mapping interface:
      - Headline tree view (collapsible hierarchy)
      - Column preview cards (show sample values)
      - Mapping controls (drag-and-drop or select boxes)

Design Principle:
    - Each component is a pure function (input - rendered UI)
    - No global state (all state passed as parameters)
    - Composable (combine widgets to build complex UIs)

"""

import streamlit as st
from typing import Dict, List, Any

def render_headline_tree(headlines: List[Dict], selected_id: str = None) -> str:
    """
    Display headlines in a hierarchical tree view with selection. 

    Purpose:
        - Show document structure (H1 > H2 > H3)
        - Allow user to select one headline for mapping
        - Visually indicate hierarchy with indentation

    How it works:
        1. Loop through headlines
        2. Indent based on level (H1 = 0, H2=1, H3 = 2)
        3. Render as radio buttons or expandable sections
        4. Return the selected headline ID
    Args:
        headlines (List[Dict]): List of headline objects from PDF parser
            Each headline: { 'id': 'h1', 'text': '...', 'level': 1, 'page': 5}
        selected_id (str): Currently selected headline ID (for persistence)

    Returns:
        str: The ID of the selected headline

    Example: 
        >>> headlines = [
        ...     {'id': 'h1', 'text': 'Background', 'level': 1, 'page': 1},
        ...     {'id': 'h2', 'text': 'About the data', 'level': 2, 'page': 2},
        ...     {'id': 'h3', 'text': 'Mean score', 'level': 3, 'page': 3}
        ... ]
        >>> selected = render_headline_tree(headlines)
        >>> print(selected) #  'h2' (if user clicked 'About data')

        UI Layout:
            Background (H1, page 1)
                About the data (H2, page 2)
                    Mean score (H3, page 3) 
    """
    st.subheader("Document Headlines")
    
    # TODO Implement tree rendering 
    # Hint: use st.radio() with formatted labels
    # Format: " " * (level - 1) + f"{text} (H{level}, page {page})"

    # For now, simple list (you'll enhance this)
    options = []
    for h in headlines:
        indent = "  " * (h['level'] - 1)
        label = f"{indent}{h['text']} (H{h['level']}, page {h['page']})"
        options.append((h['id'], label))

    selected = st.radio(
        "Select headline to map:", 
        options=[opt[0] for opt in options], 
        format_func=lambda x: dict(options)[x], 
        index=0 if not selected_id else [opt[0] for opt in options].index(selected_id)
    )

    return selected


def render_column_preview(column: Dict) -> None:
    """
    Display a single CSV column with metadata and sample values.

    Purpose:
        - Show column name, type, and inferred role
        - Display sample values (helps user understand the data)
        - Visual indication for metric vs. filter vs. identifier

    Args:
        column(Dict): Column metadata from CSV handler 
            {
                'name': 'mtc_score_average', 
                'type': 'float64', 
                'role': 'metric',
                'sample_values': {'min': 0.0, 'max': 25.0, 'mean': 19.8}
            }

    Example UI: 
        [METRIC] mtc_score_average
        Type: float64 | Role: metric
        Samples: min=0.0, max=25.0, mean=19.8
    """
    # Step 1: Choose prefix based on column role
    role_prefixes = {
        'metric': '[METRIC]', 
        'filter': '[FILTER]',
        'identifier': '[ID]',
        'unknown': '[?]'
    }

    prefix = role_prefixes.get(column['role'], '[?]')

    # Step 2: Render as expandable card
    with st.expander(f"{prefix} {column['name']}", expanded=False):

        # Step 3: Show column type 
        st.write(f"**Type**: `{column['type']}`")

        # Step 4: Show inferred role
        st.write(f"**Role**: `{column['role']}`")

        # Step 5: Display sample values
        samples = column['sample_values']

        if isinstance(samples, dict):
            # Numeric column - show statistical summary
            st.write("**Stats**:")
            st.json(samples)

        elif isinstance(samples, list):
            # Categorical column - show top values
            st.write(f"**Sample Values** ({len(samples)} shown):")
            st.write(", ".join([str(s) for s in samples[:20]]))
        else:
            # Edge case - no samples available
            st.write("**Sample**: N/A")


###################################################
# Component 3: Mapping Controls Form ##############
###################################################

def render_mapping_controls(headline: Dict, csv_file_name: str) -> Dict:
    """
    Minimal mapping interface - user just confirms the mapping.
    
    Purpose:
        Show user which headline will be verified against which CSV.
        No column selection, no filtering, no agent selection.
        The orchestrator/agent handles EVERYTHING.
    
    Design Decision - Full Agentic:
        User responsibility: Select headline to verify
        Agent responsibility: Everything else
            - Parse headline text
            - Identify relevant CSV columns
            - Determine calculation type
            - Apply appropriate filters
            - Select agents to run
            - Execute verification
    
    Args:
        headline (Dict): Full headline object with context
            {
                'id': 'h5',
                'text': 'Mean average score was 19.8',
                'level': 3,
                'page': 5,
                'subheadlines': ['Background', 'About the data'],  # Parent headlines
                'paragraphs': ['Text paragraph 1...', 'Text paragraph 2...']  # Body text
            }
        csv_file_name (str): Name of the CSV file
    
    Returns:
        Dict: Minimal mapping configuration
            {
                'headline': {...},  # Full headline object
                'csv_file': 'ks2_data.csv',
                'status': 'confirmed'
            }
    """

    st.subheader('Mapping Configuration')

    # Show what will be verified
    st.info(f"**Headline**: {headline['text']}")
    st.info(f"**CSV File**: {csv_file_name}")

    st.write("The agent will automatically:")
    st.write("- Read headline + subheadlines + paragraph text")
    st.write("- Identify relevant CSV columns")
    st.write("- Parse calculation type from full context")
    st.write("- Apply appropriate filters")
    st.write("- Select agents to run")

    # Return full headline object (not just text)
    return {
        'headline': headline,
        'csv_file': csv_file_name, 
        'status': 'confirmed'
    }
