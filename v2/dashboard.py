#!/usr/bin/env python3
"""
V2 Dashboard Server - Complete with all tracking features
Fixed encoding, comprehensive stats
"""

import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "v2_dashboard.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "v2" / "la_agenda_v2.db"
V1_SENT_LOG = Path(__file__).parent.parent / "data" / "state" / "alerts_sent.json"

class V2DashboardHandler(BaseHTTPRequestHandler):
    """V2 Dashboard API handler."""
    
    def log_message(self, format, *args):
        logger.info(format % args)
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        routes = {
            '/': self._serve_dashboard,
            '/api/stats': self._serve_stats,
            '/api/users': self._serve_users,
            '/api/emails': self._serve_emails,
            '/api/replies': self._serve_replies,
            '/api/leads': self._serve_leads,
            '/api/sources': self._serve_sources,
            '/api/outreach': self._serve_outreach,
            '/api/logs': self._serve_logs,
            '/api/health': self._serve_health,
            '/public/status': self._serve_public_status
        }
        
        handler = routes.get(path, self._send_404)
        handler()
    
    def _get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _serve_dashboard(self):
        """Serve main dashboard HTML."""
        html = self._generate_html()
        self._send_response(200, 'text/html', html.encode('utf-8'))
    
    def _serve_stats(self):
        """Serve comprehensive dashboard statistics."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        # Users by tier
        cursor.execute("SELECT plan, COUNT(*) as count FROM users GROUP BY plan")
        users_by_tier = {row["plan"]: row["count"] for row in cursor.fetchall()}
        
        # Alerts sent (24h / 7d / all time)
        day_ago = (datetime.now() - timedelta(days=1)).isoformat()
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        cursor.execute("SELECT COUNT(*) FROM alerts_sent WHERE sent_at > ?", (day_ago,))
        alerts_24h = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alerts_sent WHERE sent_at > ?", (week_ago,))
        alerts_7d = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alerts_sent")
        alerts_total = cursor.fetchone()[0]
        
        # Failed scrapes
        cursor.execute("SELECT COUNT(*) FROM system_events WHERE event_type = 'error' AND created_at > ?", (week_ago,))
        failed_scrapes = cursor.fetchone()[0]
        
        # Outreach stats
        cursor.execute("SELECT COUNT(*) FROM outreach_log")
        outreach_total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM outreach_log WHERE date(sent_at) = date('now')")
        outreach_today = cursor.fetchone()[0]
        
        # Source health
        cursor.execute("SELECT COUNT(*) FROM source_health WHERE status = 'healthy'")
        sources_healthy = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM source_health")
        sources_total = cursor.fetchone()[0]
        
        conn.close()
        
        # Calculate system health
        if sources_healthy == sources_total and failed_scrapes == 0:
            system_status = "healthy"
        elif sources_healthy >= sources_total * 0.8:
            system_status = "operational"
        else:
            system_status = "degraded"
        
        stats = {
            "users": {
                "total": sum(users_by_tier.values()),
                "by_tier": users_by_tier
            },
            "alerts": {
                "24h": alerts_24h,
                "7d": alerts_7d,
                "total": alerts_total
            },
            "outreach": {
                "total": outreach_total,
                "today": outreach_today
            },
            "sources": {
                "total": sources_total,
                "healthy": sources_healthy
            },
            "failed_scrapes": failed_scrapes,
            "system_status": system_status,
            "updated_at": datetime.now().isoformat()
        }
        
        self._send_response(200, 'application/json', json.dumps(stats).encode())
    
    def _serve_emails(self):
        """Serve sent emails history."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id as email, source_id, title, sent_at, status, retry_count
            FROM alerts_sent
            ORDER BY sent_at DESC
            LIMIT 50
        """)
        
        emails = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        self._send_response(200, 'application/json', json.dumps(emails).encode())
    
    def _serve_replies(self):
        """Serve email replies."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT email, status, sent_at as timestamp
            FROM outreach_log
            WHERE status IN ('replied', 'bounced')
            ORDER BY sent_at DESC
            LIMIT 20
        """)
        
        replies = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        self._send_response(200, 'application/json', json.dumps(replies).encode())
    
    def _serve_leads(self):
        """Serve pending leads."""
        leads_file = Path.home() / "Downloads" / "outreach_leads.txt"
        processed_file = Path.home() / "Downloads" / "outreach_processed.txt"
        
        leads = []
        if leads_file.exists():
            with open(leads_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        leads.append(line)
        
        self._send_response(200, 'application/json', json.dumps(leads).encode())
    
    def _serve_sources(self):
        """Serve source health data."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source_id, name, status, success_rate, 
                   last_check, last_success, failure_count
            FROM source_health
            ORDER BY success_rate DESC
        """)
        
        sources = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        self._send_response(200, 'application/json', json.dumps(sources).encode())
    
    def _serve_outreach(self):
        """Serve outreach activity."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT email, domain, status, sent_at, justification
            FROM outreach_log 
            ORDER BY sent_at DESC 
            LIMIT 50
        """)
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        self._send_response(200, 'application/json', json.dumps(logs).encode())
    
    def _serve_logs(self):
        """Serve recent logs."""
        logs = []
        log_files = ['v2_pipeline.log', 'v2_health.log', 'email.log', 'outreach.log']
        
        for log_file in log_files:
            log_path = LOGS_DIR / log_file
            if log_path.exists():
                try:
                    with open(log_path) as f:
                        lines = f.readlines()
                        for line in lines[-20:]:
                            logs.append({"source": log_file, "line": line.strip()})
                except:
                    pass
        
        self._send_response(200, 'application/json', json.dumps(logs[-50:]).encode())
    
    def _serve_users(self):
        """Serve user list."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, email, plan, status, created_at, last_login
            FROM users
            ORDER BY created_at DESC
        """)
        
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        self._send_response(200, 'application/json', json.dumps(users).encode())
    
    def _serve_health(self):
        """Serve system health."""
        health = {"status": "healthy", "timestamp": datetime.now().isoformat()}
        self._send_response(200, 'application/json', json.dumps(health).encode())
    
    def _serve_public_status(self):
        """Serve public system status."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM source_health WHERE status = 'healthy'")
        healthy = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM source_health")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT source_id, name, status, last_success FROM source_health")
        sources = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        status = "operational" if healthy == total else "degraded" if healthy >= total * 0.7 else "major_outage"
        
        public_status = {
            "status": status,
            "sources_healthy": healthy,
            "sources_total": total,
            "sources": sources,
            "updated_at": datetime.now().isoformat()
        }
        
        self._send_response(200, 'application/json', json.dumps(public_status).encode())
    
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
    
    def _generate_html(self):
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LA Agenda Alerts - V2 Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: #f5f5f5; 
            color: #333;
            line-height: 1.6;
        }
        .header { 
            background: linear-gradient(135deg, #6366f1, #8b5cf6); 
            color: white; 
            padding: 2rem; 
        }
        .header h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .header p { opacity: 0.8; }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 1.5rem; 
            margin-bottom: 2rem; 
        }
        .stat-card { 
            background: white; 
            padding: 1.5rem; 
            border-radius: 12px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .stat-card:hover { transform: translateY(-2px); }
        .stat-card h3 { 
            font-size: 0.75rem; 
            color: #666; 
            text-transform: uppercase; 
            letter-spacing: 0.5px;
        }
        .stat-card .number { 
            font-size: 2.5rem; 
            font-weight: 700; 
            color: #6366f1; 
            margin-top: 0.5rem; 
        }
        .section { 
            background: white; 
            padding: 1.5rem; 
            border-radius: 12px; 
            margin-bottom: 1.5rem; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .section h2 { 
            margin-bottom: 1rem; 
            font-size: 1.25rem; 
            color: #1f2937;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 0.5rem;
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            font-size: 0.875rem; 
        }
        th, td { 
            text-align: left; 
            padding: 0.75rem; 
            border-bottom: 1px solid #e5e7eb; 
        }
        th { 
            font-weight: 600; 
            color: #4b5563; 
            background: #f9fafb; 
        }
        tr:hover { background: #f9fafb; }
        .status-healthy { color: #059669; font-weight: 600; }
        .status-degraded { color: #d97706; font-weight: 600; }
        .status-down { color: #dc2626; font-weight: 600; }
        .status-sent { color: #059669; }
        .status-pending { color: #d97706; }
        .status-failed { color: #dc2626; }
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-free { background: #e5e7eb; color: #374151; }
        .badge-pro { background: #c7d2fe; color: #3730a3; }
        .badge-org { background: #fde68a; color: #92400e; }
        .system-healthy { color: #059669; }
        .system-degraded { color: #d97706; }
        .system-major_outage { color: #dc2626; }
        .log-entry {
            font-family: monospace;
            font-size: 0.8rem;
            padding: 0.5rem;
            border-bottom: 1px solid #f3f4f6;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .log-entry:hover { background: #f9fafb; }
        .refresh-btn {
            float: right;
            background: #6366f1;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
        }
        .refresh-btn:hover { background: #4f46e5; }
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #6b7280;
        }
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: 1fr; }
            table { font-size: 0.75rem; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>LA Agenda Alerts - V2 Dashboard</h1>
        <p>Real-time system monitoring, user analytics, and operational metrics</p>
    </div>
    <div class="container">
        <button class="refresh-btn" onclick="location.reload()">Refresh</button>
        <div style="clear: both; margin-bottom: 1rem;"></div>
        
        <!-- Stats Grid -->
        <div class="stats-grid" id="stats">
            <div class="stat-card">
                <h3>Total Users</h3>
                <div class="number" id="total-users">-</div>
            </div>
            <div class="stat-card">
                <h3>Alerts (24h)</h3>
                <div class="number" id="alerts-24h">-</div>
            </div>
            <div class="stat-card">
                <h3>Alerts (7d)</h3>
                <div class="number" id="alerts-7d">-</div>
            </div>
            <div class="stat-card">
                <h3>System Status</h3>
                <div class="number" id="system-status" style="font-size: 1.5rem;">-</div>
            </div>
            <div class="stat-card">
                <h3>Sources Healthy</h3>
                <div class="number" id="sources-healthy">-</div>
            </div>
            <div class="stat-card">
                <h3>Outreach Today</h3>
                <div class="number" id="outreach-today">-</div>
            </div>
        </div>
        
        <!-- Users by Tier -->
        <div class="section">
            <h2>Users by Tier</h2>
            <div id="tier-chart">
                <div class="empty-state">Loading...</div>
            </div>
        </div>
        
        <!-- Source Health -->
        <div class="section">
            <h2>Source Health & Reliability</h2>
            <table id="sources-table">
                <thead>
                    <tr>
                        <th>Source</th>
                        <th>Status</th>
                        <th>Success Rate</th>
                        <th>Last Check</th>
                        <th>Failures</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <!-- Recent Emails -->
        <div class="section">
            <h2>Recent Alerts Sent</h2>
            <table id="emails-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>To</th>
                        <th>Source</th>
                        <th>Title</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <!-- Outreach Activity -->
        <div class="section">
            <h2>Outreach Activity</h2>
            <table id="outreach-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Email</th>
                        <th>Domain</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <!-- Pending Leads -->
        <div class="section">
            <h2>Pending Leads</h2>
            <div id="leads-container">
                <div class="empty-state">Loading...</div>
            </div>
        </div>
        
        <!-- System Logs -->
        <div class="section">
            <h2>Recent Logs</h2>
            <div id="logs-container">
                <div class="empty-state">Loading...</div>
            </div>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const stats = await fetch('/api/stats').then(r => r.json());
                
                document.getElementById('total-users').textContent = stats.users.total;
                document.getElementById('alerts-24h').textContent = stats.alerts['24h'];
                document.getElementById('alerts-7d').textContent = stats.alerts['7d'];
                document.getElementById('sources-healthy').textContent = stats.sources.healthy + '/' + stats.sources.total;
                document.getElementById('outreach-today').textContent = stats.outreach.today;
                
                const statusEl = document.getElementById('system-status');
                statusEl.textContent = stats.system_status.toUpperCase();
                statusEl.className = 'number system-' + stats.system_status;
                
                // Tier chart
                const tiers = stats.users.by_tier;
                let tierHtml = '<table><thead><tr><th>Tier</th><th>Users</th></tr></thead><tbody>';
                for (const [tier, count] of Object.entries(tiers)) {
                    tierHtml += `<tr><td><span class="badge badge-${tier}">${tier.toUpperCase()}</span></td><td>${count}</td></tr>`;
                }
                tierHtml += '</tbody></table>';
                document.getElementById('tier-chart').innerHTML = tierHtml || '<p>No users yet</p>';
                
            } catch (err) {
                console.error('Error loading stats:', err);
            }
        }
        
        async function loadSources() {
            try {
                const sources = await fetch('/api/sources').then(r => r.json());
                const tbody = document.querySelector('#sources-table tbody');
                tbody.innerHTML = sources.map(s => `
                    <tr>
                        <td>${s.name}</td>
                        <td class="status-${s.status}">${s.status.toUpperCase()}</td>
                        <td>${(s.success_rate * 100).toFixed(1)}%</td>
                        <td>${s.last_check ? new Date(s.last_check).toLocaleString() : 'Never'}</td>
                        <td>${s.failure_count}</td>
                    </tr>
                `).join('');
            } catch (err) {
                console.error('Error loading sources:', err);
            }
        }
        
        async function loadEmails() {
            try {
                const emails = await fetch('/api/emails').then(r => r.json());
                const tbody = document.querySelector('#emails-table tbody');
                tbody.innerHTML = emails.slice(0, 20).map(e => `
                    <tr>
                        <td>${e.sent_at ? new Date(e.sent_at).toLocaleString() : '-'}</td>
                        <td>${e.email}</td>
                        <td>${e.source_id}</td>
                        <td>${e.title ? e.title.substring(0, 50) + '...' : '-'}</td>
                        <td class="status-${e.status}">${e.status}</td>
                    </tr>
                `).join('') || '<tr><td colspan="5" class="empty-state">No alerts sent yet</td></tr>';
            } catch (err) {
                console.error('Error loading emails:', err);
            }
        }
        
        async function loadOutreach() {
            try {
                const logs = await fetch('/api/outreach').then(r => r.json());
                const tbody = document.querySelector('#outreach-table tbody');
                tbody.innerHTML = logs.slice(0, 20).map(l => `
                    <tr>
                        <td>${l.sent_at ? new Date(l.sent_at).toLocaleString() : '-'}</td>
                        <td>${l.email}</td>
                        <td>${l.domain}</td>
                        <td class="status-${l.status}">${l.status}</td>
                    </tr>
                `).join('') || '<tr><td colspan="4" class="empty-state">No outreach activity</td></tr>';
            } catch (err) {
                console.error('Error loading outreach:', err);
            }
        }
        
        async function loadLeads() {
            try {
                const leads = await fetch('/api/leads').then(r => r.json());
                const container = document.getElementById('leads-container');
                if (leads.length === 0) {
                    container.innerHTML = '<div class="empty-state">No pending leads. Add to ~/Downloads/outreach_leads.txt</div>';
                } else {
                    container.innerHTML = '<ul style="list-style: none;">' + leads.slice(0, 10).map(l => `<li style="padding: 0.5rem; border-bottom: 1px solid #e5e7eb;">${l}</li>`).join('') + '</ul>';
                }
            } catch (err) {
                console.error('Error loading leads:', err);
            }
        }
        
        async function loadLogs() {
            try {
                const logs = await fetch('/api/logs').then(r => r.json());
                const container = document.getElementById('logs-container');
                container.innerHTML = logs.slice(-20).map(l => `<div class="log-entry">[${l.source}] ${l.line}</div>`).join('') || '<div class="empty-state">No logs available</div>';
            } catch (err) {
                console.error('Error loading logs:', err);
            }
        }
        
        // Load all data
        loadStats();
        loadSources();
        loadEmails();
        loadOutreach();
        loadLeads();
        loadLogs();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            loadStats();
            loadSources();
            loadEmails();
            loadOutreach();
        }, 30000);
    </script>
</body>
</html>'''

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, V2DashboardHandler)
    logger.info(f"V2 Dashboard running at http://localhost:{port}")
    print(f"\n🚀 V2 Dashboard: http://localhost:{port}")
    print("Press Ctrl+C to stop\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
