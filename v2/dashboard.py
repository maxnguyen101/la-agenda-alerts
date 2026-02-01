#!/usr/bin/env python3
"""
V2 Dashboard Server - Enhanced with stats and reliability metrics
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
            '/api/alerts': self._serve_alerts,
            '/api/sources': self._serve_sources,
            '/api/outreach': self._serve_outreach,
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
        self._send_response(200, 'text/html', html.encode())
    
    def _serve_stats(self):
        """Serve dashboard statistics."""
        conn = self._get_db()
        cursor = conn.cursor()
        
        # Users by tier
        cursor.execute("SELECT plan, COUNT(*) as count FROM users GROUP BY plan")
        users_by_tier = {row["plan"]: row["count"] for row in cursor.fetchall()}
        
        # Alerts sent (24h / 7d)
        day_ago = (datetime.now() - timedelta(days=1)).isoformat()
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        cursor.execute("SELECT COUNT(*) FROM alerts_sent WHERE sent_at > ?", (day_ago,))
        alerts_24h = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alerts_sent WHERE sent_at > ?", (week_ago,))
        alerts_7d = cursor.fetchone()[0]
        
        # Failed scrapes
        cursor.execute("SELECT COUNT(*) FROM system_events WHERE event_type = 'error' AND created_at > ?", (week_ago,))
        failed_scrapes = cursor.fetchone()[0]
        
        conn.close()
        
        stats = {
            "users": {
                "total": sum(users_by_tier.values()),
                "by_tier": users_by_tier
            },
            "alerts": {
                "24h": alerts_24h,
                "7d": alerts_7d
            },
            "failed_scrapes": failed_scrapes,
            "updated_at": datetime.now().isoformat()
        }
        
        self._send_response(200, 'application/json', json.dumps(stats).encode())
    
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
            SELECT email, domain, status, sent_at 
            FROM outreach_log 
            ORDER BY sent_at DESC 
            LIMIT 50
        """)
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        self._send_response(200, 'application/json', json.dumps(logs).encode())
    
    def _serve_public_status(self):
        """Serve public system status page data."""
        from v2.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        status = monitor.get_system_status()
        
        self._send_response(200, 'application/json', json.dumps(status).encode())
    
    def _serve_users(self):
        self._send_response(200, 'application/json', json.dumps({}).encode())
    
    def _serve_alerts(self):
        self._send_response(200, 'application/json', json.dumps({}).encode())
    
    def _serve_health(self):
        self._send_response(200, 'application/json', json.dumps({"status": "healthy"}).encode())
    
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
<html>
<head>
    <title>LA Agenda Alerts - V2 Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 2rem; }
        .header h1 { font-size: 2rem; }
        .header p { opacity: 0.8; margin-top: 0.5rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .stat-card h3 { font-size: 0.875rem; color: #666; text-transform: uppercase; }
        .stat-card .number { font-size: 2.5rem; font-weight: 700; color: #6366f1; margin-top: 0.5rem; }
        .section { background: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .section h2 { margin-bottom: 1rem; font-size: 1.25rem; }
        table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
        th, td { text-align: left; padding: 0.75rem; border-bottom: 1px solid #eee; }
        th { font-weight: 600; color: #666; background: #f8f9fa; }
        .status-healthy { color: #10b981; }
        .status-degraded { color: #f59e0b; }
        .status-down { color: #ef4444; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏛️ LA Agenda Alerts - V2 Dashboard</h1>
        <p>Real-time system monitoring and analytics</p>
    </div>
    <div class="container">
        <div class="stats-grid" id="stats">
            <div class="stat-card"><h3>Total Users</h3><div class="number" id="total-users">-</div></div>
            <div class="stat-card"><h3>Alerts (24h)</h3><div class="number" id="alerts-24h">-</div></div>
            <div class="stat-card"><h3>Alerts (7d)</h3><div class="number" id="alerts-7d">-</div></div>
            <div class="stat-card"><h3>Failed Scrapes</h3><div class="number" id="failed-scrapes">-</div></div>
        </div>
        <div class="section">
            <h2>📊 Users by Tier</h2>
            <div id="tier-chart">Loading...</div>
        </div>
        <div class="section">
            <h2>🔌 Source Health</h2>
            <table id="sources-table">
                <thead><tr><th>Source</th><th>Status</th><th>Success Rate</th><th>Last Check</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>
    </div>
    <script>
        async function loadStats() {
            const stats = await fetch('/api/stats').then(r => r.json());
            document.getElementById('total-users').textContent = stats.users.total;
            document.getElementById('alerts-24h').textContent = stats.alerts['24h'];
            document.getElementById('alerts-7d').textContent = stats.alerts['7d'];
            document.getElementById('failed-scrapes').textContent = stats.failed_scrapes;
            
            // Tier chart
            const tiers = stats.users.by_tier;
            document.getElementById('tier-chart').innerHTML = Object.entries(tiers)
                .map(([tier, count]) => `<p><strong>${tier.toUpperCase()}:</strong> ${count} users</p>`)
                .join('');
        }
        
        async function loadSources() {
            const sources = await fetch('/api/sources').then(r => r.json());
            const tbody = document.querySelector('#sources-table tbody');
            tbody.innerHTML = sources.map(s => `
                <tr>
                    <td>${s.name}</td>
                    <td class="status-${s.status}">${s.status.toUpperCase()}</td>
                    <td>${(s.success_rate * 100).toFixed(1)}%</td>
                    <td>${s.last_check ? new Date(s.last_check).toLocaleString() : 'Never'}</td>
                </tr>
            `).join('');
        }
        
        loadStats();
        loadSources();
        setInterval(() => { loadStats(); loadSources(); }, 30000);
    </script>
</body>
</html>'''

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, V2DashboardHandler)
    logger.info(f"V2 Dashboard running at http://localhost:{port}")
    print(f"\n🚀 V2 Dashboard: http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
