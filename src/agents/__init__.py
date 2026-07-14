"""
Agents Package

Exposes:
- TableExtractorAgent: Main orchestrator for table extraction pipeline
- TABLE_EXTRACTION_PROMPT: Prompt template for LLM code generation
"""

from .table_extractor_agent import TableExtractorAgent
from .prompts.table_extraction_prompt import TABLE_EXTRACTION_PROMPT

__all__ = [
    'TableExtractorAgent',
    'TABLE_EXTRACTION_PROMPT'
]
