# Agentic Quality Check - Statistical Reports

## Project Overview
An agentic solution for quality checking statistical reports, comparing document content against CSV data, and validating both numerical accuracy and writing style.

**Implementation Approach**: Streamlit prototype using RAG (Retrieval-Augmented Generation) with HuggingFace models and multi-agent orchestration.

## Application Architecture

### Multi-Tab Streamlit Interface

#### Tab 1: Document Upload
- Upload statistical report documents (PDF format)
- Example: UK Department for Education multiplication tables check statistics
- Document structure includes:
  - Background Information
  - Headline facts and figures
  - Multiple content sections with headlines and sub-headlines
  - Attainment by gender
  - Attainment by disadvantage status
  - Attainment by Special Education Needs
  - Attainment by region and local authority
  - etc.

#### Tab 2: CSV Upload
- Upload corresponding data files in CSV format
- CSV contains the raw numerical data referenced in the report

#### Tab 3: Analysis Configuration
- **Headline Selection**: Interactive selection of headlines and sub-headlines from the uploaded document
- **Matching**: Map selected headlines to corresponding CSV data columns/rows
- **Agent Configuration**: Configure which checks to run (numerical, style, or both)

#### Tab 4: Results Dashboard
Two separate tables for quality check results:

##### Table 1: Numerical Accuracy Check
| Column | Description |
|--------|-------------|
| **Headline** | Selected headline/section from document |
| **Analyzed Text** | Actual text block analyzed by LLM |
| **Numbers Correct** | Pass status (Yes/No) - verifies numbers against CSV |
| **Suggestions** | LLM-generated corrections or clarifications |
| **Agree** | Button (Yes/No) - user validation |
| **Commentary** | Text field for user feedback |

##### Table 2: Style & Writing Quality Check
| Column | Description |
|--------|-------------|
| **Headline** | Selected headline/section from document |
| **Analyzed Text** | Actual text block analyzed by LLM |
| **Style Check** | Pass status (Yes/No) - grammar, formal statistical tone, clarity |
| **Suggestions** | LLM-generated style improvements |
| **Agree** | Button (Yes/No) - user validation |
| **Commentary** | Text field for user feedback |

## RAG Architecture

### Vector Store for Document Context
- **PDF Chunking**: Split uploaded PDF into semantic chunks (by headline/section)
- **Embeddings**: Use HuggingFace sentence-transformers (e.g., `all-MiniLM-L6-v2`)
- **Vector DB**: FAISS or Chroma for local storage (lightweight, no external dependencies)
- **Retrieval**: For each headline analysis, retrieve relevant document context

### CSV Data Indexing
- **Structured Storage**: Parse CSV into pandas DataFrame
- **Column Metadata**: Extract column names, data types, summary statistics
- **Query Interface**: Allow agents to query CSV data via natural language → SQL/pandas operations

### RAG Flow
1. User selects headline → Retrieve relevant document chunks from vector store
2. Agent receives: headline text + surrounding context + matched CSV data
3. LLM generates analysis using retrieved context
4. Results stored with traceability back to source chunks

## Agent Capabilities

### Agent 1: Numerical Accuracy Agent
**Responsibilities:**
- Extract numerical values from report text
- Match numbers to corresponding CSV data
- Verify calculations (percentages, averages, differences)
- Identify discrepancies
- Generate correction suggestions

**RAG Integration:**
- Retrieves document context around numerical claims
- Queries CSV data to compute ground truth values
- Compares claim vs computed value
- Provides evidence trail (which CSV rows/columns used)

**Example Checks:**
- "Mean average score 19.8 out of 25" → Verify against CSV mean calculation
- "27% of pupils achieving full marks" → Verify percentage calculation
- "Disadvantaged pupils: 17.9 vs other pupils: 20.5" → Verify group comparisons

### Agent 2: Style & Quality Agent
**Responsibilities:**
- Grammar checking
- Tone consistency (formal, statistical)
- Clarity and readability
- Proper statistical language usage
- Consistency in terminology

**RAG Integration:**
- Retrieves similar sections from document for consistency checking
- Compares writing style across different sections
- Identifies terminology inconsistencies

**Example Checks:**
- Formal tone maintenance
- Correct use of statistical terms
- Sentence structure and flow
- Consistent formatting of numbers and percentages

### Agent 3: Self-Healing Agent
**Responsibilities:**
- Receive user feedback from "Agree" buttons and commentary
- Learn from disagreements
- Re-analyze sections where user disagreed
- Update suggestions based on user preferences
- Improve future checks based on feedback patterns

**RAG Integration:**
- Stores user feedback in vector store as examples
- Retrieves similar past corrections when analyzing new sections
- Builds a "correction memory" to improve over time

## Technical Stack

### Core Technologies
1. **Streamlit** - Multi-tab web UI framework
2. **HuggingFace Models**:
   - **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (22M params, ~90MB)
   - **Text Generation**: `TinyLlama-1.1B-Chat` or `Phi-1.5` (fits in Community Edition)
   - **Alternative**: DistilGPT-2 for faster CPU inference
3. **Vector Store**: FAISS or Chroma (local, lightweight)
4. **PDF Processing**: PyPDF2 or pdfplumber
5. **CSV Processing**: pandas
6. **Multi-Agent Framework**: LangChain or custom orchestration
7. **State Management**: Streamlit session state

### Python Dependencies
```txt
streamlit
transformers
torch
sentence-transformers
faiss-cpu
langchain
pypdf2
pandas
numpy
```

### Data Flow
1. User uploads PDF → Extract text, chunk by headline, embed chunks → Store in FAISS
2. User uploads CSV → Parse into DataFrame, extract metadata
3. User selects headlines → Retrieve relevant chunks + CSV data
4. Agents analyze (RAG-enhanced):
   - Numerical Agent: Retrieve context + query CSV + verify numbers
   - Style Agent: Retrieve similar sections + check consistency
5. Results displayed in interactive tables
6. User provides feedback → Self-healing agent stores feedback in vector store
7. Re-run with improved context

## Example Report Structure
**Document**: UK DfE Multiplication Tables Check Statistics 2022

**Sample Headlines**:
- Background Information
- Headline facts and figures
- About the multiplication tables check
- National attainment in the multiplication tables check
- Attainment by pupil characteristics
  - Attainment by gender
  - Attainment by disadvantage status
  - Attainment by Special Educational Need (SEN) status
  - Attainment by first language
  - Attainment by month of birth
  - Attainment by ethnicity
- Attainment by school characteristics
  - Attainment by school type
- Attainment by region and local authority
  - Attainment by region
  - Attainment by local authority

**Sample Numerical Claims to Verify**:
- "Mean average score was 19.8 out of 25"
- "27% of pupils achieving full marks"
- "Average score for disadvantaged pupils was 17.9"
- "Average score for other pupils was 20.5"
- "London highest performing region with average score of 20.9"

## Streamlit Prototype - Implementation Roadmap

### Phase 1: Foundation Setup
**Goal**: Basic Streamlit app with file uploads and data processing

- [ ] **Task 1.1**: Set up project structure
  - Create `app.py` (main Streamlit app)
  - Create `requirements.txt` with dependencies
  - Create `src/` directory for modules
  
- [ ] **Task 1.2**: Implement PDF processing
  - Upload PDF file widget
  - Extract text using PyPDF2
  - Parse document structure (identify headlines/sections)
  - Display extracted headlines in Streamlit
  
- [ ] **Task 1.3**: Implement CSV processing
  - Upload CSV file widget
  - Parse CSV with pandas
  - Display summary statistics
  - Create query interface for CSV data

### Phase 2: RAG Implementation
**Goal**: Build vector store and retrieval system

- [ ] **Task 2.1**: Set up embeddings model
  - Load `all-MiniLM-L6-v2` from HuggingFace
  - Test embedding generation on sample text
  - Measure inference speed on CPU
  
- [ ] **Task 2.2**: Build document vector store
  - Chunk PDF by headlines/paragraphs
  - Generate embeddings for each chunk
  - Store in FAISS index
  - Implement retrieval function (query → top-k chunks)
  
- [ ] **Task 2.3**: CSV data indexing
  - Extract column metadata
  - Create semantic search over column names/descriptions
  - Build pandas query interface

### Phase 3: Agent Development
**Goal**: Implement three specialized agents

- [ ] **Task 3.1**: Numerical Accuracy Agent
  - Load TinyLlama or Phi-1.5 model
  - Design prompt template for numerical verification
  - Implement number extraction from text
  - Implement CSV query logic (mean, percentage, group comparisons)
  - Create verification function (claim vs ground truth)
  - Generate suggestions for discrepancies
  
- [ ] **Task 3.2**: Style & Quality Agent
  - Design prompt template for style checking
  - Implement grammar/tone analysis
  - Check statistical terminology consistency
  - Generate style improvement suggestions
  
- [ ] **Task 3.3**: Self-Healing Agent
  - Store user feedback in vector store
  - Retrieve past feedback for similar sections
  - Update prompts based on feedback patterns
  - Re-analyze with improved context

### Phase 4: Multi-Agent Orchestration
**Goal**: Coordinate agents and manage workflow

- [ ] **Task 4.1**: Agent orchestrator
  - Sequence agent execution (parallel or sequential)
  - Manage shared context between agents
  - Handle errors and retries
  
- [ ] **Task 4.2**: RAG-enhanced agent calls
  - For each headline, retrieve relevant context
  - Pass context + CSV data to agents
  - Combine agent outputs into structured results

### Phase 5: UI/UX Implementation
**Goal**: Build interactive Streamlit interface

- [ ] **Task 5.1**: Multi-tab layout
  - Tab 1: Document Upload
  - Tab 2: CSV Upload
  - Tab 3: Analysis Configuration
  - Tab 4: Results Dashboard
  
- [ ] **Task 5.2**: Analysis Configuration UI
  - Display extracted headlines as checkboxes
  - Implement headline → CSV column mapping
  - Agent selection (numerical, style, both)
  - "Run Analysis" button
  
- [ ] **Task 5.3**: Results Dashboard
  - Display results in two tables (numerical + style)
  - Add "Agree" buttons (Yes/No)
  - Add commentary text fields
  - Export results to CSV/PDF

### Phase 6: Testing & Optimization
**Goal**: Validate accuracy and improve performance

- [ ] **Task 6.1**: Test with sample report
  - Use UK DfE multiplication tables check report
  - Verify numerical accuracy checks
  - Verify style quality checks
  - Measure end-to-end latency
  
- [ ] **Task 6.2**: Model optimization
  - Test different HuggingFace models (speed vs quality)
  - Implement model caching
  - Optimize chunk size for RAG
  - Tune retrieval parameters (top-k)
  
- [ ] **Task 6.3**: Error handling & edge cases
  - Malformed PDFs
  - Missing CSV columns
  - Ambiguous headline matching
  - Model hallucination detection

### Phase 7: Self-Healing Loop
**Goal**: Implement feedback-based improvement

- [ ] **Task 7.1**: Feedback collection
  - Capture "Agree" responses
  - Store commentary as structured feedback
  - Tag feedback by headline/agent
  
- [ ] **Task 7.2**: Feedback integration
  - Add feedback to vector store
  - Retrieve relevant feedback during analysis
  - Update prompts based on feedback
  
- [ ] **Task 7.3**: Performance tracking
  - Track agreement rate over time
  - Identify sections with frequent disagreements
  - Generate improvement reports

## Implementation Considerations

### LLM Model Selection (HuggingFace)
**Embedding Models** (for RAG):
- `sentence-transformers/all-MiniLM-L6-v2` - 22M params, 90MB, fast CPU inference
- `sentence-transformers/all-mpnet-base-v2` - 110M params, 420MB, higher quality

**Text Generation Models** (for agents):
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0` - 1.1B params, optimized for chat
- `microsoft/phi-1_5` - 1.3B params, strong reasoning for size
- `distilgpt2` - 82M params, very fast but lower quality

**Model Selection Criteria**:
- Memory: Must fit in 15GB RAM (Community Edition)
- Speed: CPU-only inference, need <5s per analysis
- Quality: Balance between speed and accuracy

### Prompt Engineering
- **Numerical Agent Prompt Template**:
  ```
  You are verifying numerical claims in a statistical report.
  
  Document Context: {retrieved_context}
  Claim: {headline_text}
  CSV Data: {csv_data}
  
  Task: Extract numbers from the claim, compute ground truth from CSV, compare.
  Output: Pass/Fail status + Suggestions
  ```

- **Style Agent Prompt Template**:
  ```
  You are checking writing quality in a statistical report.
  
  Text to analyze: {headline_text}
  Similar sections: {retrieved_similar_sections}
  
  Task: Check grammar, tone (formal statistical), clarity, terminology consistency.
  Output: Pass/Fail status + Suggestions
  ```

### RAG Optimization
- **Chunk Size**: 200-500 words per chunk (balance context vs retrieval precision)
- **Top-K Retrieval**: 3-5 most relevant chunks per query
- **Embedding Dimension**: 384 (all-MiniLM-L6-v2) - good balance for FAISS
- **Vector Store**: FAISS with IndexFlatL2 (exact search, small dataset)

### Error Handling
- Handle malformed PDFs (fallback to OCR if needed)
- Handle missing CSV columns (suggest alternatives)
- Handle ambiguous headline matching (present options to user)
- Handle model errors (timeout, OOM) with retries and degradation

### Deployment Options

#### Option 1: Databricks Community Edition (FREE)
**What Works:**
- Run Streamlit in notebook cells using `streamlit run app.py`
- Load HuggingFace models (stay under 15GB RAM)
- Process PDFs and CSVs
- Store files in workspace `/Workspace/Users/.../uploads/`

**Limitations:**
- No external sharing (only you can access)
- 2-hour session timeout
- CPU-only (slower inference)

**Setup:**
```python
# In Databricks notebook
%pip install streamlit transformers sentence-transformers faiss-cpu pypdf2 pandas

# Run app
!streamlit run app.py --server.port 8501
```

#### Option 2: Local Development
**What Works:**
- Full control, no timeouts
- Can use GPU if available
- Easy debugging

**Limitations:**
- Must install Python locally
- No cloud persistence

**Setup:**
```bash
pip install -r requirements.txt
streamlit run app.py
```

#### Option 3: Streamlit Cloud (FREE tier available)
**What Works:**
- Public sharing via URL
- Auto-deploy from GitHub
- Free tier: 1GB RAM, CPU-only

**Limitations:**
- Limited to smaller models (DistilGPT-2, all-MiniLM)
- Cannot use TinyLlama (too large for 1GB)

### Estimated Costs

**Community Edition (FREE)**:
- Compute: $0
- Storage: $0
- Models: Free (HuggingFace open-source)
- **Total: $0**

**Local Development (FREE)**:
- Your own hardware
- No ongoing costs
- **Total: $0**

**Streamlit Cloud (FREE tier)**:
- Public apps: Free
- Private apps: $20/month
- **Total: $0-20/month**

## Future Enhancements

### Beyond Prototype
- **Model Upgrades**: Use larger models (Llama 7B, Mistral) with paid GPU compute
- **Advanced RAG**: Hybrid search (dense + sparse), query expansion, re-ranking
- **Databricks Apps**: Migrate from Streamlit to Databricks Apps for enterprise features
- **Unity Catalog**: Store documents/results in UC volumes and tables
- **MLflow**: Track agent performance, log experiments
- **Batch Processing**: Process multiple reports in parallel
- **API Endpoints**: Expose agents as REST APIs
- **Fine-tuning**: Fine-tune models on user feedback data

### Additional Features
- Support for multiple document formats (Word, Excel)
- Historical tracking of quality metrics over time
- Export results to PDF/Excel reports
- AI-powered auto-matching of headlines to CSV columns
- Template library for common report types
- Integration with version control for report drafts
- Real-time collaboration (multiple users reviewing same report)

---

**Document Created**: January 2025  
**Last Updated**: January 2025  
**Author**: gb.burcea@gmail.com  
**Project**: agentic_quality_check  
**Status**: Streamlit Prototype - RAG + Multi-Agent
