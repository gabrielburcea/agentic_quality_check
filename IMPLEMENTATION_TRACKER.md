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
│  │ Headline Selection → CSV Column Mapping → Metadata Store │  │
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
│  LAYER 1: DOCUMENT & DATA INGESTION                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ PDF Upload   │  │ CSV Upload   │  │ Headline           │   │
│  │ & Parse      │  │ & Parse      │  │ Extraction         │   │
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
│   └── __init__.py
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
# src/__init__.py
from .config import (
    PATHS,
    ACTIVE_MODELS,
    get_volume_path,
    switch_to_databricks_models
)

__all__ = [
    'PATHS',
    'ACTIVE_MODELS',
    'get_volume_path',
    'switch_to_databricks_models'
]

# Usage in other modules:
from src import PATHS, ACTIVE_MODELS
pdf_path = PATHS['pdfs']
```

</td>
</tr>

</table>

---

## ✅ **COMPLETED: Layer 2 - RAG Configuration**

<table>
<tr>
<th width="30%">🏗️ What I Built</th>
<th width="40%">💬 Talking Points</th>
<th width="30%">💻 Code Snippet</th>
</tr>

<!-- Semantic Chunking -->
<tr>
<td>

**Semantic Chunking Strategy**

📊 **Methods**:
- Semantic (sentence similarity)
- Headline-based (structure-preserving)
- Fixed-size (fallback)

</td>
<td>

"Fixed-size chunking breaks semantic units mid-sentence, hurting retrieval quality. Semantic chunking uses sentence embeddings to detect topic shifts and only splits when similarity drops below a threshold.

For statistical reports with clear structure, I also support headline-based chunking to preserve the document hierarchy—this aligns perfectly with the user workflow where they select specific headlines to analyze. The chunking strategy is configurable, not hardcoded."

</td>
<td>

```python
RAG_CONFIG = {
    'chunking': {
        'strategy': 'semantic',
        
        'semantic': {
            'method': 'sentence_similarity',
            'min_chunk_size': 100,
            'max_chunk_size': 1000,
            'similarity_threshold': 0.7
        },
        
        'headline_based': {
            'method': 'extract_sections',
            'include_context': True,
            'context_window': 2
        }
    }
}
```

</td>
</tr>

<!-- Vector Store -->
<tr>
<td>

**Vector Store Options**

🔷 Databricks Vector Search
- Delta-synced index
- Auto-scaling

🔶 FAISS
- Local index
- Fast, no dependencies

</td>
<td>

"I configured both Databricks Vector Search and FAISS. Databricks Vector Search is a managed service that auto-syncs with Delta tables and scales automatically—ideal for production.

FAISS is a local alternative for development. The vector store is abstracted behind a common interface, so swapping implementations doesn't require changing retrieval code. This demonstrates the adapter pattern and separation of concerns."

</td>
<td>

```python
'vector_store': {
    'databricks': {
        'provider': 'databricks_vector_search',
        'index_name': 'doc_chunks_index',
        'index_type': 'DELTA_SYNC',
        'similarity_metric': 'cosine'
    },
    
    'faiss': {
        'provider': 'faiss',
        'index_type': 'IndexFlatL2',
        'index_path': f"{PATHS['processed']}"
    },
    
    'active': 'databricks'
}
```

</td>
</tr>

</table>

---

## ✅ **COMPLETED: Layer 3 - Mapping Configuration**

<table>
<tr>
<th width="30%">🏗️ What I Built</th>
<th width="40%">💬 Talking Points</th>
<th width="30%">💻 Code Snippet</th>
</tr>

<!-- Mapping Layer -->
<tr>
<td>

**Headline-to-CSV Mapping**

🔗 **Stores**:
- Headline text
- CSV columns
- Expected calculation
- Agent types to run

</td>
<td>

"The mapping layer is critical—it's where users connect headlines to CSV data. When a user selects 'Mean average score was 19.8', they map it to CSV columns ['score'] and specify the calculation type ('mean').

This metadata is stored as JSON (or optionally a Delta table), then passed to the Numerical Agent along with retrieved document context. The agent knows exactly which CSV columns to query, rather than guessing. This design eliminates ambiguity and makes the system deterministic."

</td>
<td>

```python
MAPPING_CONFIG = {
    'storage': {
        'format': 'json',
        'path': f"{PATHS['mappings']}"
                "headline_csv_mappings.json",
        'delta_table': 
            f"{catalog}.{schema}.mappings"
    },
    
    'schema': {
        'headline_id': 'str',
        'headline_text': 'str',
        'csv_columns': 'list[str]',
        'csv_filters': 'dict',
        'expected_calculation': 'str',
        'agent_types': 'list[str]'
    }
}
```

</td>
</tr>

<!-- Auto-suggestion -->
<tr>
<td>

**AI-Powered Auto-Suggestion**

Uses semantic similarity to suggest CSV columns for each headline

</td>
<td>

"I added an auto-suggestion feature that uses semantic similarity to match headline text with CSV column names and descriptions. When confidence exceeds 0.8, it suggests the top 3 most relevant columns.

This reduces manual mapping work while keeping the user in control—they review and approve suggestions rather than blindly accepting them. It's a human-in-the-loop approach that balances automation with accuracy."

</td>
<td>

```python
'auto_suggest': {
    'enabled': True,
    'method': 'semantic_similarity',
    'confidence_threshold': 0.8,
    'max_suggestions': 3
}

# Usage flow:
# 1. User selects headline
# 2. System embeds headline text
# 3. Compute similarity with all CSV cols
# 4. Show top 3 if similarity > 0.8
# 5. User reviews and confirms
```

</td>
</tr>

</table>

---

## 🔄 **IN PROGRESS: Layer 1 - Document Ingestion**

<table>
<tr>
<th width="30%">🏗️ Next Steps</th>
<th width="40%">💬 Approach</th>
<th width="30%">💻 Tools</th>
</tr>

<tr>
<td>

**PDF Parser Module**

Extract:
- Raw text
- Headlines/sections
- Metadata (page #, fonts)

</td>
<td>

"Next, I'll build the PDF parser using PyPDF2 or pdfplumber. The key challenge is extracting headlines accurately—I'll use font size and formatting heuristics.

The parser will output structured JSON: each headline with its associated paragraphs, page numbers, and hierarchy (H1, H2, etc.). This structure feeds directly into the mapping UI."

</td>
<td>

```python
# Libraries to use:
- pdfplumber (better layout)
- PyPDF2 (fallback)
- spaCy (sentence splitting)

# Output format:
{
  "headlines": [
    {
      "id": "h1",
      "text": "Executive Summary",
      "level": 1,
      "page": 2,
      "paragraphs": [...]
    }
  ]
}
```

</td>
</tr>

</table>

---

## 📈 **Architecture Decisions Log**

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Unity Catalog over workspace FS** | Governance, lineage tracking, production-ready | Slightly more setup complexity |
| **Dual config (Databricks + Free)** | Flexibility to develop locally, deploy enterprise | Maintain two configs |
| **Semantic chunking** | Better retrieval quality | More compute than fixed-size |
| **Mapping layer (explicit, not inferred)** | Eliminates ambiguity, user control | Requires user input |
| **JSON + Delta table storage** | JSON for quick prototyping, Delta for scale | Dual maintenance initially |

---

## 🎯 **Interview Questions I Can Answer**

### **System Design**
- ✅ "Walk me through your RAG architecture"
- ✅ "How do you handle configuration for multiple environments?"
- ✅ "Why did you choose Unity Catalog over S3 directly?"
- ✅ "How does your mapping layer work?"

### **Technical Deep Dive**
- ✅ "Explain semantic vs fixed-size chunking"
- ✅ "How would you switch from free to paid models?"
- ✅ "What's your testing strategy?" *(coming next)*
- ✅ "How do you handle PDF parsing edge cases?" *(coming next)*

### **Production Readiness**
- ✅ "How would you monitor this system in production?"
- ✅ "What's your error handling strategy?"
- ✅ "How does the self-healing loop work?" *(coming next)*

---

## 📝 **Next Session Checklist**

- [ ] Build PDF parser module (`src/utils/pdf_parser.py`)
- [ ] Extract headlines with font-based heuristics
- [ ] Build CSV handler module (`src/utils/csv_handler.py`)
- [ ] Create mapping UI prototype (Streamlit Tab 3)
- [ ] Write unit tests for config and utils

---

**Last Updated**: 2026-07-05 | **Version**: 0.1.0 | **Status**: Foundation Complete ✅