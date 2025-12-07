"""
Script to create available appointment slots.
Run this to populate the database with available appointment times.
"""
from app.database import SessionLocal
from app.services.appointment_service import AppointmentService
from datetime import datetime, timedelta, timezone

def create_appointment_slots():
    """Create appointment slots for the next 30 days."""
    db = SessionLocal()
    
    try:
        service = AppointmentService(db)
        
        # Create slots starting from tomorrow
        start_date = datetime.now(timezone.utc) + timedelta(days=1)
        
        # Create slots for next 30 days, 5 slots per day
        service.create_available_slots(
            start_date=start_date,
            num_days=30,
            slots_per_day=5
        )
        
        print(f"✓ Created appointment slots for the next 30 days")
        print(f"  Starting from: {start_date.strftime('%Y-%m-%d')}")
        print(f"  5 slots per day (09:00, 10:30, 12:00, 14:00, 15:30)")
        
        # Show next available slot
        next_slot = service.get_next_available_slot()
        if next_slot:
            print(f"\nNext available slot:")
            print(f"  Date: {next_slot.slot_date.strftime('%Y-%m-%d')}")
            print(f"  Time: {next_slot.slot_time}")
        else:
            print("\n⚠️  No available slots found (all might be booked)")
        
    except Exception as e:
        print(f"Error creating slots: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    create_appointment_slots()

