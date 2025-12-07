"""
Email notification service for sending emails to students.
Handles appointment confirmations and other notifications.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from app.config import settings


class EmailNotificationService:
    """Service for sending email notifications."""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER or settings.EMAIL_USER
        self.smtp_password = settings.SMTP_PASSWORD or settings.EMAIL_PASSWORD
        self.email_from = settings.EMAIL_FROM or settings.EMAIL_USER
        self.use_tls = settings.SMTP_USE_TLS
    
    def send_appointment_confirmation(
        self,
        recipient_email: str,
        recipient_name: str,
        appointment_date: datetime,
        appointment_time: str,
        location: str,
        appointment_id: int,
        request_id: int,
        required_documents: list
    ) -> bool:
        """
        Send appointment confirmation email to student.
        
        Args:
            recipient_email: Student's email address
            recipient_name: Student's name
            appointment_date: Appointment date and time
            appointment_time: Appointment time string
            location: Appointment location
            appointment_id: Appointment ID
            request_id: Request ID
            required_documents: List of required documents
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Format appointment date
            date_str = appointment_date.strftime("%B %d, %Y")
            time_str = appointment_time if appointment_time else appointment_date.strftime("%I:%M %p")
            
            # Format required documents
            if isinstance(required_documents, str):
                # If it's a string representation of a list, try to parse it
                import ast
                try:
                    required_documents = ast.literal_eval(required_documents)
                except:
                    required_documents = [required_documents]
            
            docs_list = "\n".join([f"  • {doc}" for doc in required_documents]) if required_documents else "  • None specified"
            
            # Create email content
            subject = f"Appointment Confirmed - Immigration Office (Appointment #{appointment_id})"
            
            # HTML email body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Appointment Confirmed</h2>
                    
                    <p>Dear {recipient_name},</p>
                    
                    <p>Your appointment has been successfully scheduled at the Immigration Office.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #2c3e50;">Appointment Details</h3>
                        <p><strong>Appointment ID:</strong> #{appointment_id}</p>
                        <p><strong>Request ID:</strong> #{request_id}</p>
                        <p><strong>Date:</strong> {date_str}</p>
                        <p><strong>Time:</strong> {time_str}</p>
                        <p><strong>Location:</strong> {location}</p>
                    </div>
                    
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                        <h3 style="margin-top: 0; color: #856404;">Required Documents</h3>
                        <p>Please bring the following documents to your appointment:</p>
                        {docs_list}
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <p style="color: #666; font-size: 14px;">
                            <strong>Important Notes:</strong><br>
                            • Please arrive 10 minutes before your scheduled time<br>
                            • Bring all required documents listed above<br>
                            • If you need to reschedule, please contact us as soon as possible<br>
                            • This is an automated email. Please do not reply to this message.
                        </p>
                    </div>
                    
                    <p style="margin-top: 30px; color: #666; font-size: 12px;">
                        Best regards,<br>
                        Immigration Office Automation System
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Plain text email body (fallback)
            text_body = f"""
Appointment Confirmed

Dear {recipient_name},

Your appointment has been successfully scheduled at the Immigration Office.

Appointment Details:
- Appointment ID: #{appointment_id}
- Request ID: #{request_id}
- Date: {date_str}
- Time: {time_str}
- Location: {location}

Required Documents:
Please bring the following documents to your appointment:
{docs_list}

Important Notes:
- Please arrive 10 minutes before your scheduled time
- Bring all required documents listed above
- If you need to reschedule, please contact us as soon as possible
- This is an automated email. Please do not reply to this message.

Best regards,
Immigration Office Automation System
            """
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Attach both plain text and HTML versions
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"Appointment confirmation email sent to {recipient_email}")
            return True
            
        except Exception as e:
            print(f"Error sending appointment confirmation email to {recipient_email}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Generic method to send an email.
        
        Args:
            recipient_email: Recipient's email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            if not text_body:
                text_body = html_body  # Fallback to HTML if no text version
            
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"Email sent to {recipient_email}")
            return True
            
        except Exception as e:
            print(f"Error sending email to {recipient_email}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

