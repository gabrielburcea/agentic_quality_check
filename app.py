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
        # Save to temporary location
        pdf_path = f"/tmp/{uploaded_pdf.name}"

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
    uploaded_csv = st.file_uploader(
        "Choose a CSV files", 
        type=['csv'],
        accept_multiple_files= True,
        help="Upload the CSV document containing data to verify against"
    )

    if uploaded_csvs:
        csv_paths=[] 

        for uploaded_csv in uploaded_csvs:
            csv_path = f"/tmp/{uploaded_csv.name}"

            with open(csv_path, 'wb') as f:
                f.write(uploaded_csv.getbuffer())

            csv_paths.append(csv_path)
            st.success(f"Uploaded: {uploaded_csv.name}")
            
        # Store list in session state

        st.session_state.csv_paths - csv_paths

        st.info(f"**{len(csv_paths)} CSV files uploaded:**")
    
########################################
# Tab 3: Mapping (using our new UI) ###
########################################

with tab3:
    # Check if PDF and CSV are uploaded

    if 'pdf_path' in st.session_state and 'csv_path' in st.session_state:
        # Render the mapping interface
        render_mapping_tab(
            pdf_path=st.session_state.pdf_path,
            csv_path=st.session_state.csv_paths
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
    st.header("Verification Results")
    st.info("Results dashboard will be built in layer 4 (Agent Orchestration)")
    st.write("This tab will show:")
    st.write("- Verification status for each mapped headline")
    st.write("- A table with different columns from Pass/Fail results to Agent explanation to Suggested corrections")
