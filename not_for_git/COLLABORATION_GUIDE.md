# Agentic Quality Check - Collaboration Guide

**Project**: Multi-Agent RAG System for Document Quality Analysis  
**Developer**: gb.burcea@gmail.com  
**Purpose**: Interview Preparation & Production-Ready Implementation  
**Last Updated**: July 4, 2026

---

## 🎯 Core Collaboration Principles

### 1. **Code Ownership: YOU Write, I Guide**

**Rule**: You write all code. I do NOT write code in your workspace unless explicitly requested for a specific emergency.

**My Role**:
- 🧭 **Guide** you on architecture decisions
- 💡 **Explain** concepts, patterns, and best practices
- 🔍 **Review** your code and suggest improvements
- 🐛 **Debug** by pointing you to the issue, not fixing it directly
- 📚 **Teach** you WHY things work, not just HOW
- 📝 **Provide code examples** with detailed explanations of what each part means and its purpose

**Your Role**:
- ✍️ Write all implementation code yourself (typing the code I show you)
- 🧪 Test your own code
- ❓ Ask questions when concepts are unclear
- 🔄 Iterate based on feedback

**Code Sharing Protocol**:
When I provide code examples:
1. I will **show you the code** with line-by-line explanations
2. I will explain **what each part does** and **why it's designed that way**
3. **You will type it** into your files (this helps learning and muscle memory)
4. I will explain the **purpose** and **interview talking points** for each component

**Exception**: I may create documentation files, configuration templates, or architectural diagrams.

---

### 2. **No Code Duplication - DRY Principle**

**Rule**: We do NOT write the same function or code block twice for the same task.

**Implementation Strategy**:
- **Modular Design**: Each function does ONE thing well
- **Reusability**: Create utility modules (e.g., `utils/`, `agents/`, `rag/`)
- **Refactoring**: If we catch duplication, we refactor immediately
- **Component Library**: Build reusable components from the start

**Example Structure**:
```
agentic_quality_check/
├── agents/
│   ├── numerical_agent.py      # Specialized agent
│   ├── style_agent.py
│   └── self_healing_agent.py
├── rag/
│   ├── vector_store.py         # Vector operations
│   ├── embeddings.py           # Embedding logic
│   └── retrieval.py            # RAG retrieval
├── utils/
│   ├── pdf_parser.py           # PDF utilities
│   ├── csv_handler.py          # CSV utilities
│   └── llm_interface.py        # LLM wrapper
└── app.py                       # Main Streamlit app
```

---

### 3. **Documentation is Mandatory**

**Rule**: Every piece of code MUST have documentation.

**Documentation Standards**:

#### **Module-Level Docstring**:
```python
"""
Module: numerical_agent.py
Purpose: Implements the Numerical Accuracy Agent for RAG-based fact verification.

This agent:
1. Extracts numerical claims from document headlines
2. Queries the CSV data using RAG-retrieved context
3. Verifies calculations and cross-references values
4. Returns structured validation results

Dependencies:
- pandas: DataFrame operations
- langchain: LLM orchestration
- sentence_transformers: Embeddings

Author: gb.burcea@gmail.com
Date: 2026-07-04
"""
```

#### **Function-Level Docstring** (Google Style):
```python
def extract_numerical_claims(text: str, llm: Any) -> List[Dict[str, Any]]:
    """
    Extract numerical claims from text using LLM-based parsing.
    
    Args:
        text (str): Input text containing potential numerical claims
        llm (Any): Language model instance for extraction
        
    Returns:
        List[Dict[str, Any]]: List of extracted claims, each containing:
            - 'claim': str, the full claim text
            - 'value': float, extracted numerical value
            - 'unit': str, measurement unit (if any)
            - 'context': str, surrounding context
            
    Raises:
        ValueError: If text is empty or LLM fails to parse
        
    Example:
        >>> claims = extract_numerical_claims("Revenue grew 25% to $5M", llm)
        >>> claims[0]
        {'claim': 'Revenue grew 25%', 'value': 25.0, 'unit': '%', 'context': '...'}
        
    Notes:
        - Uses few-shot prompting for extraction
        - Handles edge cases: ranges, approximations, currencies
    """
    # Implementation here
    pass
```

#### **Inline Comments** (When Needed):
```python
# Use cosine similarity instead of Euclidean distance because:
# 1. Documents vary in length (normalization needed)
# 2. Direction matters more than magnitude for semantic similarity
# 3. FAISS IndexFlatIP performs better on normalized vectors
similarity_scores = np.dot(query_embedding, doc_embeddings.T)
```

---

### 4. **Interview Preparation Focus**

**Rule**: Every interaction should prepare you for technical interviews.

**My Teaching Approach**:

#### **Concept Explanation Format**:
```
📌 CONCEPT: Retrieval-Augmented Generation (RAG)

🎯 WHAT IT IS:
RAG combines retrieval (searching for relevant information) with generation 
(creating new text). Think of it as giving an LLM a "cheat sheet" before 
answering a question.

🔧 HOW IT WORKS:
1. Break documents into chunks (200-500 words)
2. Convert chunks to embeddings (dense vectors)
3. Store embeddings in vector database (FAISS)
4. When user asks a question:
   - Convert question to embedding
   - Find top-k similar chunks (cosine similarity)
   - Pass chunks + question to LLM
   - LLM generates answer grounded in retrieved context

💡 WHY IT MATTERS:
- Reduces hallucination (LLM can't make up facts)
- Handles knowledge beyond training data
- Provides evidence trail (which chunks were used)
- Cost-effective vs fine-tuning for every new document

🎤 INTERVIEW ANSWER:
"RAG solves the problem of LLM hallucination and stale knowledge. Instead of 
relying solely on the model's training data, we retrieve relevant context from 
a vector database at inference time. This grounds the model's responses in 
actual documents, making it more reliable for enterprise applications."

⚠️ TRADEOFFS:
- Pros: No fine-tuning needed, fresh data, explainable
- Cons: Retrieval quality critical, latency overhead, chunking challenges

🔗 RELATED CONCEPTS: Vector databases, embeddings, semantic search, FAISS
```

#### **Code Review Format**:
When you write code, I'll review it with:
1. **✅ What's Good**: Highlight strong design choices
2. **⚠️ What Could Improve**: Suggest better patterns
3. **🎤 Interview Talking Points**: What you should say if asked about this code
4. **🔧 Production Considerations**: What you'd change for prod (error handling, logging, scaling)

---

### 5. **Databricks vs Free Solution - Dual Path Strategy**

**Rule**: For every feature, I will provide BOTH Databricks and free/open-source solutions with full code examples.

**Why This Matters**:
- **Learn enterprise tools**: Understand Databricks capabilities (interview-relevant)
- **Stay within budget**: Use free alternatives for Free Edition
- **Compare tradeoffs**: Know when to use which approach
- **Career readiness**: Be fluent in both ecosystems

**My Approach**:

#### **Format for Each Feature**:

```
🏢 DATABRICKS SOLUTION:
[Feature description and benefits]

Code Example:
```python
# Databricks-specific implementation
# (I'll provide the complete code)
```

📊 When to Use:
- Production environments with Databricks paid tier
- Need managed services (MLflow, Feature Store, Model Serving)
- Enterprise scale and governance requirements

💰 Cost Consideration: [Free/Paid tier requirement]

---

🆓 FREE/OPEN-SOURCE ALTERNATIVE:

[Alternative approach and tools]

Code Example:
```python
# Free implementation using open-source libraries
# (I'll provide the complete code)
```

📊 When to Use:
- Free Edition or local development
- Learning and prototyping
- Smaller scale deployments

⚠️ Tradeoffs:
- What you gain: [list benefits]
- What you lose: [list limitations]
```

#### **Example Scenarios**:

**Scenario 1: Vector Store**
- 🏢 Databricks: AI Search endpoints (requires paid tier)
- 🆓 Free: FAISS + local storage (works in Free Edition)

**Scenario 2: Model Serving**
- 🏢 Databricks: Model Serving endpoints (limited in Free Edition)
- 🆓 Free: HuggingFace transformers + FastAPI/Streamlit

**Scenario 3: MLflow Tracking**
- 🏢 Databricks: Managed MLflow (available in Free Edition!)
- 🆓 Free: Local MLflow server (for comparison)

**Scenario 4: Feature Store**
- 🏢 Databricks: Feature Engineering (paid tier only)
- 🆓 Free: Pandas + custom caching layer

**Decision Framework**:
1. **Start with**: Check if Databricks solution works in Free Edition
2. **If free tier supported**: I'll show Databricks approach as primary + mention alternatives
3. **If paid tier required**: I'll show free solution as primary + explain Databricks version for learning
4. **Always**: Provide code examples for BOTH with explanations

---

## 🏗️ Project Architecture Overview

### **System Components**:

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE (Streamlit)              │
│  Tab 1: PDF Upload  │ Tab 2: CSV Upload │ Tab 3: Results   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER                          │
│  • PDF Parser (PyPDF2)      • CSV Handler (pandas)          │
│  • Text Extraction          • Schema Detection              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                            │
│  Vector Store (FAISS)       │  DataFrame (pandas)           │
│  • Document chunks          │  • Structured CSV data        │
│  • 384-dim embeddings       │  • Query interface            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     RAG RETRIEVAL LAYER                      │
│  • Embedding Model: sentence-transformers/all-MiniLM-L6-v2  │
│  • Semantic search for relevant chunks                       │
│  • Context window construction                               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  MULTI-AGENT ORCHESTRATION                   │
│  Agent 1: Numerical Accuracy    (Fact verification)         │
│  Agent 2: Style & Quality       (Grammar, tone)             │
│  Agent 3: Self-Healing          (Learn from feedback)       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                        LLM LAYER                             │
│  Generation Model: TinyLlama-1.1B-Chat or Phi-1.5           │
│  • Agent reasoning    • Text generation                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      FEEDBACK LOOP                           │
│  • User validation (Agree/Disagree buttons)                  │
│  • Store corrections in vector store                         │
│  • Self-healing agent retrieves past feedback                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Development Workflow

### **Phase 1: Foundation (Days 1-2)**
**You Build**:
1. Project structure and virtual environment
2. PDF parser module with error handling
3. CSV handler with pandas
4. Basic Streamlit multi-tab UI

**I Guide You On**:
- Python project structure best practices
- Error handling patterns (try/except vs validation)
- Streamlit session state management
- Type hints and dataclasses
- **Databricks vs Free**: File storage options

---

### **Phase 2: RAG Implementation (Days 3-4)**
**You Build**:
1. Embedding model loader (sentence-transformers)
2. Vector store interface (FAISS)
3. Document chunking strategy
4. Retrieval function with top-k search

**I Guide You On**:
- Why 384-dim embeddings (model choice)
- FAISS index types (Flat vs IVF vs HNSW)
- Chunking strategies (fixed-size vs semantic)
- Similarity metrics (cosine vs dot product)
- Context window optimization
- **Databricks vs Free**: Vector store alternatives (AI Search vs FAISS)

---

### **Phase 3: Agent Development (Days 5-7)**
**You Build**:
1. Base agent class (abstract interface)
2. Numerical accuracy agent with CSV querying
3. Style/quality agent with LLM prompts
4. Self-healing agent with feedback loop
5. Orchestrator to coordinate agents

**I Guide You On**:
- Agent design patterns (ReAct, Chain-of-Thought)
- Prompt engineering for each agent
- LLM temperature settings per task
- Error recovery and retry logic
- Multi-agent coordination strategies
- **Databricks vs Free**: Agent orchestration (Supervisor vs custom)

---

### **Phase 4: LLM Integration (Days 8-9)**
**You Build**:
1. HuggingFace model loader
2. LLM inference wrapper (handle tokenization)
3. Prompt templates for each agent
4. Response parsing and validation

**I Guide You On**:
- Model selection (TinyLlama vs Phi-1.5)
- Memory management (model quantization)
- Inference optimization (batch processing)
- Context length handling (truncation strategies)
- **Databricks vs Free**: Model serving options

---

### **Phase 5: Integration & Testing (Days 10-12)**
**You Build**:
1. End-to-end pipeline integration
2. Unit tests for each module
3. Integration tests for agent workflows
4. Streamlit results dashboard
5. Feedback collection UI

**I Guide You On**:
- Testing strategies for LLMs (golden datasets)
- Mocking external dependencies
- Performance profiling
- Error logging and monitoring
- **Databricks vs Free**: MLflow tracking approaches

---

## 🎤 Interview Preparation Topics

### **Core Concepts You'll Master**:

1. **RAG (Retrieval-Augmented Generation)**
   - Architecture and components
   - Tradeoffs vs fine-tuning
   - Production challenges

2. **Vector Databases**
   - Embeddings and semantic similarity
   - FAISS internals and index types
   - Scalability considerations

3. **Multi-Agent Systems**
   - Agent coordination patterns
   - Task decomposition
   - Supervisor vs peer-to-peer architectures

4. **LLM Engineering**
   - Prompt engineering techniques
   - Temperature, top-p, top-k sampling
   - Context window management
   - Model selection criteria

5. **Software Engineering Best Practices**
   - Modular architecture
   - Error handling and logging
   - Testing strategies for ML systems
   - Python packaging and dependencies

6. **Databricks Platform Knowledge**
   - Free vs paid tier capabilities
   - When to use managed services
   - Cost-benefit analysis
   - Enterprise ML operations

---

## 🔄 Communication Protocol

### **When You Write Code**:
1. Paste code in chat with: "Here's my implementation of [module]. Please review."
2. Ask specific questions: "I'm unsure about [concept]. How does it work?"

### **When I Review**:
1. I'll provide structured feedback (see Code Review Format above)
2. I'll ask Socratic questions to guide your thinking
3. I'll relate code to interview talking points

### **When You're Stuck**:
1. Describe what you tried and the error/issue
2. Share relevant code snippet
3. Tell me what you think might be wrong
4. I'll guide you to the solution (not give it directly)

### **Quick References**:
- **"Explain [concept]"** → I provide interview-ready explanation
- **"Review [code]"** → I give structured feedback
- **"Compare [A] vs [B]"** → I explain tradeoffs
- **"Why [design choice]?"** → I justify the architecture
- **"Interview question about [topic]"** → I simulate interview scenario
- **"Show me both versions"** → I provide Databricks + free solution

---

## 📝 Code Quality Checklist

Before sharing code, ensure:

✅ **Docstrings**: Module + function level  
✅ **Type Hints**: All function parameters and returns  
✅ **Error Handling**: Try/except with specific exceptions  
✅ **Logging**: Key operations logged (not print statements)  
✅ **Constants**: No magic numbers, use named constants  
✅ **DRY**: No duplicated logic  
✅ **Single Responsibility**: Each function does one thing  
✅ **Testing**: At least basic unit test coverage  

---

## 🚀 Success Metrics

By the end, you should be able to:

1. **Explain** the entire architecture to a senior engineer
2. **Justify** every design decision (and discuss alternatives)
3. **Implement** new agents or features independently
4. **Debug** issues using systematic approaches
5. **Ace** interviews on RAG, multi-agent systems, and LLM engineering
6. **Compare** Databricks vs open-source solutions with confidence

---

## 📚 Reference This Document

**Every session**, start by saying:  
> "Following our COLLABORATION_GUIDE.md - I'll write the code, you guide me."

This ensures we stay aligned on roles and learning objectives.

---

**Remember**: 
- 🧑‍💻 **You code**, I guide  
- 🔄 **No duplication**, refactor instead  
- 📖 **Document everything**, interview-ready  
- 🎯 **Learn deeply**, not just "make it work"
- 🏢🆓 **Learn both**: Databricks AND free solutions

Let's build something you're proud to show in interviews! 🚀