"""
src package for agentic quality system checl
This package contains:
- config: Configuration and paths
- agents: Multi-agent system component
- rag: RAG retrieval and vector store 
- utils: Utility function 
"""
from .config import (
    PATHS, 
    MODELS, 
    UC_CONFIG, 
    DATABRICKS_MODELS, 
    FREE_MODELS, 
    ACTIVE_MODELS, 
    MAPPING_CONFIG, 
    AGENT_CONFIG, 
    STREAMLIT_CONFIG, 
    DATBRICKS_FEATURES,  
    RAG_CONFIG, 
    get_volume_path, 
    get_active_models, 
    switch_to_free_models,
    switch_to_databricks_models

__all__ = [
    'PATHS', 
    'MODELS', 
    'UC_CONFIG', 
    'DATABRICKS_MODELS', 
    'FREE_MODELS', 
    'ACTIVE_MODELS', 
    'MAPPING_CONFIG', 
    'AGENT_CONFIG', 
    'STREAMLIT_CONFIG', 
    'DATBRICKS_FEATURES',  
    'RAG_CONFIG', 
    'get_volume_path', 
    'get_active_models', 
    'switch_to_free_models',
    'switch_to_databricks_models'

]
# Package metadata
__version__ = "0.1.0"