"""
Configuration module for agentic quality check system.

Centralised all paths, model settings, RAG parameters and Databricks options. Support BOTH Databricks-managed service AND free/open-source alternatives.
Architecture Support:
- Layer 1: Document & CSV ingestion with headline extraction
- Layer 2: Semantic chunking + embedding + vector store
- Layer 3: Headline-toCSV mapping storage
- Layer 4: Multi-agent orchestration with RAG retrieval
- Layer 5: Self healing feedback loop


Usage:
  from config import PATHS, DATABRICKS_MODELS, FREE_MODELS, RAG_CONFIG 
"""

import os

# Unity Catalog configuration
UC_CONFIG = {
    'catalog': 'my_catalog',
    'schema': 'agentic_quality_check_dev',
    'volumes': {
        'pdfs': 'pdfs_volume',           # Raw PDF uploads
        'csvs': 'csvs_volume',           # Raw CSV data files
        'processed': 'processed_volume',  # Embeddings, FAISS indexes, chunks
        'mappings': 'mappings_volume',    # Headline-to-CSV mapping metadata
        'feedback': 'feedback_volume'     # User feedback for self-healing
    }
}
    

# Storage paths using Unity Catalog Volumes

PATHS = {
    'pdfs': f"/Volumes/{UC_CONFIG['catalog']}/{UC_CONFIG['schema']}/{UC_CONFIG['volumes']['pdfs']}/",
    'csvs': f"/Volumes/{UC_CONFIG['catalog']}/{UC_CONFIG['schema']}/{UC_CONFIG['volumes']['csvs']}/",
    'processed': f"/Volumes/{UC_CONFIG['catalog']}/{UC_CONFIG['schema']}/{UC_CONFIG['volumes']['processed']}/",
    'mappings': f"/Volumes/{UC_CONFIG['catalog']}/{UC_CONFIG['schema']}/{UC_CONFIG['volumes']['mappings']}/",
    'feedback': f"/Volumes/{UC_CONFIG['catalog']}/{UC_CONFIG['schema']}/{UC_CONFIG['volumes']['feedback']}/"
}

# Model Configurations (I will use the models in Layer 2)

DATABRICKS_MODELS = {
    # Embedding models via Databricks Foundation Model APIs
    'embedding': {
        'provider': 'databricks', 
        'model_name': 'databricks-bge-large-en', 
        'endpoint': 'foundation-model-api', 
        'dimension': 1024, 
        'max_tokens': 512, 
        'use_case': 'Semantic search for document chuncks and CSV column matching'
    }, 
    # LLM for Agents via Databricks Model Serving
    'llm': {
        'provider': 'databricks', 
        'model_name': 'databricks-meta-llama-3-1-70b-instruct', 
        'endpoint': 'foundation_model_api', 
        'temperature': 0.0,
        'max_tokens': 2048, 
        'use_case': 'Numerical accuracy verification and style checking'
    }, 
    # Alternative: Custom fine-tuned model (if I train one later?)
    'llm_custom': {
        'provider': 'databricks', 
        'model_name': 'custom-statistical-qa-model', 
        'endpoint': 'custom-model-serving-endpoint',
        'temperature': 0.0, 
        'max_tokens': 2048, 
        'use_case': 'Fine-tuned statistical report validation'
    }
}


FREE_MODELS = {
    'embedding': {
        'provider': 'huggingface', 
        'model_name': 'sentence-transformers/all-MiniLM-L6-v2',
        'dimension': 384,
        'max_tokens': 256,
        'use_case': 'Fast CPU inference for semantic search'
    },
    # LLM from HuggingFace (smaller models fit in memory)
    'llm': {
        'provider': 'huggingface', 
        'model_name': 'microsoft/phi-2',    # Phi-2: 2.7B params, good for reasoning
        'temperature': 0.0, 
        'max_tokens': 2048, 
        'use_case': 'Local inference for development/testing'
    },
    # Alternative smaller LLM
    'llm_tiny': {
        'provider': 'huggingface', 
        'model_name': 'TinyLlama/TinyLlama-1.1b-Chat-v1.0', 
        'temperature': 0.0, 
        'max_tokens': 2048, 
        'use_case': 'Very fast inference, lower quality'
    }
}

# Active model selection (switch between Databricks and FREE)

ACTIVE_MODELS = {
    'embedding': DATABRICKS_MODELS['embedding'],
    'llm': DATABRICKS_MODELS['llm']
}

# RAG parameters (I will use these in layer 2)
RAG_CONFIG = {
    # Chunking strategy
    'chunking': 'semantic',  # Options: 'semantic', 'fixed_size', 'headlines_based'

    # Semantic chunking (uses sentence boundaries + embeddings)
    'semantic': {
        'method': 'sentence_similarity',  # Break when similarity drops
        'min_chunk_size': 100,     # Minimum characters per chunk
        'max_chunk_size': 1000,    # Maximum characters per chunk
        'similarity_threshold': 0.7,   # Cosine similarity threshold for splitting
        'use_case': 'Creates semantically coherent chunks, better retrieval quality'
    }, 

    # Headline-based chunking (preserve document structure)
    'headline_based': {
        'method': 'extract_sections',  # Break at headlines
        'include_context': True,  # Include surrounding paragraphs
        'context_window': 2,    # Number of paragraphs before/after
        'use_case': 'Preserves document structure, aligns with user-selected headlines'
    }, 
    # Fixed-size chunking (fallback)
    'fixed_size': {
        'chunk_size': 500,   # Characters per chunk
        'chunk_overlap': 100,    # Overlap for context preservation
        'use_case': 'Simple, fast but may break semantic units'
    }, 

    # Vector store configuration 
    'vector_store': {
        # Databricks Vector Search (managed service)
        'databricks': {
            'provider': 'databricks_vector_search', 
            'endpoint_name': 'agentic_quality_check_vs_endpoint', 
            'index_name': f"{UC_CONFIG['catalog']}.{UC_CONFIG['schema']}.document_chunks_index",
            'index_type': 'DELTA_SYNC',   # Auto-sync with Delta Table
            'similarity_metric': 'cosine', 
            'use_case': 'Managed, auto-synced, scales automatically'
        }, 
        'faiss': {
            'provider': 'faiss', 
            'index_type': 'IndexFlatL2',  # Exact search, good for small datasets
            'index_path': f"{PATHS['processed']}faiss_index.bin", 
            'similarity_metric': 'L2',    # Euclidean distance
            'use_case': 'Local, fast, no external dependencies'
        }, 
        # Active vector store selection 
        'active': 'databricks'  # Change to 'faiss' for free option
    }, 

    # Retrieval parameters
    'retrieval': {
        'top_k': 5,   # Number of chunks to retrieve per query
        'rerank': True,    # Re-rank retrieved chunks using LLM
        'rerank_top_k': 3,   # Final number after re-ranking
        'include_metadata': True,  # Return chunk metadata (headline, page, section)
        'filters': {
            'by_headline': True,   # Filter by user-selected headline 
            'by_document': True    # Filter by specific PDF (if multiple uploaded)
        }
    }, 
    'csv_indexing': {
        'strategy': 'semantic_columns',    # Indexing column names descriptions semantically 
        'embed_column_names': True,    # Create embeddings for column names
        'embed_value_samples': True,     # Embed sample values for better matching
        'metadata': {
            'extract_statistics': True,  # Min, total, sums, averages, max, mean, std for numerical columns
            'extract_unique_values': True,     # Unique values for categorical columns
            'detect_data_type': True      # Auto-detect data types
        }
    }
}

# Headline-TO-CSV Mapping Configurations 

MAPPING_CONFIG = {
    # Where to store user-created mappings
    'storage': {
        'format': 'json',  # JSON or Delta table
        'path': f"{PATHS['mappings']}headline_csv_mappings.json",
        'delta_table': f"{UC_CONFIG['catalog']}.{UC_CONFIG['schema']}.headline_mappings"
    }, 
    # Mapping structure (what gets stored)
    'schema': {
        'headline_id': 'str',    # Unique ID for the headline
        'headline_text': 'str',    # The actual headline text
        'csv_columns': 'list[str]',  # List of CSV column names to query
        'csv_filters': 'dict',    # Filters to apply (e.g. {"year": 2022})
        'expected_calculation': 'str',    # Type mean, percentage, count, comparison
        'agent_types': 'list[str]',    # Which agents to run ['numerical', 'style']
        'created_by': 'str',   # User who created the mapping 
        'created_at': 'timestamp'
    }, 

    # Auto-suggestion (AI powered headline-CSV matching)
    'auto_suggest': {
        'enabled': True, 
        'method': 'semantic_similarity',     # Match headline text to column names/descriptions
        'confidence_threshold': 0.8,     # Only suggest if similarity >= 0.8
        'max_suggestions': 3     # Show top 3 suggestions per headline  
    }
}

# Agent CONFIGURATION 

AGENT_CONFIG = {

    # Agent 1: Numerical Accuracy Agent
    'numerical_agent': {
        'name': 'Numerical Accuracy Verifier', 
        'model': ACTIVE_MODELS['llm'], 
        'prompt_template': 'prompts/numerical_verification.txt',  # need to create this
        'capabilities': [
            'extract_numbers',   # extract numerical claims from text
            'query_csv',    # Query CSV using pandas/SQL
            'verify_calculations',   # Check percentages, means, differences
            'detect_discrepancies',    # Flag mismatches 
            'suggest_corrections'  # Generate corrections
        ],
        'rag_enabled': True,    # Use RAG to retrieve context 
        'temperature': 0.0,     # Deterministic for fact-checking 
        'max_retries': 2
    }, 

    # Agent 2: Style & Quality Agent 
    'style_agent': {
        'name': 'Style & Writing Quality Checker', 
        'model': ACTIVE_MODELS['llm'], 
        'prompt_template': 'prompts/style_checking.txt', 
        'capabilities': [
            'check_grammar', 
            'check_tone',    # Formal, statistical tone
            'check_clarity', 
            'check_terminology',    # Consistent statistical terms
            'suggest_improvements'
        ], 
        'rag_enabled': True,    # Retrieve similar sections for consistency
        'temperature': 0.0,    
        'max_retries': 2
    }, 

    # Agent 3: Self-Healing Agent 
    'self_healing_agent': {
        'name': 'Feedback Learning Agent', 
        'model': ACTIVE_MODELS['llm'], 
        'prompt_template': 'prompts/self_healing.txt', 
        'capabilities': [
            'store_feedback',    # Store user Agree/Disagree + Commentary
            'retrieve_past_feedback',    # Retrieve similar past corrections
            'update_prompts',   # Adjust prompts based on patterns
            'reanalyse'      # Re-run analysis with improved context
        ], 
        'feedback_storage': f"{PATHS['feedback']}user_feedback.json",
        'feedback_table': f"{UC_CONFIG['catalog']}.{UC_CONFIG['schema']}.user_feedback", 
        'learning_rate': 0.1,    # How much to weight recent feedback
        'min_feedback_samples': 5   # Minimum feedback before updating prompts 
    }
}


# Streamlit UI Config

STREAMLIT_CONFIG = {
    'tabs': [
        'Document Upload', 
        'CSV Upload', 
        'Analysis', 
        'Configuration',    # This is where mapping happens
        'Result Dashboard'
    ], 

    # Session state keys (for storing data across iterations)
    'session_keys': {
        'uploaded_pdf': 'pdf_file', 
        'uploaded_csv': 'csv_file', 
        'extracted_headlines': 'headlines', 
        'headline_mappings': 'mappings',    # User created mappings
        'analysis_results': 'results', 
        'user_feedback': 'feedback'
    }, 

    # Results table configuration
    'results_tables': {
        'numerical': {
            'columns': [
                'Headline', 
                'Analyzed Text', 
                'Numbers Correct',  # Pass / Fail
                'Suggestions', 
                'Agree',    # Yes/No buttons
                'Commentary'  # Text field
            ]
        }, 
        'style': {
            'columns': [
                'Headline', 
                'Analyzed Text', 
                'Style Check',    # Pass/Fail
                'Suggestions', 
                'Agree', 
                'Commentary'
            ]
        }
    }
}

#############################################
#####  Databricks-specific features  ########
#############################################

DATABRICKS_FEATURES = {
    # MLflow tracking (tracking agent performance)
    'mlflow': {
        'enabled': True,
        'experiment_name': f"/Users/{os.getenv('USER')}/agentic-quality-check",
        'track_metrics': [
            'accuracy_agreement_rate',   # % of times user agrees with numerical agent 
            'style_agreement_rate',    # % of times user agrees with style agent 
            'average_analysis_time',   # Time per headline analysis
            'retrieval_relevance_score'  # RAG retrieval quality
        ]
    }, 
    # Feature Store (optional - for advance use)
    'feature_store': {
        'enabled': False, 
        'table': f"{UC_CONFIG['catalog']}.{UC_CONFIG['schema']}.headline_features"
    }, 

    # Model Serving endpoints
    'model_serving': {
        'numerical_agent_endpoint': 'numerical-accuracy-agent', 
        'style_agent_endpoint': 'style-quality-agent', 
        'auto_scaling': True, 
        'min_instance': 0,   # Scale to 0 when not in use
        'max_instances': 2
    }
}

# Convenience function to get full paths
def get_volume_path(volume_type: str) -> str:
    """
    Get the full Unity Catalog Volume path for a given volume type. 

    Args:
        volume_type (str): One of 'pdfs', 'csvs', 'processed', 'mappings', 'feedback'
    Returns:
        str: Full path like '/Volumes/my_catalog/agentic_quality_check_dev/csvs_volume/'
    Example:
        >>> get_volume_path('pdfs')
        '/Volumes/my_catalog/agentic_quality_check_dev/pdfs_volume/'
    """
    if volume_type not in PATHS: 
        raise ValueError(f"Invalid volume type: {volume_type}. Must be one of {list(PATHS.keys())}")
    return PATHS[volume_type]

def get_active_model(model_type: str) -> dict:
    """
    Get the currently active model configuration. 

    Args:
        model_type (str): One of 'llm', 'embedding'
    Returns:
        dict: Model configuration dictionary
    Example:
        >>> get_active_model('embedding')
        {'provider': 'databricks', 'model_name': 'databricks-bge-large-en', ...}
    """
    if model_type not in ACTIVE_MODELS:
        raise ValueError(f"Invalid model type: {model_type}. Must be one of {list(ACTIVE_MODELS.keys())}")
    return ACTIVE_MODELS[model_type]

def switch_to_free_models():
    """
    Switch all active models to free/open-source alternatives.
    Useful for development or when running locally
    """
    ACTIVE_MODELS['embedding'] = FREE_MODELS['embedding']
    ACTIVE_MODELS['llm'] = FREE_MODELS['llm']
    print("Switched to free models:")
    print(f" - Embedding: {FREE_MODELS['embedding']['model_name']}")
    print(f" - LLM: {FREE_MODELS['llm']['model_name']}")

def switch_to_databricks_models():
    """
    Switch all active models to Databricks managed services 
    Requires Databricks workspace with Foundation Model API access
    """
    ACTIVE_MODELS['embedding'] = DATABRICKS_MODELS['embedding']
    ACTIVE_MODELS['llm'] = DATABRICKS_MODELS['llm']
    print("Switched to Databricks models:")
    print(f" - Embedding: {DATABRICKS_MODELS['embedding']['model_name']}")
    print(f" - LLM: {DATABRICKS_MODELS['llm']['model_name']}")
