#!/usr/bin/env python3
"""
Test email notification system
Usage: python3 scripts/test_email.py
"""

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

AGENT_MAIL_API_KEY = os.environ.get("AGENT_MAIL_API_KEY")
OPERATOR_EMAIL = os.environ.get("OPERATOR_EMAIL")

if not AGENT_MAIL_API_KEY:
    print("❌ AGENT_MAIL_API_KEY not set!")
    sys.exit(1)

if not OPERATOR_EMAIL:
    print("❌ OPERATOR_EMAIL not set!")
    sys.exit(1)

print(f"✓ API Key loaded: {AGENT_MAIL_API_KEY[:30]}...")
print(f"✓ Sending test email to: {OPERATOR_EMAIL}")

subject = "[LA Agenda Alerts] Test Email - System Working!"
body = f"""This is a test email from LA Agenda Alerts.

System Status: ✅ Operational
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

If you're receiving this, the email notification system is working correctly!

Your system is monitoring:
- LA City Council agendas
- PLUM Committee agendas  
- LA County Board of Supervisors agendas
- LA City Planning Commission
- LA Metro Board
- LA Housing Department
- Rent Stabilization Board

Next steps:
1. The system checks for updates 3x daily (8am, 1pm, 6pm)
2. You'll receive instant alerts when agendas change
3. Dashboard available at: http://localhost:8080

Questions? Just reply to this email.

Best,
LA Agenda Alerts Bot
"""

payload = {
    "to": OPERATOR_EMAIL,
    "subject": subject,
    "body": body,
    "from": "alerts@laagendaalerts.com"
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AGENT_MAIL_API_KEY}"
}

try:
    req = urllib.request.Request(
        "https://api.agentmail.ai/v1/send",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode())
        print(f"\n✅ Test email sent successfully!")
        print(f"   Message ID: {result.get('message_id', 'N/A')}")
        print(f"   Check your inbox at: {OPERATOR_EMAIL}")
        
except Exception as e:
    print(f"\n❌ Failed to send test email: {e}")
    sys.exit(1)
