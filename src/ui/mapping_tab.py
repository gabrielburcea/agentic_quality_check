"""
Mapping Tab - Headline-to-CSV Mapping Interface

Purpose:
    Main orchestrator for the mapping UI. This is Layer 3 of the architecture. 
    Coordinates the entire mapping workflow from headline selection to saving. 

Architecture Alignment:
    - Layer 3: Mapping UI (this module)
    - Inputs: PDF metadata (Layer 1), CSV metadata (Layer 1)
    - Outputs: Mapping JSON files stored in mappings_volume 
    - Feeds into: Layer 4 (agent orchestration) - to be built later

Workflow:
    1. Select PDF headlines (from session state or parse)
    2. Load CSV metadata (from session state or parse)
    3. User selects headline from tree view
    4. System shows headline context (paragraphs, subheadlines)
    5. System shows CSV column previews
    6. User confirms mapping (no filtering, no column selection)
    7. Save mapping to JSON in mappings_volume
    8. Repeat for all headlines user wants to verify

Design Decision - Full Agentic:
    - User only selects WHICH headlines to verify,
    - Agent figures out HOW to verify them (columns, filters, calculation type).
"""
# Import Layer 1 utilities (PDF parser, CSV handler)
import streamlit as st
import json
from datetime import datetime 
from typing import Dict, List, Any

import sys 
import os 

# Get the src directory dynamically (parent of ui folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# import normally
from utils import parse_pdf, get_csv_metadata
from components import render_headline_tree, render_column_preview, render_mapping_controls



###############################################
#### Main Orchestrator Function ###############
###############################################

def render_mapping_tab(pdf_path: str = None, csv_path: str = None):
    """
    Main entry point for the mapping tab.
    
    Purpose:
        Orchestrate the entire mapping workflow:
        - Load/parse PDF and CSV
        - Display headline tree
        - Show selected headline context
        - Show CSV column previews
        - Capture user confirmation
        - Save mapping to JSON
    
    Args:
        pdf_path (str): Path to uploaded PDF (optional - can use session state)
        csv_path (str): Path to uploaded CSV (optional - can use session state)
    
    How it works:
        1. Check if PDF/CSV are already parsed (in session state)
        2. If not, parse them now
        3. Render headline tree (left panel)
        4. On headline selection, show context and column previews (right panel)
        5. User confirms mapping
        6. Save to session state and JSON file
        7. Show list of all saved mappings
    
    Session State Variables:
        - pdf_metadata: Parsed PDF structure (headlines, paragraphs, etc.)
        - csv_metadata: Parsed CSV structure (columns, roles, samples)
        - csv_file_name: Name of the CSV file
        - mappings: List of all mappings created by user
        - selected_headline_id: Currently selected headline (for UI persistence)
    
    Example Usage:
        >>> # In main Streamlit app:
        >>> with tab3:
        >>>     render_mapping_tab(pdf_path, csv_path)
    """
    
    st.header("Headline-to-CSV Mapping")
    st.write("Select headlines to verify. Agent will handle the rest.")
    
    # Step 1: Load or parse PDF
    if 'pdf_metadata' not in st.session_state:
        if pdf_path:
            with st.spinner("Parsing PDF..."):
                st.session_state.pdf_metadata = parse_pdf(pdf_path)
            st.success("PDF parsed successfully")
        else:
            st.warning("No PDF uploaded. Go to Tab 1 to upload PDF.")
            return
    
    # Step 2: Load or parse CSV
    if 'csv_metadata' not in st.session_state:
        if csv_path:
            with st.spinner("Parsing CSV..."):
                st.session_state.csv_metadata = get_csv_metadata(csv_path)
                st.session_state.csv_file_name = os.path.basename(csv_path)
            st.success("CSV parsed successfully")
        else:
            st.warning("No CSV uploaded. Go to Tab 2 to upload CSV.")
            return
    
    # Step 3: Extract data from session state
    pdf_meta = st.session_state.pdf_metadata
    csv_meta = st.session_state.csv_metadata
    csv_file_name = st.session_state.get('csv_file_name', 'unknown.csv')
    
    headlines = pdf_meta['headlines']
    csv_columns = csv_meta['columns']
    
    # Step 4: Initialize mappings storage
    if 'mappings' not in st.session_state:
        st.session_state.mappings = []
    
    st.divider()
    
    # Step 5: Two-column layout
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        # Render headline tree
        selected_headline_id = render_headline_tree(
            headlines,
            selected_id=st.session_state.get('selected_headline_id')
        )
        st.session_state.selected_headline_id = selected_headline_id
    
    with col_right:
        # Find the selected headline object
        selected_headline = next(
            (h for h in headlines if h['id'] == selected_headline_id),
            None
        )
        
        if selected_headline:
            # Show headline details
            st.subheader(f"Mapping: {selected_headline['text']}")
            st.write(f"**Page {selected_headline['page']}** | Level H{selected_headline['level']}")
            
            # Show headline context (paragraphs)
            if 'paragraphs' in selected_headline and selected_headline['paragraphs']:
                with st.expander("Headline Context (paragraphs)", expanded=False):
                    for i, para in enumerate(selected_headline['paragraphs'][:3]):
                        st.write(f"**Paragraph {i+1}**: {para[:200]}...")
            
            st.divider()
            
            # Show some CSV column previews (top 5 metrics)
            st.write("### CSV Columns Preview")
            st.write("These are the available data columns. Agent will select automatically.")
            
            metric_cols = [col for col in csv_columns if col['role'] == 'metric'][:5]
            for col in metric_cols:
                render_column_preview(col)
            
            st.divider()
            
            # Mapping controls (simple confirmation)
            mapping_config = render_mapping_controls(selected_headline, csv_file_name)
            
            # Save mapping button
            if st.button("Save Mapping", type="primary"):
                # Build mapping object
                new_mapping = {
                    'headline_id': selected_headline_id,
                    'headline': selected_headline,
                    'csv_file': csv_file_name,
                    'status': 'confirmed',
                    'created_at': datetime.now().isoformat()
                }
                
                # Check if mapping already exists
                existing_idx = next(
                    (i for i, m in enumerate(st.session_state.mappings) 
                     if m['headline_id'] == selected_headline_id),
                    None
                )
                
                if existing_idx is not None:
                    # Update existing
                    st.session_state.mappings[existing_idx] = new_mapping
                    st.success(f"Updated mapping for: {selected_headline['text']}")
                else:
                    # Add new
                    st.session_state.mappings.append(new_mapping)
                    st.success(f"Saved mapping for: {selected_headline['text']}")
                
                # Persist to JSON file
                _persist_mappings_to_json(st.session_state.mappings)
    
    # Step 6: Show all saved mappings
    st.divider()
    st.subheader("Saved Mappings")
    
    if st.session_state.mappings:
        st.write(f"**{len(st.session_state.mappings)} mappings created**")
        
        for mapping in st.session_state.mappings:
            with st.expander(f"{mapping['headline']['text']} (page {mapping['headline']['page']})"):
                st.write(f"**Headline ID**: {mapping['headline_id']}")
                st.write(f"**CSV File**: {mapping['csv_file']}")
                st.write(f"**Status**: {mapping['status']}")
                st.write(f"**Created**: {mapping['created_at']}")
        
        # Export button
        if st.button("Export Mappings to JSON"):
            json_str = json.dumps(st.session_state.mappings, indent=2)
            st.download_button(
                label="Download mappings.json",
                data=json_str,
                file_name=f"mappings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.info("No mappings created yet. Select a headline above and click 'Save Mapping'.")


###############################################
#### Helper Function - Persist Mappings #######
###############################################

def _persist_mappings_to_json(mappings: List[Dict], volume_path: str = None):
    """
    Save mappings to JSON file in mappings_volume.
    
    Purpose:
        Persist user-created mappings for future runs.
        Enable mapping reuse across sessions.
    
    Args:
        mappings (List[Dict]): All mappings to save
        volume_path (str): Path to Unity Catalog volume (or local dir)
    
    How it works:
        1. Serialize mappings to JSON
        2. Write to file (with timestamp in filename)
        3. Store in mappings_volume (Unity Catalog) or local folder
    
    Example:
        >>> _persist_mappings_to_json(st.session_state.mappings)
        # Creates: /Volumes/catalog/schema/mappings_volume/mappings_20250706_143022.json
    """
    
    # Default to local directory if no volume path provided
    # TODO: Update this with your actual Unity Catalog volume path
    if not volume_path:
        # For now, save to project directory
        volume_path = os.path.join(src_dir, 'data', 'mappings')
        
        # Create directory if it doesn't exist
        os.makedirs(volume_path, exist_ok=True)
    
    # Create filename with timestamp
    filename = f"mappings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(volume_path, filename)
    
    try:
        with open(filepath, 'w') as f:
            json.dump(mappings, f, indent=2)
        st.success(f"Persisted to {filepath}")
    except Exception as e:
        st.error(f"Failed to save: {e}")
