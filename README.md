# LA Agenda Alerts

[![Deploy to GitHub Pages](https://github.com/YOUR_USERNAME/la-agenda-alerts/actions/workflows/deploy.yml/badge.svg)](https://github.com/YOUR_USERNAME/la-agenda-alerts/actions/workflows/deploy.yml)

🔗 **Live Site**: https://YOUR_USERNAME.github.io/la-agenda-alerts/

Never miss an important LA government meeting. Automated agenda monitoring for LA City Council, PLUM Committee, and LA County Board of Supervisors.

## What We Monitor

- **LA City Council** - Main council meetings and council files
- **PLUM Committee** - Planning and Land Use Management
- **LA County Board of Supervisors** - County-wide decisions

## How It Works

We check government websites 3x daily (8 AM, 1 PM, 6 PM) and email you when:
- New agenda items are added
- Meeting times change
- New documents are attached
- Items are removed or updated

## Request Access

LA Agenda Alerts is currently in limited release. Email [mnguyen9@usc.edu](mailto:mnguyen9@usc.edu?subject=LA%20Agenda%20Alerts%20Access%20Request) to request access.

## Tech Stack

- **Backend**: Python 3.11+ with standard library only
- **Frontend**: Static HTML/CSS
- **Hosting**: GitHub Pages (free)
- **Email**: Agent Mail API
- **Monitoring**: Cron + macOS iMessage

## Project Structure

```
la-agenda-alerts/
├── src/              # Python workers
├── scripts/          # Shell scripts
├── web/              # Static website (GitHub Pages)
├── docs/             # Documentation
├── data/             # Runtime data
└── logs/             # Runtime logs
```

## Local Development

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/la-agenda-alerts.git
cd la-agenda-alerts

# Set environment variables
export AGENT_MAIL_API_KEY="your_key"
export OPERATOR_EMAIL="youremail@example.com"
export OPERATOR_IMESSAGE="youremail@example.com"

# Run tests
./scripts/run_tests.sh

# Run pipeline once
./scripts/run_once.sh

# Serve web locally
./scripts/serve_web.sh
```

## Deployment

### Web (GitHub Pages)

1. Push to GitHub
2. Go to Settings → Pages
3. Source: GitHub Actions
4. Site auto-deploys on every push

### Backend (Your Mac)

```bash
./scripts/install_cron.sh
```

This installs automated 3x daily checks.

## License

MIT License - See LICENSE file
