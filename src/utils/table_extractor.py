"""
Table Extractor - Generic, Scalable Pivot Table Generation

Architecture Alignment:
    - Input: Headline text + paragraphs + CSV path + column metadata (From layer 1)
    - Process: LLM (Phi-3-Mini-4K-Instruct) analyzes context -> generates pandas code
    - Output: Small extracted table (10-50 rows, only relevant columns)
    - Feeds into: Layer 2 (RAG verification pipeline)

Design Philosophy - GENERIC EXTRACTION:
    - WORKS ACROSS all 40-60 government publications
    - No hardcoded column names, filters or domain logic
    - LLM infers what data to extract from headline + paragraph context
    - Validates generated code before execution (security)
"""

from transformers import AutoModelForCausalLM, AutoTokenizer
import pandas as pd
import ast
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

class TableExtractor:
    """
    LLM-powered table extractor that generates pandas code to extract small, focused tables from 
    large CSVs

    Model: Phi-3-Mini-4K-Instruct (3.8B params, CPU-friendly)
    """
    def __init__(self, model_name: str = "microsoft/Phi-3-mini-4k-instruct"):
        """
        Initialise the LLM model for code generation

        Args: 
            model_name (str): HuggingFace model ID
        """
        print(f"Loading {model_name}...")
        print("⚠️ Note: Using a workaround for Phi-3 RoPE config issue")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # Workaround: Disable rope_scaling entirely to avoid KeyError
        from transformers import AutoConfig
        config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
        
        # Completely disable RoPE scaling
        if hasattr(config, 'rope_scaling'):
            print("⚠️ Disabling rope_scaling to avoid config error...")
            config.rope_scaling = None
        
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name, 
                config=config,
                device_map='cpu',
                torch_dtype="auto",
                trust_remote_code=True
            )
            print("Model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            import traceback
            traceback.print_exc()
            raise

    def extract_table(self, headline: Dict, csv_path: str, column_metadata: List[Dict]) -> Dict:
        """
        Main entry point: Extract small table using LLM-generated pandas code.

        Args:
            headline:{
                'text': 'Attainment by sex, 2022 to 2025', 
                'level': 2, 
                'page': 5, 
                'paragraphs': ['Boys scored higher...', ...]}
            csv_path: Path to CSV file
            column_metadata:[
                {'name': 'sex', 'type': 'object', 'role': 'filter', 'sample_values': ['Boys', 'Girls']}, 
                {'name': 'score_average', 'type': 'float64', 'role': 'metric', 'sample_values': {}}
            ]
        Returns:
            {
                'headline_id': 'h5', 
                'extracted_table': [...], # List of dicts (pandas records)
                'filters_applied': {'sex': ['Boys', 'Girls', 'Total']},
                'columns_selected': ['sex', 'time_period', 'score_average'], 
                'pandas_code': 'df[df["sex"].isin(...)].pivot(...)',
                'confidence': 0.9
            }
        """
        try:
            # Step 1: Build prompt for LLM 
            prompt = self._build_extraction_prompt(headline, column_metadata)

            # Step 2: Generate pandas code using LLM
            pandas_code = self._generate_pandas_code(prompt)

            # Step 3: Validate code safety (no imports, file ops, system calls)
            if not self._is_safe_pandas_code(pandas_code):
                raise ValueError("Generated code contains unsafe operations")

            # Step 4: Load CSV and execute code
            df = pd.read_csv(csv_path)
            extracted_df = self._execute_pandas_safely(df, pandas_code)

            # Step 5: Build result
            # Cache columns once (fixes SCPAP001 lint)
            columns = extracted_df.columns.tolist()
            
            result = {
                'headline_id': headline.get('id', 'unknown'), 
                'headline_text': headline['text'], 
                'extracted_table': extracted_df.to_dict('records'), 
                'filters_applied': self._extract_filters_from_code(pandas_code),
                'columns_selected': columns,
                'pandas_code': pandas_code, 
                'row_count': len(extracted_df),
                'confidence': self._calculate_confidence(extracted_df, headline), 
                'extracted_at': datetime.now().isoformat()
            }

            return result
            
        except Exception as e:
            error_dict = {
                'headline_id': headline.get('id', 'unknown'), 
                'headline_text': headline['text'],
                'extracted_table': [],
                'error': str(e),
                'confidence': 0.0,
                'extracted_at': datetime.now().isoformat()
            }
            # Include the generated code if available (for debugging)
            if 'pandas_code' in locals():
                error_dict['pandas_code'] = pandas_code
            return error_dict

    def _build_extraction_prompt(self, headline: Dict, column_metadata: List[Dict]) -> str:
        """
        Build prompt for LLM to generate pandas filtering code.
        
        Uses Dynamic Context Injection:
        1. Build dynamic context (headline, paragraphs, CSV columns) - specific to this extraction
        2. Import static template (TABLE_EXTRACTION_PROMPT) - generic rules and examples
        3. Combine: dynamic context + static template
        
        This scales to 40+ publications because the template never changes,
        only the runtime context does.
        """     
        # Step 1: Format dynamic context - CSV column metadata
        columns_desc = []
        for col in column_metadata:
            role = col.get('role', 'unknown')
            samples = col.get('sample_values', [])

            if role == 'filter' and samples:
                columns_desc.append(
                    f" - {col['name']}: {col['type']} (sample values: {samples})"
                )   
            elif role == 'metric':
                columns_desc.append(
                    f" - {col['name']}: ({col['type']}, metric): Numeric column for analysis"
                )
                                    
        columns_str = "\n".join(columns_desc)

        # Step 2: Format dynamic context - paragraphs (first 3)
        paragraphs = "\n".join(headline.get('paragraphs', [])[:3])

        # Step 3: Import the static template (generic across all publications)
        from agents.prompts.table_extraction_prompt import TABLE_EXTRACTION_PROMPT

        # Step 4: Build final prompt - Dynamic context FIRST, then static template
        prompt = f"""
Headline: "{headline['text']}"

Context (paragraphs): 
{paragraphs}

Available CSV columns: 
{columns_str}

{TABLE_EXTRACTION_PROMPT}
"""
        return prompt

    def _generate_pandas_code(self, prompt: str) -> str:
        """
        Use Phi-3-Mini to generate pandas filtering code.
        
        Updated to work with the new TABLE_EXTRACTION_PROMPT template.
        Extracts code after the prompt by looking for Python code patterns.
        """
        inputs = self.tokenizer(prompt, return_tensors="pt")

        # Generate code (reduced tokens for faster CPU inference)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=150,  # Increased to 150 for complete code generation
            temperature=0.1,     # Low temperature for deterministic code
            do_sample=False
        )

        # Decode output
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract code: The LLM echoes the prompt and generates new code after it
        # Strategy: Find where the new code starts after the prompt template
        # Look for the start of Python code (common patterns after few-shot examples)
        
        # First, try to find code after the last example in the template
        # The template ends with "result_df = df_final" from the ethnicity example
        if "result_df = df_final" in generated_text:
            # Split after the last occurrence of this pattern
            parts = generated_text.split("result_df = df_final")
            if len(parts) > 1:
                # Take everything after the last example
                pandas_code = parts[-1].strip()
            else:
                pandas_code = generated_text
        else:
            # Fallback: take everything after the prompt (rough approach)
            pandas_code = generated_text

        # Clean up common formatting issues
        pandas_code = pandas_code.replace("```python", "").replace("```", "").strip()
        
        # Filter out non-code lines and extract only valid Python statements
        code_lines = []
        for line in pandas_code.split('\n'):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip lines that are clearly prompt echoes or text (not code)
            skip_markers = [
                'Headline:', 'Context:', 'Available CSV', 'RULES:', 'Example',
                'FEW-SHOT', '---', '**Input:**', '**Generated Code:**',
                'CSV Columns:', 'CSV Metadata', 'Analysis:', 'Pandas code:',
                'You are a table', 'Output Format', 'Simple Breakdown', 'Complex breakdown'
            ]
            if any(line.startswith(marker) for marker in skip_markers):
                continue
            
            # Skip lines that are just quoted strings without assignment
            if line.startswith('"') and line.endswith('"') and '=' not in line:
                continue
            
            # Skip markdown or comment headers
            if line.startswith('#') and not line.startswith('# '):
                continue
            
            # Keep lines that look like Python code
            # Must contain Python operators or be valid statements
            if any(pattern in line for pattern in ['=', '(', '[', 'import', 'df', 'pd.', 'result']):
                code_lines.append(line)
        
        pandas_code = '\n'.join(code_lines)

        # Final safety: If we got no code, return a safe placeholder
        if not pandas_code or len(pandas_code) < 10:
            print("⚠️ Warning: Could not extract valid code from LLM output")
            print(f"Generated text preview: {generated_text[:500]}...")
            pandas_code = "result_df = df.head(10)  # Fallback: return first 10 rows"

        return pandas_code

    def _is_safe_pandas_code(self, code: str) -> bool:
        """
        Validate that generated code is safe to execute.

        Security checks:
        - No import statements
        - No file operations (open, read, write)
        - No system calls (os.system, subprocess)
        - No exec/eval
        - Only pandas operations allowed
        """  
        dangerous_keywords = [
            'import', '__import__', 'eval', 'exec', 'compile',
            'open', 'file', 'os.', 'sys.', 'subprocess',
            '__builtins__', '__globals__', '__locals__'
        ]  

        code_lower = code.lower()

        for keyword in dangerous_keywords:
            if keyword in code_lower:
                print(f"⚠️ Unsafe code detected: contains '{keyword}'")
                return False

        # Try to parse as valid Python AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f"⚠️ Invalid Python syntax: {e}")
            return False

        return True

    def _execute_pandas_safely(self, df: pd.DataFrame, pandas_code: str) -> pd.DataFrame:
        """
        Execute LLM-generated pandas code in a sandboxed environment.

        Security:
        - Code has already been validated
        - Executed with minimal namespace (only df and pandas)
        - Result must be a DataFrame
        """
        # Create sandboxed namespace
        namespace = {
            'df': df,
            'pd': pd,
            '__builtins__': {}  # Disable built-in functions
        }
        
        try:
            # Execute code 
            exec(pandas_code, namespace)

            # Extract result - try multiple common variable names
            result = None
            for var_name in ['result_df', 'df_final', 'result', 'output', 'df']:
                if var_name in namespace:
                    result = namespace[var_name]
                    break
            
            if result is None:
                raise RuntimeError("Generated code did not produce a result variable (tried: result_df, df_final, result, output, df)")

            if not isinstance(result, pd.DataFrame):
                raise TypeError(f"Generated code did not return a DataFrame, got {type(result)}")
                
            # Limit size for safety
            if len(result) > 1000:
                print(f"⚠️ Extracted table too large ({len(result)} rows), limiting to 1000")
                result = result.head(1000)
                
            return result
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute pandas code: {e}")
        
    def _extract_filters_from_code(self, pandas_code: str) -> Dict[str, List]:
        """
        Parse pandas code to extract applied filters.

        Example: 
            Input: "df[df['sex'].isin(['Boys', 'Girls'])]"
            Output: {'sex': ['Boys', 'Girls']}
        """
        filters = {}
        
        # Pattern 1: df['column'].isin([...]) or df["column"].isin([...])
        isin_pattern = r"df\[['\"](\w+)['\"]\]\.isin\(\[(.*?)\]\)"
        matches = re.findall(isin_pattern, pandas_code)
        
        for col, values_str in matches:
            # Parse values
            values = [v.strip().strip("'\"") for v in values_str.split(',') if v.strip()]
            filters[col] = values
        
        # Pattern 2: df[df.column.isin([...])]
        isin_pattern2 = r"df\.(\w+)\.isin\(\[(.*?)\]\)"
        matches2 = re.findall(isin_pattern2, pandas_code)
        
        for col, values_str in matches2:
            values = [v.strip().strip("'\"") for v in values_str.split(',') if v.strip()]
            filters[col] = values
        
        return filters

    def _calculate_confidence(self, extracted_df: pd.DataFrame, headline: Dict) -> float:
        """
        Estimate confidence score based on extracted table quality

        Factors:
        - Table size (10-50 rows is ideal)
        - Non-empty results
        - Column count (not too many, not too few)
        """
        confidence = 0.5  # Baseline

        if not extracted_df.empty:
            confidence += 0.2

        row_count = len(extracted_df)
        if 10 <= row_count <= 50:
            confidence += 0.2  # Ideal size
        elif row_count > 50:
            confidence += 0.1  # Acceptable but large

        # Cache columns once (fixes SCPAP001 lint)
        columns = extracted_df.columns.tolist()
        col_count = len(columns)
        if 2 <= col_count <= 10:
            confidence += 0.1  # Reasonable column count

        return min(confidence, 1.0)
