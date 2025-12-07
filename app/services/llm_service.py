"""
LLM service for categorizing immigration requests.
"""
from typing import Dict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.models import RequestType


class LLMService:
    """Service for LLM-based categorization."""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            google_api_key=settings.GEMINI_OPEN_KEY
        )
    
    def categorize_request(self, email_subject: str, email_body: str, documents_text: List[str]) -> Dict:
        """
        Categorize immigration request using LLM.
        
        Args:
            email_subject: Email subject line
            email_body: Email body text
            documents_text: List of extracted text from documents
            
        Returns:
            Dictionary with category, confidence, and analysis
        """
        # Combine all text
        combined_text = f"Subject: {email_subject}\n\nBody: {email_body}\n\n"
        combined_text += "\n\n---\n\n".join(documents_text)
        
        # Create categorization prompt
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert immigration officer assistant.
            Your task is to categorize immigration requests based on the content.
            
            Categories:
            - residence_permit_extension: Extension of existing residence permit
            - residence_permit_new: New residence permit application
            - visa_extension: Extension of existing visa
            - temporary_visa: Application for temporary visa
            - work_permit: Work permit application
            - other: Any other type of request
            
            Analyze the request and determine the most appropriate category."""),
            HumanMessage(content=f"""
            STUDENT REQUEST:
            {combined_text}
            
            Please categorize this request and provide:
            1. Category (one of: residence_permit_extension, residence_permit_new, visa_extension, temporary_visa, work_permit, other)
            2. Confidence level (0-100)
            3. Brief explanation of why this category was chosen
            4. Key information extracted from the request
            
            Format your response as JSON with keys: category, confidence, explanation, key_info.
            """)
        ])
        
        # Get LLM response
        messages = prompt.format_messages()
        response = self.llm.invoke(messages)
        
        # Parse response
        categorization = self._parse_categorization(response.content)
        
        return categorization
    
    def _parse_categorization(self, response_text: str) -> Dict:
        """
        Parse LLM categorization response.
        """
        import json
        import re
        
        # Try to extract JSON
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                category = parsed.get("category", "other")
                
                # Map to RequestType enum
                category_map = {
                    "residence_permit_extension": RequestType.RESIDENCE_PERMIT_EXTENSION,
                    "residence_permit_new": RequestType.RESIDENCE_PERMIT_NEW,
                    "visa_extension": RequestType.VISA_EXTENSION,
                    "temporary_visa": RequestType.TEMPORARY_VISA,
                    "work_permit": RequestType.WORK_PERMIT,
                    "other": RequestType.OTHER
                }
                
                return {
                    "category": category_map.get(category, RequestType.OTHER),
                    "confidence": float(parsed.get("confidence", 0.0)),
                    "explanation": parsed.get("explanation", ""),
                    "key_info": parsed.get("key_info", ""),
                    "raw_response": response_text
                }
            except Exception as e:
                print(f"Error parsing categorization: {str(e)}")
        
        # Fallback
        return {
            "category": RequestType.OTHER,
            "confidence": 0.0,
            "explanation": "Could not parse LLM response",
            "key_info": "",
            "raw_response": response_text
        }

