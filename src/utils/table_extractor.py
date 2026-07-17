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
    def __init__(self, model_name: str="microsoft/Phi-3-mini-4k-instruct", use_claude: bool = True, api_key: str = None):

        if use_claude:
            self.use_claude = True
            # API key must be provided when use_claude=True
            if api_key is None:
                raise ValueError("api_key is required when use_claude=True")
            self.api_key = api_key
            
            #Initialize Anthropic client
            import anthropic
            import os
            # 🔒 Safe method: Set API key via environment variable
            os.environ["ANTHROPIC_API_KEY"] = self.api_key
            self.client = anthropic.Anthropic()  # Auto-reads from env var
            self.model_name = "claude-opus-4-8"  # Newer model that works with your account
            print(f"Using Claude API: {self.model_name}")

        else:
            # Fall back to HuggingFace Phi-3-Mini
            self.use_claude = False
            print(f"Loading {model_name}...")
            print("Note: Using a workaround for Phi-3 RoPe config issue")
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code = True)

            # Workaround: Disable rope_scaling entirely to avoid KeyError

            from transformers import AutoConfig
            config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)

            # Completely disable RoPE scaling
            if hasattr(config, 'rope_scaling'):
                print("Disabling rope_scaling to avoid config error...")
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
                print(f"Error loading model: {e}")
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
            # Extract paragraph text for the execution context
            paragraph = '\n'.join(headline.get('paragraphs', [headline.get('text', '')]))
            extracted_df = self._execute_pandas_safely(df, pandas_code, paragraph)

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
        import os
        import sys
        # Get the path to the prompts directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_dir = os.path.join(os.path.dirname(current_dir), 'agents', 'prompts')
        if prompts_dir not in sys.path:
            sys.path.insert(0, prompts_dir)
        from table_extraction_prompt import TABLE_EXTRACTION_PROMPT

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
        Generate pandas filtering code using Claude API or Phi-3-Mini. 

        Uses Claude API if available (use_claude=True), otherwise falls back to Phi-3-Mini
        Extracts code after the prompt by looking for Python code patterns.
        """
        if self.use_claude:
            # Use Claude API
            try:
                message = self.client.messages.create(
                    model = self.model_name, 
                    max_tokens = 3072,  # Increased for complete code generation
                    # Note: temperature parameter is deprecated for claude-opus-4-8
                    messages=[{
                        "role": "user", 
                        "content": prompt
                    }]
                )
                # Extract text from response
                generated_text = message.content[0].text
            except Exception as e:
                print(f"Error calling Claude API: {e}")
                # Fallback to simple head()
                return "result_df = df.head(10) # Fallback: Claude API error"
        else:
            # Use Phi-3-Mini (HuggingFace)

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

        # First, clean up markdown code fences
        generated_text = generated_text.replace("```python", "").replace("```", "").strip()
        
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
        
        # Remove obvious non-code headers from the start
        lines = generated_text.split('\n')
        code_start_idx = 0
        
        # Skip leading lines that are clearly not code
        skip_markers = [
            'Headline:', 'Context:', 'Available CSV', 'RULES:', 'Example',
            'FEW-SHOT', '---', '**Input:**', '**Generated Code:**',
            'CSV Columns:', 'CSV Metadata', 'Analysis:', 'Pandas code:',
            'You are a table', 'Output Format', 'Simple Breakdown', 'Complex breakdown'
        ]
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            # If we hit a line that starts with actual Python code (comment or code), start there
            if stripped and (stripped.startswith('#') or '=' in stripped or 'df' in stripped):
                code_start_idx = i
                break
            # Skip obvious non-code lines
            if any(stripped.startswith(marker) for marker in skip_markers):
                continue
        
        pandas_code = '\n'.join(lines[code_start_idx:])

        # Final safety: If we got no code, return a safe placeholder
        if not pandas_code or len(pandas_code) < 10:
            print("⚠️ Warning: Could not extract valid code from LLM output")
            print(f"Code length: {len(pandas_code)}")
            print(f"Extracted code: '{pandas_code}'")
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
        # Check for dangerous keywords in actual code (not comments)
        # Remove comments and check each line
        lines = code.split('\n')
        code_lines = []
        for line in lines:
            # Remove comments
            if '#' in line:
                line = line[:line.index('#')]
            code_lines.append(line.strip())
        
        code_no_comments = '\n'.join(code_lines).lower()
        
        # Check for actual import statements (at start of line)
        if re.search(r'^\s*(import|from)\s+', code, re.MULTILINE):
            print(f"⚠️ Unsafe code detected: contains import statement")
            return False
        
        # Check for other dangerous keywords
        dangerous_keywords = [
            '__import__', 'eval', 'exec', 'compile',
            'open', 'file', 'os.', 'sys.', 'subprocess',
            '__builtins__', '__globals__', '__locals__'
        ]  

        for keyword in dangerous_keywords:
            if keyword in code_no_comments:
                print(f"Unsafe code detected: contains '{keyword}'")
                return False

        # Try to parse as valid Python AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f"Invalid Python syntax: {e}")
            return False

        return True

    def _execute_pandas_safely(self, df: pd.DataFrame, pandas_code: str, paragraph: str = "") -> pd.DataFrame:
        """
        Execute LLM-generated pandas code in a sandboxed environment.

        Security:
        - Code has already been validated
        - Executed with minimal namespace (only df, pandas, and paragraph)
        - Result must be a DataFrame
        """
        # Create sandboxed namespace
        # Allow safe builtins that pandas code might need
        safe_builtins = {
            'enumerate': enumerate,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'range': range,
            'list': list,
            'dict': dict,
            'set': set,
            'tuple': tuple,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sum': sum,
            'min': min,
            'max': max,
            'sorted': sorted,
            'reversed': reversed,
            'round': round,
            'abs': abs,
            'any': any,
            'all': all
        }
        
        namespace = {
            'df': df,
            'pd': pd,
            'paragraph': paragraph,
            '__builtins__': safe_builtins
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
                print(f"Extracted table too large ({len(result)} rows), limiting to 1000")
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
