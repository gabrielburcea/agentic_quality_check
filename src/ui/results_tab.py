"""
Results Tab - Table extraction and Verifications Results

Purpose:
    Orchestrate table extraction from saved mappings
    Display extracted pivot tables
    Show agent reasoning and generated code
    Save extraction results as JSON for downstream agents

Architecture Alignment:
    - Input: Mapping JSON from mappings_volume (Layer 3)
    - Porcess: TableExtractorAgent extraction (Layer 4)
    - Output: Extracted tables + lineage JSON for verificatio agents
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import sys
import os
from datetime import datetime

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from agents.table_extractor_agent import TableExtractorAgent
from utils.table_extractor import TableExtractor


def render_results_tab():
    """
    Main entry point for results/extraction tab

    Workflow:
        1. List available mapping JSON files
        2. User selects a mapping to process
        3. Run TableExtractorAgent on selected mapping
        4. Display extracted tables
        5. Show generated code and lineage
        6. Save results as JSON for downstram agents
    """
    st.header("Table Extraction Results")
    st.write("Extract pivot tables from mapped headlines using Claude AI")

    # Initialize paths

    mappings_dir = "/tmp/mappings_volume"
    csvs_dir = "/tmp/" # CSV's are uploaded to /tmp in your app
    results_dir "/tmp.extraction_results." # Output for downstream agents

    # Check is mappings exist
    mappings_path = Path(mappings_dir)
    if not mappings_path.exists() or not list(mappings_path.glob("*.json")):
        st.warning("No mappings found. Please create mappings in Tab 3 first.")
        return
    
# Step 1: List available mappings
st.subheader("Select Mapping File")
mapping_files = sorted([f.name for f in mappings_path.glob("*.json")])

selected_mapping = st.selectbox(
    "Choose a mapping file to process:",
    options = mapping_files, 
    help = "These are the mapping files you saved in Tab 3")

    if not selected_mapping:
        return
    
    # Load and preview mapping
    with open(mappings_path / selected_mapping, 'r') as f:
        mapping_data = json.load(f)

    st.info(f"**PDF**: {mapping_data['pdf_filename']}")
    st.info(f"**Headlines**: {len(mapping_data['mappings'])}mapped")

    with st.expander("Preview Mappings")L:
        for idx, m in enumerate(mapping_data['mappings'], 1):
            st.write(f"{idx}. **{m['headline_text']}** -> {', '.join(m['csv_files'])}")
    st.divider()

    # Step 2: Run extraction
    st.subheader("Extract Tables")

    # API Key input
    api_key = st.text_input(
        "Antropic API Key",
        type = "password", 
        help = "Enter your Claude API Key (from console.antropic.com)",
        value = st.session_state.get('anthropic_api_key', '') 
                            )
    if api_key:
        st.session_state.antropic_api_key = api_key
    if st.button("Run Extraction", 
                 type = 'primary', disabled= not api_key):
        if not api_key:
            st.error("Please enter yoyr Anthropic API key")
            return
        
        # Initialize agent

        agent = TableExtractorAgent(
            use_claude = True, api_ke=api_key
        )
        # Initialize extractor with Claude
        extractor = TableExtractor(use_claude= True, api_key = api_key)

        #Procees mapping file

        with st.spinned("Extracting tables ... Ths may table a minute"):
            results = []

            for idx, headline_mapping in enumerate(mapping_data['mappings']):
                st.write(f"Processing {idx + 1} / {len(mapping_data['mappings'])}:
                        {headline_mapping['headline_text']}")
                
                # Get first paragraph and VSV 

                paragraph = headline_mapping['paragraphs'][0] if headline_mapping['paragraphs']
                else "" csv_file = headline_mapping['csv_files'][0] if headline_mapping['csv_files']
                else ""

                if not paragraph or not csv_file:
                    results.append({
                        'status': 'error',
                        'headline_text': headline_mapping['headline_text'],
                        'paragraph': csv_file, 
                        'error': 'Missing paragraph or CSV'
                    })
                    continue

                # Extract tables
                try:
                    # Build headline dict for extractor
                    headline_dict = {
                        'id': f"f{idx}", 
                        'text': headline_mapping['headline_text'], 
                        'paragraphs': headline_mapping['paragraphs']
                    }
                    # Get column metadata
                    from uti;s import get_csv_metadata
                    get_csv_metadata(str(csv_path))
                    column_metadata = csv_metadata['column']

                    # Extract table
                    result = extractor.extract_table(
                        headline = headline_dict, 
                        csv_path = str(csv_path), 
                        column_metadata = column_medatada
                    )

                    # Add additional context for JSON export
                    result['status'] = 'success'
                    result['paragraph'] = paragraph
                    result['csv_filename'] = csv_file
                    result.append(result)
                except Exception as e:
                    results.append({
                        'status':'error', 
                        'headline_text': headline_mapping['headline_text'], 
                        'paragraph': paragraph, 
                        'csv_filename': csv_file, 
                        'error': str(e)
                    })
        #Stpre resu;ts in session state
        st.session_state.extraction_results = results
        st.session_state.current_mapping_filename= selected_mapping
        st.session_state.pdf_filename = mapping_data['pdf_filename']
        st.success(f"Processed {len(results)}headlines")
    st.divider()

    # Step 3: Display results
    if 'extraction_results' in st.session_state:
        st.subheader('Extracted Tables')

        results = st.session_state.extraction_results

        # Summary stats

        successful = sum(1 for r in results if r['status']=='success')
        failed = sum(1 for r in results if r['status'] == 'error')

        col1. col2, col3, st.columns(3)
        col1.metric("Total", len(results))
        col2.metric("Success", successful)
        col3.metric("Failed", failed)

        st.divider()

        # Dispaly each resu;t
        for idx, result in enumerate(results, 1):
            with st.expander(f"{idx}. {result.get('headline_text', 'Unknown')}", 
                             expanded = (idx==1)):
                if result['status'] == 'error':
                    st.error(f"Error: {result.get('error', 'Unknown error')}")
                    continue
                # Show extracted table
                st.markdown("Extracted Pivot Table")

                if result.get('extracted_table'):
                    df.result = pd.DataFrame(result['extracted_table'])
                    st.dataframe(df_result, use_container_width = True)

                    # Download button
                    csv_data = df_result.to_csv(index= False)
                    st.download_button(
                        label = "Download CSV=",
                        data = csv_data, 
                        file_name = f"extracted_table_{idx}.csv", 
                        mime = "text/csv"
                    )
                else:
                    st.warning("No data extracted")

                # Show metadata 
                st.markdown(" Extractio Metadata")
                col1, col2 = st.columns(2)
                col1.metric("Rows", result.get('row_count', 0))
                col2.metric("Confidence", f"{result.get('confidence', 0):.0%}")

                # Show paragraph used
                st.markdown(" Source Context") 
                with st.expander("View paragraph"):
                    st.write(result.get('paragraph', "N/A"))

                st.markdown(f"**CSV File**: '{result.get('csv_filename', 'N/A')}'")

                # Show generated code
                st.markdown(" Generated Code")
                with st.expander("View pandas code"):
                    st.code(result.get('pandas_code', 'N/A'), 
                            lamguage = 'python')
                    
                # Show filters and columns
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Filters Applied**")
                    st.json(result.get('filters_applied', {}))

                with col2:
                    st.markdown("**Columns Selected:**")
                    st.write(result.get('columns_selected', []))
    st.divider()

    # Step 4. Save results as JSONS for downstram agents
    st.subheader("Save Resu;ts for Verification")
    st.write("Save extraction results as JSON for Numerical and Style Agents")

    if st.button("Save Extraction Resu;ts as JSON", type = "primary"): 
        # Build JSON structure for downstram agents
        extraction_output = {
             "extraction_id": f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "pdf_filename": st.session_state.pdf_filename,
                "mapping_filename": st.session_state.current_mapping_filename,
                "extracted_at": datetime.now().isoformat(),
                "total_headlines": len(results),
                "successful_extractions": successful,
                "failed_extractions": failed,
                "extractions": []
            }
            
            # Add each extraction
            for idx, result in enumerate(results, 1):
                extraction_entry = {
                    "extraction_number": idx,
                    "headline_text": result.get('headline_text', ''),
                    "paragraph": result.get('paragraph', ''),
                    "csv_filename": result.get('csv_filename', ''),
                    "status": result['status']
                }
                
                if result['status'] == 'success':
                    # Add pivot table and metadata for successful extractions
                    extraction_entry.update({
                        "pivot_table": result.get('extracted_table', []),
                        "metadata": {
                            "row_count": result.get('row_count', 0),
                            "columns_selected": result.get('columns_selected', []),
                            "filters_applied": result.get('filters_applied', {}),
                            "confidence": result.get('confidence', 0.0),
                            "generated_code": result.get('pandas_code', ''),
                            "extracted_at": result.get('extracted_at', '')
                        }
                    })
                else:
                    # Add error info for failed extractions
                    extraction_entry['error'] = result.get('error', 'Unknown error')
                
                extraction_output['extractions'].append(extraction_entry)
            
            # Create output directory if needed
            output_path = Path(results_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            base_name = Path(st.session_state.current_mapping_filename).stem
            json_filename = f"{base_name}_extraction_results.json"
            json_path = output_path / json_filename
            
            # Save JSON
            with open(json_path, 'w') as f:
                json.dump(extraction_output, f, indent=2)
            
            st.success(f"✅ Saved extraction results to: `{json_path}`")
            
            # Show preview
            with st.expander("Preview JSON Structure"):
                st.json(extraction_output)
            
            # Download button for JSON
            json_str = json.dumps(extraction_output, indent=2)
            st.download_button(
                label="⬇️ Download JSON",
                data=json_str,
                file_name=json_filename,
                mime="application/json"
            )
            
            st.info("📋 **Next Steps**: This JSON file can now be used by:\n"
                   "- **Numerical Agent**: Verify calculations and numbers\n"
                   "- **Style Agent**: Check formatting and presentation")
        }
