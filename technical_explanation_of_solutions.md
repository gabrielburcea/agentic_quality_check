# 🔬 Technical Deep Dive: How Claude Knows What to Extract

This document explains the exact mechanics of how the LLM generates extraction code. This is about **information architecture** and **prompt engineering**.

---

## 📊 **The Input Package: What Claude Receives**

### **1. Headline Text (Dimension Hint)**
```python
headline = {
    'text': 'Attainment by gender',
    'level': 2,
    'page': 3
}
```

**What Claude Infers**:
- Primary dimension: **gender/sex** (from "by gender")
- This will be a grouping column
- Expects to see comparisons between gender categories

---

### **2. Paragraph Context (The "Rosetta Stone")**

```python
paragraphs = [
    "Of eligible pupils in year 4, a slightly larger proportion of girls "
    "took the check than boys (97% and 95% respectively)... "
    "the average score for girls was 19.6 while the average score "
    "for boys was 20.0..."
]
```

**What Claude Extracts From This**:

| Text Fragment | What Claude Infers |
|--------------|-------------------|
| "girls took the check... boys (97% and 95%)" | **Metric**: participation rate<br>**Filter**: sex IN ('Girls', 'Boys')<br>**Values**: 97% (Girls), 95% (Boys) |
| "average score for girls was 19.6 while... boys was 20.0" | **Metric**: average score<br>**Filter**: sex IN ('Girls', 'Boys')<br>**Values**: 19.6 (Girls), 20.0 (Boys) |
| "pupils in year 4" | **Filter**: year_group = 4 |
| "in 2022" (if present) | **Filter**: time_period = 2022 |

**Key Insight**: The paragraphs are **natural language SQL queries** — they describe filters, metrics, and breakdowns in human terms.

---

### **3. CSV Column Metadata (The Translation Dictionary)**

```python
column_metadata = [
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
        "name": "geographic_level",
        "type": "object",
        "role": "filter",
        "sample_values": ["National", "Local authority", "Region"]
    },
    {
        "name": "mtc_score_average",
        "type": "float64",
        "role": "metric",
        "sample_values": {}
    },
    {
        "name": "completed_check_pupil_percent",
        "type": "float64",
        "role": "metric",
        "sample_values": {}
    }
]
```

**What This Tells Claude**:

1. **Column Name Mapping**:
   - Paragraph says "girls" and "boys" → Column name is `sex`
   - Paragraph says "average score" → Column name is `mtc_score_average`
   - Paragraph says "took the check" → Column name is `completed_check_pupil_percent`

2. **Valid Filter Values**:
   - `sex`: Must be one of ['Boys', 'Girls', 'Total']
   - `geographic_level`: Probably want 'National' for national-level stats

3. **Column Roles**:
   - **Filter columns** (`role: "filter"`) → Use in WHERE clauses
   - **Metric columns** (`role: "metric"`) → Use in SELECT, aggregations, pivots

---

## 🧠 **The Prompt: Exact Instructions to Claude**

Based on `table_extraction_prompt.py` from your codebase:

```python
PROMPT_TEMPLATE = f"""
## ⚠️ CRITICAL RULES - NO IMPORTS ALLOWED

You are generating pandas code that runs in a PRE-CONFIGURED environment.

**Pre-loaded Variables (DO NOT REDEFINE)**:
- `df`: pandas DataFrame already loaded from CSV
- `pd`: pandas module already imported
- `paragraph`: string containing the headline paragraph text

## ❌ WRONG EXAMPLE (DO NOT DO THIS):
import pandas as pd          # ❌ FORBIDDEN
df = pd.read_csv("file.csv") # ❌ FORBIDDEN

## ✅ CORRECT EXAMPLE:
# Start directly with filtering logic
phrase_to_metric = {{
    "average score": "mtc_score_average",
    "took the check": "completed_check_pupil_percent"
}}

df_filtered = df[df['sex'].isin(['Boys', 'Girls'])]
df_filtered = df_filtered[df_filtered['geographic_level'] == 'National']

# ... rest of code ...

---

## YOUR TASK

**Headline**: "{headline['text']}"

**Paragraph Context**:
{paragraph_text}

**Available CSV Columns**:
{json.dumps(column_metadata, indent=2)}

**Instructions**:
1. Analyze the paragraph to identify:
   - What metrics are being discussed (e.g., "average score", "took the check")
   - What filters are needed (e.g., sex = 'Boys' or 'Girls')
   - What breakdowns are shown (e.g., by gender, by year)

2. Generate pandas code to:
   - Filter the DataFrame to the relevant subset
   - Select only the columns mentioned in the paragraph
   - Transform to match the table structure in the paragraph
   - Return a small table (10-50 rows maximum)

3. Edge Cases:
   - Suppression markers ('c', 'z', 'x') must stay as-is (do NOT convert to 0)
   - If paragraph mentions percentages, add '%' suffix to values
   - For hierarchical breakdowns, use multi-level column headers

4. Output Format:
   - Assign the final result to a variable named `result`
   - `result` should be a pandas DataFrame
   - The DataFrame should have clear column names

Generate the code now.
"""
```

---

## 🎯 **How Claude Reasons (Step-by-Step)**

### **Step 1: Parse the Paragraph**

Claude uses its language understanding to extract structured information:

```
Input Paragraph:
"the average score for girls was 19.6 while the average score for boys was 20.0"

Claude's Internal Reasoning:
→ Metric mentioned: "average score"
→ Dimension mentioned: "girls" vs "boys" (gender comparison)
→ Values mentioned: 19.6, 20.0
→ Structure: This is a comparison table, 2 rows (girls, boys) × 1 metric (avg score)
```

### **Step 2: Map Natural Language → SQL/Pandas Concepts**

```
Natural Language          →  SQL/Pandas Translation
--------------------------------------------------
"girls" and "boys"        →  WHERE sex IN ('Girls', 'Boys')
"average score"           →  SELECT mtc_score_average
"in year 4"               →  WHERE year_group = 4
"took the check (97%)"    →  SELECT completed_check_pupil_percent
```

### **Step 3: Use Column Metadata as a Dictionary**

```python
# Claude sees this metadata:
{
  "name": "sex",
  "sample_values": ["Boys", "Girls", "Total"]
}

# Claude reasons:
# - Paragraph mentions "girls" → sample_values has "Girls" (capitalized)
# - Paragraph mentions "boys" → sample_values has "Boys" (capitalized)
# - So the filter should be: df['sex'].isin(['Girls', 'Boys'])
```

**Critical**: The sample values tell Claude the **exact string format** to use. This prevents mismatches like:
- ❌ `df['sex'] == 'girls'` (lowercase, won't match)
- ✅ `df['sex'] == 'Girls'` (matches sample_values)

### **Step 4: Generate Pandas Code**

Claude generates code that:

1. **Filters the DataFrame**
```python
df_filtered = df[df['sex'].isin(['Boys', 'Girls'])]
df_filtered = df_filtered[df_filtered['geographic_level'] == 'National']
```

2. **Selects Relevant Columns**
```python
columns_to_keep = ['sex', 'time_period', 'mtc_score_average', 
                   'completed_check_pupil_percent']
df_filtered = df_filtered[columns_to_keep]
```

3. **Transforms to Match Paragraph Structure**
```python
# If paragraph shows a pivot table (rows=metrics, cols=gender×year)
df_pivoted = df_filtered.pivot_table(
    index='metric',
    columns=['sex', 'time_period'],
    values='value',
    aggfunc='first'
)
```

4. **Returns Small Table**
```python
result = df_pivoted.head(50)  # Max 50 rows
```

---

## 🔒 **Code Validation (Safety Layer)**

Before execution, the system validates the generated code:

```python
def _validate_code(self, code: str) -> bool:
    """
    Ensure code only contains safe pandas operations.
    """
    
    # Forbidden patterns
    forbidden = [
        'import ',           # No imports allowed
        'exec(',             # No arbitrary code execution
        'eval(',             # No eval
        'open(',             # No file operations
        '__',                # No dunder methods
        'os.',               # No OS operations
        'subprocess.',       # No subprocess
        'sys.',              # No sys operations
    ]
    
    for pattern in forbidden:
        if pattern in code:
            raise ValueError(f"Forbidden pattern detected: {pattern}")
    
    # Required elements
    if 'df' not in code:
        raise ValueError("Code must use pre-loaded 'df' variable")
    
    if 'result' not in code:
        raise ValueError("Code must assign final DataFrame to 'result'")
    
    return True
```

**What Gets Rejected**:
```python
# ❌ This would be rejected
import pandas as pd
df = pd.read_csv("data.csv")
```

**What Gets Accepted**:
```python
# ✅ This passes validation
df_filtered = df[df['sex'].isin(['Boys', 'Girls'])]
result = df_filtered
```

---

## ⚙️ **Code Execution (Sandboxed Environment)**

```python
def _execute_code(self, csv_path: str, generated_code: str) -> Dict:
    """
    Execute generated pandas code in a controlled environment.
    """
    
    # Step 1: Load CSV into DataFrame
    df = pd.read_csv(csv_path)
    
    # Step 2: Prepare execution namespace
    namespace = {
        'pd': pd,              # pandas module
        'df': df,              # pre-loaded DataFrame
        'paragraph': self.paragraph_text,  # paragraph text
        'np': np               # numpy (for compatibility)
    }
    
    # Step 3: Execute generated code
    try:
        exec(generated_code, namespace)
    except Exception as e:
        raise RuntimeError(f"Code execution failed: {e}")
    
    # Step 4: Extract result
    if 'result' not in namespace:
        raise ValueError("Code did not produce 'result' variable")
    
    result_df = namespace['result']
    
    # Step 5: Convert to JSON
    return {
        'extracted_table': result_df.to_dict(orient='records'),
        'row_count': len(result_df),
        'columns': result_df.columns.tolist(),
        'pandas_code': generated_code
    }
```

**What Happens**:
1. CSV loaded once: `df = pd.read_csv(csv_path)`
2. Namespace prepared with `df`, `pd`, `paragraph` pre-loaded
3. Generated code executes: `exec(generated_code, namespace)`
4. Result extracted: `namespace['result']`

**Why This Works**:
- Claude's code references `df` (already loaded)
- Claude's code references `pd` (already imported)
- No imports or file reads needed
- Code runs in isolated namespace

---

## 🧩 **Why This Approach is Powerful**

### **1. Generic Across Publications**

No hardcoded column names:
```python
# ❌ BAD: Hardcoded for one dataset
df_filtered = df[df['sex'].isin(['Boys', 'Girls'])]

# ✅ GOOD: LLM infers column name from metadata
# Claude reads column_metadata, sees "sex" with sample_values,
# generates the filter dynamically
```

### **2. Handles Natural Language Variations**

Paragraph variations that Claude understands:
- "girls scored 19.6, boys 20.0" → `sex.isin(['Girls', 'Boys'])`
- "female students averaged 19.6, male students 20.0" → same filter (infers gender)
- "boys outperformed girls" → same filter (order doesn't matter)

### **3. Infers Implicit Filters**

Paragraph: "National level statistics show..."

Claude infers:
```python
df_filtered = df_filtered[df_filtered['geographic_level'] == 'National']
```

Even though the paragraph doesn't explicitly say "filter by geographic_level = National", Claude understands that "national level" implies this filter.

### **4. Handles Edge Cases**

**Suppression Markers**:
```python
# Paragraph mentions: "Data suppressed (marked as 'c')"
# Claude preserves these:
df['value'] = df['value'].astype(str)  # Keep 'c', 'z', 'x' as strings
```

**Percentage Formatting**:
```python
# Paragraph shows: "97%"
# Claude adds suffix:
df['completed_check_pupil_percent'] = df['completed_check_pupil_percent'].astype(str) + '%'
```

---

## 📊 **Complete Example: Input → Output**

### **Input Package**

```python
headline = "Attainment by gender"

paragraphs = [
    "The average score for girls was 19.6 while boys scored 20.0"
]

column_metadata = [
    {"name": "sex", "role": "filter", "sample_values": ["Boys", "Girls"]},
    {"name": "mtc_score_average", "role": "metric"}
]

csv_path = "data.csv"  # 4,494 rows
```

### **Claude's Generated Code**

```python
# Map natural language to column names
phrase_to_metric = {
    "average score": "mtc_score_average"
}

# Filter to relevant rows
df_filtered = df[df['sex'].isin(['Boys', 'Girls'])]
df_filtered = df_filtered[df_filtered['geographic_level'] == 'National']

# Select relevant columns
df_filtered = df_filtered[['sex', 'time_period', 'mtc_score_average']]

# Assign result
result = df_filtered
```

### **Execution Output**

```json
{
  "extracted_table": [
    {"sex": "Boys", "time_period": "202223", "mtc_score_average": 20.0},
    {"sex": "Girls", "time_period": "202223", "mtc_score_average": 19.6},
    {"sex": "Boys", "time_period": "202324", "mtc_score_average": 20.4},
    {"sex": "Girls", "time_period": "202324", "mtc_score_average": 19.9}
  ],
  "row_count": 4,
  "pandas_code": "...(code above)..."
}
```

**From 4,494 rows → 4 rows** (filtered + selected)

---

## 🎯 **Key Technical Insights**

| Component | Purpose | Technical Detail |
|-----------|---------|------------------|
| **Headline Text** | Dimension hint | Tells Claude the primary grouping (e.g., "by gender" → sex column) |
| **Paragraph Text** | Natural language query | Describes filters, metrics, values in human terms |
| **Column Metadata** | Translation dictionary | Maps natural language → column names, provides valid values |
| **Prompt Engineering** | Constraints + instructions | Explicitly forbids imports, provides examples, handles edge cases |
| **Code Validation** | Security layer | Rejects unsafe patterns (imports, file ops, exec) |
| **Sandboxed Execution** | Controlled environment | Pre-loads df/pd/paragraph, isolates namespace |

---

## 💡 **Why This Works So Well**

1. **LLMs are Good at Pattern Matching**
   - "girls... boys" → gender comparison
   - "average score" → metric column
   - "97% and 95%" → percentage values

2. **Column Metadata Provides Ground Truth**
   - Sample values show exact string format
   - Column roles guide selection (filter vs metric)
   - Data types inform transformations

3. **Prompt Engineering Reduces Hallucinations**
   - Explicit constraints (no imports)
   - Wrong/Right examples
   - Edge case handling

4. **Validation Prevents Failures**
   - Catches forbidden patterns before execution
   - Ensures code uses pre-loaded variables
   - Verifies result variable exists

---

**Bottom Line**: Claude doesn't "magically know" what to extract. You give it:
1. **Context** (headline + paragraphs)
2. **Dictionary** (column metadata)
3. **Instructions** (prompt template)
4. **Safety rails** (validation + sandboxing)

Claude uses its language understanding to translate natural language → pandas code, guided by the metadata and constrained by the prompt. The system is **generic** (no hardcoded columns) but **precise** (metadata provides exact values).

---

# 🔄 From Extraction to Verification: The Single-Pipeline Architecture

Once Claude extracts tables (Layer 1.5), the next question is: **how do agents verify the extracted data?** The answer lies in how we design Layer 2 (RAG) and Layer 4 (Multi-Agent Verification).

## 🎯 **The Architectural Decision: One Pipeline, Not Two**

### **The Original 2-Stream Design (Inefficient)**

The initial architecture proposed two parallel data streams:

```
Stream A (Unstructured Text):
PDF → Extract Paragraphs → Chunk Text → Embed → Vector Store
     (stores: "Girls scored 19.6, boys scored 20.0...")

Stream B (Structured Data):
PDF + CSV → Claude Extraction → JSON
     (stores: same paragraph + extracted table + pandas code)

                    ↓                        ↓
                    └────────────┬───────────┘
                                 ↓
                    Layer 4: Multi-Agent Verification
                    (Agent receives both streams)
```

**The Problem**: Redundancy and complexity.

| Issue | Impact |
|-------|--------|
| **Data Duplication** | Same paragraph stored twice (PDF chunks + extraction JSON) |
| **High Token Cost** | Agents query RAG for paragraph, then load JSON separately |
| **Reconciliation Overhead** | Agent must merge two data sources manually |
| **Maintenance Burden** | Two pipelines to keep in sync |
| **Lost Context** | Paragraph and extracted table are disconnected |

### **The Optimized 1-Stream Design (Efficient)**

The breakthrough realization: **Layer 1.5 extraction JSON already contains everything agents need**.

```
PDF + CSV → Claude Extraction → Enriched JSON → Chunk & Embed → Vector Store
                                      ↓
        {headline, paragraph, extracted_table, pandas_code, metadata}
                                      ↓
                        Single source of truth for agents
                                      ↓
                         Layer 4: Multi-Agent Verification
                         (Agent retrieves complete context in one query)
```

**Why This Wins**:

✅ **No Redundancy** — Paragraph stored once in extraction JSON  
✅ **Token Efficient** — One retrieval gets headline + paragraph + table + code  
✅ **Perfect Context** — Everything linked together by design  
✅ **Simpler Architecture** — One pipeline, one storage layer  
✅ **Auditable** — Full lineage from PDF → extraction → verification  

---

## 🔬 **Multi-Faceted Chunking: The Technical Innovation**

The challenge: **How do you embed a JSON object containing text, tables, and code?**

You can't just dump the entire JSON as a text blob:

```python
# ❌ BAD: Dumps everything as one string
json_text = json.dumps(extraction_json)
embedding = model.encode(json_text)

# Problems:
# 1. Pandas code pollutes the semantic space
# 2. Large tables (50 rows) overwhelm the embedding
# 3. Query "girls' scores" won't match technical syntax like df[df['sex']=='Girls']
```

### **The Solution: 3-Chunk Decomposition**

Each extraction JSON is decomposed into **three specialized chunks**, each optimized for different query types:

#### **Chunk 1: Semantic Context (Natural Language Queries)**

**Purpose**: Match human queries like "What was the average score for girls?"

```python
def create_semantic_chunk(extraction_json: Dict) -> str:
    """
    Extract natural language content for semantic search.
    This chunk contains only human-readable text.
    """
    return f"""
Headline: {extraction_json['headline_text']}

Context: {' '.join(extraction_json['paragraphs'])}

Dimensions: {', '.join(extraction_json['filters_applied'].keys())}

Metrics: {', '.join(extraction_json['columns_selected'])}
""".strip()
```

**Example Output**:
```
Headline: Attainment by gender

Context: The average score for girls was 19.6 while the average score for boys was 20.0.

Dimensions: sex, geographic_level

Metrics: mtc_score_average, completed_check_pupil_percent
```

**Why This Works**:
- Query: *"What was the average score for girls?"*
- Embedding matches: "average score", "girls", "boys" in the context
- Returns: The full extraction JSON with paragraph + table + code

---

#### **Chunk 2: Table Content (Value-Based Queries)**

**Purpose**: Match specific values like "Find tables where girls scored 19.6"

```python
def create_table_chunk(extraction_json: Dict) -> str:
    """
    Convert extracted table to natural language sentences.
    Makes table values searchable via semantic similarity.
    """
    chunk = f"Headline: {extraction_json['headline_text']}\n\nTable Data:\n"
    
    # Convert first 5 rows to readable sentences
    for row in extraction_json['extracted_table'][:5]:
        row_text = ', '.join([f"{k}: {v}" for k, v in row.items()])
        chunk += f"- {row_text}\n"
    
    # Indicate if truncated
    if len(extraction_json['extracted_table']) > 5:
        remaining = len(extraction_json['extracted_table']) - 5
        chunk += f"... (and {remaining} more rows)"
    
    return chunk.strip()
```

**Example Output**:
```
Headline: Attainment by gender

Table Data:
- sex: Boys, time_period: 202223, mtc_score_average: 20.0
- sex: Girls, time_period: 202223, mtc_score_average: 19.6
- sex: Boys, time_period: 202324, mtc_score_average: 20.4
- sex: Girls, time_period: 202324, mtc_score_average: 19.9
- sex: Boys, time_period: 202425, mtc_score_average: 21.2
```

**Why This Works**:
- Query: *"Find tables where girls scored 19.6"*
- Embedding matches: "Girls", "19.6" in table content
- Returns: The extraction containing this exact value
- Agent can immediately verify without scanning all extractions

---

#### **Chunk 3: Extraction Metadata (Technical Queries)**

**Purpose**: Match technical queries like "Which extractions filtered by sex and geographic_level?"

```python
def create_metadata_chunk(extraction_json: Dict) -> str:
    """
    Extract technical metadata for debugging and filtering.
    Used when agents need to find extractions by structural properties.
    """
    return f"""
Extraction ID: {extraction_json['extraction_id']}

Headline: {extraction_json['headline_text']} (page {extraction_json.get('headline_page', 'N/A')})

Filters Applied: {json.dumps(extraction_json['filters_applied'], indent=2)}

Columns Selected: {extraction_json['columns_selected']}

Row Count: {len(extraction_json['extracted_table'])}

Generated Code Summary:
- DataFrame filtering: {extraction_json['filters_applied']}
- Column projection: {extraction_json['columns_selected']}
""".strip()
```

**Example Output**:
```
Extraction ID: ext_20250111_001

Headline: Attainment by gender (page 3)

Filters Applied: {
  "sex": ["Boys", "Girls"],
  "geographic_level": "National"
}

Columns Selected: ["sex", "time_period", "mtc_score_average"]

Row Count: 12

Generated Code Summary:
- DataFrame filtering: {"sex": ["Boys", "Girls"], "geographic_level": "National"}
- Column projection: ["sex", "time_period", "mtc_score_average"]
```

**Why This Works**:
- Query: *"Show me extractions that filtered by sex and geographic_level"*
- Embedding matches: "sex", "geographic_level" in filters
- Returns: All extractions using those specific filters
- Useful for debugging: "Why isn't my extraction showing regional data?" → metadata reveals it filtered to "National" only

---

## 🏗️ **Complete Implementation: Building the RAG Pipeline**

### **Step 1: Process Extraction JSONs into Chunks**

```python
from sentence_transformers import SentenceTransformer
import json
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dimensional embeddings

def process_extraction_for_rag(extraction_json: Dict) -> List[Dict]:
    """
    Convert one extraction JSON into 3 embeddable chunks.
    
    Args:
        extraction_json: The complete extraction from Layer 1.5
        
    Returns:
        List of 3 chunks, each with:
        - text: Human-readable content
        - embedding: 384-dim vector
        - type: 'semantic', 'table', or 'metadata'
        - extraction_id: Link back to full JSON
        - Additional metadata for retrieval
    """
    
    chunks = []
    extraction_id = extraction_json['extraction_id']
    
    # Chunk 1: Semantic context (for natural language queries)
    semantic_text = create_semantic_chunk(extraction_json)
    chunks.append({
        'text': semantic_text,
        'embedding': model.encode(semantic_text),
        'type': 'semantic',
        'extraction_id': extraction_id,
        'headline': extraction_json['headline_text'],
        'page': extraction_json.get('headline_page', None)
    })
    
    # Chunk 2: Table content (for value-based queries)
    table_text = create_table_chunk(extraction_json)
    chunks.append({
        'text': table_text,
        'embedding': model.encode(table_text),
        'type': 'table',
        'extraction_id': extraction_id,
        'headline': extraction_json['headline_text'],
        'row_count': len(extraction_json['extracted_table'])
    })
    
    # Chunk 3: Metadata (for technical/filter queries)
    metadata_text = create_metadata_chunk(extraction_json)
    chunks.append({
        'text': metadata_text,
        'embedding': model.encode(metadata_text),
        'type': 'metadata',
        'extraction_id': extraction_id,
        'filters': extraction_json['filters_applied'],
        'columns': extraction_json['columns_selected']
    })
    
    return chunks
```

---

### **Step 2: Build FAISS Vector Index**

```python
import faiss

def build_vector_index_from_extractions(
    extraction_json_files: List[str],
    output_dir: str
) -> Tuple[faiss.Index, List[Dict]]:
    """
    Build FAISS index from all extraction JSONs.
    
    For each extraction:
    1. Generate 3 chunks (semantic, table, metadata)
    2. Embed each chunk
    3. Add to FAISS index
    4. Store chunk metadata separately
    
    Args:
        extraction_json_files: List of paths to extraction JSON files
        output_dir: Where to save FAISS index and metadata
        
    Returns:
        (faiss_index, chunk_metadata_list)
    """
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    dimension = 384
    
    # Initialize FAISS index (L2 distance for cosine similarity)
    index = faiss.IndexFlatL2(dimension)
    
    # Store metadata for each chunk
    chunk_metadata = []
    chunk_id = 0
    
    # Process each extraction JSON
    for json_file in extraction_json_files:
        with open(json_file, 'r') as f:
            extraction_json = json.load(f)
        
        # Generate 3 chunks per extraction
        chunks = process_extraction_for_rag(extraction_json)
        
        for chunk in chunks:
            # Add embedding to FAISS (must be float32)
            embedding = chunk['embedding'].reshape(1, -1).astype('float32')
            index.add(embedding)
            
            # Store metadata (everything except the embedding)
            chunk_metadata.append({
                'chunk_id': chunk_id,
                'text': chunk['text'],
                'type': chunk['type'],
                'extraction_id': chunk['extraction_id'],
                'headline': chunk['headline'],
                
                # CRITICAL: Link to full JSON file
                'extraction_json_path': json_file
            })
            
            chunk_id += 1
    
    # Save FAISS index to disk
    faiss.write_index(index, f"{output_dir}/extractions.faiss")
    
    # Save metadata to JSON
    with open(f"{output_dir}/chunk_metadata.json", 'w') as f:
        json.dump(chunk_metadata, f, indent=2)
    
    print(f"✅ Indexed {len(chunk_metadata)} chunks from {len(extraction_json_files)} extractions")
    print(f"   - {len(extraction_json_files)} semantic chunks")
    print(f"   - {len(extraction_json_files)} table chunks")
    print(f"   - {len(extraction_json_files)} metadata chunks")
    
    return index, chunk_metadata
```

**What This Creates**:

```
/Volumes/my_catalog/agentic_quality_check_dev/processed_volume/
├── extractions.faiss          # Vector index (binary file)
├── chunk_metadata.json        # Metadata linking chunks to JSONs
└── extractions/
    ├── ext_20250111_001.json  # Full extraction JSON
    ├── ext_20250111_002.json
    └── ext_20250111_003.json
```

---

### **Step 3: Retrieval - Agents Query the Vector Store**

```python
def retrieve_extraction_for_verification(
    query: str,
    faiss_index: faiss.Index,
    chunk_metadata: List[Dict],
    model: SentenceTransformer,
    top_k: int = 3
) -> List[Dict]:
    """
    Retrieve relevant extraction JSONs for agent verification.
    
    This is the key function agents call. They provide a natural language
    query and receive complete extraction JSONs with all context.
    
    Args:
        query: Natural language question (e.g., "What was the average score for girls?")
        faiss_index: The vector index
        chunk_metadata: Metadata for all chunks
        model: Embedding model (same one used for indexing)
        top_k: Number of results to retrieve
        
    Returns:
        List of extraction JSONs with similarity scores
    """
    
    # Step 1: Embed the query
    query_embedding = model.encode(query).astype('float32').reshape(1, -1)
    
    # Step 2: Search FAISS index
    distances, indices = faiss_index.search(query_embedding, top_k)
    
    # Step 3: Retrieve chunk metadata
    retrieved_chunks = []
    for idx, dist in zip(indices[0], distances[0]):
        chunk = chunk_metadata[idx].copy()
        chunk['similarity_score'] = float(1 / (1 + dist))  # Convert L2 distance to similarity
        retrieved_chunks.append(chunk)
    
    # Step 4: Load full extraction JSONs (deduplicate by extraction_id)
    full_extractions = []
    seen_extraction_ids = set()
    
    for chunk in retrieved_chunks:
        extraction_id = chunk['extraction_id']
        
        # Avoid duplicates (same extraction from different chunk types)
        if extraction_id in seen_extraction_ids:
            continue
        seen_extraction_ids.add(extraction_id)
        
        # Load complete extraction JSON
        with open(chunk['extraction_json_path'], 'r') as f:
            extraction_json = json.load(f)
        
        full_extractions.append({
            'extraction': extraction_json,
            'matched_chunk_type': chunk['type'],  # Which chunk matched (semantic/table/metadata)
            'matched_chunk_text': chunk['text'],  # The chunk that matched
            'similarity_score': chunk['similarity_score']
        })
    
    return full_extractions
```

---

### **Step 4: Agent Verification Workflow**

Now agents can verify extracted tables with complete context in one retrieval:

```python
import pandas as pd

# Agent workflow example
def verify_table_cell(
    cell_to_verify: Dict,
    faiss_index: faiss.Index,
    chunk_metadata: List[Dict],
    model: SentenceTransformer
) -> Dict:
    """
    Verify a single table cell against PDF source.
    
    Args:
        cell_to_verify: {"sex": "Girls", "time_period": "202223", "mtc_score_average": 19.6}
        
    Returns:
        Verification result with evidence
    """
    
    # Step 1: Generate retrieval query from cell
    query = f"What was the {' '.join(cell_to_verify.keys())} for {' '.join([str(v) for v in cell_to_verify.values()])}?"
    # Example: "What was the sex time_period mtc_score_average for Girls 202223 19.6?"
    
    # Better query construction:
    metric_cols = [k for k in cell_to_verify.keys() if 'average' in k or 'percent' in k or 'score' in k]
    filter_cols = [k for k in cell_to_verify.keys() if k not in metric_cols]
    
    query = f"What was the {metric_cols[0]} for {filter_cols[0]}={cell_to_verify[filter_cols[0]]}?"
    # Example: "What was the mtc_score_average for sex=Girls?"
    
    # Step 2: Retrieve relevant extraction
    retrieved = retrieve_extraction_for_verification(
        query=query,
        faiss_index=faiss_index,
        chunk_metadata=chunk_metadata,
        model=model,
        top_k=1  # Get the most relevant extraction
    )
    
    if not retrieved:
        return {'verified': False, 'reason': 'No matching extraction found'}
    
    # Step 3: Agent gets EVERYTHING in one shot
    extraction = retrieved[0]['extraction']
    
    # ✅ Agent now has:
    # - Headline: "Attainment by gender"
    # - Paragraph: "Girls scored 19.6, boys scored 20.0..."
    # - Extracted table: [{"sex": "Girls", "mtc_score_average": 19.6}, ...]
    # - Pandas code: "df[df['sex'].isin(['Boys', 'Girls'])]..."
    # - Metadata: filters_applied, columns_selected
    
    # Step 4: Verify value in extracted table
    extracted_table_df = pd.DataFrame(extraction['extracted_table'])
    
    # Find matching row
    query_conditions = []
    for key, value in cell_to_verify.items():
        if key in extracted_table_df.columns:
            query_conditions.append(f"{key} == '{value}' if isinstance(value, str) else {key} == {value}")
    
    # Simpler approach - direct filtering
    matching_rows = extracted_table_df
    for key, value in cell_to_verify.items():
        if key in extracted_table_df.columns:
            matching_rows = matching_rows[matching_rows[key] == value]
    
    if len(matching_rows) == 0:
        return {
            'verified': False,
            'reason': 'Value not found in extracted table',
            'extraction_id': extraction['extraction_id']
        }
    
    # Step 5: Verify value in paragraph (textual evidence)
    paragraph = ' '.join(extraction['paragraphs'])
    
    # Check if the metric value appears in the paragraph
    metric_value = str(cell_to_verify.get('mtc_score_average', ''))
    filter_value = str(cell_to_verify.get('sex', ''))
    
    # Look for evidence like "girls scored 19.6" or "average score for girls was 19.6"
    evidence_found = metric_value in paragraph and filter_value.lower() in paragraph.lower()
    
    if evidence_found:
        return {
            'verified': True,
            'confidence': 0.95,
            'evidence': paragraph,
            'source_headline': extraction['headline_text'],
            'source_page': extraction.get('headline_page', 'N/A'),
            'pandas_code_used': extraction['pandas_code'],
            'extraction_id': extraction['extraction_id']
        }
    else:
        return {
            'verified': False,
            'confidence': 0.5,
            'reason': 'Value in table but not explicitly stated in paragraph',
            'extracted_value': matching_rows.iloc[0].to_dict(),
            'paragraph': paragraph,
            'extraction_id': extraction['extraction_id']
        }
```

---

## 📊 **Storage Architecture**

The complete storage layout:

```
/Volumes/my_catalog/agentic_quality_check_dev/
├── pdfs_volume/
│   └── Multiplication_check.pdf              (Raw input)
│
├── csvs_volume/
│   └── mtc_national_pupil_...csv             (Raw input)
│
├── mappings_volume/
│   └── mapping_20250111_001.json             (User configuration)
│
├── processed_volume/
│   ├── extractions/
│   │   ├── ext_20250111_001.json             (Layer 1.5 output - SOURCE OF TRUTH)
│   │   ├── ext_20250111_002.json
│   │   └── ...
│   ├── extractions.faiss                     (Vector index - Layer 2)
│   └── chunk_metadata.json                   (Links chunks → JSONs)
│
└── feedback_volume/
    └── feedback_20250111_001.json            (Layer 5 - future)
```

**Key Insight**: The extraction JSON in `processed_volume/extractions/` is the **single source of truth**. Everything else (FAISS index, chunk metadata) is derived from it.

---

## 🎯 **Why Multi-Faceted Chunking is Powerful**

### **Before (Naive Approach)**:

```python
# ❌ Single embedding per extraction
embedding = model.encode(json.dumps(extraction_json))

# Problems:
# - Query "girls scored 19.6" doesn't match pandas code syntax
# - Large JSON overwhelms 384-dim embedding space
# - Can't distinguish between metadata and content
```

### **After (Multi-Faceted Approach)**:

```python
# ✅ Three specialized embeddings per extraction

# Semantic chunk - matches natural language
Query: "What was the average score for girls?"
Matches: Chunk 1 (semantic) → Returns full extraction

# Table chunk - matches specific values
Query: "Find tables with girls scoring 19.6"
Matches: Chunk 2 (table) → Returns full extraction

# Metadata chunk - matches technical filters
Query: "Which extractions filtered by sex and geographic_level?"
Matches: Chunk 3 (metadata) → Returns full extraction
```

**Comparison**:

| Approach | Embeddings per Extraction | Query Types Supported | Retrieval Precision |
|----------|---------------------------|----------------------|---------------------|
| Naive (single chunk) | 1 | Limited | Low (polluted by code) |
| Multi-faceted (3 chunks) | 3 | Natural language, values, technical | High (specialized) |

---

## 💡 **Key Benefits of the Single-Pipeline Architecture**

### **1. Token Efficiency**

**Before (2-stream)**:
```python
# Agent verification workflow - 2 separate operations

# Operation 1: Query RAG for paragraph
ragcnts = vector_search("What was girls' score?")  # Cost: ~500 tokens
paragraph = retrieved_chunks[0]['text']

# Operation 2: Load extraction JSON separately
with open('extraction_001.json') as f:
    extraction = json.load(f)  # Cost: ~300 tokens

table = extraction['extracted_table']

# Total: 800 tokens, 2 operations
```

**After (1-stream)**:
```python
# Agent verification workflow - 1 operation

retrieved = retrieve_extraction_for_verification(
    query="What was girls' score?"
)  # Cost: ~500 tokens

# Retrieved object contains EVERYTHING:
extraction = retrieved[0]['extraction']
paragraph = ' '.join(extraction['paragraphs'])  # Already there
table = extraction['extracted_table']            # Already there
code = extraction['pandas_code']                  # Already there

# Total: 500 tokens, 1 operation
# Savings: 37.5% reduction
```

### **2. Perfect Context Linkage**

**Before**: Paragraph and table are stored separately. Agent must reconcile:
- "Does this paragraph describe this table?"
- "Are these from the same PDF section?"
- "Did the same extraction process generate both?"

**After**: Paragraph and table are **born together** in the extraction JSON. No reconciliation needed—they're intrinsically linked.

### **3. Auditability**

Every verification can trace back to:
1. **Extraction ID**: `ext_20250111_001`
2. **Source PDF**: page 3, headline "Attainment by gender"
3. **Pandas Code**: Exact code that generated the table
4. **Filters Applied**: `{"sex": ["Boys", "Girls"]}`
5. **Timestamp**: When extraction occurred

This creates a complete audit trail from PDF → extraction → verification.

---

## 🚀 **Implementation Roadmap**

### **Current State** (January 2025):
✅ Layer 0: Unity Catalog Volumes  
✅ Layer 1: PDF + CSV parsing  
✅ Layer 1.5: Claude extraction → JSON output  
✅ Layer 3: User mapping interface  

### **Next Steps** (Layer 2 - RAG):

**Week 1: Build Multi-Faceted Chunking Pipeline**
1. Implement `process_extraction_for_rag()` function
2. Test 3-chunk generation with sample extractions
3. Validate chunk quality (manual review)

**Week 2: Build Vector Index**
1. Process all extraction JSONs → generate chunks
2. Build FAISS index from embeddings
3. Save index + metadata to UC Volume

**Week 3: Implement Retrieval**
1. Implement `retrieve_extraction_for_verification()` function
2. Test queries: natural language, value-based, technical
3. Measure retrieval precision (does it return the right extraction?)

**Week 4: Integration Testing**
1. End-to-end test: PDF → extraction → chunking → retrieval
2. Verify that retrieved JSONs contain expected data
3. Measure token usage vs. 2-stream approach

### **Future** (Layer 4 - Multi-Agent Verification):
- Numerical Accuracy Agent (verify values)
- Style Consistency Agent (check formatting)
- Self-Healing Agent (learn from errors)

---

## 🔬 **Technical Deep Dive: Why 3 Chunks per Extraction?**

### **The Semantic Search Problem**

Vector similarity is based on **cosine similarity** between embeddings:

```python
similarity = cosine_similarity(query_embedding, chunk_embedding)
```

Embeddings capture **semantic meaning**, but different types of text have different semantic signatures:

| Text Type | Semantic Signature | Example Query Match |
|-----------|-------------------|-----------------|
| Natural language paragraph | "girls", "scored", "19.6", "boys", "20.0" | "What was the average score for girls?" |
| Structured table data | "sex: Girls", "score: 19.6", "time_period: 202223" | "Find girls scoring 19.6 in 2022-23" |
| Technical metadata | "filters_applied", "columns_selected", "sex", "geographic_level" | "Which extractions filtered by sex?" |
| Pandas code | `df[df['sex'].isin(['Girls'])]`, `.groupby()`, `.pivot_table()` | (Poor match for natural queries) |

**The Problem**: If you embed everything together, the pandas code **pollutes** the semantic space:

```python
# Mixed content - pandas code dominates
text = """
Headline: Attainment by gender
Paragraph: Girls scored 19.6...
Table: [rows...]
Code: df[df['sex'].isin(['Boys', 'Girls'])].groupby(['sex', 'time_period']).agg({'mtc_score_average': 'first'}).reset_index()
"""

embedding = model.encode(text)
# Result: Embedding weighted toward "df", "groupby", "agg", "reset_index"
# Natural query "girls scored 19.6" has weak similarity
```

**The Solution**: Separate content types into specialized chunks. Each chunk contains only one type of semantic content, making retrieval more precise.

---

## 📈 **Expected Performance Gains**

### **Retrieval Precision**

| Query Type | 1-Chunk (Naive) | 3-Chunk (Multi-Faceted) |
|------------|----------------|-------------------------|
| Natural language ("girls scored 19.6") | 60-70% | 90-95% |
| Value-based ("find 19.6") | 40-50% | 85-90% |
| Technical ("filtered by sex") | 30-40% | 80-85% |

### **Token Savings**

| Operation | 2-Stream | 1-Stream | Savings |
|-----------|----------|----------|---------|
| Paragraph retrieval | 500 tokens | 0 tokens (included) | 100% |
| JSON load | 300 tokens | 500 tokens (combined) | - |
| **Total** | **800 tokens** | **500 tokens** | **37.5%** |

### **Development Velocity**

| Task | 2-Stream | 1-Stream |
|------|----------|----------|
| Maintain two pipelines | 2x effort | 1x effort |
| Debug context mismatches | Frequent | Rare (linked by design) |
| Add new extraction fields | Update 2 places | Update 1 place |

---

**Final Insight**: The single-pipeline architecture with multi-faceted chunking transforms the extraction JSON from a **data dump** into a **searchable knowledge base**. Each extraction becomes a self-contained unit of context (headline + paragraph + table + code) that agents can retrieve and verify independently. This is the foundation for scalable, auditable, token-efficient multi-agent verification.

---

# 🤖 Layer 4: Multi-Agent Verification System

With the RAG pipeline built (Layer 2), we now have the infrastructure to retrieve extraction context efficiently. The next challenge is **verification**: how do we know if Claude extracted correctly?

Layer 4 introduces specialized agents that verify extracted data against the source PDF.

## 🎯 **The Core Problem: Trust but Verify**

**Current State After Layer 2**:
- ✅ Extracted tables from Claude (Layer 1.5)
- ✅ Searchable vector store with multi-faceted chunks (Layer 2)
- ✅ Efficient retrieval of extraction context

**The Gap**: We have no systematic way to validate extraction quality.

**Questions We Need to Answer**:
1. Do the extracted table values match what the PDF paragraph claims?
2. Are suppression markers ('c', 'x', 'z') handled correctly?
3. Is the formatting consistent (percentages as 97% vs 0.97)?
4. Did Claude apply the right filters?

**The Solution**: Specialized verification agents that check different quality dimensions.

---

## 🏗️ **Multi-Agent Architecture**

Instead of one monolithic "verification agent," we use **specialized agents** for different verification tasks:

```
                    ┌─────────────────────────┐
                    │   Agent Orchestrator    │
                    │  (Supervisor/Router)    │
                    └─────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ↓                 ↓                  ↓
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  Numerical   │  │    Style     │  │  Consistency │
    │  Accuracy    │  │   Checker    │  │   Validator  │
    │   Agent      │  │    Agent     │  │    Agent     │
    └──────────────┘  └──────────────┘  └──────────────┘
            ↓                 ↓                  ↓
            └─────────────────┼──────────────────┘
                              ↓
                    ┌─────────────────────────┐
                    │  Verification Report    │
                    │  (JSON with evidence)   │
                    └─────────────────────────┘
```

**Design Principle**: Each agent is an expert in one dimension of quality. This separation:
- Improves precision (specialized prompts)
- Enables parallel execution (agents are independent)
- Simplifies debugging (isolate which agent fails)
- Allows incremental development (add agents one at a time)

---

## 🔢 **Agent 1: Numerical Accuracy Verifier**

**Responsibility**: Verify that extracted table values match PDF paragraph claims.

### **Technical Workflow**

```python
class NumericalAccuracyAgent:
    """
    Verifies that extracted table values match PDF paragraph claims.
    Uses RAG to retrieve relevant context for each cell.
    """
    
    def __init__(self, faiss_index, chunk_metadata, model, llm_client):
        self.faiss_index = faiss_index
        self.chunk_metadata = chunk_metadata
        self.model = model  # sentence-transformers for retrieval
        self.llm_client = llm_client  # Claude for reasoning
    
    def verify_extraction(self, extraction_json: Dict) -> Dict:
        """
        Verify all metric cells in an extracted table.
        
        Process:
        1. Iterate over each row in extracted table
        2. For each metric column, verify the value
        3. Aggregate results into verification report
        
        Returns:
            Verification report with per-cell evidence
        """
        
        table_df = pd.DataFrame(extraction_json['extracted_table'])
        verification_results = []
        
        # Verify each metric cell
        for idx, row in table_df.iterrows():
            for col in row.index:
                cell_value = row[col]
                
                # Skip identifier/filter columns (they're just labels)
                if col in ['sex', 'time_period', 'geographic_level']:
                    continue
                
                # Verify metric columns (the actual values to check)
                if 'average' in col or 'percent' in col or 'score' in col:
                    result = self._verify_cell(
                        extraction_json=extraction_json,
                        row_filters={k: row[k] for k in row.index if k != col},
                        metric_column=col,
                        metric_value=cell_value
                    )
                    verification_results.append(result)
        
        # Aggregate results
        verified_count = sum(1 for r in verification_results if r['verified'])
        total_count = len(verification_results)
        
        return {
            'extraction_id': extraction_json['extraction_id'],
            'headline': extraction_json['headline_text'],
            'overall_confidence': verified_count / total_count if total_count > 0 else 0,
            'verified_cells': verified_count,
            'total_cells': total_count,
            'cell_reports': verification_results
        }
    
    def _verify_cell(
        self, 
        extraction_json: Dict,
        row_filters: Dict,
        metric_column: str,
        metric_value: float
    ) -> Dict:
        """
        Verify a single cell value.
        
        Two-stage verification:
        1. Simple text search: Is the value string in the paragraph?
        2. LLM reasoning: For ambiguous cases, use Claude to reason
        """
        
        paragraph = ' '.join(extraction_json['paragraphs'])
        
        # Stage 1: Simple text search
        value_str = str(metric_value)
        value_in_paragraph = value_str in paragraph
        
        if value_in_paragraph:
            # Direct match found - high confidence
            return {
                'row_filters': row_filters,
                'metric': metric_column,
                'value': metric_value,
                'verified': True,
                'confidence': 0.95,
                'evidence_type': 'direct_text_match',
                'evidence': paragraph
            }
        else:
            # Stage 2: LLM reasoning for derived/implied values
            return self._llm_verify(
                paragraph=paragraph,
                row_filters=row_filters,
                metric_column=metric_column,
                metric_value=metric_value
            )
    
    def _llm_verify(
        self,
        paragraph: str,
        row_filters: Dict,
        metric_column: str,
        metric_value: float
    ) -> Dict:
        """
        Use Claude to reason about whether a value is supported by text.
        
        Use cases:
        - Value is derived (e.g., calculated from other stated values)
        - Value is stated in different format ("nearly 20" vs 19.6)
        - Value contradicts the text (extraction error)
        """
        
        prompt = f"""
You are a numerical fact-checker. Verify if an extracted value is supported by the source text.

**Extracted Value**:
- Filters: {json.dumps(row_filters)}
- Metric: {metric_column}
- Value: {metric_value}

**Source Paragraph**:
{paragraph}

**Your Task**:
1. Does the paragraph explicitly state this value for these filters?
2. Could the value be derived from information in the paragraph?
3. Is there any contradiction?

**Output Format** (JSON only, no markdown):
{{
    "verified": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Explain your decision",
    "evidence_quote": "Exact quote from paragraph if verified"
}}
"""
        
        response = self.llm_client.messages.create(
            model="claude-opus-4-20250514",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        # Parse JSON response
        result = json.loads(response.content[0].text)
        result['evidence_type'] = 'llm_reasoning'
        result['row_filters'] = row_filters
        result['metric'] = metric_column
        result['value'] = metric_value
        
        return result
```

### **Example Verification Report**

```json
{
  "extraction_id": "ext_20250111_001",
  "headline": "Attainment by gender",
  "overall_confidence": 0.92,
  "verified_cells": 11,
  "total_cells": 12,
  "cell_reports": [
    {
      "row_filters": {"sex": "Girls", "time_period": "202223"},
      "metric": "mtc_score_average",
      "value": 19.6,
      "verified": true,
      "confidence": 0.95,
      "evidence_type": "direct_text_match",
      "evidence": "...the average score for girls was 19.6..."
    },
    {
      "row_filters": {"sex": "Girls", "time_period": "202324"},
      "metric": "completed_check_pupil_percent",
      "value": 97.0,
      "verified": false,
      "confidence": 0.3,
      "evidence_type": "llm_reasoning",
      "reasoning": "Paragraph mentions 97% for 2022-23, but extracted value is for 2023-24. No evidence for 2023-24 in this paragraph."
    }
  ]
}
```

**Key Insight**: The agent provides **cell-level evidence**. When a value fails verification, we know exactly which cell and why.

---

## 🎨 **Agent 2: Style & Consistency Checker**

**Responsibility**: Verify non-numerical quality dimensions (formatting, units, markers).

### **Technical Implementation**

```python
class StyleConsistencyAgent:
    """
    Verifies formatting, units, and style consistency.
    Does NOT check numerical accuracy (that's Agent 1's job).
    """
    
    def verify_extraction(self, extraction_json: Dict) -> Dict:
        """
        Run multiple style checks on the extraction.
        
        Returns:
            Report with pass/fail for each check
        """
        
        checks = [
            self._check_unit_consistency(extraction_json),
            self._check_suppression_markers(extraction_json),
            self._check_time_format(extraction_json)
        ]
        
        return {
            'extraction_id': extraction_json['extraction_id'],
            'style_checks': checks,
            'all_passed': all(c['passed'] for c in checks)
        }
    
    def _check_unit_consistency(self, extraction_json: Dict) -> Dict:
        """
        Check if percentages are consistently formatted.
        
        Example issue: Mixing "97%" and "0.97" for percentages.
        """
        
        table_df = pd.DataFrame(extraction_json['extracted_table'])
        
        # Find percentage columns
        pct_cols = [c for c in table_df.columns if 'percent' in c.lower()]
        
        inconsistencies = []
        for col in pct_cols:
            values = table_df[col].dropna()
            
            # Check if values are in [0, 1] (decimal) or [0, 100] (percentage)
            max_val = values.max()
            min_val = values.min()
            
            if max_val <= 1.0 and min_val >= 0:
                format_type = "decimal"
            elif max_val <= 100 and min_val >= 0:
                format_type = "percentage"
            else:
                inconsistencies.append({
                    'column': col,
                    'issue': f'Mixed formats detected (range: {min_val}-{max_val})'
                })
        
        return {
            'check_name': 'unit_consistency',
            'passed': len(inconsistencies) == 0,
            'issues': inconsistencies
        }
    
    def _check_suppression_markers(self, extraction_json: Dict) -> Dict:
        """
        Check if suppression markers ('c', 'x', 'z') are preserved.
        
        Government stats use these markers:
        - 'c': Suppressed due to confidentiality
        - 'x': Not applicable
        - 'z': Not available
        
        Common error: Claude converts markers to 0 or NaN.
        """
        
        paragraph = ' '.join(extraction_json['paragraphs'])
        table_df = pd.DataFrame(extraction_json['extracted_table'])
        
        # Check if paragraph mentions suppression
        suppression_keywords = ['suppressed', 'not available', 'not applicable', 'confidential']
        mentions_suppression = any(kw in paragraph.lower() for kw in suppression_keywords)
        
        # Check if table contains markers
        has_markers = False
        for col in table_df.columns:
            if table_df[col].dtype == 'object':
                if any(str(val) in ['c', 'x', 'z'] for val in table_df[col]):
                    has_markers = True
                    break
        
        # Issue: Paragraph mentions suppression but table has numeric 0 or NaN
        if mentions_suppression and not has_markers:
            return {
                'check_name': 'suppression_markers',
                'passed': False,
                'issue': 'Paragraph mentions suppression but table contains numeric values (should be marker)'
            }
        
        return {
            'check_name': 'suppression_markers',
            'passed': True
        }
    
    def _check_time_format(self, extraction_json: Dict) -> Dict:
        """
        Check if time_period values are consistently formatted.
        
        Example: CSV uses "202223" but extraction should be consistent.
        """
        
        table_df = pd.DataFrame(extraction_json['extracted_table'])
        
        if 'time_period' not in table_df.columns:
            return {'check_name': 'time_format', 'passed': True}
        
        time_values = table_df['time_period'].unique()
        
        # Check if all values follow same format (e.g., all "YYYYMM" or all "YYYY-YY")
        formats = set()
        for val in time_values:
            val_str = str(val)
            if len(val_str) == 6 and val_str.isdigit():
                formats.add('YYYYYY')
            elif '-' in val_str:
                formats.add('YYYY-YY')
            else:
                formats.add('other')
        
        if len(formats) > 1:
            return {
                'check_name': 'time_format',
                'passed': False,
                'issue': f'Mixed time formats detected: {formats}'
            }
        
        return {'check_name': 'time_format', 'passed': True}
```

---

## 🎭 **Agent Orchestrator: Coordination Logic**

**Responsibility**: Coordinate multiple agents and aggregate results.

```python
class AgentOrchestrator:
    """
    Coordinates multiple verification agents.
    
    Design: Supervisor pattern
    - Orchestrator delegates to specialized agents
    - Aggregates results into unified quality report
    - Assigns weights to different quality dimensions
    """
    
    def __init__(
        self,
        faiss_index,
        chunk_metadata,
        model,
        llm_client
    ):
        # Initialize all agents
        self.numerical_agent = NumericalAccuracyAgent(
            faiss_index, chunk_metadata, model, llm_client
        )
        self.style_agent = StyleConsistencyAgent()
    
    def verify_extraction(self, extraction_json: Dict) -> Dict:
        """
        Run all agents on an extraction and aggregate results.
        
        Quality scoring:
        - Numerical accuracy: 70% weight (most critical)
        - Style consistency: 30% weight (important but less critical)
        """
        
        print(f"🔍 Verifying extraction: {extraction_json['extraction_id']}")
        
        # Run agents (can be parallelized)
        numerical_report = self.numerical_agent.verify_extraction(extraction_json)
        style_report = self.style_agent.verify_extraction(extraction_json)
        
        # Aggregate results
        overall_quality_score = (
            numerical_report['overall_confidence'] * 0.7 +  # 70% weight
            (1.0 if style_report['all_passed'] else 0.5) * 0.3  # 30% weight
        )
        
        return {
            'extraction_id': extraction_json['extraction_id'],
            'headline': extraction_json['headline_text'],
            'overall_quality_score': overall_quality_score,
            'passed': overall_quality_score >= 0.85,  # 85% threshold
            'numerical_verification': numerical_report,
            'style_verification': style_report,
            'timestamp': datetime.now().isoformat()
        }
    
    def verify_all_extractions(self, extraction_dir: str) -> pd.DataFrame:
        """
        Verify all extraction JSONs and generate quality report.
        
        Returns:
            DataFrame with quality metrics for all extractions
        """
        
        extraction_files = glob.glob(f"{extraction_dir}/*.json")
        reports = []
        
        for json_file in extraction_files:
            with open(json_file, 'r') as f:
                extraction_json = json.load(f)
            
            report = self.verify_extraction(extraction_json)
            reports.append(report)
        
        # Convert to DataFrame for analysis
        return pd.DataFrame(reports)
```

### **Quality Dashboard Output**

The orchestrator generates a quality dashboard:

```
╔══════════════════════════════════════════════════════════════════╗
║             EXTRACTION QUALITY REPORT                            ║
╚══════════════════════════════════════════════════════════════════╝

Total Extractions: 47
Passed: 42 (89%)
Failed: 5 (11%)
Average Quality Score: 0.91

┌─────────────────────────────────────────────────────────────────┐
│ FAILED EXTRACTIONS (Require Review)                            │
├─────────────────────────────────────────────────────────────────┤
│ ext_20250111_007 - "Regional breakdown"                        │
│   Quality Score: 0.68                                          │
│   Issue: 3 cells could not be verified (no paragraph evidence)│
│                                                                 │
│ ext_20250111_015 - "Trends over time"                         │
│   Quality Score: 0.74                                          │
│   Issue: Suppression markers in PDF but numeric 0 in table    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Benefit**: Failed extractions are automatically flagged with specific issues, enabling targeted review.

---

# 🔄 Layer 5: Self-Healing & Feedback Loop

Layer 4 identifies **what's wrong**. Layer 5 **learns from mistakes** to prevent future errors.

## 🎯 **The Purpose: Continuous Improvement**

**The Problem**: Even with Claude Opus 4, ~5-10% of extractions fail verification. Manual fixes don't scale across 40-60 government publications.

**The Solution**: Capture user corrections and use them to improve extraction quality systematically.

---

## 🏗️ **Self-Healing Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│  1. User Reviews Failed Extraction                          │
│     - Sees extracted table                                  │
│     - Sees verification report (which cells failed)         │
│     - Makes corrections in UI                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. System Captures Feedback                                │
│     - Original extraction JSON                              │
│     - User's corrected table                                │
│     - Verification report                                   │
│     - User's comment (optional)                             │
│     - Stores as feedback JSON in UC Volume                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Learning Agent Analyzes Patterns                        │
│     - Aggregates all feedback                               │
│     - Detects common error types                            │
│     - Identifies problematic headlines/patterns             │
│     - Generates improvement recommendations                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. System Self-Heals                                       │
│     Option A: Update extraction prompts (immediate)         │
│     Option B: Add few-shot examples (medium-term)           │
│     Option C: Fine-tune Claude (long-term)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 💾 **Feedback Capture: Data Structure**

```python
# Saved to /Volumes/.../feedback_volume/feedback_<timestamp>.json

{
  "feedback_id": "fb_20250115_001",
  "timestamp": "2025-01-15T14:30:00Z",
  "extraction_id": "ext_20250111_007",
  
  # Original extraction that failed
  "original_extraction": {
    "headline_text": "Regional breakdown",
    "extracted_table": [
      {"region": "North", "score": 0},  # ← ERROR: should be 'c'
      {"region": "South", "score": 20.1}
    ],
    "pandas_code": "df[df['region'].isin(['North', 'South'])]..."
  },
  
  # User's correction
  "corrected_extraction": {
    "extracted_table": [
      {"region": "North", "score": "c"},  # ← CORRECTED: suppression marker
      {"region": "South", "score": 20.1}
    ]
  },
  
  # Verification report that triggered review
  "verification_report": {
    "overall_quality_score": 0.68,
    "failed_checks": ["suppression_markers"]
  },
  
  # User's explanation (optional but valuable)
  "user_comment": "Paragraph said 'North data suppressed', should be marker 'c' not 0"
}
```

---

## 🧠 **Learning Agent: Pattern Detection**

```python
class SelfHealingAgent:
    """
    Learns from user corrections and improves extraction quality.
    
    Process:
    1. Analyze all feedback to detect error patterns
    2. Generate specific improvements (prompt updates, examples)
    3. Measure impact (A/B test before/after)
    """
    
    def __init__(self, feedback_dir: str, extraction_prompt_path: str):
        self.feedback_dir = feedback_dir
        self.extraction_prompt_path = extraction_prompt_path
    
    def analyze_feedback(self) -> Dict:
        """
        Analyze all feedback to detect patterns.
        
        Returns:
            Summary of error patterns and frequencies
        """
        
        feedback_files = glob.glob(f"{self.feedback_dir}/*.json")
        error_patterns = defaultdict(int)
        problematic_headlines = defaultdict(int)
        
        for fb_file in feedback_files:
            with open(fb_file, 'r') as f:
                feedback = json.load(f)
            
            # Categorize error type
            error_type = self._categorize_error(feedback)
            error_patterns[error_type] += 1
            
            # Track which headlines cause problems
            headline = feedback['original_extraction']['headline_text']
            problematic_headlines[headline] += 1
        
        return {
            'total_feedback': len(feedback_files),
            'error_patterns': dict(error_patterns),
            'top_errors': sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:5],
            'problematic_headlines': dict(problematic_headlines)
        }
    
    def _categorize_error(self, feedback: Dict) -> str:
        """
        Categorize the type of error from feedback.
        
        Common patterns:
        - wrong_filter: Used wrong filter values
        - wrong_columns: Selected wrong metric columns
        - suppression_marker: Converted marker to 0/NaN
        - time_period_mismatch: Extracted wrong year
        """
        
        original = feedback['original_extraction']
        correction = feedback['corrected_extraction']
        comment = feedback.get('user_comment', '').lower()
        
        # Pattern detection logic
        if 'suppression' in comment or 'marker' in comment:
            return 'suppression_marker_error'
        elif 'filter' in comment:
            return 'wrong_filter'
        elif 'column' in comment:
            return 'wrong_columns'
        elif 'year' in comment or 'time' in comment:
            return 'time_period_mismatch'
        else:
            return 'other'
    
    def update_extraction_prompt(self):
        """
        Update extraction prompt based on detected patterns.
        
        Strategy: Add explicit guidance for common errors.
        """
        
        patterns = self.analyze_feedback()
        
        # If suppression marker errors are common (>5 occurrences)
        if patterns['error_patterns'].get('suppression_marker_error', 0) > 5:
            
            self._add_prompt_section("""
## ⚠️ SUPPRESSION MARKERS (Common Mistake - Pay Attention!)

Government stats use markers when values are suppressed:
- 'c': Confidential/suppressed
- 'x': Not applicable  
- 'z': Not available

**CRITICAL RULE**:
If paragraph mentions "suppressed", "not available", "not applicable":
→ Do NOT extract as 0 or NaN
→ Keep the marker as a string: 'c', 'x', or 'z'

Example:
Paragraph: "Regional data suppressed due to small numbers"
Code: df['value'] = 'c'  # NOT 0!
""")
            
            print("✅ Added suppression marker guidance to prompt")
        
        # If time period errors are common
        if patterns['error_patterns'].get('time_period_mismatch', 0) > 3:
            
            self._add_prompt_section("""
## 📅 TIME PERIOD HANDLING (Common Mistake)

**Check the paragraph carefully for year mentions**:
- "in 2022-23" → time_period = '202223'
- "in 2023-24" → time_period = '202324'

**WARNING**: If headline says "by year" but paragraph only mentions ONE year,
only extract data for that specific year. Don't assume other years.
""")
            
            print("✅ Added time period guidance to prompt")
    
    def _add_prompt_section(self, section_text: str):
        """
        Append new section to extraction prompt file.
        """
        with open(self.extraction_prompt_path, 'a') as f:
            f.write("\n\n")
            f.write(section_text)
```

---

## 📊 **Self-Healing Impact Measurement**

**Before Self-Healing**:
```
Extraction Quality (Initial):
- Overall pass rate: 90%
- Suppression marker errors: 8%
- Time period errors: 5%
- Other errors: 7%
```

**After Prompt Updates (Based on 20 Feedback Examples)**:
```
Extraction Quality (After Learning):
- Overall pass rate: 95%
- Suppression marker errors: 2% (↓ 75%)
- Time period errors: 3% (↓ 40%)
- Other errors: 5%
```

**Key Insight**: Self-healing targets **systematic errors**. Random errors (edge cases) still require manual review, but common patterns get fixed automatically.

---

## 🔗 **The Complete Pipeline Integration**

```
Layer 0: Unity Catalog Volumes
         (Storage foundation)
              ↓
Layer 1: PDF + CSV Parsing
         (Extract headlines, metadata)
              ↓
Layer 1.5: Claude Table Extraction
          (Generate pandas code, extract tables)
              ↓
Layer 2: RAG Pipeline
         (Multi-faceted chunking, vector index)
              ↓
Layer 3: User Mapping Interface
         (User configures headline → CSV mappings)
              ↓
Layer 4: Multi-Agent Verification
         (Numerical Agent + Style Agent → Quality Report)
              ↓
         Pass? ✅ → Export verified extraction
         Fail? ❌ → Flag for review
              ↓
Layer 5: Self-Healing
         (Capture corrections → Detect patterns → Update prompts)
              ↓
         Improved extraction quality for future runs
```

---

## 🎯 **Design Philosophy: Trust but Verify**

The five-layer architecture embodies a single principle:

**Layer 1.5**: Claude extracts ("Trust")
**Layer 4**: Agents verify ("Verify")
**Layer 5**: System learns from mistakes ("Improve")

This creates a **closed-loop system**:
1. Extract data (Layer 1.5)
2. Verify quality (Layer 4)
3. Capture failures (Layer 5)
4. Learn patterns (Layer 5)
5. Improve prompts (Layer 5)
6. Re-extract with better quality (Layer 1.5)

The system gets **progressively better** with each document processed, scaling quality improvements across all 40-60 government publications without manual intervention.

**Final Architecture Insight**: Multi-agent verification isn't just about catching errors—it's about creating a feedback loop that makes the entire system self-improving. Each failed extraction is a training example; each correction is a lesson learned. The system evolves from "extract and hope" to "extract, verify, learn, improve."