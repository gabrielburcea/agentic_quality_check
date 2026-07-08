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
                trust_remote_code=True,
                attn_implementation='eager'
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
                raise SecurityError("Generated code contains unsafe operations")

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
            return {
                'headline_id': headline.get('id', 'unknown'), 
                'headline_text': headline['text'],
                'extracted_table': [],
                'error': str(e),
                'confidence': 0.0,
                'extracted_at': datetime.now().isoformat()
            }

    def _build_extraction_prompt(self, headline: Dict, column_metadata: List[Dict]) -> str:
        """
        Build prompt for LLM to generate pandas filtering code.
        The prompt includes:
        - Headline text and paragraphs (context)
        - Available CSV columns with types and sample values
        - Instructions to generate pandas code 
        """     
        # Format column info
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

        # Format paragraphs
        paragraphs = "\n".join(headline.get('paragraphs', [])[:3]) # First 3 paragraphs

        prompt = f"""You are a data extraction agent. Your task is to generate pandas code to extract a small, focused table from a large CSV and PIVOT it to match document format.

Headline: "{headline['text']}"

Context (paragraphs): 
{paragraphs}

Available CSV columns: 
{columns_str}

Instructions:
1. Analyse the headline and context to understand what data is needed
2. Generate pandas code that:
   - Filters to relevant rows (e.g., df[df['sex'].isin(['Boys', 'Girls', 'Total'])])
   - Selects relevant columns
   - PIVOTS the table to match document format (use .pivot() or .pivot_table())
   - Returns a small table, yet complete (10-50 rows)
3. Output ONLY the pandas code, no explanation
4. Use 'df' as the DataFrame variable name
5. Code must be valid Python that can be executed with exec()

EXAMPLES (Few-Shot Learning):

Example 1 - SIMPLE (Single dimension × metrics × time):
Headline: "Attainment by sex, 2022 to 2025"
Desired output format:
                                     Boys    Girls
Average attainment score  
2021/22                              20.0    19.6
2022/23                              20.4    19.9
2023/24                              20.9    20.4
2024/25                              21.2    20.7

Percentage of eligible pupils who took the check
2021/22                              95%     97%
2022/23                              95%     97%
2023/24                              95%     97%
2024/25                              95%     97%

Pandas code:
filtered = df[df['sex'].isin(['Boys', 'Girls'])]
result = filtered.pivot_table(index=['metric_name', 'time_period'], columns='sex', values='value', aggfunc='first')

Example 2 - MEDIUM (Multiple dimensions × time):
Headline: "Attainment by school type, 2022 to 2025"
Desired output format:
                               State funded    Local authority    Academies    Academy sponsor led    Academy converter    Free schools
Average attainment score
2021/22                        19.8            19.8              19.8          19.2                  19.9                  20.9
2022/23                        20.2            20.2              20.2          19.8                  20.3                  21.2
2023/24                        20.7            20.6              20.8          20.3                  20.9                  21.6
2024/25                        21.0            20.8              21.2          20.9                  21.3                  21.8

Number of eligible pupils
2021/22                        643675          380551            263124        70552                 183431                9141
2022/23                        638222          367860            270362        70576                 189426                10360

Pandas code:
school_types = ['State funded mainstream schools', 'Local authority maintained', 'Academies and free schools', 'Academy sponsor led', 'Academy converter', 'Free schools']
filtered = df[df['school_type'].isin(school_types)]
result = filtered.pivot_table(index=['metric_name', 'time_period'], columns='school_type', values='value', aggfunc='first')

Example 3 - COMPLEX (Distribution table with multi-column headers):
Headline: "Percentage of eligible pupils who achieved each score by first language, 2022 to 2025"
Desired output format:
       Known or believed to be English              Known or believed to be other than English
       2021/22    2022/23    2023/24    2024/25     2021/22    2022/23    2023/24    2024/25
0      0%         0%         0%         0%          0%         0%         0%         0%
1      0%         0%         0%         0%          0%         0%         0%         0%
...
25     24%        27%        31%        34%         36%        38%        42%        45%

Pandas code:
languages = ['Known or believed to be English', 'Known or believed to be other than English']
filtered = df[df['first_language'].isin(languages) & df['score'].between(0, 25)]
result = filtered.pivot_table(index='score', columns=['first_language', 'time_period'], values='percentage', aggfunc='first')

Now generate pandas code for this headline:
"""

        return prompt

    def _generate_pandas_code(self, prompt: str) -> str:
        """
        Use Phi-3-Mini to generate pandas filtering code.
        """
        inputs = self.tokenizer(prompt, return_tensors="pt")

        # Generate code (reduced tokens for faster CPU inference)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=100,  # Reduced from 200 for 2x speedup
            temperature=0.1, # Low temperature for deterministic code
            do_sample=False
        )

        # Decode output
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract only the pandas code (remove prompt echo)
        pandas_code = generated_text.split("Now generate pandas code for this headline:")[-1].strip()

        # Clean up common formatting issues
        pandas_code = pandas_code.replace("```python", "").replace("```", "").strip()

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

            # Extract result (should be last variable or 'df' if modified in place)
            result = namespace.get('result', namespace['df'])

            if not isinstance(result, pd.DataFrame):
                raise TypeError("Generated code did not return a DataFrame")
                
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

        # Simple regex-based extraction (can be improved)
        import re
        
        # Pattern: df['column'].isin([...])
        isin_pattern = r"df\['(\w+)'\]\.isin\(\[(.*?)\]\)"
        matches = re.findall(isin_pattern, pandas_code)
        
        for col, values_str in matches:
            # Parse values
            values = [v.strip().strip("'\"") for v in values_str.split(',')]
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
        confidence = 0.5 # Baseline

        if not extracted_df.empty:
            confidence += 0.2

        row_count = len(extracted_df)
        if 10 <= row_count <= 50:
            confidence += 0.2 # Ideal size
        elif row_count > 50:
            confidence += 0.1 # Acceptable but large

        # Cache columns once (fixes SCPAP001 lint)
        columns = extracted_df.columns.tolist()
        col_count = len(columns)
        if 2 <= col_count <= 10:
            confidence += 0.1 # Reasonable column count

        return min(confidence, 1.0)


# Example usage
if __name__ == '__main__':
    extractor = TableExtractor()
    
    headline = {
        'id': 'h5',
        'text': 'Attainment by sex, 2022 to 2025',
        'level': 2,
        'page': 5,
        'paragraphs': [
            'Boys scored higher than girls in 2024/25.',
            'The gap has widened from 0.4 in 2021/22 to 0.5 in 2024/25.'
        ]
    }
    
    csv_path = '/Volumes/my_catalog/agentic_quality_check_dev/csvs_volume/mtc_national_pupil_characteristics_2022_to_2025.csv'
    
    column_metadata = [
        {'name': 'sex', 'type': 'object', 'role': 'filter', 'sample_values': ['Boys', 'Girls', 'Total']},
        {'name': 'time_period', 'type': 'object', 'role': 'filter', 'sample_values': ['202223', '202324', '202425']},
        {'name': 'score_average', 'type': 'float64', 'role': 'metric', 'sample_values': {}}
    ]
    
    result = extractor.extract_table(headline, csv_path, column_metadata)
    
    print(json.dumps(result, indent=2))
