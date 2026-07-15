# Architecture Documentation

## Why LangChain + LangGraph for Your Project

### Why This Was Chosen

**LangChain**: Chosen as the foundation for building the RAG pipeline because it:
* **Abstracts complexity** — Provides pre-built components for document loading, text splitting, embeddings, and vector stores, reducing boilerplate code
* **Modular design** — Each component (loader, splitter, embedder, retriever) can be swapped independently, making it easy to experiment and optimize
* **Production-ready integrations** — Native support for FAISS (free) or Databricks Vector Search (enterprise), HuggingFace embeddings or Databricks Foundation Models, and common document formats
* **Chain composition** — Enables building complex workflows by chaining retrieval → context injection → LLM generation steps
* **Open-source & framework-agnostic** — Works with any LLM provider (OpenAI, HuggingFace, Databricks Foundation Models, local models) without vendor lock-in

**LangGraph**: Chosen for multi-agent orchestration because it:
* **Stateful workflows** — Maintains conversation state and intermediate results across multiple agent turns, crucial for iterative quality checking
* **Graph-based execution** — Agents are nodes, transitions are edges; enables conditional routing (e.g., "if quality check fails, route to refinement agent")
* **Cyclic flows** — Unlike linear chains, supports loops for iterative refinement (e.g., generate → check → refine → check again until pass)
* **Supervisor pattern** — Built-in support for a supervisor agent that delegates tasks to specialized worker agents (quality checker, document retriever, response generator)
* **Human-in-the-loop** — Easy to add approval/intervention points where the system pauses for user input before proceeding
* **Transparent execution** — Every agent's decision and tool call is logged, making it easy to debug and explain why the system took a particular path

### How They Fit Your Architecture

**Layer 1: Document Ingestion & Preprocessing (LangChain)**
* **Components**: Document loaders, text splitters, CSV metadata extractors
* **PDF Flow**: PDF files → `pdfplumber` (character-level font analysis) → Headlines with hierarchy + paragraphs
* **CSV Flow**: CSV files → `pandas` → Column metadata (name, type, role, unique values for filters)
* **Storage Options**:
  * **Free/Local**: Local filesystem, read directly from disk
  * **Databricks**: Unity Catalog Volumes (`/Volumes/catalog/schema/volume/`) for managed, governed storage with ACL controls
* **Output**: 
  * Headlines with full context (paragraphs)
  * CSV metadata (columns with roles: metric/filter/identifier)

**Layer 1.5: Agentic Table Extraction (NEW)**
* **Purpose**: Extract small, focused tables from huge CSVs (like government stats tables)
* **Components**:
  * **LLM**: Phi-3-Mini-4K-Instruct (3.8B params) — free, CPU-friendly, runs locally
  * **Input**: Headline text + paragraphs + CSV path + column metadata from Layer 1
  * **Process**: 
    1. LLM analyzes headline/paragraphs to understand what data is needed
    2. LLM generates pandas filtering code (e.g., `df[df['sex'].isin(['Boys', 'Girls'])].groupby(['sex', 'time_period']).mean()`)
    3. Execute pandas code on CSV → extract small table (10-50 rows)
    4. Save as JSON
  * **Output**: Extracted table JSON (filters applied, only relevant rows/columns)
* **Why This Layer**:
  * Full CSVs are too large (4,000+ rows) for agents to reason about
  * Pre-calculated stats (min/max/mean) are useless for verification
  * Government stats show filtered subsets — we replicate that approach
  * Generic: works across all 40-60 publications (no hardcoded logic)
* **Example**:
  * Headline: "Attainment by gender"
  * Paragraphs: "Girls scored 20.1, boys scored 19.5..."
  * CSV: 4,494 rows with columns [sex, time_period, score_average, ...]
  * Extracted table: 12 rows (3 genders × 4 years) with [sex, time_period, score_average]

**Layer 2: RAG Pipeline (LangChain + FAISS/Vector Search)**
* **Start**: Text chunks from Layer 1
* **Components**:
  * **Embeddings**: 
    * **Free**: `sentence-transformers` (via HuggingFace) — runs locally, all-MiniLM-L6-v2 model (384-dim vectors)
    * **Databricks**: Foundation Models API with `databricks-bge-large-en` (1024-dim vectors, optimized for enterprise scale)
  * **Vector Store**: 
    * **Free**: FAISS — in-memory index, fast but not persistent across sessions
    * **Databricks**: Vector Search — managed service with automatic sync from Delta tables, persistent indexes, and built-in access controls
  * **Retriever**: LangChain retriever wraps either FAISS or Databricks Vector Search, exposes unified `.get_relevant_documents(query)` API
* **Flow**: 
  1. User query → Embed query using same model (sentence-transformers or Databricks FM)
  2. Similarity search (FAISS `.search()` or Vector Search `.similarity_search()`) → Top-k most relevant chunks
  3. Chunks + metadata → Context for LLM
* **Stop**: Retrieved context (text chunks) passed to Layer 3
* **Key Detail**: This layer is **stateless** — each query is independent. LangGraph (Layer 3) adds state and multi-turn logic on top.

**Layer 3: Multi-Agent Orchestration (LangGraph)**
* **Components**: Supervisor agent, quality checker agent, retrieval agent, response generator agent
* **LLM Options**:
  * **Free**: HuggingFace models (e.g., `mistralai/Mistral-7B-Instruct-v0.2`) — runs locally via `transformers` library, requires GPU for reasonable speed
  * **Databricks**: Foundation Models API (DBRX Instruct, Llama 3.1, Mixtral) — serverless inference, pay-per-token, no infrastructure management
* **Flow**:
  1. **Supervisor** receives user question → decides which agent to invoke
  2. **Retrieval Agent** calls Layer 2 RAG pipeline → gets relevant context
  3. **Response Generator Agent** takes context + question + **extracted table from Layer 1.5** → generates answer
  4. **Quality Checker Agent** evaluates answer (factual accuracy, completeness, citation presence)
  5. **Conditional routing**: 
     * Pass → Return to user
     * Fail → Loop back to Response Generator with feedback
* **State Management**: LangGraph maintains the conversation history, retrieved documents, extracted tables, quality scores, and iteration count across the loop
* **Execution Environment**:
  * **Free/Local**: Run on local machine or free cloud compute (Google Colab, Kaggle)
  * **Databricks**: Run on Databricks cluster or serverless compute, integrate with Databricks Jobs for scheduling
* **Output**: Final validated answer with citations

**Layer 4: User Interface (Streamlit/Databricks Apps)**
* **Components**: Chat interface, document upload widget, agent execution logs, **extracted table preview**
* **UI Options**:
  * **Free**: Streamlit — Python-based web framework, run locally or deploy to Streamlit Cloud
  * **Databricks**: Databricks Apps — deploy directly to workspace, integrated with Unity Catalog for data access and authentication
* **Flow**: User input → LangGraph execution (Layer 3) → Display response + trace of agent decisions + **show extracted table**
* **Output**: Interactive web app where users can see which agents were invoked and why

---

## Complete Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                          AGENTIC RAG QUALITY CHECKER                           │
│                    (LangChain + LangGraph Multi-Agent System)                  │
└────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: DOCUMENT INGESTION & PREPROCESSING                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  PDF Files                          CSV Files                                   │
│      ↓                                  ↓                                        │
│  [pdfplumber Parser]              [pandas Parser]                               │
│  Character-level font              Column metadata extraction                   │
│      ↓                                  ↓                                        │
│  Headlines + Paragraphs            Metadata: {name, type, role, samples}        │
│  (H1/H2/H3 hierarchy)              (metric/filter/identifier)                   │
│                                                                                  │
│  Storage:                                                                        │
│   • Free: Local filesystem                                                      │
│   • Databricks: Unity Catalog Volumes (/Volumes/catalog/schema/volume/)        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1.5: AGENTIC TABLE EXTRACTION (NEW)                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ INPUTS (from Layer 1)                                                     │  │
│  │  • Headline text: "Attainment by gender"                                 │  │
│  │  • Paragraphs: "Girls scored 20.1, boys scored 19.5..."                 │  │
│  │  • CSV path: /path/to/data.csv                                           │  │
│  │  • Column metadata: [{name: 'sex', role: 'filter'}, ...]                │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                     ↓                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ LLM-POWERED EXTRACTION                                                    │  │
│  │                                                                            │  │
│  │  Model: Phi-3-Mini-4K-Instruct (3.8B params)                             │  │
│  │   • Free, runs on CPU                                                    │  │
│  │   • 4K context window (enough for headline + metadata)                   │  │
│  │   • Optimized for code generation                                        │  │
│  │                                                                            │  │
│  │  Prompt Template:                                                         │  │
│  │  ┌────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ You are a data extraction agent.                                   │  │  │
│  │  │ Given:                                                              │  │  │
│  │  │  - Headline: "Attainment by gender"                                │  │  │
│  │  │  - Paragraph: "Girls scored 20.1..."                               │  │  │
│  │  │  - CSV columns: ['sex', 'time_period', 'score_average', ...]      │  │  │
│  │  │                                                                     │  │  │
│  │  │ Generate pandas code to extract a small relevant table.            │  │  │
│  │  │ Example output:                                                    │  │  │
│  │  │   df[df['sex'].isin(['Boys', 'Girls', 'Total'])]                  │  │  │
│  │  │     .groupby(['sex', 'time_period'])                               │  │  │
│  │  │     .agg({'score_average': 'mean'})                                │  │  │
│  │  └────────────────────────────────────────────────────────────────────┘  │  │
│  │           ↓                                                               │  │
│  │  LLM generates pandas code                                                │  │
│  │           ↓                                                               │  │
│  │  Execute code on CSV → Extract small table (10-50 rows)                  │  │
│  │           ↓                                                               │  │
│  │  Save as JSON with metadata                                               │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                     ↓                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ OUTPUT                                                                    │  │
│  │  {                                                                        │  │
│  │    "headline_id": "h5",                                                  │  │
│  │    "extracted_table": [                                                  │  │
│  │      {"sex": "Boys", "time_period": "202223", "score_average": 19.5},   │  │
│  │      {"sex": "Girls", "time_period": "202223", "score_average": 20.1},  │  │
│  │      {"sex": "Total", "time_period": "202223", "score_average": 19.8},  │  │
│  │      ...                                                                  │  │
│  │    ],                                                                     │  │
│  │    "filters_applied": {"sex": ["Boys", "Girls", "Total"]},              │  │
│  │    "columns_selected": ["sex", "time_period", "score_average"]          │  │
│  │  }                                                                        │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  Why This Works:                                                                │
│   • Full CSVs are too large (4,000+ rows) for agents to reason about          │
│   • Pre-calculated stats (min/max/mean) are useless for verification          │
│   • Government stats show filtered subsets — we replicate that                 │
│   • Generic approach works across all 40-60 publications                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: RAG PIPELINE (Embedding + Vector Store + Retrieval)                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ EMBEDDING GENERATION                                                      │  │
│  │                                                                            │  │
│  │  Free Option:                    Databricks Option:                       │  │
│  │  ┌─────────────────────────┐    ┌────────────────────────────────┐       │  │
│  │  │ sentence-transformers   │    │ Databricks Foundation Models  │       │  │
│  │  │ all-MiniLM-L6-v2        │    │ databricks-bge-large-en       │       │  │
│  │  │ 384-dim vectors         │    │ 1024-dim vectors              │       │  │
│  │  │ Runs locally            │    │ Serverless API                │       │  │
│  │  └─────────────────────────┘    └────────────────────────────────┘       │  │
│  │           ↓                                    ↓                           │  │
│  │      Vector embeddings (numpy arrays)                                     │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                     ↓                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ VECTOR INDEXING & STORAGE                                                 │  │
│  │                                                                            │  │
│  │  Free Option:                    Databricks Option:                       │  │
│  │  ┌─────────────────────────┐    ┌────────────────────────────────┐       │  │
│  │  │ FAISS                   │    │ Databricks Vector Search       │       │  │
│  │  │ In-memory index         │    │ Managed service                │       │  │
│  │  │ Fast, not persistent    │    │ Auto-sync from Delta tables    │       │  │
│  │  │ faiss.IndexFlatL2       │    │ Persistent, scalable           │       │  │
│  │  └─────────────────────────┘    └────────────────────────────────┘       │  │
│  │           ↓                                    ↓                           │  │
│  │      Indexed vectors ready for similarity search                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                     ↓                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ RETRIEVAL (Query → Top-K Relevant Documents)                              │  │
│  │                                                                            │  │
│  │  User Query (string)                                                      │  │
│  │       ↓                                                                    │  │
│  │  Embed query (same model as documents)                                    │  │
│  │       ↓                                                                    │  │
│  │  Similarity search (cosine similarity / L2 distance)                      │  │
│  │       ↓                                                                    │  │
│  │  Top-5 chunks: [(chunk_text, metadata, score), ...]                      │  │
│  │  Metadata: {source_file, page_num, chunk_idx}                            │  │
│  │                                                                            │  │
│  │  LangChain Retriever API: .get_relevant_documents(query)                 │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  OUTPUT: List[Document] → Passed to LangGraph agents                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: MULTI-AGENT ORCHESTRATION (LangGraph)                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐        │
│  │                        SUPERVISOR AGENT                             │        │
│  │  (Routes user query to appropriate worker agent)                   │        │
│  └────────────────────────────────────────────────────────────────────┘        │
│                        ↓             ↓             ↓                            │
│         ┌──────────────┴─────────────┴─────────────┴──────────────┐            │
│         ↓                            ↓                             ↓            │
│  ┌─────────────────┐      ┌─────────────────────┐      ┌────────────────────┐ │
│  │ RETRIEVAL       │      │ RESPONSE GENERATOR  │      │ QUALITY CHECKER    │ │
│  │ AGENT           │      │ AGENT               │      │ AGENT              │ │
│  │                 │      │                     │      │                    │ │
│  │ Calls Layer 2   │──→   │ Context + Question  │──→   │ Evaluates:        │ │
│  │ RAG pipeline    │      │ + Extracted Table   │      │ • Accuracy        │ │
│  │                 │      │        ↓            │      │ • Completeness    │ │
│  │ Returns docs    │      │ Generate answer     │      │ • Citations       │ │
│  └─────────────────┘      └─────────────────────┘      └────────────────────┘ │
│                                     ↑                             ↓             │
│                                     │                      Pass / Fail?         │
│                                     │                             ↓             │
│                                     └─────────────────────────────┘             │
│                                     (Loop back with feedback if fail)           │
│                                                                                  │
│  LLM Options:                                                                   │
│   • Free: HuggingFace models (Mistral-7B, Llama-2-7B) — local inference        │
│   • Databricks: Foundation Models API (DBRX, Llama 3.1, Mixtral) — serverless  │
│                                                                                  │
│  State Management (LangGraph):                                                  │
│   • Conversation history                                                        │
│   • Retrieved documents                                                         │
│   • Extracted tables (from Layer 1.5)                                          │
│   • Quality scores per iteration                                                │
│   • Loop counter (max 3 refinement attempts)                                   │
│                                                                                  │
│  OUTPUT: Final validated answer with citations                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: USER INTERFACE                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Free Option:                           Databricks Option:                      │
│  ┌───────────────────────────────┐     ┌──────────────────────────────────┐    │
│  │ Streamlit                     │     │ Databricks Apps                  │    │
│  │  • Chat interface             │     │  • Integrated authentication     │    │
│  │  • Document upload            │     │  • Direct Unity Catalog access   │    │
│  │  • Extracted table preview    │     │  • Native notebook integration   │    │
│  │  • Agent execution trace      │     │  • One-click deployment          │    │
│  │  • Local or Streamlit Cloud   │     │  • Workspace-native experience   │    │
│  └───────────────────────────────┘     └──────────────────────────────────┘    │
│                                                                                  │
│  Key UI Components:                                                              │
│   • Document upload widget (PDF + CSV)                                          │
│   • Headline selection tree                                                     │
│   • Extracted table preview (from Layer 1.5)                                   │
│   • Chat interface for questions                                                │
│   • Agent decision trace (which agents ran, why)                                │
│   • Citation links back to source documents                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---



---

## Detailed End-to-End Flow: "Attainment by Gender" Example

This section demonstrates how the complete pipeline processes a specific headline from PDF through to a pivoted table for verification.

### Example Headline: "Attainment by gender"

**PDF Content (Page 3)**:
```
Headline: Attainment by gender

Paragraphs:
"Of eligible pupils in year 4, a slightly larger proportion of girls took the check than 
boys (97% and 95% respectively). This was due to a larger proportion of boys being 
recorded as not taking the check due to working below the level of the assessment.

Boys performed slightly better than girls in the check, even when factoring in the 
difference in the proportion of pupils taking the check, however the difference is 
relatively small. Of pupils who took the check, the average score for girls was 19.6 
while the average score for boys was 20.0.

The most common score in the check was 25 (full marks) for both boys and girls. 
The percentage of eligible pupils who achieved this score was 25% for girls and 28% 
for boys."
```

### Phase 1: PDF Parsing (Layer 1 - Already Implemented)

**Input**: PDF file → Page 3

**Process**: 
* pdfplumber analyzes character-level fonts to identify headlines
* Extracts headline hierarchy (H1/H2/H3)
* Associates paragraphs with each headline

**Output** (Stored in mapping JSON):
```json
{
  "headline_text": "Attainment by gender",
  "headline_page": 3,
  "paragraphs": [
    "Of eligible pupils in year 4, a slightly larger proportion of girls took the check..."
  ]
}
```

### Phase 2: CSV Parsing (Layer 1 - Already Implemented)

**Input**: `mtc_national_pupil_characteristics_2022_to_2025.csv` (4,494 rows × 33 columns)

**Process**:
* pandas reads CSV structure
* csv_handler.py classifies columns by role:
  * **Filter columns** (dimension): sex, time_period, geographic_level, etc.
  * **Metric columns** (measures): mtc_score_average, completed_check_pupil_percent, etc.
* Extracts sample values for filter columns

**Output** (CSV Metadata):
```json
{
  "filename": "mtc_national_pupil_characteristics_2022_to_2025.csv",
  "row_count": 4494,
  "column_count": 33,
  "columns": [
    {
      "name": "sex",
      "type": "object",
      "role": "filter",
      "sample_values": ["Boys", "Girls", "Total"]
    },
    {
      "name": "time_period",
      "type": "object",
      "role": "filter",
      "sample_values": ["202122", "202223", "202324", "202425"]
    },
    {
      "name": "mtc_score_average",
      "type": "float64",
      "role": "metric"
    },
    {
      "name": "completed_check_pupil_percent",
      "type": "float64",
      "role": "metric"
    },
    {
      "name": "working_below_pupil_percent",
      "type": "float64",
      "role": "metric"
    }
  ]
}
```

### Phase 3: User Mapping (Layer 3 - Already Implemented)

**Input**: Headline + Available CSV files

**User Action**: In Streamlit UI (Tab 3), user selects which CSV file(s) contain data for this headline

**Output** (Mapping JSON saved to `/tmp/mappings_volume/` or UC Volume):
```json
{
  "pdf_filename": "Multiplication_check.pdf",
  "created_at": "2025-01-11T22:12:57",
  "mappings": [
    {
      "headline_text": "Attainment by gender",
      "headline_page": 3,
      "paragraphs": ["Of eligible pupils in year 4..."],
      "csv_files": ["mtc_national_pupil_characteristics_2022_to_2025.csv"]
    }
  ]
}
```

### Phase 4: Paragraph Analysis (Layer 4 - Next Implementation Phase)

**Input**: Headline text + Paragraphs + CSV metadata

**Agent Analysis** (LLM-powered reasoning):

**Phrase-by-Phrase Extraction**:

1. **Phrase**: "girls took the check than boys (97% and 95% respectively)"
   * **Filter Hint**: `sex` IN ('Boys', 'Girls')
   * **Metric Hint**: `completed_check_pupil_percent` 
   * **Values Mentioned**: 97% (Girls), 95% (Boys)

2. **Phrase**: "average score for girls was 19.6 while the average score for boys was 20.0"
   * **Filter Hint**: `sex` IN ('Boys', 'Girls')
   * **Metric Hint**: `mtc_score_average`
   * **Values Mentioned**: 19.6 (Girls), 20.0 (Boys)

3. **Phrase**: "working below the level of the assessment"
   * **Metric Hint**: `working_below_pupil_percent`

4. **Phrase**: "percentage of eligible pupils who achieved this score was 25% for girls and 28% for boys"
   * **Filter Hint**: `sex` IN ('Boys', 'Girls')
   * **Metric Hint**: Score distribution metric (e.g., `mtc_score_25`)
   * **Values Mentioned**: 25% (Girls), 28% (Boys)

**Agent Reasoning Summary**:
```json
{
  "filters_needed": {
    "sex": ["Boys", "Girls"],
    "geographic_level": "National",
    "time_period": ["202122", "202223", "202324", "202425"]
  },
  "metrics_needed": [
    "mtc_score_average",
    "completed_check_pupil_percent",
    "working_below_pupil_percent"
  ],
  "pivot_structure": {
    "rows": "metrics",
    "columns": ["time_period", "sex"]
  }
}
```

### Phase 5: Query Construction & Filtering

**SQL Query** (Generated by agent):
```sql
SELECT 
  time_period,
  sex,
  mtc_score_average,
  completed_check_pupil_percent,
  working_below_pupil_percent
FROM mtc_national_pupil_characteristics_2022_to_2025
WHERE sex IN ('Boys', 'Girls')
  AND geographic_level = 'National'
```

**Filtered Result** (Long format - 8 rows):
```
time_period | sex   | mtc_score_average | completed_check_pupil_percent | working_below_pupil_percent
202122      | Boys  | 20.0              | 95                            | 3
202122      | Girls | 19.6              | 97                            | 2
202223      | Boys  | 20.4              | 95                            | 4
202223      | Girls | 19.9              | 97                            | 2
202324      | Boys  | 20.9              | 95                            | 4
202324      | Girls | 20.4              | 97                            | 2
202425      | Boys  | 21.2              | 95                            | ...
202425      | Girls | 20.7              | 97                            | ...
```

### Phase 6: Pivot Transformation (pandas)

**Python Code** (Generated by agent):
```python
import pandas as pd

# Read filtered data
df = pd.read_csv('filtered_data.csv')

# Unpivot metrics into long format first
df_long = df.melt(
    id_vars=['time_period', 'sex'],
    value_vars=['mtc_score_average', 'completed_check_pupil_percent', 'working_below_pupil_percent'],
    var_name='metric',
    value_name='value'
)

# Pivot: rows=metric, columns=[time_period, sex]
df_pivot = df_long.pivot_table(
    index='metric',
    columns=['time_period', 'sex'],
    values='value',
    aggfunc='first'
)

# Rename metric labels for readability
df_pivot.index = df_pivot.index.map({
    'mtc_score_average': 'Average attainment score',
    'completed_check_pupil_percent': 'Pupils who took check %',
    'working_below_pupil_percent': 'Below expectation %'
})
```

### Phase 7: Final Pivoted Table (Output)

**Result** (Wide format - matches PDF table structure):
```
                                2021/22       2022/23       2023/24       2024/25
                              Boys  Girls   Boys  Girls   Boys  Girls   Boys  Girls
────────────────────────────────────────────────────────────────────────────────────
Average attainment score      20.0   19.6   20.4   19.9   20.9   20.4   21.2   20.7
Pupils who took check %       95     97     95     97     95     97     95     97
Below expectation %           3      2      4      2      4      2      ...    ...
```

### Key Insight: How Each Component Contributes

**Headline Text**: "Attainment by gender"
* Tells agent: Primary grouping dimension is SEX (boys vs girls)

**Paragraph Phrases**:
* "girls" and "boys" → `sex` filter values
* "took the check" + percentages → `completed_check_pupil_percent` metric
* "average score" + numbers → `mtc_score_average` metric
* "working below" → `working_below_pupil_percent` metric
* "in 2022" → time reference (but need all years for trend analysis)

**CSV Metadata (filter columns)**:
* Tells agent: Available filters are `sex`, `time_period`, `geographic_level`, etc.
* Provides valid values: `sex` IN ('Boys', 'Girls', 'Total')

**CSV Metadata (metric columns)**:
* Tells agent: Available metrics match paragraph hints
* `mtc_score_average` ← "average score"
* `completed_check_pupil_percent` ← "took the check"
* `working_below_pupil_percent` ← "working below"

**Mapped CSV File**:
* Tells agent: Query this specific CSV (`mtc_national_pupil_characteristics_2022_to_2025.csv`), not others

### Complete Flow Summary

```
PDF Headline + Paragraphs
        ↓
    [Parse hints: filters, metrics, dimensions]
        ↓
CSV Metadata (from mapping)
        ↓
    [Match hints to actual column names]
        ↓
Query CSV with filters
        ↓
    [Get long-format data]
        ↓
Pivot transformation
        ↓
    [metrics as rows, time×sex as columns]
        ↓
Compare pivoted table with PDF values
        ↓
    [Verification: Pass/Fail with explanations]
```

**Next Implementation Phase**: Build the agent that performs Phase 4-7 (paragraph analysis → query construction → pivot transformation → verification).


## Technical Stack Summary

### Free/Open-Source Path
* **PDF Parsing**: pdfplumber (character-level font analysis)
* **CSV Parsing**: pandas (metadata extraction)
* **Table Extraction**: Phi-3-Mini-4K-Instruct (3.8B params, CPU-friendly)
* **Embeddings**: sentence-transformers (all-MiniLM-L6-v2, 384-dim)
* **Vector Store**: FAISS (in-memory, local)
* **Agents**: HuggingFace models (Mistral-7B, Llama-2-7B)
* **Orchestration**: LangGraph
* **UI**: Streamlit

### Databricks Path
* **PDF Parsing**: pdfplumber (same as free path)
* **CSV Parsing**: pandas (same as free path)
* **Table Extraction**: Phi-3-Mini-4K-Instruct (same as free path)
* **Embeddings**: Databricks Foundation Models API (databricks-bge-large-en, 1024-dim)
* **Vector Store**: Databricks Vector Search (managed, persistent)
* **Agents**: Databricks Foundation Models API (DBRX, Llama 3.1, Mixtral)
* **Orchestration**: LangGraph (same as free path)
* **UI**: Databricks Apps

### Hybrid Approach (Recommended)
* Use **free models** for development/testing
* Switch to **Databricks** for production via config toggle
* Best of both worlds: cost-effective development, scalable production
