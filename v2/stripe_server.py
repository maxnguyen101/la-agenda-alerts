#!/usr/bin/env python3
"""
Stripe Checkout & Webhook Handler for V2
Handles Pro ($9) and Org ($39) subscriptions
"""

import hashlib
import hmac
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Load environment
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Configuration
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_xxx")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_xxx")
STRIPE_PRO_PRICE_ID = os.environ.get("STRIPE_PRO_PRICE_ID", "price_xxx")
STRIPE_ORG_PRICE_ID = os.environ.get("STRIPE_ORG_PRICE_ID", "price_xxx")

DB_PATH = Path(__file__).parent.parent / "data" / "v2" / "la_agenda_v2.db"
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "stripe.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class StripeHandler(BaseHTTPRequestHandler):
    """Handle Stripe webhooks and checkout."""
    
    def log_message(self, format, *args):
        logger.info(format % args)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        if path == '/stripe/checkout':
            self._create_checkout_session(query)
        elif path == '/stripe/success':
            self._handle_success(query)
        elif path == '/stripe/cancel':
            self._handle_cancel(query)
        else:
            self._send_404()
    
    def do_POST(self):
        """Handle POST requests (webhooks)."""
        parsed = urlparse(self.path)
        
        if parsed.path == '/stripe/webhook':
            self._handle_webhook()
        else:
            self._send_404()
    
    def _get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_checkout_session(self, query):
        """Create Stripe Checkout session."""
        email = query.get('email', [''])[0]
        plan = query.get('plan', ['pro'])[0]
        
        if not email:
            self._send_response(400, 'text/plain', b'Email required')
            return
        
        # Store pending checkout in database
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO billing_events (user_id, event_type, details, created_at)
            VALUES ((SELECT id FROM users WHERE email = ?), 'checkout_started', ?, ?)
        """, (email, json.dumps({"plan": plan}), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # In production, this would create actual Stripe session
        # For now, return manual payment link
        checkout_url = f"https://buy.stripe.com/test_xxxx?prefilled_email={email}"
        
        response = {
            "checkout_url": checkout_url,
            "email": email,
            "plan": plan
        }
        
        self._send_response(200, 'application/json', json.dumps(response).encode())
    
    def _handle_webhook(self):
        """Handle Stripe webhook events."""
        content_length = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(content_length)
        
        sig_header = self.headers.get('Stripe-Signature')
        
        try:
            # In production, verify signature with STRIPE_WEBHOOK_SECRET
            event = json.loads(payload)
            event_type = event.get('type')
            
            logger.info(f"Stripe webhook received: {event_type}")
            
            if event_type == 'checkout.session.completed':
                self._handle_payment_success(event['data']['object'])
            elif event_type == 'invoice.payment_failed':
                self._handle_payment_failure(event['data']['object'])
            elif event_type == 'customer.subscription.deleted':
                self._handle_subscription_cancelled(event['data']['object'])
            
            self._send_response(200, 'application/json', json.dumps({"status": "ok"}).encode())
            
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            self._send_response(400, 'application/json', json.dumps({"error": str(e)}).encode())
    
    def _handle_payment_success(self, session):
        """Process successful payment."""
        email = session.get('customer_email')
        plan = self._get_plan_from_session(session)
        
        conn = self._get_db()
        cursor = conn.cursor()
        
        # Update user plan
        cursor.execute("""
            UPDATE users 
            SET plan = ?, billing_status = 'active'
            WHERE email = ?
        """, (plan, email))
        
        # Log billing event
        cursor.execute("""
            INSERT INTO billing_events (user_id, event_type, amount_cents, details, created_at)
            VALUES ((SELECT id FROM users WHERE email = ?), 'payment_success', ?, ?, ?)
        """, (email, session.get('amount_total', 0), json.dumps(session), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Send welcome email
        self._send_upgrade_email(email, plan)
        
        logger.info(f"✅ User upgraded: {email} to {plan}")
    
    def _handle_payment_failure(self, invoice):
        """Handle failed payment."""
        email = invoice.get('customer_email')
        
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET billing_status = 'payment_failed' WHERE email = ?
        """, (email,))
        
        cursor.execute("""
            INSERT INTO billing_events (user_id, event_type, details, created_at)
            VALUES ((SELECT id FROM users WHERE email = ?), 'payment_failed', ?, ?)
        """, (email, json.dumps(invoice), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"⚠️ Payment failed: {email}")
    
    def _handle_subscription_cancelled(self, subscription):
        """Handle cancelled subscription."""
        email = subscription.get('customer_email')
        
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET plan = 'free', billing_status = 'cancelled' WHERE email = ?
        """, (email,))
        
        cursor.execute("""
            INSERT INTO billing_events (user_id, event_type, details, created_at)
            VALUES ((SELECT id FROM users WHERE email = ?), 'cancelled', ?, ?)
        """, (email, json.dumps(subscription), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📤 Subscription cancelled: {email}")
    
    def _get_plan_from_session(self, session):
        """Determine plan from Stripe session."""
        # In production, check line items
        # For now, check metadata or default to pro
        return session.get('metadata', {}).get('plan', 'pro')
    
    def _send_upgrade_email(self, email, plan):
        """Send welcome email after upgrade."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            gmail_user = os.environ.get("GMAIL_USER")
            gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
            
            if not gmail_user or not gmail_pass:
                return
            
            subject = f"Welcome to LA Agenda Alerts {plan.title()}!"
            body = f"""Thank you for upgrading to {plan.title()}!

Your account has been activated with these features:
"""
            if plan == "pro":
                body += """
✓ Email + SMS alerts
✓ Advanced keyword filtering
✓ Calendar integration
✓ 3 retry attempts for reliability
"""
            elif plan == "org":
                body += """
✓ Everything in Pro
✓ Up to 5 recipients
✓ Team dashboard
✓ Priority support
✓ 5 retry attempts
"""
            
            body += """
Manage your account: https://maxnguyen.github.io/la-agenda-alerts/dashboard

Questions? Reply to this email.

Best,
LA Agenda Alerts Team
"""
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = gmail_user
            msg['To'] = email
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Upgrade email sent to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send upgrade email: {e}")
    
    def _handle_success(self, query):
        """Handle successful checkout redirect."""
        html = """<!DOCTYPE html>
<html>
<head><title>Payment Successful</title></head>
<body style="text-align: center; padding: 50px; font-family: sans-serif;">
    <h1>🎉 Payment Successful!</h1>
    <p>Your account has been upgraded. Check your email for details.</p>
    <a href="/">Return to Dashboard</a>
</body>
</html>"""
        self._send_response(200, 'text/html', html.encode())
    
    def _handle_cancel(self, query):
        """Handle cancelled checkout."""
        html = """<!DOCTYPE html>
<html>
<head><title>Checkout Cancelled</title></head>
<body style="text-align: center; padding: 50px; font-family: sans-serif;">
    <h1>Checkout Cancelled</h1>
    <p>No worries! You can upgrade anytime.</p>
    <a href="/">Return to Pricing</a>
</body>
</html>"""
        self._send_response(200, 'text/html', html.encode())
    
    def _send_response(self, code, content_type, data):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)
    
    def _send_404(self):
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Not Found')


def run_server(port=8081):
    """Run Stripe webhook server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, StripeHandler)
    logger.info(f"Stripe server running at http://localhost:{port}")
    print(f"\n💳 Stripe Webhook: http://localhost:{port}/stripe/webhook")
    print("Press Ctrl+C to stop\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stripe server stopped")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    run_server(port)
