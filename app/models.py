"""
SQLAlchemy database models.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


class RequestType(str, enum.Enum):
    """Enumeration of request types."""
    RESIDENCE_PERMIT_EXTENSION = "residence_permit_extension"
    RESIDENCE_PERMIT_NEW = "residence_permit_new"
    VISA_EXTENSION = "visa_extension"
    TEMPORARY_VISA = "temporary_visa"
    WORK_PERMIT = "work_permit"
    OTHER = "other"


class RequestStatus(str, enum.Enum):
    """Enumeration of request statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    CATEGORIZED = "categorized"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPOINTMENT_SCHEDULED = "appointment_scheduled"
    COMPLETED = "completed"


class Student(Base):
    """Student information model."""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))
    student_id = Column(String(100), unique=True, index=True)
    phone = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    requests = relationship("Request", back_populates="student")


class Request(Base):
    """Immigration request model."""
    __tablename__ = "requests"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    email_subject = Column(String(500))
    email_body = Column(Text)
    request_type = Column(SQLEnum(RequestType), nullable=True)
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING)
    
    # LLM Analysis
    llm_category = Column(String(100))
    llm_confidence = Column(Float, default=0.0)
    llm_analysis = Column(Text)
    
    # Compliance
    is_compliant = Column(Boolean, default=False)
    compliance_score = Column(Float, default=0.0)
    missing_documents = Column(Text)  # JSON string of missing docs
    required_documents = Column(Text)  # JSON string of required docs
    
    # Appointment
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="requests")
    documents = relationship("Document", back_populates="request")
    # One-to-one relationship: Request.appointment_id -> Appointment.id
    # Note: We must specify foreign_keys because Appointment also has request_id pointing to Request
    # This tells SQLAlchemy to use Request.appointment_id, not Appointment.request_id
    appointment = relationship(
        "Appointment",
        foreign_keys=[appointment_id],
        uselist=False
    )


class Document(Base):
    """Document model for storing document metadata."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_type = Column(String(50))  # pdf, docx, etc.
    extracted_text = Column(Text)
    vector_id = Column(String(255))  # ID in vector database
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    request = relationship("Request", back_populates="documents")


class Appointment(Base):
    """Appointment scheduling model."""
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=True)
    appointment_date = Column(DateTime(timezone=True), nullable=False)
    appointment_time = Column(String(50))
    status = Column(String(50), default="scheduled")  # scheduled, completed, cancelled
    location = Column(String(255))
    required_documents = Column(Text)  # JSON string
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    # One-to-one relationship: Appointment.request_id -> Request.id
    # Note: We must specify foreign_keys because Request also has appointment_id pointing to Appointment
    # This tells SQLAlchemy to use Appointment.request_id, not Request.appointment_id
    request = relationship(
        "Request",
        foreign_keys=[request_id],
        uselist=False
    )


class AvailableSlot(Base):
    """Available appointment slots."""
    __tablename__ = "available_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    slot_date = Column(DateTime(timezone=True), nullable=False)
    slot_time = Column(String(50), nullable=False)
    is_available = Column(Boolean, default=True)
    max_capacity = Column(Integer, default=1)
    current_bookings = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

