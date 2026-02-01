#!/usr/bin/env python3
"""
Gmail Integration for LA Agenda Alerts
Handles OAuth, reading emails, and sending alerts
"""

import base64
import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logging.warning("Google API libraries not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

class GmailIntegration:
    """Gmail API integration for LA Agenda Alerts."""
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pickle'):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.service = None
        self.email_address = 'laagendaalerts@gmail.com'
        
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google API libraries required. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API.
        
        Returns True if authenticated successfully.
        """
        creds = None
        
        # Load existing token
        if self.token_path.exists():
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Gmail token...")
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    logger.error(f"Credentials file not found: {self.credentials_path}")
                    return False
                
                logger.info("Starting Gmail OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save token for future runs
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
            logger.info("Gmail token saved")
        
        # Build service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("✅ Gmail API authenticated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            return False
    
    def check_new_signups(self, since_hours: int = 1) -> List[Dict]:
        """
        Check inbox for new signup emails.
        
        Returns list of signup requests.
        """
        if not self.service:
            logger.error("Gmail service not authenticated")
            return []
        
        signups = []
        
        try:
            # Search for emails in last N hours
            since_time = datetime.now() - timedelta(hours=since_hours)
            since_str = since_time.strftime('%Y/%m/%d')
            
            # Search query: unread emails with signup keywords
            query = f'after:{since_str} (signup OR subscribe OR "sign up" OR "LA Agenda")'
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            
            for msg in messages:
                # Get full message details
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                # Extract email info
                signup_info = self._parse_signup_email(message)
                if signup_info:
                    signups.append(signup_info)
                    
                    # Mark as processed (archive + mark read)
                    self._mark_processed(msg['id'])
            
            logger.info(f"Found {len(signups)} new signup requests")
            return signups
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error checking signups: {e}")
            return []
    
    def _parse_signup_email(self, message: Dict) -> Optional[Dict]:
        """Parse an email to extract signup information."""
        try:
            headers = message['payload']['headers']
            
            # Get sender and subject
            from_email = None
            subject = None
            
            for header in headers:
                if header['name'] == 'From':
                    from_email = self._extract_email(header['value'])
                elif header['name'] == 'Subject':
                    subject = header['value']
            
            if not from_email:
                return None
            
            # Get email body
            body = self._get_email_body(message)
            
            return {
                'id': message['id'],
                'from': from_email,
                'subject': subject or '',
                'body': body or '',
                'date': message.get('internalDate'),
                'thread_id': message.get('threadId')
            }
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    def _extract_email(self, from_header: str) -> str:
        """Extract email address from 'From' header."""
        import re
        match = re.search(r'<(.+?)>', from_header)
        if match:
            return match.group(1)
        # Try simple email pattern
        match = re.search(r'[\w\.-]+@[\w\.-]+', from_header)
        if match:
            return match.group(0)
        return from_header
    
    def _get_email_body(self, message: Dict) -> str:
        """Extract text body from email message."""
        try:
            parts = message['payload'].get('parts', [])
            
            # Try to find text/plain part
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Fallback to snippet
            return message.get('snippet', '')
            
        except Exception as e:
            logger.error(f"Error extracting body: {e}")
            return ''
    
    def _mark_processed(self, message_id: str):
        """Mark email as read and archive it."""
        try:
            # Remove UNREAD label
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD', 'INBOX']}
            ).execute()
        except Exception as e:
            logger.warning(f"Could not mark email as processed: {e}")
    
    def send_welcome_email(self, to_email: str, name: str = None) -> bool:
        """Send welcome email to new subscriber."""
        if not self.service:
            logger.error("Gmail service not authenticated")
            return False
        
        try:
            greeting = f"Hi {name}," if name else "Hi there,"
            
            subject = "Welcome to LA Agenda Alerts!"
            body = f"""{greeting}

Welcome to LA Agenda Alerts! You're now subscribed to receive instant notifications when LA government agendas change.

WHAT YOU'LL GET:
• Email alerts when City Council, County Board, and 11+ agencies update agendas
• Keyword-based filtering (we match based on your interests)
• Checks 3× daily at 8am, 1pm, and 6pm PT
• Links directly to agenda PDFs and meeting info

HOW IT WORKS:
Our system monitors 13 LA government sources and automatically compares them to previous versions. When something changes that matches your keywords, you get an alert within minutes.

YOUR SUBSCRIPTION:
• Plan: Free
• Alerts: Email only
• Sources: All 13 monitored
• Keywords: Default set (can be customized)

To upgrade to Pro ($5/month) with SMS alerts and calendar integration, reply to this email or visit our website.

Questions? Just reply to this email.

Best,
LA Agenda Alerts Team
https://maxnguyen101.github.io/la-agenda-alerts

---
To unsubscribe, reply with "UNSUBSCRIBE"
"""
            
            return self.send_email(to_email, subject, body)
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email via Gmail API."""
        if not self.service:
            logger.error("Gmail service not authenticated")
            return False
        
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to_email
            message['from'] = self.email_address
            message['subject'] = subject
            
            # Encode for API
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"✅ Email sent to {to_email}: {subject}")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def send_alert_email(self, to_email: str, source: str, title: str, 
                         details: str, url: str, keywords_matched: List[str]) -> bool:
        """Send an agenda alert email."""
        subject = f"[LA Agenda Alert] {source}: {title[:50]}..."
        
        keywords_str = ', '.join(keywords_matched) if keywords_matched else 'N/A'
        
        body = f"""LA Agenda Alert
{'='*50}

SOURCE: {source}
TITLE: {title}

DETAILS:
{details}

VIEW AGENDA:
{url}

MATCHED KEYWORDS: {keywords_str}

---
You're receiving this because you subscribed to LA Agenda Alerts.
To change your keywords or unsubscribe, reply to this email.

LA Agenda Alerts
https://maxnguyen101.github.io/la-agenda-alerts
"""
        
        return self.send_email(to_email, subject, body)


def create_credentials_file(client_id: str, client_secret: str, output_path: str = 'credentials.json'):
    """
    Create credentials.json file from client_id and client_secret.
    
    This is used when you have the credentials but not the JSON file.
    """
    credentials = {
        "installed": {
            "client_id": client_id,
            "project_id": "la-agenda-alerts",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"]
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(credentials, f, indent=2)
    
    logger.info(f"✅ Credentials file created: {output_path}")


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Load credentials from environment
    import os
    CLIENT_ID = os.environ.get('GMAIL_CLIENT_ID')
    CLIENT_SECRET = os.environ.get('GMAIL_CLIENT_SECRET')
    
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables")
        print("Example:")
        print("  export GMAIL_CLIENT_ID='your-client-id'")
        print("  export GMAIL_CLIENT_SECRET='your-client-secret'")
        exit(1)
    
    create_credentials_file(CLIENT_ID, CLIENT_SECRET)
    
    # Test authentication
    print("\n" + "="*60)
    print("GMAIL INTEGRATION SETUP")
    print("="*60)
    print("\n1. Credentials file created: credentials.json")
    print("\n2. Starting authentication...")
    print("   A browser window will open.")
    print("   Sign in with: laagendaalerts@gmail.com")
    print("   Grant all requested permissions.")
    print("\n" + "="*60 + "\n")
    
    gmail = GmailIntegration()
    if gmail.authenticate():
        print("\n✅ Authentication successful!")
        print("\n3. Testing email send...")
        
        # Send test email to yourself
        test_sent = gmail.send_email(
            'laagendaalerts@gmail.com',
            'LA Agenda Alerts - Test Email',
            'This is a test email from LA Agenda Alerts.\n\nIf you received this, the Gmail integration is working!'
        )
        
        if test_sent:
            print("✅ Test email sent successfully!")
            print("\n4. Checking for new signups...")
            signups = gmail.check_new_signups(since_hours=24)
            print(f"   Found {len(signups)} signup requests")
        else:
            print("❌ Failed to send test email")
    else:
        print("\n❌ Authentication failed")
