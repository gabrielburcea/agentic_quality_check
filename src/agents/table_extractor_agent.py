"""
Table Extractor Agent - Phase 1 Implementation

Purpose:
    Orchestrate the complete table extraction pipeline:
    1. Load mapping JSON (headline -> paragraph -> CSV)
    2. Analyze text to identify metrics, breakdowns, filters
    3. Generate pandas code using few-shot templates
    4. Execute code and capture output
    5. Verify correctness
    6. Save Lineage JSON

Architecture Alignment:
- Input: Mapping JSON from mappings_volume
- Process: Semantic analysis -> Code generation -> Execution -> Verification 
- Output: Lineage JSON with complete audit trail
"""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class TableExtractorAgent:
    """
    Main orchestrator for table extraction pipeline.

    Responsibilities:
    1. Load mapping JSON files
    2. Coordinate semantic analysis
    3. Generate extraction code
    4. Execute and verify
    5. Store complete lineage
    """
    def __init__(
        self, 
        mappings_dir: str = "/tmp/mappings_volume/", 
        csvs_dir: str = "/Volumes/my_catalog/agentic_quality_check_dev/csvs_volume/", 
        output_dir: str = "/tmp/extraction_results/"):
        """
        Initialise the agent with directory paths.

        Args:
            mappings_dir: Path to mapping JSON files
            csvs_dir: Path to CSV data files
            output_dir: Path to save extraction results
        """
        self.mappings_dir = Path(mappings_dir)
        self.csvs_dir = Path(csvs_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_mapping_file(self, mapping_filename: str) -> Dict[str, Any]:
        """
        Process a single mapping JSON file through the full pipeline.

        This is the main entry point that orchestrates all phases. 

        Args:
            mapping_filename: Name of the mapping JSON file

        Returns:
            Dict containing:
                - status: success or error
                - results: List of extraction results (one per headline)
                - summary: Overall statistics

        Example:
            >>> agent = TableExtractorAgent()
            >>> result = agent.process_mapping_file("test_mapping.json")
            >>> print(f"Processed {result['summary']['total_headlines']} headlines")
        """
        # Phase 1: Load mapping JSON
        mapping_path = self.mappings_dir / mapping_filename

        try:
            with open(mapping_path, "r") as f:
                mapping_data = json.load(f)
        except FileNotFoundError:
            return {
                'status': 'error', 
                'error': f"Mapping file not found: {mapping_path}"
            }
        except json.JSONDecodeError as e:
            return {
                'status': 'error', 
                'error': f"Invalid JSON: {e}"
            }
        
        # Process each headline mapping
        results = []
        for idx, headline_mapping in enumerate(mapping_data['mappings']):
            result = self._process_single_headline(headline_mapping, idx)
            results.append(result)

        # Build summary
        summary = {
            'total_headlines': len(results), 
            'successful': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'error'), 
            'processed_at': datetime.now().isoformat()
        }

        return {
            'status': 'success', 
            'results': results,
            'summary': summary
        }
    
    def _process_single_headline(
        self,
        headline_mapping: Dict[str, Any], 
        index: int
    ) -> Dict[str, Any]:
        """
        Process a single headline through the extraction pipeline. 

        Pipeline Phases:
            Phase 1: Load Data (Headline + Text + CSV)
            Phase 2: Semantic analysis (identify metrics/breakdowns/filters)
            Phase 3: Code generation (using few-shot templates)
            Phase 4: Execution (run generated code)
            Phase 5: Verification (check correctness)
            Phase 6: Storage (save Lineage)

        Args:
             headline_mapping: Dict with keys:
                - 'headline_text': str
                - 'paragraphs': List[str]
                - 'csv_files': List[str]
            index: Position in the mapping file (for tracking)

        Returns: 
            Dict with extraction result and lineage
        """

        headline_text = headline_mapping['headline_text']
        paragraphs = headline_mapping['paragraphs']
        csv_files = headline_mapping['csv_files']

        print(f"\n{'=' * 60}")
        print(f"Processing Headline {index + 1}: {headline_text}")
        print(f"{'=' * 60}")

        # For now, focus on the first paragraph and first CSV
        # (Multi-paragraph and multi-CSV support will come in Phase 2)

        paragraph = paragraphs[0] if paragraphs else ""
        csv_file = csv_files[0] if csv_files else ""

        if not paragraph or not csv_file:
            return {
                'status': 'error',
                'headline': headline_text, 
                'error': 'Missing paragraph or CSV file'
            }
        
        # Load CSV 
        csv_path = self.csvs_dir / csv_file
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            return {
                'status': 'error', 
                'headline': headline_text, 
                'error': f'Failed to load CSV: {e}'
            }

        # Phase 2: Semantic Analysis
        # This is where we analyse the paragraph to find metrics, breakdowns, filters
        analysis = self._analyze_paragraph(paragraph, df)

        # Phase 3: Code Generation
        # Generate pandas code using few-shot template
        generated_code = self._generate_extraction_code(analysis, df)

        # Phase 4: Execution
        # Run the generated code
        execution_result = self._execute_code(generated_code, df, csv_path)

        # Phase 5: Verification
        verification = self._verify_output(execution_result, analysis, paragraph)

        # Phase 6: Build lineage
        lineage = {
            'status': 'success' if execution_result['success'] else 'error',
            'headline': headline_text,
            'paragraph': paragraph, 
            'csv_file': csv_file, 
            'analysis': analysis, 
            'generated_code': generated_code, 
            'execution': execution_result, 
            'verification': verification, 
            'timestamp': datetime.now().isoformat()
        }
        return lineage
    
    def _analyze_paragraph(self, paragraph: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phase 2: Semantic Analysis

        Analyze paragraph text to identify:
        - Which metrics are mentioned
        - Which breakdown dimensions (e.g. sex, ethnicity)
        - Which filters to apply (e.g., geographic_level='National')

        Args:
            paragraph: Text to analyze
            df: CSV DataFrame (to validate column existence)

        Returns:
            Dict with:
            - 'metrics_found': List[str] - column names
            - 'breakdown_column': str - dimension to pivot on
            - 'breakdown_values': List[str] - values to include
            - 'filters': Dict[str, Any] - filters to apply
        """
        # TODO: Implement semantic analysis
        # For now return a placeholder
        return {
            'metrics_found': [], 
            'breakdown_column': None, 
            'breakdown_values': [],
            'filters': {}
        }

    def _generate_extraction_code(
        self, 
        analysis: Dict[str, Any], 
        df: pd.DataFrame
    ) -> str: 
        """
        Phase 3: Code Generation
        Generate pandas code using few-shot template

        Returns:
            str: Executable Python code
        """
        # TODO: Implement code generation
        # For now, return a placeholder
        return "# Generated code will go here\nresult_df = pd.DataFrame()"
    

    def _execute_code(
        self, 
        code: str, 
        df: pd.DataFrame, 
        csv_path: Path,
    ) -> Dict[str, Any]:
        """
        Phase 4: Execution

        Safely execute the generated pandas code.

        Args: 
            code: Python code string to execute
            df: CSV DataFrame
            csv_path: Path to CSV file (for loading in exec context)
        Returns:
            Dict with:
            - 'success': bool - True if code executed successfully
            - 'result': pd.DataFrame - Result of code execution
            - 'error': str - Error message if code execution failed
        """
        # TODO: Implement safe execution
        return {
            'success': False, 
            'error': 'Execution not yet implemented'
        }

    def _verify_output(
        self, 
        execution_result: Dict[str, Any], 
        analysis: Dict[str, Any], 
        paragraph: str, 
    ) -> Dict[str, Any]:
        """
        Phase 5: Verification 
        Verify that the extracted table is correct.

        Checks:
            1. Code review (does it use the right columns?)
            2. Output validation (does table have expected shape?)
            3. Claim verification (do numbers match the paragraph?)

        Args:
            execution_result: Output from _execute_code
            analysis: Output from _analyze_paragraph
            paragraph: Original paragraph text

        Returns:
            Dict with:
            - 'verified': bool - True if output is valid
            - 'checks': List - List of verification checks performed
        """
        # TODO: Implement verification
        return {
            'verified': False, 
            'checks': []
        }

# Entry point for testing

if __name__ == '__main__':
    # Test data
    agent = TableExtractorAgent()
    result = agent.process_mapping_file("testing_mapping.json")
    print(json.dumps(result, indent=2))
