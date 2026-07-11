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
from .components import render_headline_tree, render_column_preview, render_mapping_controls



###############################################
#### Main Orchestrator Function ###############
###############################################

def render_mapping_tab(pdf_path: str, csv_paths: List[str]):
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

    # Step 2: Load CSV metadata
    csv_metadata_list = []
    for csv_path in csv_paths:
        metadata = get_csv_metadata(csv_path)
        csv_metadata_list.append(metadata)
    
    # Step 3: Initialize mapping storage in session state
    if 'headline_mappings' not in st.session_state:
        st.session_state.headline_mappings = {}

    # Step 4: Load or parse PDF
    if 'pdf_metadata' not in st.session_state:
        if pdf_path:
            with st.spinner("Parsing PDF..."):
                st.session_state.pdf_metadata = parse_pdf(pdf_path)
            st.success("PDF parsed successfully")
        else:
            st.warning("No PDF uploaded. Go to Tab 1 to upload PDF.")
            return
    
    # Step 5: Extract data from session state
    pdf_meta = st.session_state.pdf_metadata
    
    headlines = pdf_meta['headlines']
    
    
    # Step 6: Initialize mappings storage
    if 'mappings' not in st.session_state:
        st.session_state.mappings = []
    
    st.divider()
    
    # Step 7: Two-column layout
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
            st.markdown("### Headline Details")
            st.write(f"**Text:** {selected_headline['text']}")
            st.write(f"**Page:** {selected_headline['page']}")
            
            # Show paragraphs
            if selected_headline.get('paragraphs'):
                st.markdown("**Paragraphs:**")
                for i, para in enumerate(selected_headline['paragraphs'], 1):
                    with st.expander(f"Paragraph {i}"):
                        st.write(para)
            
            st.markdown("---")

            # CSV Selection UI
            st.markdown("### Map to CSV Files")
            st.write("Select which CSV file(s) contain data for this headline:")

            # Create options list: CSV filenames
            csv_options = [meta['filename'] for meta in csv_metadata_list]

            # Get current mapping for this headline (if exists)
            headline_id = f"h{selected_headline['page']}_{selected_headline['text'][:50]}"
            current_mapping = st.session_state.headline_mappings.get(headline_id, [])

            # Multi-select widget
            selected_csvs = st.multiselect(
                "Choose CSV file(s):", 
                options=csv_options, 
                default=current_mapping,
                key=f"csv_select_{headline_id}",
                help="You can select multiple CSVs if the headline needs data from different sources"
            )
            
            # Update mapping in session state
            if selected_csvs:
                st.session_state.headline_mappings[headline_id] = selected_csvs
                st.success(f"Mapped to {len(selected_csvs)} CSV(s)")
            else:
                # Remove mapping if user deselects all
                if headline_id in st.session_state.headline_mappings:
                    del st.session_state.headline_mappings[headline_id]
        
        else:
            st.info("Select a headline from the tree to map it to CSV files")
    
    # Step 8: Save mappings
    st.divider()
    st.subheader("Save Mappings")
    
    if st.session_state.headline_mappings:
        st.write(f"**{len(st.session_state.headline_mappings)} headlines mapped**")
        
        # Show preview
        with st.expander("Preview mappings"):
            for headline_id, csv_files in st.session_state.headline_mappings.items():
                st.write(f"- {headline_id}: {', '.join(csv_files)}")
        
        if st.button("Save All Mappings to Volume", type="primary"):
            # Build structured mapping data
            mappings_data = {
                'pdf_filename': os.path.basename(pdf_path),
                'created_at': datetime.now().isoformat(),
                'mappings': []
            }
            
            # Convert headline_mappings to structured format
            for headline in headlines:
                headline_id = f"h{headline['page']}_{headline['text'][:50]}"
                
                if headline_id in st.session_state.headline_mappings:
                    mappings_data['mappings'].append({
                        'headline_text': headline['text'],
                        'headline_page': headline['page'],
                        'paragraphs': headline.get('paragraphs', []),
                        'csv_files': st.session_state.headline_mappings[headline_id]
                    })
            
            # Save to Unity Catalog volume
            try:
                volume_path = "/Volumes/my_catalog/agentic_quality_check_dev/mappings_volume/"
                os.makedirs(volume_path, exist_ok=True)
            except (PermissionError, FileNotFoundError):
                # Fall back to local tmp directory (local development)
                volume_path = "/tmp/mappings_volume/"
                os.makedirs(volume_path, exist_ok=True)
            
            mapping_filename = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_mappings.json"
            full_path = os.path.join(volume_path, mapping_filename)
            
            with open(full_path, 'w') as f:
                json.dump(mappings_data, f, indent=2)
            
            st.success(f"Saved {len(mappings_data['mappings'])} mappings to: {full_path}")
            
            # Show saved data
            with st.expander("View saved JSON"):
                st.json(mappings_data)
    else:
        st.info("No mappings yet. Select CSV files for headlines above.")


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
