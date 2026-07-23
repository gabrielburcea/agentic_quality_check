"""
Streamlit App - Agentic Quality Check RAG System

Purpose:
    Main user interface for the agentic quality check system
    Multi-tab interface for PDF/CSV upload and headline mapping


Architecture:
    - Tab 1: PDF Upload
    - Tab 2: CSV Upload
    - Tab 3: Mapping (using render_mapping_tab ui module)
    - Tab 4: Results (to be built later)

Usage: 
    Run from project root: streamlit run app.py
"""

import streamlit as st
import sys
import os

# Try to set API key from environment on app startup
if "ANTHROPIC_API_KEY" not in os.environ:
    try:
        # Only works in Databricks notebook context
        claude_key = dbutils.secrets.get(scope="my-api-keys", key="claude-api-key")
        os.environ["ANTHROPIC_API_KEY"] = claude_key
        print("✅ Claude API key loaded from secrets")
    except:
        # dbutils not available (running locally or in pure Streamlit)
        print("⚠️ Running without dbutils - API key must be provided manually")
        pass


# Add src to path so we can import modules 
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Import the mapping UI
from ui import render_mapping_tab

# Page configuration
st.set_page_config(
    page_title="Agentic Quality Check", 
    layout="wide"
)

# Main title
st.title("Agentic Quality Check - RAG System")
st.write("Verify PDF reports using intelligent agents")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "PDF Upload",
    "CSV Upload",
    "Mapping", 
    "Agents Results"
])

##############################
# Tab 1: PDF UPLOAD ##########
##############################
with tab1:
    st.header("Upload PDF Document")
    st.write("Upload the PDF containing headlines to verify")

    # File uploader
    uploaded_pdf = st.file_uploader(
        "Choose a PDF file", 
        type=['pdf'], 
        help="Upload the PDF document containing headlines to verify"
    )

    if uploaded_pdf:
        # Import storage module
        from utils.json_storage import JSONStorage
        #Initialise storage
        storage = JSONStorage()

        # Save to Unity Catalog Volume (persistent!)
        pdf_filename = uploaded_pdf.name.replace(".pdf", "")
        volume_path = f"/Volumes/my_catalog/agentic_quality_check_dev/pdf_volume/{pdf_filename}"
       

        with open(pdf_path, 'wb') as f:
            f.write(uploaded_pdf.getbuffer())

        st.success(f"PDF uploaded: {uploaded_pdf.name}")
        st.session_state.pdf_path = pdf_path

        st.info(f"**Saved to**: {pdf_path}")

#########################
# Tab 2: CSV UPLOAD #####
##########################

with tab2:
    st.header("Upload CSV File")
    st.write("Upload the CSV containing headlines to verify against")

    # File uploader
    uploaded_csvs = st.file_uploader(
        "Choose a CSV files", 
        type=['csv'],
        accept_multiple_files= True,
        help="Upload the CSV document containing data to verify against"
    )

    if uploaded_csvs:
        csv_paths=[] 

        for uploaded_csv in uploaded_csvs:
            # Save to Unity Catalog Volume (persistent)
            
            csv_path = f"/Volumes/my_catalog/agentic_quality_check_dev/csvs_volume/{uploaded_csv.name}"

            with open(csv_path, 'wb') as f:
                f.write(uploaded_csv.getbuffer())

            csv_paths.append(csv_path)
            st.success(f"Uploaded: {uploaded_csv.name}")
            
        # Store list in session state
        st.session_state.csv_paths = csv_paths

        st.info(f"**{len(csv_paths)} CSV files uploaded:**")
        
        # Display CSV file details
        st.divider()
        st.subheader(f"Available CSV Files ({len(csv_paths)})")
        
        from utils import get_csv_metadata
        
        for i, csv_path in enumerate(csv_paths, 1):
            metadata = get_csv_metadata(csv_path)
            
            with st.expander(f"CSV {i}: {metadata['filename']} ({metadata['row_count']} rows)"):
                st.write(f"**Columns:** {metadata['column_count']}")

                # Show filter columns
                filter_cols = [col for col in metadata['columns'] if col['role'] == 'filter']
                st.write("**Filter columns:**")
                for col in filter_cols:
                    st.write(f" - {col['name']}: {col['sample_values']}")
                
                # Show metric count only
                metric_count = len([col for col in metadata['columns'] if col['role'] == 'metric'])
                st.write(f"**Data metrics:** {metric_count} available")
    
########################################
# Tab 3: Mapping (using our new UI) ###
########################################

with tab3:
    # Check if PDF and CSV are uploaded

    if 'pdf_path' in st.session_state and 'csv_paths' in st.session_state:
        # Render the mapping interface
        render_mapping_tab(
            pdf_path=st.session_state.pdf_path,
            csv_paths=st.session_state.csv_paths
        )
    else:
        st.warning("Please upload PDF and CSV files first (Tab 1 and 2)")

        # Show status

        st.write("**Current Status:**")
        st.write(f"- PDF: {'Uploaded' if 'pdf_path' in st.session_state else 'Not uploaded'}")
        st.write(f"- CSV: {'Uploaded' if 'csv_paths' in st.session_state else 'Not uploaded'}")
        if 'csv_paths' in st.session_state:
            st.write(f" ({len(st.session_state.csv_paths)} file uploaded)")

########################################
# Tab 4: Results (placeholder) ########
########################################

with tab4:
    # Import the results from tab renderer
    from ui import render_results_tab
    # Render the extraction interface
    render_results_tab()
