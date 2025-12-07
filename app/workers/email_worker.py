"""
Celery worker tasks for processing emails asynchronously.
"""
from app.celery_app import celery_app
from app.services.email_service import EmailService
from app.services.pdf_service import PDFService
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.services.appointment_service import AppointmentService
from app.services.vector_db import VectorDBService
from app.services.email_notification_service import EmailNotificationService
from app.database import SessionLocal
from app.models import Student, Request, Document, RequestStatus, RequestType
from typing import Dict
from datetime import datetime, timezone
import os


@celery_app.task(name="process_email")
def process_email_task(email_data: Dict):
    """
    Process a single email: extract, store, categorize, and schedule.
    
    This is the main workflow task that processes emails one by one.
    """
    db = SessionLocal()
    
    try:
        subject = email_data.get("subject", "")
        existing_request = db.query(Request).filter(Request.email_subject == subject).first()
        
        if existing_request and existing_request.created_at:
            time_diff = datetime.now(timezone.utc) - existing_request.created_at.replace(tzinfo=timezone.utc)
            if time_diff.total_seconds() < 86400:
                print(f"Email already processed (duplicate): {subject}")
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "request_id": existing_request.id
                }
        
        pdf_service = PDFService()
        rag_service = RAGService()
        llm_service = LLMService()
        vector_db = VectorDBService()
        
        sender = email_data.get("sender", "")
        body = email_data.get("body", "")
        attachments = email_data.get("attachments", [])
        
        email_address = sender.split("<")[-1].split(">")[0] if "<" in sender else sender
        
        student = db.query(Student).filter(Student.email == email_address).first()
        if not student:
            name = sender.split("<")[0].strip() if "<" in sender else email_address.split("@")[0]
            student = Student(email=email_address, name=name)
            db.add(student)
            db.commit()
            db.refresh(student)
        
        request = Request(
            student_id=student.id,
            email_subject=subject,
            email_body=body,
            status=RequestStatus.PENDING
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        
        documents_text = []
        print(f"\n{'='*60}")
        print(f"PROCESSING ATTACHMENTS for Request #{request.id}:")
        print(f"{'='*60}")
        print(f"Total attachments received: {len(attachments)}")
        
        for idx, attachment in enumerate(attachments, 1):
            content_type = attachment.get("content_type", "")
            filename = attachment.get("filename", "")
            file_path = attachment.get("file_path")
            
            print(f"\nAttachment #{idx}:")
            print(f"  - Filename: {filename}")
            print(f"  - Content Type: {content_type}")
            print(f"  - File Path: {file_path}")
            print(f"  - File Exists: {os.path.exists(file_path) if file_path else False}")
            
            # Check if it's a PDF by content_type or filename
            is_pdf = (
                content_type == "application/pdf" or 
                filename.lower().endswith(".pdf")
            )
            print(f"  - Is PDF: {is_pdf}")
            
            if is_pdf and file_path and os.path.exists(file_path):
                try:
                    print(f"  → Processing PDF: {filename}")
                    pdf_result = pdf_service.extract_text(file_path)
                    extracted_text = pdf_result.get("text", "")
                    print(f"  → Extracted text length: {len(extracted_text)} characters")
                    
                    # Save document to database even if no text extracted (might be scanned/image PDF)
                    # Use filename as fallback text for vector DB if extraction failed
                    text_for_vector = extracted_text if extracted_text else f"Document: {filename}"
                    
                    if extracted_text:
                        documents_text.append(extracted_text)
                        print(f"  → Adding to vector database with extracted text...")
                    else:
                        print(f"  ⚠ No text extracted (may be scanned/image PDF), using filename as text")
                        # Still add to documents_text for RAG processing (filename might contain info)
                        documents_text.append(text_for_vector)
                    
                    vector_id = vector_db.add_document(
                        text=text_for_vector,
                        metadata={
                            "request_id": request.id,
                            "filename": filename,
                            "type": "student_document",
                            "has_text": bool(extracted_text)
                        }
                    )
                    print(f"  → Vector ID: {vector_id}")
                    
                    # Save document to database regardless of text extraction success
                    document = Document(
                        request_id=request.id,
                        filename=filename,
                        file_path=file_path,
                        file_type="pdf",
                        extracted_text=extracted_text[:5000] if extracted_text else f"Scanned/image PDF: {filename}",
                        vector_id=vector_id
                    )
                    db.add(document)
                    print(f"  ✓ Document saved to database: {filename} (vector_id: {vector_id})")
                    
                except Exception as doc_error:
                    print(f"  ✗ Error processing document {filename}: {str(doc_error)}")
                    import traceback
                    traceback.print_exc()
                    # Still try to save document metadata even if extraction fails
                    try:
                        document = Document(
                            request_id=request.id,
                            filename=filename,
                            file_path=file_path,
                            file_type="pdf",
                            extracted_text=f"Error extracting text: {str(doc_error)}",
                            vector_id=None
                        )
                        db.add(document)
                        print(f"  ✓ Document metadata saved (extraction failed): {filename}")
                    except Exception as save_error:
                        print(f"  ✗ Failed to save document metadata: {str(save_error)}")
            else:
                if not is_pdf:
                    print(f"  ✗ Skipped: Not a PDF file")
                elif not file_path:
                    print(f"  ✗ Skipped: No file path provided")
                elif not os.path.exists(file_path):
                    print(f"  ✗ Skipped: File does not exist at path")
        
        print(f"\nTotal documents processed: {len(documents_text)}")
        print(f"{'='*60}\n")
        
        db.commit()
        request.status = RequestStatus.PROCESSING
        db.commit()
        
        email_content_lower = (subject + " " + body).lower()
        request_type_for_rag = None
        if "residence permit" in email_content_lower and "extension" in email_content_lower:
            request_type_for_rag = "residence_permit_extension"
        
        rag_result = rag_service.compare_with_guidelines(body, documents_text, request_type=request_type_for_rag)
        
        request.is_compliant = rag_result.get("is_compliant", False)
        request.compliance_score = rag_result.get("compliance_score", 0.0)
        request.missing_documents = str(rag_result.get("missing_documents", []))
        request.required_documents = str(rag_result.get("required_documents", []))
        db.commit()
        
        try:
            categorization = llm_service.categorize_request(subject, body, documents_text)
            request.request_type = categorization.get("category")
            request.llm_category = str(categorization.get("category"))
            request.llm_confidence = categorization.get("confidence", 0.0)
            request.llm_analysis = categorization.get("raw_response", "")
        except Exception as llm_error:
            print(f"LLM categorization failed: {str(llm_error)}")
            request.request_type = RequestType.OTHER
            request.llm_category = "error"
            request.llm_confidence = 0.0
            request.llm_analysis = f"LLM error: {str(llm_error)}"
        
        request.status = RequestStatus.CATEGORIZED
        request.processed_at = datetime.now(timezone.utc)
        db.commit()
        
        if request.is_compliant:
            appointment_service = AppointmentService(db)
            required_docs = rag_result.get("required_documents", [])
            appointment = appointment_service.schedule_appointment(
                student_id=student.id,
                request_id=request.id,
                required_documents=required_docs
            )
            
            if appointment:
                request.appointment_id = appointment.id
                request.status = RequestStatus.APPOINTMENT_SCHEDULED
                db.commit()
                
                try:
                    email_notification = EmailNotificationService()
                    email_notification.send_appointment_confirmation(
                        recipient_email=student.email,
                        recipient_name=student.name or "Student",
                        appointment_date=appointment.appointment_date,
                        appointment_time=appointment.appointment_time or "",
                        location=appointment.location or "Immigration Office - Main Building",
                        appointment_id=appointment.id,
                        request_id=request.id,
                        required_documents=required_docs
                    )
                    print(f"Appointment confirmation email sent to {student.email}")
                except Exception as email_error:
                    print(f"Failed to send appointment confirmation email: {str(email_error)}")
                    import traceback
                    traceback.print_exc()
        
        return {
            "request_id": request.id,
            "status": "success",
            "categorized_as": str(request.request_type),
            "appointment_scheduled": request.appointment_id is not None
        }
    
    except Exception as e:
        if 'request' in locals():
            if not request.llm_analysis:
                request.llm_analysis = f"Processing error: {str(e)}"
            db.commit()
        
        print(f"Error processing email: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }
    
    finally:
        db.close()


@celery_app.task(name="process_all_emails")
def process_all_emails_task():
    """
    Fetch all new emails and queue them for processing.
    """
    email_service = EmailService()
    emails = email_service.fetch_emails(limit=10)
    
    results = []
    for email_data in emails:
        serializable_data = {
            "email_id": email_data.get("email_id"),
            "subject": email_data.get("subject"),
            "sender": email_data.get("sender"),
            "body": email_data.get("body"),
            "attachments": email_data.get("attachments", []),
            "date": email_data.get("date")
        }
        
        task = process_email_task.delay(serializable_data)
        results.append(task.id)
        email_service.mark_as_read(email_data.get("email_id"))
    
    return {
        "emails_fetched": len(emails),
        "tasks_queued": results
    }
