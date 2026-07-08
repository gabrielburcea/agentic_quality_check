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
- **Extraction Process**: Parse CSV to extract column metadata only (not full data)
  - Column names
  - Data types (detected via pandas)
  - Roles (metric/filter/identifier - inferred from content)
  - Sample unique values for filter columns (e.g., ['Boys', 'Girls', 'Total'] for sex column)
  - Time grouping categories for date columns (e.g., ['202223', '202324'] for academic years)
- **Note**: Full CSV data is NOT loaded into memory; only metadata is stored for later agentic extraction

#### Tab 3: Analysis Configuration
- **Headline Selection**: Interactive selection of headlines and sub-headlines from the uploaded document
- **Agentic Table Extraction** (NEW):
  - When user selects a headline, LLM agent (Phi-3-Mini-4K-Instruct) analyzes:
    - Headline text
    - Associated paragraphs
    - CSV column metadata
  - Agent generates pandas code to extract a small, focused table (10-50 rows)
  - Example: For "Attainment by gender", extract only rows where `sex IN ['Boys', 'Girls', 'Total']` and relevant columns
  - UI displays **extracted table preview** (not column stats) so user can verify correct data was selected
- **Matching**: Map selected headlines to CSV files (supports multiple CSVs per session)
- **Agent Configuration**: Configure which checks to run (numerical, style, or both)

#### Tab 4: Results Dashboard
Two separate tables for quality check results:

##### Table 1: Numerical Accuracy Check
| Column | Description |
|--------|-------------|
| **Headline** | Selected headline/section from document |
| **Analyzed Text** | Actual text block analyzed by LLM |
| **Numbers Correct** | Pass status (Yes/No) - verifies numbers against extracted CSV table |
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
- **Structured Storage**: Parse CSV into pandas DataFrame (keep in memory only during extraction)
- **Column Metadata**: Extract column names, data types, roles (metric/filter/identifier), sample unique values
- **Agentic Extraction**: Use Phi-3-Mini-4K-Instruct LLM to generate pandas code that extracts small, focused tables from large CSVs

### RAG Flow
1. User selects headline → Retrieve relevant document chunks from vector store
2. **Agentic table extraction**: LLM analyzes headline + paragraphs + CSV metadata → generates pandas code → extracts small table (10-50 rows) → saves as JSON
3. Agent receives: headline text + surrounding context + **extracted table** (not full CSV)
4. LLM generates analysis using retrieved context + extracted table
5. Results stored with traceability back to source chunks

## Agent Capabilities

### Agent 1: Numerical Accuracy Agent
**Responsibilities:**
- Extract numerical values from report text
- Match numbers to corresponding **extracted CSV table** (not full CSV)
- Verify calculations (percentages, averages, differences)
- Identify discrepancies
- Generate correction suggestions

**RAG Integration:**
- Retrieves document context around numerical claims
- Works with **small extracted table** from Layer 1.5 (not querying full CSV)
- Compares claim vs table values
- Provides evidence trail (which table rows used)

**Example Checks:**
- "Mean average score 19.8 out of 25" → Verify against extracted table mean calculation
- "27% of pupils achieving full marks" → Verify percentage calculation
- "Disadvantaged pupils: 17.9 vs other pupils: 20.5" → Verify group comparisons from extracted table

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
   - **Table Extraction**: `microsoft/Phi-3-mini-4k-instruct` (3.8B params, CPU-friendly, for pandas code generation)
   - **Text Generation**: `TinyLlama-1.1B-Chat` or `Phi-1.5` (fits in Community Edition)
   - **Alternative**: DistilGPT-2 for faster CPU inference
3. **Vector Store**: FAISS or Chroma (local, lightweight)
4. **PDF Processing**: pdfplumber (character-level font analysis)
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
pdfplumber
pandas
numpy
```

### Data Flow
1. User uploads PDF → Extract text, chunk by headline, embed chunks → Store in FAISS
2. User uploads CSV → Parse into DataFrame, **extract metadata only** (column names, types, roles, samples)
3. User selects headlines → Retrieve relevant chunks + **trigger agentic table extraction**:
   - LLM (Phi-3-Mini) analyzes headline + paragraphs + CSV metadata
   - Generates pandas code to extract focused table (10-50 rows)
   - Execute code on CSV → save extracted table as JSON
   - Display extracted table preview in UI
4. Agents analyze (RAG-enhanced):
   - Numerical Agent: Retrieve context + use **extracted table** (not full CSV) + verify numbers
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
  - Extract text using pdfplumber (character-level font analysis)
  - Parse document structure (identify headlines/sections with hierarchy)
  - Display extracted headlines in Streamlit
  
- [ ] **Task 1.3**: Implement CSV processing
  - Upload CSV file widget
  - Parse CSV with pandas
  - **Extract metadata only** (column names, types, roles, sample unique values)
  - Display metadata summary (not full data)

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
  
- [ ] **Task 2.3**: Implement agentic table extraction (NEW)
  - Load Phi-3-Mini-4K-Instruct model
  - Design prompt template for pandas code generation
  - Input: headline + paragraphs + CSV metadata
  - Output: pandas code → execute → save extracted table JSON
  - Display extracted table preview in UI

### Phase 3: Agent Development
**Goal**: Implement three specialized agents

- [ ] **Task 3.1**: Numerical Accuracy Agent
  - Load TinyLlama or Phi-1.5 model
  - Design prompt template for numerical verification
  - Implement number extraction from text
  - Work with **extracted tables** (not full CSV queries)
  - Create verification function (claim vs extracted table values)
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
  - Pass context + **extracted table** (not full CSV) to agents
  - Combine agent outputs into structured results

### Phase 5: UI/UX Implementation
**Goal**: Build interactive Streamlit interface

- [ ] **Task 5.1**: Multi-tab layout
  - Tab 1: Document Upload
  - Tab 2: CSV Upload (with metadata display)
  - Tab 3: Analysis Configuration (with extracted table preview)
  - Tab 4: Results Dashboard
  
- [ ] **Task 5.2**: Analysis Configuration UI
  - Display extracted headlines as checkboxes
  - Implement headline → CSV file mapping (support multiple CSVs)
  - Trigger agentic table extraction on headline selection
  - Display **extracted table preview** (not column stats)
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
  - Verify numerical accuracy checks with extracted tables
  - Verify style quality checks
  - Measure end-to-end latency (including table extraction)
  
- [ ] **Task 6.2**: Model optimization
  - Test different HuggingFace models (speed vs quality)
  - Optimize Phi-3-Mini inference (CPU-friendly settings)
  - Implement model caching
  - Optimize chunk size for RAG
  - Tune retrieval parameters (top-k)
  
- [ ] **Task 6.3**: Error handling & edge cases
  - Malformed PDFs
  - Missing CSV columns in extracted tables
  - Ambiguous headline matching
  - LLM-generated pandas code errors (syntax, runtime)
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

**Table Extraction Model** (NEW):
- `microsoft/Phi-3-mini-4k-instruct` - 3.8B params, CPU-friendly, strong code generation
- Purpose: Generate pandas filtering code from headline + CSV metadata

**Text Generation Models** (for agents):
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0` - 1.1B params, optimized for chat
- `microsoft/phi-1_5` - 1.3B params, strong reasoning for size
- `distilgpt2` - 82M params, very fast but lower quality

**Model Selection Criteria**:
- Memory: Must fit in 15GB RAM (Community Edition)
- Speed: CPU-only inference, need <5s per analysis
- Quality: Balance between speed and accuracy

### Prompt Engineering

- **Table Extraction Prompt Template** (NEW):
  ```
  You are a data extraction agent.
  
  Given:
   - Headline: "{headline_text}"
   - Paragraph: "{paragraph_text}"
   - CSV columns: {column_metadata}
  
  Task: Generate pandas code to extract a small, relevant table (10-50 rows).
  Focus on filtering by values mentioned in the headline/paragraph.
  
  Example output:
    df[df['sex'].isin(['Boys', 'Girls', 'Total'])]
      .groupby(['sex', 'time_period'])
      .agg({'score_average': 'mean'})
  
  Generate ONLY the pandas code, no explanation.
  ```

- **Numerical Agent Prompt Template**:
  ```
  You are verifying numerical claims in a statistical report.
  
  Document Context: {retrieved_context}
  Claim: {headline_text}
  Extracted Table: {extracted_table_json}
  
  Task: Extract numbers from the claim, find them in the extracted table, compare.
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
- **Table Extraction**: Phi-3-Mini generates pandas code, execute on CSV in-memory

### Error Handling
- Handle malformed PDFs (fallback to OCR if needed)
- Handle missing CSV columns in extracted tables (suggest alternatives)
- Handle ambiguous headline matching (present options to user)
- Handle LLM-generated code errors (syntax, runtime) with retries and validation
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
%pip install streamlit transformers sentence-transformers faiss-cpu pdfplumber langchain

# Run Streamlit app
!streamlit run /Workspace/Users/your-email/app.py --server.port 8501
```

#### Option 2: Local Development
**What Works:**
- Full control over environment
- Faster iteration during development
- Can use GPU if available
- Easy debugging

**Setup:**
```bash
pip install -r requirements.txt
streamlit run app.py
```

#### Option 3: Databricks Apps (Paid)
**What Works:**
- Direct deployment to Databricks workspace
- Integrated with Unity Catalog
- Authentication built-in
- Can share with team members

**Requirements:**
- Databricks workspace with Apps enabled
- Unity Catalog configured
- Appropriate permissions

---

## Success Criteria
1. **Accuracy**: Numerical verification catches >95% of errors in test reports
2. **Speed**: End-to-end analysis (with table extraction) completes in <30 seconds per headline
3. **Usability**: Non-technical users can upload, configure, and review results without assistance
4. **Self-Healing**: Agreement rate improves by >10% after 50 user feedback cycles
5. **Scalability**: System handles reports with 20+ headlines and CSVs with 5,000+ rows
