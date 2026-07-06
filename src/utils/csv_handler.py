"""
CSV handler - Agnostic CVS Parsign and Metadata Extraction 

Purprose:
    Parse ANY CSV file (no hardcoded column names) and extract:
    - Column names, types, and roles (metric, vs filter vs identifier)
    - Sample values for semantic matching
    - Metadata for mapping UI and agent queries

Architecture Alignment:
    - Layer 1: Document& Data Ingestion (CSV side)
    - Feeds into: Layer 3 (mapping UI) and Layer 4 (agent verificaion)

Key Design Principle:
    - No hardcoding - works for any CSV structure across 40+ different reports

"""

import pandas as pd
import os
from typing import Dict, List, Any
from datetime import datetime


############################################
#### Build the Column Role Classifier #####
###########################################

def infer_column_role(series: pd.Series) -> str:
    """
    Classify a column's role in the dataset.

    Returns one of:
        - 'metric': Numeric values verified (scores, counts, percentages)
        - 'filter': Categorical dimensions for groupign (sex, region, year)
        - 'identifier': Unique IDs or codes (school_id, pupil_id)

    How it works:
        1. Check data types(number vs. text)
        2. Check uniqueness ration (how many different values?)
        3. Apply rules to classify

    Args:
        series(pd.Series): A single column from the CSV 

    Returns:
        str: 'metric', 'filter', or 'identifier'
    Example:
        >>> df = pd.read_csv('data.csv')
        >>> role = infer_column_role(df['mtc_score_average'])
        >>> print(role) # Output: 'metric'   
    
    """
    # Rule 1: Check if it's a number column
    if series.dtype in ['int64', 'float64']:

        # Calculate uniqueness ration
        # if column has 1000 rows and 800 different values ratio = 0.8 
        unique_ratio = series.nunique() / len(series)
        # High variance (many different values) -> probably a metric
        # Example: score like 19.8, 20.1, etc (many unique values)
        if unique_ratio > 0.5:
            return 'metric'
        
        # Low variance (few different values) -> probably a filter
        # Example: year column: [2022, 2023, 2024] (only unique values)

        else:
            return 'filter'
        
    # Rule 2: Text columns
    elif series.dtype == 'object':
        # If < 50 unique valyes -> categorical filter
        # Example: sex column: ['Male', 'Female', 'Total'] (3 unique)
        if series.nunique() < 50:
            return 'filter'
        
        # if many unique values -> probably an ID 
        # Example: school_id: ['SC001', 'SCH002', ...]
        else:
            return 'identifier'
    # Fallback for rare types
    return 'unknown'

#####################################
#### Get Sample Values Function #####
#####################################

def get_sample_values(series: pd.Series, n: int = 5) -> Any:
    """
    Extract representative sample values from a column.
    
    Purpose:
        - For FILTERS: Show the actual values (for dropdowns in UI)
        - For METRICS: Show min/max/mean (to understand the range)
    
    How it works:
        - Text columns → Most common values (top 5 by default)
        - Time/date columns → ALL unique values (for temporal comparisons)
        - Numeric columns → Statistical summary (min, max, mean, median)
    
    Smart Sampling:
        - Time-related columns (year, period, date): Return ALL values
          Why? Headlines often compare across years: "from 2022 to 2025"
        - Small categorical columns (< 20 unique): Return ALL values
          Example: sex (3 values), ethnicity_major (8 values)
        - Large categorical columns (≥ 20 unique): Return top 10 most common
          Example: region (150+ values) - only show the most frequent
    
    Args:
        series (pd.Series): A single column from the CSV
        n (int): Number of sample values to return (default: 5)
    
    Returns:
        For text: List of strings (e.g., ['Male', 'Female', 'Total'])
        For numbers: Dict with stats (e.g., {'min': 0, 'max': 25, 'mean': 19.8})
    
    Example:
        >>> df = pd.read_csv('data.csv')
        
        # Filter column (categorical)
        >>> samples = get_sample_values(df['sex'])
        >>> print(samples)  # ['Total', 'Girls', 'Boys']
        
        # Time column (all values returned for comparisons)
        >>> samples = get_sample_values(df['time_period'])
        >>> print(samples)  # [202122, 202223, 202324, 202425]
        
        # Metric column (numeric stats)
        >>> samples = get_sample_values(df['mtc_score_average'])
        >>> print(samples)  # {'min': 0.0, 'max': 25.0, 'mean': 19.8, 'median': 20.0}
    
    """

    if series.dtype =='object':

        #Check if this s a time-related column 
        # Look for keywords in column name: year, period, date, time, quarter, month
        column_name = series.name.lower()
        is_time_column = any(keyword in column_name for keyword in ['year', 'period', 'date', 'time', 'quarter', 'month'])

        # For time columns: Return ALL unique values
        # Why ? Headlines compare across time
        # We need all years available for matching 

        if is_time_column:
            return sorted(series.unique().tolist())
        #For other categorical columns: Apply smart sampling 
        unique_count = series.nunique()

        if unique_count <= 20:
            # Small categorical: Return ALL values 
            # Example:sex (3), ethicity_major (8), school_type(12)
            return series.value_counts().index.tolist()
        else:
            # Large categegorical: Return top 10 most common 
            # Example: region(150+), school_id(1000+)
            return series.value_counts().head(10).index.tolist()
    # Case 2: numeric columns
    elif series.dtype in ['int64', 'float64']:
        # Check inf numeric column is actually a year/period (lif 202223)
        column_name = series.name.lower()
        is_time_column = any(keyword in column_name for keyword in ['year', 'period', 'date', 'time', 'quarter', 'month'])

        if is_time_column:
            return sorted(series.unique().tolist())
        else:
            return {
                'min': float(series.min()),
                'max': float(series.max()),
                'mean': float(series.mean()),
                'median': float(series.median())
            }
    else:
        return None
    

    #############################################
    #### Building the Main Metadata Extractor####
    #############################################
def get_csv_metadata(csv_path: str) -> Dict:
    """
    Main entry point - Extract complete metadata from any CSV file. 

    This is the CSV equivalent of parse_pd() - it return a unified structure that works for ANY CSV across 40+ dofferent reports. 

    What it does:
    1. Read the CSV using pandas
    2. Loop through eahc column
    3. Classify role (metric/filter/identifier)
    4. Extract sample values
    5. Return unified metadata structure 

    Architecture:
        - No hardcoded columns names
        - Works for any CSV structure
        - Output feeds into Layer 3 (mapping UI) and Layer 4 (agents)

    Args:
        - csv_path (str): Full path to CSV file

    Returns:
        - Dict: Unified metadata structured:
        {
            "filename": str, 
            "row_count': int, 
            "column_count": int, 
            "columns": [
                {
                    "name": str, 
                    "type": str, 
                    "role": str, # 'metric', 'filter', or 'identifier'
                    "sample_values": Any 
                    }, 
                    ...
                ], 
                "metadata": {
                    "parser_used": str, 
                    "parse_timestamp": str
                }
            }
    Example: 
        >>> medatada = get_csv_metadata('/path/to/data.csv')
        >>> print(metadata['filename']) 
        >>> print(metadata['column_count']) 
        >>>
        >>> # Fing all metric columns
        >>> metrics = [col for col in metadata['columns'] if col['role'] == 'metric']
        >>> print(metrics) # Extract representative sample values from a column.

    Raises: 
        FileNotFoundError: If CSV file doesn;t exist 
        Exception: If CSV cannot be parsed
    """
    try:
        # Step 1 : Read CSV file
        # We use pandas because it's industry standard and handles edge cases

        df = pd.read_csv(csv_path)

        # Step 2: Initialize the metadata structure
        metadata = {
            'filename': os.path.basename(csv_path),
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': [],
            'metadata': {
                'parser_used': 'pandas',
                'parse_timestamp': datetime.now().isoformat()
            }
        }

        # Step 3: Loop through each column extract metadata
        for column_name in df.columns:
            # Get the column as a pandas Serier
            column_series = df[column_name]

            # Use our helper functiosn to classify and sample
            role = infer_column_role(column_series)
            samples = get_sample_values(column_series)

            # Build columns metadata
            column_metadata = {
                'name': column_name, 
                'type': str(column_series.dtype), # 'int64', 'float64', 'object'
                'role': role, # 'metric', 'filter', or 'identifier
                'sample_values': samples # List or dict depending on type

            }

            # Add to our columns list
            metadata['columns'].append(column_metadata)

        # Step 4: Return the complete metadata
        return metadata
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    except Exception as e :
        raise RuntimeError(f"Error parsing CSV: {e}")





