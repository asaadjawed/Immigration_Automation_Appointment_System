"""
Email service for fetching and processing emails from IMAP server.
"""
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Dict
import os
from app.config import settings


class EmailService:
    """Service for handling email operations."""
    
    def __init__(self):
        self.host = settings.EMAIL_HOST
        self.port = settings.EMAIL_PORT
        self.user = settings.EMAIL_USER
        self.password = settings.EMAIL_PASSWORD
        self.use_ssl = settings.EMAIL_USE_SSL
        self.upload_dir = settings.UPLOAD_DIR
        
        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def connect(self):
        """Connect to email server."""
        try:
            if self.use_ssl:
                mail = imaplib.IMAP4_SSL(self.host, self.port, timeout=30)
            else:
                mail = imaplib.IMAP4(self.host, self.port, timeout=30)
                try:
                    mail.starttls()
                except:
                    pass
            
            mail.login(self.user, self.password)
            return mail
        except imaplib.IMAP4.error as e:
            raise Exception(f"IMAP login failed: {str(e)}. Check your EMAIL_USER and EMAIL_PASSWORD.")
        except Exception as e:
            error_msg = str(e)
            if "WRONG_VERSION_NUMBER" in error_msg or "SSL" in error_msg:
                raise Exception(
                    f"SSL connection error: {error_msg}\n"
                    f"Troubleshooting:\n"
                    f"1. For Gmail: EMAIL_HOST=imap.gmail.com, EMAIL_PORT=993, EMAIL_USE_SSL=True\n"
                    f"2. For Outlook: EMAIL_HOST=outlook.office365.com, EMAIL_PORT=993, EMAIL_USE_SSL=True\n"
                    f"3. Check your .env file settings\n"
                    f"4. Verify you're using an App Password (not regular password) for Gmail"
                )
            raise Exception(f"Email connection failed: {error_msg}. Check your EMAIL_HOST, EMAIL_PORT, and EMAIL_USE_SSL settings.")
    
    def is_relevant_email(self, email_message) -> bool:
        """
        Check if email is relevant (immigration request).
        Only processes emails that contain immigration-related keywords.
        
        Args:
            email_message: Email message object
            
        Returns:
            True if email should be processed, False otherwise
        """
        subject = email_message.get("Subject", "").lower()
        body_text = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" or content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_text += payload.decode('utf-8', errors='ignore').lower()
                    except:
                        pass
        else:
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    body_text = payload.decode('utf-8', errors='ignore').lower()
            except:
                pass
        
        combined_text = subject + " " + body_text
        
        immigration_keywords = [
            "residence permit",
            "residence permit extension",
            "visa extension",
            "immigration visa",
            "immigration visa extension",
            "permit extension",
            "extend residence",
            "extend visa",
            "immigration office",
            "immigration application",
            "residence card",
            "residence permit renewal"
        ]
        
        return any(keyword in combined_text for keyword in immigration_keywords)
    
    def fetch_emails(self, limit: int = 10) -> List[Dict]:
        """
        Fetch emails from inbox.
        Only fetches emails that appear to be student immigration requests.
        ONLY processes emails received TODAY (not old unread emails).
        
        Args:
            limit: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries with subject, body, sender, attachments
        """
        mail = self.connect()
        mail.select("INBOX")
        
        # Only get emails from today - no fallback to old emails
        from datetime import datetime, timezone
        
        today = datetime.now()
        date_str = today.strftime("%d-%b-%Y")
        
        # Search for unread emails received today only
        # This ensures we only process NEW emails from today, not old unread ones
        search_criteria = f'(UNSEEN SINCE {date_str})'
        status, messages = mail.search(None, search_criteria)
        
        # No fallback - only process emails from today
        email_ids = messages[0].split() if messages[0] else []
        
        emails = []
        
        # Process emails and filter for relevant ones
        processed_count = 0
        for email_id in email_ids:
            if processed_count >= limit:
                break
                
            try:
                # Fetch email
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                
                if status != "OK":
                    continue
                
                # Parse email
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Additional date validation: Ensure email is actually from today
                email_date_str = email_message.get("Date")
                if email_date_str:
                    try:
                        email_date = parsedate_to_datetime(email_date_str)
                        # Convert to local timezone if needed
                        if email_date.tzinfo is None:
                            # Assume UTC if no timezone info
                            email_date = email_date.replace(tzinfo=timezone.utc)
                        
                        # Check if email is from today
                        if email_date.date() < today.date():
                            subject_preview = email_message.get('Subject', 'No Subject')[:50]
                            print(f"✗ Skipping old email (not from today):")
                            print(f"  Subject: {subject_preview}")
                            print(f"  Date: {email_date.date()}")
                            # Mark as read so we don't check it again
                            mail.store(email_id, "+FLAGS", "\\Seen")
                            continue
                    except Exception as date_error:
                        # If date parsing fails, skip this email to be safe
                        print(f"✗ Skipping email with unparseable date: {str(date_error)}")
                        mail.store(email_id, "+FLAGS", "\\Seen")
                        continue
                
                # Filter: Skip notification/automated emails
                if not self.is_relevant_email(email_message):
                    subject_preview = email_message.get('Subject', 'No Subject')[:50]
                    sender_preview = email_message.get('From', 'Unknown')[:50]
                    print(f"✗ Skipping notification email:")
                    print(f"  Subject: {subject_preview}")
                    print(f"  Sender: {sender_preview}")
                    # Mark as read anyway so we don't process it again
                    mail.store(email_id, "+FLAGS", "\\Seen")
                    continue
                
                # Log emails that pass the filter
                subject_preview = email_message.get('Subject', 'No Subject')[:50]
                sender_preview = email_message.get('From', 'Unknown')[:50]
                print(f"✓ Processing relevant email:")
                print(f"  Subject: {subject_preview}")
                print(f"  Sender: {sender_preview}")
                
                # Decode subject
                subject, encoding = decode_header(email_message["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                
                # Decode sender
                sender, encoding = decode_header(email_message["From"])[0]
                if isinstance(sender, bytes):
                    sender = sender.decode(encoding or "utf-8")
                
                # Get email body
                body = self._get_email_body(email_message)
                
                # Get attachments
                attachments = self._get_attachments(email_message, email_id)
                
                email_data = {
                    "email_id": email_id.decode(),
                    "subject": subject,
                    "sender": sender,
                    "body": body,
                    "attachments": attachments,
                    "date": email_message["Date"]
                    # Note: We don't include raw_email because Message objects are not JSON serializable
                    # All needed data (subject, body, attachments) is already extracted
                }
                
                emails.append(email_data)
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing email {email_id}: {str(e)}")
                continue
        
        mail.close()
        mail.logout()
        
        return emails
    
    def _get_email_body(self, email_message) -> str:
        """Extract email body text."""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Get text content
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                    except:
                        pass
                elif content_type == "text/html":
                    # Prefer plain text, but use HTML if no plain text
                    if not body:
                        try:
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
        else:
            # Simple email
            try:
                body = email_message.get_payload(decode=True).decode()
            except:
                pass
        
        return body
    
    def _get_attachments(self, email_message, email_id) -> List[Dict]:
        """Extract attachments from email."""
        attachments = []
        
        if not email_message.is_multipart():
            return attachments
        
        for part in email_message.walk():
            content_disposition = str(part.get("Content-Disposition"))
            
            # Check if it's an attachment
            if "attachment" in content_disposition:
                filename = part.get_filename()
                
                if filename:
                    # Decode filename
                    filename, encoding = decode_header(filename)[0]
                    if isinstance(filename, bytes):
                        filename = filename.decode(encoding or "utf-8")
                    
                    # Save attachment
                    file_path = os.path.join(
                        self.upload_dir,
                        f"{email_id.decode()}_{filename}"
                    )
                    
                    with open(file_path, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    
                    attachments.append({
                        "filename": filename,
                        "file_path": file_path,
                        "content_type": part.get_content_type()
                    })
        
        return attachments
    
    def mark_as_read(self, email_id: str):
        """Mark email as read."""
        mail = self.connect()
        mail.select("INBOX")
        mail.store(email_id.encode(), "+FLAGS", "\\Seen")
        mail.close()
        mail.logout()

