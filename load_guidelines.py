"""
Script to load guidelines into the vector database.
Run this after setting up the system to load your immigration guidelines.
"""
import os
from app.services.rag_service import RAGService
from app.config import settings

def load_guidelines():
    """Load all guideline files from the guidelines directory."""
    rag_service = RAGService()
    
    guidelines_dir = settings.GUIDELINES_DIR
    
    # Create directory if it doesn't exist
    os.makedirs(guidelines_dir, exist_ok=True)
    
    # Check if directory has files
    if not os.listdir(guidelines_dir):
        print(f"No guideline files found in {guidelines_dir}")
        print("Please add your immigration guidelines as .txt files in the guidelines/ folder")
        return
    
    # Load all guideline files
    loaded_count = 0
    for filename in os.listdir(guidelines_dir):
        if filename.endswith((".txt", ".md")) and filename != "README.md":
            file_path = os.path.join(guidelines_dir, filename)
            try:
                rag_service.load_guidelines_from_file(file_path, filename)
                print(f"✓ Loaded: {filename}")
                loaded_count += 1
            except Exception as e:
                print(f"✗ Error loading {filename}: {str(e)}")
    
    print(f"\nTotal guidelines loaded: {loaded_count}")
    if loaded_count > 0:
        print("Guidelines are now available for RAG comparison!")
    else:
        print("No guidelines were loaded. Add .txt files to the guidelines/ folder.")

if __name__ == "__main__":
    load_guidelines()

