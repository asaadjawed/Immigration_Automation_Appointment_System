"""
RAG (Retrieval Augmented Generation) service.
Compares student documents with guidelines and generates compliance reports.
"""
from typing import Dict, List, Optional
from app.services.vector_db import VectorDBService
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings


class RAGService:
    """Service for RAG operations."""
    
    def __init__(self):
        self.vector_db = VectorDBService()
        self.llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            google_api_key=settings.GEMINI_OPEN_KEY
        )
    
    def compare_with_guidelines(self, student_text: str, student_documents: List[str], request_type: Optional[str] = None) -> Dict:
        """
        Compare student submission with guidelines using RAG.
        
        Args:
            student_text: Text from student email
            student_documents: List of extracted text from PDF documents
            request_type: Optional request type to filter specific guidelines
            
        Returns:
            Dictionary with compliance analysis
        """
        # Combine all student content
        combined_text = student_text + "\n\n" + "\n\n".join(student_documents)
        
        # For residence permit extension, use only residence_permit.txt
        guideline_name = None
        if request_type and "residence_permit" in request_type.lower() and "extension" in request_type.lower():
            guideline_name = "residence_permit.txt"
        
        # Search for relevant guidelines
        # If specific guideline requested, use only that one
        if guideline_name:
            relevant_guidelines = self.vector_db.search_similar(
                query=combined_text,
                n_results=1,
                guideline_name=guideline_name
            )
        else:
            # Otherwise, search all guidelines (limit to 3 to avoid confusion)
            relevant_guidelines = self.vector_db.search_similar(
                query=combined_text,
                n_results=3
            )
        
        # Extract guideline texts (prioritize the first/most relevant one)
        guideline_texts = [doc["document"] for doc in relevant_guidelines]
        
        # If we have multiple guidelines, prioritize the first one and note others
        if len(guideline_texts) > 1:
            primary_guideline = guideline_texts[0]
            other_guidelines = "\n\n---\n\n".join(guideline_texts[1:])
            guidelines_context = f"""PRIMARY GUIDELINE (MOST RELEVANT - USE THIS FOR COMPLIANCE CHECK):
{primary_guideline}

---
OTHER GUIDELINES (FOR REFERENCE ONLY):
{other_guidelines}"""
        else:
            guidelines_context = "\n\n---\n\n".join(guideline_texts)
        
        # Create prompt for LLM
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert immigration officer assistant. 
            Your task is to analyze student submissions and compare them with official guidelines.
            
            CRITICAL RULE: You MUST ONLY use the documents explicitly listed in the guidelines provided.
            DO NOT add any documents based on your general knowledge or training data.
            DO NOT infer additional requirements."""),
            HumanMessage(content=f"""
            STUDENT SUBMISSION:
            {combined_text}
            
            ---
            
            OFFICIAL GUIDELINES (USE ONLY THESE - DO NOT ADD ANYTHING ELSE):
            {guidelines_context}
            
            ---
            
            CRITICAL RULES - FOLLOW EXACTLY:
            1. REQUIRED_DOCUMENTS: List ONLY the documents explicitly mentioned in the guidelines above
               - If guideline says "passport", then required_documents = ["passport"] ONLY
               - DO NOT add: residence permit card, enrollment proof, financial statements, health insurance, etc.
               - DO NOT use your general knowledge about immigration requirements
               - ONLY use what is written in the guideline text
            
            2. DOCUMENT DETECTION (CRITICAL):
               - Look for documents in the STUDENT SUBMISSION text (both email body and PDF content)
               - For "passport": Look for keywords like "passport", "passport number", "passport no", "passport #", 
                 "passport id", "passport document", "travel document", "passport page", "passport copy", 
                 or any text that clearly indicates a passport document
               - If you see passport-related information (passport number, passport details, passport pages, etc.) 
                 in the submission → add "passport" to present_documents
               - Be lenient: If there's ANY indication of a passport in the text, consider it present
            
            3. COMPLIANCE CHECK:
               - If student has ALL documents from required_documents list → is_compliant = true
               - If student is missing ANY document from required_documents list → is_compliant = false
               - Example: If required_documents = ["passport"] and passport is provided → is_compliant = true
            
            4. MISSING_DOCUMENTS:
               - Only list documents from required_documents that are NOT present
               - If all required documents are present → missing_documents = []
            
            Please analyze and return JSON:
            {{
              "is_compliant": true/false,
              "compliance_score": 0-100,
              "present_documents": ["list of documents found in submission"],
              "missing_documents": ["only documents from required_documents that are missing"],
              "required_documents": ["ONLY documents listed in the guideline above - nothing else"],
              "issues": []
            }}
            
            EXAMPLE: If guideline says "Current valid passport" and student has passport:
            {{
              "is_compliant": true,
              "compliance_score": 100,
              "present_documents": ["passport"],
              "missing_documents": [],
              "required_documents": ["passport"],
              "issues": []
            }}
            
            DO NOT add documents to required_documents that are NOT in the guideline text!
            
            Format your response as JSON with keys: is_compliant (boolean), compliance_score (number), 
            present_documents (array), missing_documents (array), required_documents (array), issues (array).
            Example: {{"is_compliant": true, "compliance_score": 100, "present_documents": ["passport"], "missing_documents": [], "required_documents": ["passport"], "issues": []}}
            """)
        ])
        
        # Get LLM response
        messages = prompt.format_messages()
        response = self.llm.invoke(messages)
        
        # Parse response (simplified - in production, use proper JSON parsing)
        analysis_text = response.content
        
        # Extract compliance information
        compliance_data = self._parse_compliance_analysis(analysis_text)
        
        # Extract required documents directly from guideline text to override LLM inference
        # This ensures we only use what's actually in the guideline
        guideline_required_docs = self._extract_required_documents_from_guideline(guideline_texts[0] if guideline_texts else "")
        
        # Override required_documents if we extracted them from guideline
        if guideline_required_docs:
            compliance_data["required_documents"] = guideline_required_docs
            # Recalculate missing_documents based on actual guideline requirements
            present_docs = compliance_data.get("present_documents", [])
            
            # Fallback: Check for passport keywords in the combined text if LLM didn't detect it
            combined_text_lower = (student_text + " " + " ".join(student_documents)).lower()
            passport_keywords = [
                "passport", "passport number", "passport no", "passport #", 
                "passport id", "passport document", "travel document", 
                "passport page", "passport copy", "passport details"
            ]
            
            # If passport is required but not detected, check for keywords
            if "passport" in [d.lower() for d in guideline_required_docs]:
                has_passport_keywords = any(keyword in combined_text_lower for keyword in passport_keywords)
                if has_passport_keywords and "passport" not in [p.lower() for p in present_docs]:
                    present_docs.append("passport")
                    print(f"DEBUG: Detected passport via keyword fallback in text")
            
            compliance_data["present_documents"] = present_docs
            compliance_data["missing_documents"] = [
                doc for doc in guideline_required_docs 
                if doc.lower() not in [p.lower() for p in present_docs]
            ]
            # Recalculate compliance based on actual guideline
            compliance_data["is_compliant"] = len(compliance_data["missing_documents"]) == 0
            # Update compliance score to match compliance status
            if compliance_data["is_compliant"]:
                compliance_data["compliance_score"] = 100.0
            else:
                # Calculate score based on how many documents are missing
                missing_count = len(compliance_data["missing_documents"])
                total_required = len(guideline_required_docs)
                if total_required > 0:
                    compliance_data["compliance_score"] = max(0.0, ((total_required - missing_count) / total_required) * 100.0)
                else:
                    compliance_data["compliance_score"] = 0.0
            print(f"DEBUG: Overrode with guideline extraction - required: {guideline_required_docs}, missing: {compliance_data['missing_documents']}, compliant: {compliance_data['is_compliant']}")
        
        return {
            "is_compliant": compliance_data.get("is_compliant", False),
            "compliance_score": compliance_data.get("compliance_score", 0.0),
            "present_documents": compliance_data.get("present_documents", []),
            "missing_documents": compliance_data.get("missing_documents", []),
            "required_documents": compliance_data.get("required_documents", []),
            "issues": compliance_data.get("issues", []),
            "analysis": analysis_text,
            "relevant_guidelines": [doc["id"] for doc in relevant_guidelines]
        }
    
    def _extract_required_documents_from_guideline(self, guideline_text: str) -> List[str]:
        """Extract required documents directly from guideline text (passport only)."""
        if not guideline_text:
            return []
        
        required_docs = []
        guideline_lower = guideline_text.lower()
        
        lines = guideline_text.split('\n')
        in_requirements_section = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if "required" in line_lower and ("document" in line_lower or "valid" in line_lower):
                in_requirements_section = True
                continue
            
            if in_requirements_section and (line.strip().startswith('-') or line.strip().startswith('•')):
                if "passport" in line_lower and "passport" not in [d.lower() for d in required_docs]:
                    required_docs.append("passport")
        
        if not required_docs and "passport" in guideline_lower:
            if "required" in guideline_lower or "-" in guideline_text:
                required_docs.append("passport")
        
        return required_docs
    
    def _parse_compliance_analysis(self, analysis_text: str) -> Dict:
        """
        Parse LLM compliance analysis response.
        In production, use proper JSON parsing or structured output.
        """
        import json
        import re
        
        json_patterns = [
            r'\{[^{}]*"is_compliant"[^{}]*\}',  # Simple JSON
            r'\{.*?"is_compliant".*?\}',  # JSON with is_compliant
            r'\{.*?\}',  # Any JSON object
        ]
        
        for pattern in json_patterns:
            json_match = re.search(pattern, analysis_text, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    if "is_compliant" in parsed:
                        if isinstance(parsed["is_compliant"], bool):
                            return parsed
                        elif isinstance(parsed["is_compliant"], str):
                            parsed["is_compliant"] = parsed["is_compliant"].lower() in ["true", "yes", "1", "compliant"]
                            return parsed
                        else:
                            parsed["is_compliant"] = bool(parsed["is_compliant"])
                            return parsed
                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue
        
        text_lower = analysis_text.lower()
        
        negative_indicators = [
            "not compliant", "non-compliant", "non compliant",
            "missing", "incomplete", "insufficient",
            "does not meet", "doesn't meet", "fails to",
            "rejected", "rejection", "cannot be approved"
        ]
        
        positive_indicators = [
            "is compliant", "fully compliant", "meets requirements",
            "all required", "complete", "sufficient",
            "approved", "acceptable", "valid"
        ]
        
        has_negative = any(indicator in text_lower for indicator in negative_indicators)
        has_positive = any(indicator in text_lower for indicator in positive_indicators)
        
        if has_negative and not has_positive:
            is_compliant = False
        elif has_positive and not has_negative:
            is_compliant = True
        elif "is_compliant" in text_lower or '"is_compliant"' in text_lower:
            if re.search(r'is_compliant["\s:]*true', text_lower):
                is_compliant = True
            elif re.search(r'is_compliant["\s:]*false', text_lower):
                is_compliant = False
            else:
                is_compliant = False
        else:
            if "not compliant" in text_lower or "non-compliant" in text_lower:
                is_compliant = False
            elif "compliant" in text_lower:
                is_compliant = True
            else:
                is_compliant = False
        
        compliance_score = 50.0
        score_patterns = [
            r'"compliance_score"\s*:\s*(\d+(?:\.\d+)?)',
            r'compliance_score["\s:]*(\d+(?:\.\d+)?)',
            r'score["\s:]*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*%',  # Percentage
        ]
        
        for pattern in score_patterns:
            score_match = re.search(pattern, text_lower)
            if score_match:
                try:
                    score = float(score_match.group(1))
                    if 0 <= score <= 100:
                        compliance_score = score
                        break
                except:
                    continue
        
        if is_compliant and compliance_score < 50:
            compliance_score = 100.0
        elif not is_compliant and compliance_score > 50:
            compliance_score = 30.0
        
        return {
            "is_compliant": is_compliant,
            "compliance_score": compliance_score,
            "present_documents": [],
            "missing_documents": [],
            "required_documents": [],
            "issues": [analysis_text]
        }
    
    def load_guidelines_from_file(self, file_path: str, guideline_name: str):
        """
        Load guidelines from a file and add to vector database.
        
        Args:
            file_path: Path to guidelines file
            guideline_name: Name of the guideline
        """
        with open(file_path, "r", encoding="utf-8") as f:
            guidelines_text = f.read()
        
        return self.vector_db.add_guidelines(guidelines_text, guideline_name)

