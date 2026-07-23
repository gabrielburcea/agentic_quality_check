"""
Tests for JSON Storage Module

Purpose:
  - Test JSON Storage CLASS that bridges Layer 1.5 (extraction) and Layer 2 (RAG pipeline) by saving/ loading JSON files to Unity Catalog Volumes. 

Run:
    pytest tests/test_json_storage.py 

    Or from notebook:
    import pytest
    pytest.main(["-v", "tests/test_json_storage.py"])

"""

import pytest
import json
import os
from pathlib import Path
import sys

# Import json_storage directly without loading the full utils package
# (avoids dependency issues with pdf_parser, pdfplumber, etc.)
import importlib.util

json_storage_path = str(Path(os.path.abspath(__file__)).parent.parent / "src" / "utils" / "json_storage.py")
spec = importlib.util.spec_from_file_location("json_storage", json_storage_path)
json_storage_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(json_storage_module)
JSONStorage = json_storage_module.JSONStorage
# Test fixture to create a temporary JSON file for testing
@pytest.fixture
def storage():
    """
    Fixture: Create a JSONStorage instance for testing

    This runs BEFORE each test to give you a fresh storage ojects
    After the test runs, this fixture cleans up any test files.
    """
    # Create storage instance
    storage_instance = JSONStorage()

    # Yield it to the test (this is where the test runs)
    yield storage_instance

    # Cleanup: Delete test files created during the test
    test_doc_ids = ["test_doc", "test_report_q4_2024", "test_cleanup"]
    for doc_id in test_doc_ids:
        try:
            storage_instance.delete_extraction(doc_id)
        except:
            pass # Ignore if file doesn't exist

@pytest.fixture
def sample_extraction_data():
    """
    Fixture: Provide sample extraction data for tests. 
    This represents what Layer 1.5 (table extraction) would output
    
    """
    return {
        "headlines": [
            {"text": "Revenue Growth 15%", "page": 1, "context": "Q4 Results"},
            {"text": "Market Share Increased", "page": 2, "context": "Competition"}
        ],
        "paragraphs": [
            "The company achieved 15% revenue growth in Q4 2024...",
            "Market share increased from 12% to 18%..."
        ],
        "tables": [
            {
                "caption": "Quarterly Revenue",
                "data": [
                    ["Q1", "Q2", "Q3", "Q4"],
                    [100, 120, 140, 161]
                ]
            }
        ]
    }
        
class TestJSONStorage:
    """
    Test class for JSONStorage class

    Tests cover:
    - Initialization
    - Saving extractions
    - Loading extractions
    - Listing extractions
    - Deleting extractions
    - Storage stats
    """

    def test_initialization(self, storage):
        """Test that storage initializes correctly."""
        assert storage.base_path.exists(), "Base path should exist"
        assert storage.extractions_path.exists(), "Extractions path should be created"
        assert str(storage.base_path).endswith("processed_volume")
    
    def test_save_extraction(self, storage, sample_extraction_data):
        """Test saving an extraction to JSON file."""
        doc_id = "test_doc"
        
        # Save extraction
        path = storage.save_extraction(doc_id, sample_extraction_data)
        
        # Verify file was created
        assert Path(path).exists(), "JSON file should exist after save"
        
        # Verify file content
        with open(path, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["doc_id"] == doc_id
        assert "timestamp" in saved_data
        assert "version" in saved_data
        assert saved_data["data"]["headlines"] == sample_extraction_data["headlines"]
    
    def test_save_without_metadata(self, storage, sample_extraction_data):
        """Test saving without metadata wrapper."""
        doc_id = "test_no_metadata"
        
        # Save without metadata
        path = storage.save_extraction(doc_id, sample_extraction_data, include_metadata=False)
        
        # Verify file content has no metadata wrapper
        with open(path, 'r') as f:
            saved_data = json.load(f)
        
        assert "doc_id" not in saved_data  # No metadata wrapper
        assert "headlines" in saved_data  # Direct data
        
        # Cleanup
        storage.delete_extraction(doc_id)
    
    def test_load_extraction(self, storage, sample_extraction_data):
        """Test loading an extraction from JSON file."""
        doc_id = "test_load"
        
        # Save first
        storage.save_extraction(doc_id, sample_extraction_data)
        
        # Load it back
        loaded_data = storage.load_extraction(doc_id)
        
        # Verify loaded data
        assert loaded_data is not None
        assert loaded_data["doc_id"] == doc_id
        assert len(loaded_data["data"]["headlines"]) == 2
        assert loaded_data["data"]["headlines"][0]["text"] == "Revenue Growth 15%"
        
        # Cleanup
        storage.delete_extraction(doc_id)
    
    def test_load_nonexistent(self, storage):
        """Test loading a file that doesn't exist."""
        result = storage.load_extraction("nonexistent_doc")
        assert result is None
    
    def test_list_extractions(self, storage, sample_extraction_data):
        """Test listing all extraction files."""
        # Save multiple files
        storage.save_extraction("doc_001", sample_extraction_data)
        storage.save_extraction("doc_002", sample_extraction_data)
        storage.save_extraction("doc_003", sample_extraction_data)
        
        # List files
        files = storage.list_extractions()
        
        # Verify list
        assert len(files) >= 3  # At least our 3 files
        doc_ids = [f["doc_id"] for f in files]
        assert "doc_001" in doc_ids
        assert "doc_002" in doc_ids
        assert "doc_003" in doc_ids
        
        # Verify metadata structure
        for file_info in files:
            assert "doc_id" in file_info
            assert "filename" in file_info
            assert "path" in file_info
            assert "size_kb" in file_info
            assert "modified" in file_info
        
        # Cleanup
        storage.delete_extraction("doc_001")
        storage.delete_extraction("doc_002")
        storage.delete_extraction("doc_003")
    
    def test_delete_extraction(self, storage, sample_extraction_data):
        """Test deleting an extraction file."""
        doc_id = "test_delete"
        
        # Save file
        path = storage.save_extraction(doc_id, sample_extraction_data)
        assert Path(path).exists()
        
        # Delete file
        result = storage.delete_extraction(doc_id)
        assert result is True
        assert not Path(path).exists()
    
    def test_delete_nonexistent(self, storage):
        """Test deleting a file that doesn't exist."""
        result = storage.delete_extraction("nonexistent_doc")
        assert result is False
    
    def test_get_storage_stats(self, storage, sample_extraction_data):
        """Test getting storage statistics."""
        # Save some files
        storage.save_extraction("stats_001", sample_extraction_data)
        storage.save_extraction("stats_002", sample_extraction_data)
        
        # Get stats
        stats = storage.get_storage_stats()
        
        # Verify stats structure
        assert "total_files" in stats
        assert "total_size_mb" in stats
        assert "base_path" in stats
        assert "extractions_path" in stats
        
        # Verify counts
        assert stats["total_files"] >= 2
        assert stats["total_size_mb"] >= 0
        
        # Cleanup
        storage.delete_extraction("stats_001")
        storage.delete_extraction("stats_002")
    
    def test_filename_sanitization(self, storage, sample_extraction_data):
        """Test that doc_id with spaces and slashes are sanitized."""
        doc_id = "test doc/with spaces"
        
        # Save extraction
        path = storage.save_extraction(doc_id, sample_extraction_data)
        
        # Verify filename has no spaces or slashes
        assert " " not in Path(path).name
        assert "/" not in Path(path).name
        assert Path(path).name == "test_doc_with_spaces.json"
        
        # Verify we can load it back
        loaded = storage.load_extraction(doc_id)
        assert loaded is not None
        
        # Cleanup
        storage.delete_extraction(doc_id)


# Example: How to run tests from a notebook
if __name__ == "__main__":
    print("Running JSON Storage tests...")
    print("=" * 70)
    
    # Run with pytest
    import pytest
    exit_code = pytest.main([
        "-v",                    # Verbose output
        "--tb=short",            # Short traceback format
        __file__                 # This file
    ])
    
    if exit_code == 0:
        print("\nAll tests passed!")
    else:
        print(f"\nSome tests failed (exit code: {exit_code})")