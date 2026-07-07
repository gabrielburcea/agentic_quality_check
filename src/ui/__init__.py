"""
UI Components - Streamlit Interface Modules

Purpose:
    Provide the user interface for:
    - Headline-to-CSV mapping (Tab 3)
    - Results dashboard (Tab 4) - to be built later
    - Configuration (agent selection) - to be built later

Architecture Alignment:
    - Layer 3: Mapping UI (this module)
    - Inputs: PDF metadata (from Layer 1), CSV metadata (from Layer 1)
    - Outputs: Mapping JSON (stored in mappings_volume)
    - Feeds into: Layer 4 (agent orchestration) - to be built later

Public API:
    Component-level functions:
    - render_headline_tree(): Show document headlines as tree
    - render_column_preview(): Show CSV column metadata
    - render_mapping_controls(): Simple mapping confirmation
    
    Main orchestrator:
    - render_mapping_tab(): Complete mapping interface (use this in main app)
"""

from .components import (
    render_headline_tree,
    render_column_preview,
    render_mapping_controls
)

from .mapping_tab import render_mapping_tab

__all__ = [
    'render_headline_tree',
    'render_column_preview',
    'render_mapping_controls',
    'render_mapping_tab'
]
