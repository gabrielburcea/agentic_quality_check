"""
JSON Storage Module - Layer 1.5 to Layer 2 Bridge

Purpose:
    Handles saving and loading JSON extraction results between layers:
    - Layer 1.5: Table extraction outputs (headlines, paragraphs, tables)
    - Layer 2: RAG pipeline inputs (for indexing and retrieval)

Storage Location:
    Unity Catalog Volume: /Volumes/my_catalog/agentic_quality_check_dev/processed_volume
    
File Structure:
    /Volumes/.../processed_volume/
        extractions/              # Raw JSON outputs from Layer 1.5
            doc_001.json
            doc_002.json
            ...
        embeddings/               # Future: Vector embeddings from Layer 2
            ...

Usage:
    from utils.json_storage import JSONStorage
    
    storage = JSONStorage()
    
    # Save extraction result
    storage.save_extraction("doc_001", extraction_data)
    
    # Load specific document
    data = storage.load_extraction("doc_001")
    
    # List all available extractions
    files = storage.list_extractions()
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class JSONStorage:
    """
    Manages JSON file storage in Unity Catalog Volumes.
    
    Attributes:
        base_path: Root path to the UC volume
        extractions_path: Subdirectory for Layer 1.5 JSON outputs
    """
    
    def __init__(self, base_volume_path: Optional[str] = None):
        """
        Initialize storage with Unity Catalog volume path.
        
        Args:
            base_volume_path: Optional custom volume path. 
                            Defaults to your project volume.
        """
        # Use your existing volume for the project
        if base_volume_path is None:
            base_volume_path = "/Volumes/my_catalog/agentic_quality_check_dev/processed_volume"
        
        self.base_path = Path(base_volume_path)
        self.extractions_path = self.base_path / "extractions"
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """
        Create necessary subdirectories if they don't exist.
        
        This is important because Unity Catalog volumes start empty.
        We need to create the folder structure ourselves.
        """
        # Create extractions directory
        os.makedirs(self.extractions_path, exist_ok=True)
        
        print(f"✅ Storage initialized: {self.extractions_path}")
    
    def save_extraction(self, 
                       doc_id: str, 
                       data: Dict[str, Any],
                       include_metadata: bool = True) -> str:
        """
        Save extraction result as JSON file.
        
        Args:
            doc_id: Unique identifier for the document (e.g., "doc_001")
            data: The extraction data to save (headlines, paragraphs, tables)
            include_metadata: Whether to add timestamp and metadata
        
        Returns:
            Full path to saved file
            
        Example:
            extraction_result = {
                "headlines": [...],
                "paragraphs": [...],
                "tables": [...]
            }
            path = storage.save_extraction("report_q1_2024", extraction_result)
        """
        # Add metadata if requested
        if include_metadata:
            data = {
                "doc_id": doc_id,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "data": data
            }
        
        # Create filename (sanitize doc_id)
        safe_doc_id = doc_id.replace(" ", "_").replace("/", "_")
        filename = f"{safe_doc_id}.json"
        filepath = self.extractions_path / filename
        
        # Save JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved: {filepath}")
        return str(filepath)
    
    def load_extraction(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Load extraction result from JSON file.
        
        Args:
            doc_id: Unique identifier for the document
        
        Returns:
            The extracted data as a dictionary, or None if not found
            
        Example:
            data = storage.load_extraction("report_q1_2024")
            if data:
                headlines = data['data']['headlines']
        """
        # Create filename
        safe_doc_id = doc_id.replace(" ", "_").replace("/", "_")
        filename = f"{safe_doc_id}.json"
        filepath = self.extractions_path / filename
        
        # Check if file exists
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            return None
        
        # Load JSON file
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📂 Loaded: {filepath}")
        return data
    
    def list_extractions(self) -> List[Dict[str, Any]]:
        """
        List all available extraction JSON files.
        
        Returns:
            List of dicts with file metadata:
            [
                {
                    "doc_id": "doc_001",
                    "filename": "doc_001.json",
                    "path": "/Volumes/.../doc_001.json",
                    "size_kb": 45.2,
                    "modified": "2024-01-15T10:30:00"
                },
                ...
            ]
        """
        # Get all JSON files
        json_files = list(self.extractions_path.glob("*.json"))
        
        # Build metadata for each file
        files_info = []
        for filepath in sorted(json_files):
            # Get file stats
            stat = filepath.stat()
            
            files_info.append({
                "doc_id": filepath.stem,  # filename without .json
                "filename": filepath.name,
                "path": str(filepath),
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        print(f"📋 Found {len(files_info)} extraction files")
        return files_info
    
    def delete_extraction(self, doc_id: str) -> bool:
        """
        Delete an extraction JSON file.
        
        Args:
            doc_id: Unique identifier for the document
        
        Returns:
            True if deleted successfully, False if not found
        """
        safe_doc_id = doc_id.replace(" ", "_").replace("/", "_")
        filename = f"{safe_doc_id}.json"
        filepath = self.extractions_path / filename
        
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            return False
        
        # Delete file
        filepath.unlink()
        print(f"🗑️ Deleted: {filepath}")
        return True
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the storage.
        
        Returns:
            Dictionary with storage metrics:
            {
                "total_files": 10,
                "total_size_mb": 125.4,
                "base_path": "/Volumes/..."
            }
        """
        files = self.list_extractions()
        total_size_mb = sum(f["size_kb"] for f in files) / 1024
        
        return {
            "total_files": len(files),
            "total_size_mb": round(total_size_mb, 2),
            "base_path": str(self.base_path),
            "extractions_path": str(self.extractions_path)
        }


# Example usage and testing
if __name__ == "__main__":
    # This block runs when you execute: python json_storage.py
    # Useful for testing!
    
    print("Testing JSON Storage Module")
    print("=" * 70)
    
    # Initialize storage
    storage = JSONStorage()
    
    # Test save
    test_data = {
        "headlines": [
            {"text": "Q4 Revenue Growth", "page": 1},
            {"text": "Market Expansion", "page": 2}
        ],
        "paragraphs": [
            "Revenue increased by 15% in Q4..."
        ],
        "tables": [
            {"rows": 10, "cols": 5}
        ]
    }
    
    print("\n1. Saving test extraction...")
    storage.save_extraction("test_doc", test_data)
    
    print("\n2. Loading test extraction...")
    loaded = storage.load_extraction("test_doc")
    print(f"   Headlines: {len(loaded['data']['headlines'])}")
    
    print("\n3. Listing all extractions...")
    files = storage.list_extractions()
    for f in files:
        print(f"   • {f['filename']} ({f['size_kb']} KB)")
    
    print("\n4. Storage stats...")
    stats = storage.get_storage_stats()
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_mb']} MB")
    
    print("\n5. Cleaning up test file...")
    storage.delete_extraction("test_doc")
    
    print("\n✅ All tests passed!")
