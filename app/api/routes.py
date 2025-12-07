"""
FastAPI routes for the immigration automation system.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Request, Student, Appointment, RequestStatus, RequestType
from app.workers.email_worker import process_all_emails_task
from app.services.appointment_service import AppointmentService
from datetime import datetime, timezone
from pydantic import BaseModel

router = APIRouter()


# Pydantic models for request/response
class RequestResponse(BaseModel):
    id: int
    student_id: int
    email_subject: str
    request_type: str
    status: str
    is_compliant: bool
    compliance_score: float
    appointment_id: int | None
    
    class Config:
        from_attributes = True


class StudentResponse(BaseModel):
    id: int
    email: str
    name: str | None
    
    class Config:
        from_attributes = True


class AppointmentResponse(BaseModel):
    id: int
    student_id: int
    appointment_date: datetime
    appointment_time: str
    status: str
    
    class Config:
        from_attributes = True


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Immigration Office Automation",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/emails/process")
async def process_emails():
    """
    Manually trigger email processing.
    Fetches new emails and queues them for processing.
    """
    try:
        # Queue the task
        task = process_all_emails_task.delay()
        
        return {
            "status": "success",
            "message": "Email processing started",
            "task_id": task.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requests", response_model=List[RequestResponse])
async def get_requests(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all requests with optional filtering.
    """
    query = db.query(Request)
    
    if status:
        try:
            status_enum = RequestStatus(status)
            query = query.filter(Request.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    requests = query.offset(skip).limit(limit).all()
    return requests


@router.get("/requests/{request_id}", response_model=RequestResponse)
async def get_request(request_id: int, db: Session = Depends(get_db)):
    """
    Get a specific request by ID.
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return request


@router.get("/students", response_model=List[StudentResponse])
async def get_students(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all students."""
    students = db.query(Student).offset(skip).limit(limit).all()
    return students


@router.get("/students/{student_id}/requests", response_model=List[RequestResponse])
async def get_student_requests(student_id: int, db: Session = Depends(get_db)):
    """Get all requests for a specific student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return student.requests


@router.get("/appointments/available")
async def get_available_appointments(db: Session = Depends(get_db)):
    """
    Get available appointment slots.
    """
    appointment_service = AppointmentService(db)
    slot = appointment_service.get_next_available_slot()
    
    if not slot:
        return {
            "available": False,
            "message": "No available slots at the moment"
        }
    
    return {
        "available": True,
        "slot_date": slot.slot_date.isoformat(),
        "slot_time": slot.slot_time,
        "slot_id": slot.id
    }


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    """Get appointment details."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return appointment


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    Get system statistics.
    """
    total_requests = db.query(Request).count()
    total_students = db.query(Student).count()
    total_appointments = db.query(Appointment).count()
    
    # Count by status
    pending = db.query(Request).filter(Request.status == RequestStatus.PENDING).count()
    processing = db.query(Request).filter(Request.status == RequestStatus.PROCESSING).count()
    categorized = db.query(Request).filter(Request.status == RequestStatus.CATEGORIZED).count()
    scheduled = db.query(Request).filter(Request.status == RequestStatus.APPOINTMENT_SCHEDULED).count()
    
    # Count by type
    type_counts = {}
    for req_type in RequestType:
        count = db.query(Request).filter(Request.request_type == req_type).count()
        type_counts[req_type.value] = count
    
    return {
        "total_requests": total_requests,
        "total_students": total_students,
        "total_appointments": total_appointments,
        "requests_by_status": {
            "pending": pending,
            "processing": processing,
            "categorized": categorized,
            "appointment_scheduled": scheduled
        },
        "requests_by_type": type_counts
    }

