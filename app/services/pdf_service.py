"""
PDF processing service for extracting text from PDF documents.
"""
import pdfplumber
import PyPDF2
from typing import Dict
import os


class PDFService:
    """Service for processing PDF files."""
    
    def extract_text(self, file_path: str) -> Dict[str, any]:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        text = ""
        metadata = {}
        
        try:
            # Try using pdfplumber (better for complex PDFs)
            with pdfplumber.open(file_path) as pdf:
                # Extract text from all pages
                pages_text = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
                
                text = "\n\n".join(pages_text)
                
                # Extract metadata
                metadata = {
                    "num_pages": len(pdf.pages),
                    "title": pdf.metadata.get("Title", ""),
                    "author": pdf.metadata.get("Author", ""),
                    "subject": pdf.metadata.get("Subject", ""),
                }
        
        except Exception as e:
            print(f"Error with pdfplumber, trying PyPDF2: {str(e)}")
            
            # Fallback to PyPDF2
            try:
                with open(file_path, "rb") as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    
                    # Extract text from all pages
                    pages_text = []
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            pages_text.append(page_text)
                    
                    text = "\n\n".join(pages_text)
                    
                    # Extract metadata
                    metadata = {
                        "num_pages": len(pdf_reader.pages),
                        "title": pdf_reader.metadata.get("/Title", ""),
                        "author": pdf_reader.metadata.get("/Author", ""),
                        "subject": pdf_reader.metadata.get("/Subject", ""),
                    }
            
            except Exception as e2:
                print(f"Error extracting text from PDF: {str(e2)}")
                text = ""
                metadata = {"error": str(e2)}
        
        return {
            "text": text,
            "metadata": metadata,
            "file_path": file_path,
            "file_size": os.path.getsize(file_path)
        }
    
    def extract_text_simple(self, file_path: str) -> str:
        """
        Simple text extraction (returns only text).
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text as string
        """
        result = self.extract_text(file_path)
        return result.get("text", "")

