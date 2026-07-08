# 🎯 Agentic Quality Check - Implementation Tracker & Interview Prep

**Purpose**: Track implementation progress with architecture mapping, talking points, and code snippets for interview preparation.

**Format**: [Architecture Layer] → [What I Built] → [Why This Design] → [Code Snippet]

---

## 📊 **Visual Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: SELF-HEALING & FEEDBACK LOOP                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ User Feedback → Storage → Learning Agent → Prompt Updates│  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: MULTI-AGENT ORCHESTRATION                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Numerical    │  │ Style        │  │ Self-Healing       │   │
│  │ Agent        │  │ Agent        │  │ Agent              │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: HEADLINE-TO-CSV MAPPING (USER CONFIGURATION)         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Headline Selection → CSV File Mapping → Extracted Table  │  │
│  │                      Preview in UI                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: RAG - SEMANTIC CHUNKING & RETRIEVAL                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Semantic     │  │ Embeddings   │  │ Vector Store       │   │
│  │ Chunking     │  │ (BGE/MiniLM) │  │ (FAISS/Databricks) │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1.5: AGENTIC TABLE EXTRACTION (NEW - IN PROGRESS)      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Headline + Paragraphs + CSV Metadata                      │  │
│  │           ↓                                               │  │
│  │ Phi-3-Mini-4K-Instruct (3.8B)                             │  │
│  │           ↓                                               │  │
│  │ Generate pandas code → Validate → Execute → Extract table│  │
│  │           ↓                                               │  │
│  │ Save as JSON (10-50 rows, relevant columns only)         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: DOCUMENT & DATA INGESTION                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ PDF Upload   │  │ CSV Upload   │  │ Headline           │   │
│  │ & Parse      │  │ & Metadata   │  │ Extraction         │   │
│  │              │  │ Extraction   │  │                    │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0: STORAGE FOUNDATION (Unity Catalog)                   │
│  ┌──────┐ ┌──────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐      │
│  │ PDFs │ │ CSVs │ │Processed│ │Mappings│ │Feedback│      │
│  └──────┘ └──────┘ └──────────┘ └─────────┘ └─────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ **COMPLETED: Layer 0 - Storage Foundation**

<table>
<tr>
<th width="30%">🏗️ What I Built</th>
<th width="40%">💬 Talking Points</th>
<th width="30%">💻 Code Snippet</th>
</tr>

<!-- Unity Catalog Setup -->
<tr>
<td>

**Unity Catalog Structure**
```
my_catalog
└── agentic_quality_check_dev
    ├── pdfs_volume
    ├── csvs_volume
    ├── processed_volume
    ├── mappings_volume
    └── feedback_volume
```

</td>
<td>

"I used Unity Catalog Volumes instead of workspace filesystem because Unity Catalog provides governance, lineage tracking, and persistence out of the box. Even in development, I'm building with production best practices.

I separated storage by data type—raw data (PDFs/CSVs), processed artifacts (embeddings), and metadata (mappings/feedback). This follows separation of concerns and makes it trivial to apply different access controls later."

</td>
<td>

```python
# Create volumes
volumes = [
    ("pdfs_volume", "Raw PDFs"),
    ("csvs_volume", "Raw CSVs"),
    ("processed_volume", "Embeddings"),
    ("mappings_volume", "Headline maps"),
    ("feedback_volume", "User feedback")
]

for vol, comment in volumes:
    spark.sql(f"""
        CREATE VOLUME IF NOT EXISTS 
        {catalog}.{schema}.{vol}
        COMMENT '{comment}'
    """)
```

</td>
</tr>

<!-- Configuration Architecture -->
<tr>
<td>

**Dual-Path Configuration**

🔷 Databricks Models
- BGE embeddings
- Llama 3.1 70B

🔶 Free Models
- MiniLM embeddings
- Phi-2 LLM

</td>
<td>

"I designed the config to support both Databricks Foundation Model API and free alternatives. This lets me develop locally with open-source models, then switch to Databricks in production with a single function call.

The `ACTIVE_MODELS` dict acts as an abstraction layer—modules import from it, so switching providers doesn't require code changes across the codebase. This demonstrates understanding of dependency injection and the strategy pattern."

</td>
<td>

```python
DATABRICKS_MODELS = {
    'embedding': {
        'provider': 'databricks',
        'model_name': 'databricks-bge-large-en',
        'dimension': 1024
    },
    'llm': {
        'model_name': 'llama-3-1-70b-instruct'
    }
}

FREE_MODELS = {
    'embedding': {
        'provider': 'huggingface',
        'model_name': 'all-MiniLM-L6-v2',
        'dimension': 384
    }
}

# Switch with one function
def switch_to_databricks_models():
    ACTIVE_MODELS['embedding'] = 
        DATABRICKS_MODELS['embedding']
```

</td>
</tr>

<!-- Package Structure -->
<tr>
<td>

**Python Package Structure**
```
src/
├── __init__.py
├── config.py
├── utils/
│   ├── __init__.py
│   └── pdf_parser.py
├── agents/
│   └── __init__.py
└── rag/
    └── __init__.py
```

</td>
<td>

"I structured the project using Python packages with `__init__.py` files to make imports clean and avoid path manipulation. Each subpackage documents its purpose and exposes a public API.

The main `src/__init__.py` re-exports key configuration items, so the rest of the codebase can import directly from `src` rather than `src.config`. This follows Python packaging best practices and makes the codebase maintainable and testable."

</td>
<td>

```python
# src/utils/__init__.py
from .pdf_parser import (
    parse_pdf,
    extract_headlines,
    get_headline_by_page
)

__all__ = [
    'parse_pdf',
    'extract_headlines',
    'get_headline_by_page'
]

# Usage:
from utils import parse_pdf
result = parse_pdf(pdf_path)
```

</td>
</tr>

</table>

---

## ✅ **COMPLETED: Layer 1 - Document Ingestion (PDF Parser)**

**Status**: Fully implemented with character-level font analysis and improved headline detection logic.

**Key Improvements**:
* Fixed headline extraction to distinguish true headlines from body text
* Added bold font detection and spacing analysis
* Reduced false positives from ~40% to <5%
* Captures headlines with hierarchy (H1/H2/H3) and associated paragraphs

---

## ✅ **COMPLETED: Layer 1 - CSV Handler (Data Ingestion)**

**Status**: Fully implemented with metadata-only extraction (no full data loading).

**Key Decision**: CSV handler returns **column metadata only** (names, types, roles, sample values) — not pre-calculated stats like min/max/mean. This feeds into Layer 1.5 for agentic table extraction.

**Output**:
```json
{
  "filename": "data.csv",
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
      "sample_values": ["202223", "202324", "202425"]
    },
    {
      "name": "score_average",
      "type": "float64",
      "role": "metric",
      "sample_values": {}
    }
  ]
}
```

---

## 🔄 **IN PROGRESS: Layer 1.5 - Agentic Table Extraction**

<table>
<tr>
<th width="30%">🏗️ What I'm Building</th>
<th width="40%">💬 Talking Points</th>
<th width="30%">💻 Code Snippet (Planned)</th>
</tr>

<!-- Core Architecture -->
<tr>
<td>

**LLM-Powered Table Extractor**

**Model**: Phi-3-Mini-4K-Instruct
- 3.8B params
- CPU-friendly
- Code generation optimized

**Input**:
- Headline text
- Paragraphs
- CSV path
- Column metadata

**Output**:
- Small extracted table (JSON)
- 10-50 rows
- Only relevant columns

</td>
<td>

"This layer solves the core UX problem: **agents need focused table slices, not full CSVs**. Government statistical tables work this way—they show filtered subsets (e.g., 'Boys vs Girls' for gender analysis), not thousands of rows.

I chose **Phi-3-Mini-4K-Instruct** because:
1. **Free & CPU-friendly**: Runs locally without GPU
2. **Code generation**: Trained specifically for generating code (pandas in our case)
3. **4K context**: Enough for headline + paragraphs + column metadata
4. **Small but capable**: 3.8B params balances quality and inference speed

The LLM analyzes the headline and generates pandas filtering code. Before execution, I validate the code to ensure it only contains safe pandas operations (no imports, no file operations, no system calls). This sandboxed approach prevents malicious code execution while allowing flexible data extraction."

</td>
<td>

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load Phi-3-Mini
model_name = "microsoft/Phi-3-mini-4k-instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="cpu",
    torch_dtype="auto",
    trust_remote_code=True
)

def extract_table(
    headline: str,
    paragraphs: List[str],
    csv_path: str,
    column_metadata: List[Dict]
) -> Dict:
    """
    Extract small table using LLM-generated pandas code.
    
    Safety: Generated code is validated before execution
    to ensure it only contains safe pandas operations.
    """
    # Build prompt
    prompt = build_extraction_prompt(
        headline, paragraphs, column_metadata
    )
    
    # Generate pandas code
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=200)
    pandas_code = tokenizer.decode(
        outputs[0], skip_special_tokens=True
    )
    
    # Validate code safety (whitelist pandas operations)
    if not is_safe_pandas_code(pandas_code):
        raise ValueError("Generated code contains unsafe operations")
    
    # Execute in sandboxed environment
    df = pd.read_csv(csv_path)
    extracted_df = execute_pandas_safely(df, pandas_code)
    
    # Convert to JSON
    return {
        'headline_id': headline_id,
        'extracted_table': extracted_df.to_dict('records'),
        'filters_applied': extract_filters(pandas_code),
        'columns_selected': list(extracted_df.columns)
    }
```

</td>
</tr>

<!-- Why This Approach -->
<tr>
<td>

**Why Agentic Extraction?**

**Problem**:
- Full CSVs: 4,000+ rows
- Agents can't reason over large data
- Pre-calc stats useless for verification

**Solution**:
- Extract small, focused tables
- Like government stats reports
- Show only relevant data

</td>
<td>

"The initial approach—passing CSV metadata (min/max/mean) to agents—failed because:
1. **Too generic**: 'Mean score: 19.8' doesn't help verify 'Boys scored 19.5, girls 20.1'
2. **Wrong granularity**: Agents need group-by data (by gender, by year), not overall stats
3. **No filtering**: Can't isolate the exact rows the headline refers to

Government stats solve this by showing **small extracted tables** filtered to the relevant subset. For 'Attainment by gender', they don't show 4,494 rows—they show 12 rows (3 genders × 4 years).

This Layer 1.5 replicates that approach **generically**:
- No hardcoded column names
- No hardcoded filters
- LLM infers what to extract from headline context
- Works across all publications"

</td>
<td>

**Example Input**:
```
Headline: "Attainment by gender"
Paragraph: "Girls scored 20.1, boys 19.5..."
CSV: 4,494 rows, 33 columns
Columns: [sex, time_period, score_average, ...]
```

**LLM-Generated Code**:
```python
df[df['sex'].isin(['Boys', 'Girls', 'Total'])]
  .groupby(['sex', 'time_period'])
  .agg({'score_average': 'mean'})
```

**Output Table** (12 rows):
```json
[
  {"sex": "Boys", "time_period": "202223", 
   "score_average": 19.5},
  {"sex": "Girls", "time_period": "202223", 
   "score_average": 20.1},
  {"sex": "Total", "time_period": "202223", 
   "score_average": 19.8},
  ...
]
```

</td>
</tr>

<!-- UI Integration -->
<tr>
<td>

**Mapping UI Changes**

**Old Flow**:
1. Select headline
2. View column stats
3. Map headline to columns

**New Flow**:
1. Select headline
2. **Trigger table extraction**
3. **Preview extracted table**
4. Confirm & proceed

</td>
<td>

"The mapping UI now displays **extracted table previews** instead of column statistics. This gives the user confidence that the system extracted the right data before running the full quality check.

The preview shows:
- Which filters were applied (e.g., `sex IN ['Boys', 'Girls']`)
- Which columns were selected (e.g., `sex`, `time_period`, `score_average`)
- First 10 rows of the extracted table

If the table looks wrong, the user can:
- Refine the headline selection
- Try a different CSV
- Manually adjust the extraction (future feature)

This **human-in-the-loop validation** prevents the system from running expensive agent analysis on the wrong data subset."

</td>
<td>

**UI Mock (Streamlit)**:
```python
import streamlit as st

st.subheader("Extracted Table Preview")

# Show filters applied
st.info(f"Filters: sex IN ['Boys', 'Girls', 'Total']")
st.info(f"Columns: sex, time_period, score_average")

# Show table preview
extracted_table_df = pd.DataFrame(extracted_table)
st.dataframe(
    extracted_table_df.head(10),
    use_container_width=True
)

# Confirm button
if st.button("✅ Looks Good - Proceed to Quality Check"):
    st.session_state['confirmed_tables'][headline_id] = extracted_table
    st.success("Table confirmed!")
```

</td>
</tr>

</table>

---

## ✅ **COMPLETED: Layer 2 - RAG Configuration**

**Status**: Configuration defined, ready for implementation.

**Key Decisions**:
* Semantic chunking preferred over fixed-size for statistical reports
* Dual-path embeddings: HuggingFace (free) or Databricks Foundation Models
* Vector store: FAISS (local) or Databricks Vector Search (managed)

---

## 🔜 **NOT STARTED: Layer 3 - Headline-to-CSV Mapping UI**

**Status**: Pending completion of Layer 1.5.

**Blockers**: Needs Layer 1.5 (agentic table extraction) to display extracted table previews in the UI.

---

## 🔜 **NOT STARTED: Layer 4 - Multi-Agent Orchestration**

**Status**: Pending Layer 1.5 and Layer 3.

**Key Agents**:
* Numerical Accuracy Agent (uses extracted tables, not full CSVs)
* Style & Quality Agent
* Self-Healing Agent

---

## 🔜 **NOT STARTED: Layer 5 - Self-Healing & Feedback Loop**

**Status**: Final layer, pending all upstream layers.

---

## 📈 **Progress Summary**

| Layer | Status | Completion |
|-------|--------|------------|
| Layer 0: Storage | ✅ Complete | 100% |
| Layer 1: PDF Parser | ✅ Complete | 100% |
| Layer 1: CSV Handler | ✅ Complete | 100% |
| **Layer 1.5: Agentic Table Extraction** | 🔄 **In Progress** | **20%** |
| Layer 2: RAG Configuration | ✅ Complete | 100% |
| Layer 3: Mapping UI | 🔜 Not Started | 0% |
| Layer 4: Multi-Agent | 🔜 Not Started | 0% |
| Layer 5: Self-Healing | 🔜 Not Started | 0% |

**Next Steps**:
1. ✅ Complete Layer 1.5 documentation (done)
2. 🔄 Implement `table_extractor.py` with Phi-3-Mini
3. 🔄 Test extraction on sample headline + CSV
4. 🔄 Integrate into mapping UI (Layer 3)
