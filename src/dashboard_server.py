#!/usr/bin/env python3
"""
Dashboard Server - Local web interface for monitoring the system
Runs on http://localhost:8080
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
LOGS_DIR = Path(__file__).parent.parent / "logs"
STATE_DIR = DATA_DIR / "state"
PROJECT_DIR = Path(__file__).parent.parent

LOGS_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "dashboard.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for dashboard."""
    
    def log_message(self, format, *args):
        logger.info(format % args)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/':
            self._serve_dashboard()
        elif path == '/api/stats':
            self._serve_stats()
        elif path == '/api/emails':
            self._serve_emails()
        elif path == '/api/replies':
            self._serve_replies()
        elif path == '/api/logs':
            self._serve_logs()
        elif path == '/api/leads':
            self._serve_leads()
        else:
            self._send_404()
    
    def _serve_dashboard(self):
        """Serve the main dashboard HTML."""
        html = self._generate_html()
        self._send_response(200, 'text/html', html.encode())
    
    def _serve_stats(self):
        """Serve JSON stats."""
        stats = self._get_stats()
        self._send_response(200, 'application/json', json.dumps(stats).encode())
    
    def _serve_emails(self):
        """Serve sent emails."""
        emails = self._get_sent_emails()
        self._send_response(200, 'application/json', json.dumps(emails).encode())
    
    def _serve_replies(self):
        """Serve email replies."""
        replies = self._get_replies()
        self._send_response(200, 'application/json', json.dumps(replies).encode())
    
    def _serve_logs(self):
        """Serve recent logs."""
        logs = self._get_recent_logs()
        self._send_response(200, 'application/json', json.dumps(logs).encode())
    
    def _serve_leads(self):
        """Serve pending leads."""
        leads = self._get_pending_leads()
        self._send_response(200, 'application/json', json.dumps(leads).encode())
    
    def _send_response(self, code, content_type, data):
        """Send HTTP response."""
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)
    
    def _send_404(self):
        """Send 404 response."""
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Not Found')
    
    def _get_stats(self):
        """Get system statistics."""
        # Count sent emails
        sent_count = 0
        sent_path = STATE_DIR / "outreach_sent.json"
        if sent_path.exists():
            with open(sent_path) as f:
                sent_count = len(json.load(f))
        
        # Count replies
        reply_count = 0
        replies_path = STATE_DIR / "email_replies.json"
        if replies_path.exists():
            with open(replies_path) as f:
                reply_count = len(json.load(f))
        
        # Count pending leads
        pending_count = 0
        leads_file = Path.home() / "Downloads" / "outreach_leads.txt"
        if leads_file.exists():
            with open(leads_file) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        pending_count += 1
        
        # Check cron status (last run)
        last_run = None
        run_log = LOGS_DIR / "run.log"
        if run_log.exists():
            try:
                with open(run_log) as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if 'Starting run' in line:
                            last_run = line.split(']')[0].strip('[')
                            break
            except:
                pass
        
        return {
            "emails_sent": sent_count,
            "replies_received": reply_count,
            "pending_leads": pending_count,
            "last_system_run": last_run,
            "status": "healthy" if last_run and datetime.now() - datetime.fromisoformat(last_run.replace(' ', 'T')) < timedelta(hours=6) else "check needed"
        }
    
    def _get_sent_emails(self):
        """Get list of sent emails."""
        sent_path = STATE_DIR / "outreach_sent.json"
        if sent_path.exists():
            with open(sent_path) as f:
                return json.load(f)
        return []
    
    def _get_replies(self):
        """Get email replies."""
        replies_path = STATE_DIR / "email_replies.json"
        if replies_path.exists():
            with open(replies_path) as f:
                return json.load(f)
        return []
    
    def _get_recent_logs(self, lines=50):
        """Get recent log entries."""
        logs = []
        
        # Check multiple log files
        for log_file in ['outreach.log', 'replies.log', 'run.log']:
            log_path = LOGS_DIR / log_file
            if log_path.exists():
                try:
                    with open(log_path) as f:
                        file_lines = f.readlines()
                        for line in file_lines[-20:]:  # Last 20 from each
                            logs.append({"source": log_file, "line": line.strip()})
                except:
                    pass
        
        # Sort by timestamp if possible and return last 50
        return logs[-lines:]
    
    def _get_pending_leads(self):
        """Get pending leads."""
        leads = []
        leads_file = Path.home() / "Downloads" / "outreach_leads.txt"
        processed_file = Path.home() / "Downloads" / "outreach_processed.txt"
        
        processed = set()
        if processed_file.exists():
            with open(processed_file) as f:
                for line in f:
                    if '|' in line:
                        processed.add(line.split('|')[1].strip())
        
        if leads_file.exists():
            with open(leads_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '|' in line:
                            email = line.split('-')[0].strip()
                            if email not in processed:
                                leads.append(line)
                        else:
                            leads.append(line)
        
        return leads
    
    def _generate_html(self):
        """Generate dashboard HTML."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LA Agenda Alerts - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        header h1 { font-size: 2em; margin-bottom: 10px; }
        header p { opacity: 0.9; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .stat-card .number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        .section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .section h2 {
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        th {
            font-weight: 600;
            color: #666;
            background: #f8f9fa;
        }
        tr:hover { background: #f8f9fa; }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .badge-sent { background: #d4edda; color: #155724; }
        .badge-pending { background: #fff3cd; color: #856404; }
        .badge-reply { background: #cce5ff; color: #004085; }
        .badge-unsub { background: #f8d7da; color: #721c24; }
        .status-healthy { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-error { color: #dc3545; }
        .log-entry {
            font-family: monospace;
            font-size: 0.85em;
            padding: 8px;
            border-bottom: 1px solid #f0f0f0;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .log-entry:hover { background: #f8f9fa; }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            float: right;
        }
        .refresh-btn:hover { background: #5568d3; }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: 1fr; }
            table { font-size: 0.8em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 LA Agenda Alerts Dashboard</h1>
            <p>Monitor your outreach, track replies, and manage leads</p>
        </header>
        
        <div class="info-box">
            <strong>📋 Quick Actions:</strong> Add new leads to <code>~/Downloads/outreach_leads.txt</code>. 
            The system checks at 9am, 12pm, and 3pm daily. <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        </div>
        
        <div class="stats-grid" id="stats">
            <div class="stat-card">
                <h3>📧 Emails Sent</h3>
                <div class="number" id="stat-sent">-</div>
            </div>
            <div class="stat-card">
                <h3>💬 Replies</h3>
                <div class="number" id="stat-replies">-</div>
            </div>
            <div class="stat-card">
                <h3>⏳ Pending Leads</h3>
                <div class="number" id="stat-pending">-</div>
            </div>
            <div class="stat-card">
                <h3>🤖 System Status</h3>
                <div class="number" id="stat-status" style="font-size: 1.5em;">-</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📨 Recent Emails Sent</h2>
            <div id="emails-container">
                <div class="empty-state">Loading...</div>
            </div>
        </div>
        
        <div class="section">
            <h2>💬 Email Replies</h2>
            <div id="replies-container">
                <div class="empty-state">Loading...</div>
            </div>
        </div>
        
        <div class="section">
            <h2>⏳ Pending Leads</h2>
            <div id="leads-container">
                <div class="empty-state">Loading...</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 Recent Logs</h2>
            <div id="logs-container">
                <div class="empty-state">Loading...</div>
            </div>
        </div>
    </div>
    
    <script>
        // Load all data
        async function loadData() {
            try {
                // Load stats
                const stats = await fetch('/api/stats').then(r => r.json());
                document.getElementById('stat-sent').textContent = stats.emails_sent;
                document.getElementById('stat-replies').textContent = stats.replies_received;
                document.getElementById('stat-pending').textContent = stats.pending_leads;
                const statusEl = document.getElementById('stat-status');
                statusEl.textContent = stats.status === 'healthy' ? '✅ Healthy' : '⚠️ Check Needed';
                statusEl.className = 'number ' + (stats.status === 'healthy' ? 'status-healthy' : 'status-warning');
                
                // Load emails
                const emails = await fetch('/api/emails').then(r => r.json());
                renderEmails(emails);
                
                // Load replies
                const replies = await fetch('/api/replies').then(r => r.json());
                renderReplies(replies);
                
                // Load leads
                const leads = await fetch('/api/leads').then(r => r.json());
                renderLeads(leads);
                
                // Load logs
                const logs = await fetch('/api/logs').then(r => r.json());
                renderLogs(logs);
                
            } catch (err) {
                console.error('Error loading data:', err);
            }
        }
        
        function renderEmails(emails) {
            const container = document.getElementById('emails-container');
            if (!emails || emails.length === 0) {
                container.innerHTML = '<div class="empty-state">No emails sent yet</div>';
                return;
            }
            
            let html = '<table><thead><tr><th>Date</th><th>To</th><th>Name</th><th>Subject</th><th>Status</th></tr></thead><tbody>';
            emails.slice().reverse().slice(0, 10).forEach(email => {
                html += `<tr>
                    <td>${email.timestamp || '-'}</td>
                    <td>${email.email}</td>
                    <td>${email.name}</td>
                    <td>${email.subject}</td>
                    <td><span class="badge badge-sent">${email.status}</span></td>
                </tr>`;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
        
        function renderReplies(replies) {
            const container = document.getElementById('replies-container');
            if (!replies || replies.length === 0) {
                container.innerHTML = '<div class="empty-state">No replies yet</div>';
                return;
            }
            
            let html = '<table><thead><tr><th>Date</th><th>From</th><th>Subject</th><th>Status</th></tr></thead><tbody>';
            replies.slice().reverse().slice(0, 10).forEach(reply => {
                const badgeClass = reply.status === 'unsubscribed' ? 'badge-unsub' : 
                                  reply.status === 'interested' ? 'badge-reply' : 'badge-pending';
                html += `<tr>
                    <td>${reply.timestamp || '-'}</td>
                    <td>${reply.from}</td>
                    <td>${reply.subject}</td>
                    <td><span class="badge ${badgeClass}">${reply.status}</span></td>
                </tr>`;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
        
        function renderLeads(leads) {
            const container = document.getElementById('leads-container');
            if (!leads || leads.length === 0) {
                container.innerHTML = '<div class="empty-state">No pending leads - add some to ~/Downloads/outreach_leads.txt</div>';
                return;
            }
            
            let html = '<table><thead><tr><th>#</th><th>Lead Info</th></tr></thead><tbody>';
            leads.slice(0, 10).forEach((lead, i) => {
                html += `<tr>
                    <td>${i + 1}</td>
                    <td>${lead}</td>
                </tr>`;
            });
            if (leads.length > 10) {
                html += `<tr><td colspan="2" style="text-align:center;color:#666;">...and ${leads.length - 10} more</td></tr>`;
            }
            html += '</tbody></table>';
            container.innerHTML = html;
        }
        
        function renderLogs(logs) {
            const container = document.getElementById('logs-container');
            if (!logs || logs.length === 0) {
                container.innerHTML = '<div class="empty-state">No logs available</div>';
                return;
            }
            
            let html = '';
            logs.slice().reverse().forEach(log => {
                html += `<div class="log-entry">[${log.source}] ${log.line}</div>`;
            });
            container.innerHTML = html;
        }
        
        // Load on page load
        loadData();
        
        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>'''


def run_server(port=8080):
    """Run the dashboard server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, DashboardHandler)
    logger.info(f"Dashboard server running at http://localhost:{port}")
    print(f"\n🚀 Dashboard running at: http://localhost:{port}")
    print("Press Ctrl+C to stop\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        print("\n✅ Server stopped")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
