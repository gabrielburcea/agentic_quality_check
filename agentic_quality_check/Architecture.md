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
* **Components**: Document loaders, text splitters
* **Flow**: PDF files → `PyPDF2` (free) or `LangChain PDF loader` → Text chunks (with overlap for context preservation)
* **Storage Options**:
  * **Free/Local**: Local filesystem, read directly from disk
  * **Databricks**: Unity Catalog Volumes (`/Volumes/catalog/schema/volume/`) for managed, governed storage with ACL controls
* **Output**: List of text chunks ready for embedding

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
  3. **Response Generator Agent** takes context + question → generates answer (using local model or Databricks FM)
  4. **Quality Checker Agent** evaluates answer (factual accuracy, completeness, citation presence)
  5. **Conditional routing**: 
     * Pass → Return to user
     * Fail → Loop back to Response Generator with feedback
* **State Management**: LangGraph maintains the conversation history, retrieved documents, quality scores, and iteration count across the loop
* **Execution Environment**:
  * **Free/Local**: Run on local machine or free cloud compute (Google Colab, Kaggle)
  * **Databricks**: Run on Databricks cluster or serverless compute, integrate with Databricks Jobs for scheduling
* **Output**: Final validated answer with citations

**Layer 4: User Interface (Streamlit/Databricks Apps)**
* **Components**: Chat interface, document upload widget, agent execution logs
* **UI Options**:
  * **Free**: Streamlit — Python-based web framework, run locally or deploy to Streamlit Cloud
  * **Databricks**: Databricks Apps — deploy directly to workspace, integrated with Unity Catalog for data access and authentication
* **Flow**: User input → LangGraph execution (Layer 3) → Display response + trace of agent decisions
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
│  PDF Files                                                                       │
│      ↓                                                                           │
│  [PyPDF2 Loader]  ──────────→  [LangChain Text Splitter]                       │
│                                  (chunk_size=1000, overlap=200)                 │
│      ↓                                                                           │
│  Text Chunks (List[str])                                                        │
│                                                                                  │
│  Storage:                                                                        │
│   • Free: Local filesystem                                                      │
│   • Databricks: Unity Catalog Volumes (/Volumes/catalog/schema/volume/)        │
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
│  │ RAG pipeline    │      │        ↓            │      │ • Accuracy        │ │
│  │                 │      │ Generate answer     │      │ • Completeness    │ │
│  │ Returns docs    │      │ using LLM           │      │ • Citations       │ │
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
│  │                               │     │                                  │    │
│  │ • Chat interface              │     │ • Integrated with workspace      │    │
│  │ • Document upload widget      │     │ • Unity Catalog auth             │    │
│  │ • Agent execution trace       │     │ • Direct access to UC data       │    │
│  │ • Run locally or deploy       │     │ • Deploy to workspace            │    │
│  │   to Streamlit Cloud          │     │                                  │    │
│  └───────────────────────────────┘     └──────────────────────────────────┘    │
│                                                                                  │
│  Display:                                                                        │
│   • User question                                                               │
│   • Retrieved context (with sources)                                            │
│   • Generated answer                                                            │
│   • Quality score                                                               │
│   • Agent decision trace (which agents were invoked, why, and in what order)    │
└─────────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════
KEY ARCHITECTURAL DECISIONS
═══════════════════════════════════════════════════════════════════════════════════

1. DUAL-PATH DESIGN: Every component has free and Databricks options
   → Develop on free tools, migrate to Databricks for production scale

2. LANGCHAIN ABSTRACTION: Unified API regardless of backend
   → Switch from FAISS to Vector Search without changing retrieval code

3. LANGGRAPH ORCHESTRATION: Stateful, cyclic agent workflows
   → Quality feedback loops impossible with simple chains

4. MODULAR LAYERS: Each layer has clear input/output contracts
   → Easy to test, debug, and optimize independently
```

---

### RAG Layer Boundaries

**Where RAG Starts**: When the Retrieval Agent in LangGraph calls `retriever.get_relevant_documents(query)`

**Where RAG Stops**: When the retrieved `Document` objects (text + metadata) are returned to LangGraph state

**Key Insight**: RAG is a **service layer** invoked by agents — it doesn't orchestrate or make decisions. LangGraph controls *when* to retrieve, *how many times* to retrieve (e.g., re-retrieve after refinement), and *what to do* with the results.

---

## Technology Comparison Table

| Component | Free/Open-Source | Databricks | Trade-offs |
|-----------|------------------|------------|------------|
| **Document Storage** | Local filesystem | Unity Catalog Volumes | Free: Simple, local. DB: Governed, versioned, ACLs |
| **Embeddings** | sentence-transformers (local) | Foundation Models API | Free: Runs anywhere. DB: Optimized, serverless |
| **Vector Store** | FAISS (in-memory) | Vector Search | Free: Fast prototyping. DB: Persistent, scalable, auto-sync |
| **LLM** | HuggingFace (local GPU) | Foundation Models API | Free: No cost per token. DB: No infra, larger models |
| **Orchestration** | Local Python process | Databricks Workflows/Jobs | Free: Simple. DB: Scheduled, monitored, retries |
| **UI** | Streamlit (local/cloud) | Databricks Apps | Free: Quick iteration. DB: Integrated auth, data access |

**Recommendation**: Start with free tools for development and prototyping. Migrate to Databricks for production when you need:
* Persistent vector indexes (don't rebuild FAISS on every restart)
* Governed data access (Unity Catalog permissions)
* Serverless LLM inference (no GPU management)
* Production monitoring and scheduling