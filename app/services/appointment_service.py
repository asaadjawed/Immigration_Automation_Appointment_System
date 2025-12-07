"""
Appointment scheduling service.
Manages available slots and schedules appointments for students.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from app.models import AvailableSlot, Appointment


class AppointmentService:
    """Service for appointment scheduling."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_next_available_slot(self) -> Optional[AvailableSlot]:
        """
        Get the next available appointment slot.
        
        Returns:
            AvailableSlot object or None if no slots available
        """
        # Find next available slot (not full, in the future)
        now = datetime.now(timezone.utc)
        
        slot = self.db.query(AvailableSlot).filter(
            and_(
                AvailableSlot.is_available == True,
                AvailableSlot.slot_date > now,
                AvailableSlot.current_bookings < AvailableSlot.max_capacity
            )
        ).order_by(AvailableSlot.slot_date.asc()).first()
        
        return slot
    
    def schedule_appointment(
        self,
        student_id: int,
        request_id: int,
        required_documents: List[str]
    ) -> Optional[Appointment]:
        """
        Schedule an appointment for a student.
        
        Args:
            student_id: Student ID
            request_id: Request ID
            required_documents: List of required documents
            
        Returns:
            Appointment object or None if scheduling failed
        """
        # Get next available slot
        slot = self.get_next_available_slot()
        
        if not slot:
            return None
        
        # Create appointment
        appointment = Appointment(
            student_id=student_id,
            request_id=request_id,
            appointment_date=slot.slot_date,
            appointment_time=slot.slot_time,
            status="scheduled",
            location="Immigration Office - Main Building",
            required_documents=str(required_documents),  # Store as JSON string
            notes=f"Automated appointment for request #{request_id}"
        )
        
        # Update slot bookings
        slot.current_bookings += 1
        if slot.current_bookings >= slot.max_capacity:
            slot.is_available = False
        
        # Save to database
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        
        return appointment
    
    def create_available_slots(self, start_date: datetime, num_days: int, slots_per_day: int = 5):
        """
        Create available appointment slots.
        
        Args:
            start_date: Starting date for slots
            num_days: Number of days to create slots for
            slots_per_day: Number of slots per day
        """
        time_slots = ["09:00", "10:30", "12:00", "14:00", "15:30"]
        
        for day in range(num_days):
            slot_date = start_date + timedelta(days=day)
            
            for i, time_slot in enumerate(time_slots[:slots_per_day]):
                # Check if slot already exists
                existing = self.db.query(AvailableSlot).filter(
                    and_(
                        AvailableSlot.slot_date == slot_date,
                        AvailableSlot.slot_time == time_slot
                    )
                ).first()
                
                if not existing:
                    slot = AvailableSlot(
                        slot_date=slot_date,
                        slot_time=time_slot,
                        is_available=True,
                        max_capacity=1,
                        current_bookings=0
                    )
                    self.db.add(slot)
        
        self.db.commit()
    
    def get_appointment_details(self, appointment_id: int) -> Optional[Appointment]:
        """Get appointment details by ID."""
        return self.db.query(Appointment).filter(Appointment.id == appointment_id).first()
    
    def get_student_appointments(self, student_id: int) -> List[Appointment]:
        """Get all appointments for a student."""
        return self.db.query(Appointment).filter(
            Appointment.student_id == student_id
        ).order_by(Appointment.appointment_date.asc()).all()

