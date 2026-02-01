#!/bin/bash
#
# LA Agenda Alerts - Complete Deployment Script
# Deploys website to GitHub Pages and starts all services

set -e

echo "🚀 LA Agenda Alerts - Complete Deployment"
echo "=========================================="
echo ""

# Check we're in the right directory
if [ ! -f "web/index.html" ]; then
    echo "❌ Error: Not in project directory"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Step 1/5: Checking Git status...${NC}"
if [ -d ".git" ]; then
    echo "✅ Git repository found"
else
    echo "Initializing Git repository..."
    git init
    git remote add origin https://github.com/maxnguyen/la-agenda-alerts.git 2>/dev/null || true
fi

echo ""
echo -e "${BLUE}Step 2/5: Adding files to Git...${NC}"
git add web/
git add v2/
git add config/
git add docs/
git add README.md
git add DEPLOY_WEBSITE_NOW.md
git add BUSINESS_PROPOSAL.md
git add V2_UPGRADE_COMPLETE.md
git add setup.sh
git status --short

echo ""
echo -e "${BLUE}Step 3/5: Committing changes...${NC}"
git commit -m "V2 Launch: Stripe payments, webhook automation, enhanced dashboard" || echo "Nothing to commit"

echo ""
echo -e "${BLUE}Step 4/5: Pushing to GitHub...${NC}"
echo "This will deploy the website to GitHub Pages"
echo ""
read -p "Push to GitHub? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push -u origin main || git push -u origin master
    echo "✅ Pushed to GitHub"
    echo ""
    echo "🌐 WEBSITE URL:"
    echo "   https://maxnguyen.github.io/la-agenda-alerts"
    echo ""
    echo "⚠️  IMPORTANT: Enable GitHub Pages in settings:"
    echo "   1. Go to: https://github.com/maxnguyen/la-agenda-alerts/settings/pages"
    echo "   2. Source: Deploy from branch"
    echo "   3. Branch: main / (root)"
    echo "   4. Click Save"
    echo "   5. Wait 2-5 minutes for deployment"
else
    echo "⏭️  Skipped GitHub push"
fi

echo ""
echo -e "${BLUE}Step 5/5: Starting local services...${NC}"
echo ""

# Kill any existing servers
echo "Stopping existing servers..."
pkill -f "python3 v2/dashboard.py" 2>/dev/null || true
pkill -f "python3 v2/stripe_server.py" 2>/dev/null || true
sleep 2

# Start dashboard
echo "Starting V2 Dashboard on port 8080..."
python3 v2/dashboard.py > logs/dashboard_server.log 2>&1 &
DASHBOARD_PID=$!
echo "✅ Dashboard PID: $DASHBOARD_PID"

# Start Stripe server
echo "Starting Stripe Webhook Server on port 8081..."
python3 v2/stripe_server.py > logs/stripe_server.log 2>&1 &
STRIPE_PID=$!
echo "✅ Stripe Server PID: $STRIPE_PID"

sleep 3

echo ""
echo "=========================================="
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo "=========================================="
echo ""
echo "📊 LOCAL SERVICES:"
echo "   Dashboard:     http://localhost:8080"
echo "   Stripe API:    http://localhost:8081"
echo ""
echo "🌐 WEBSITE:"
echo "   https://maxnguyen.github.io/la-agenda-alerts"
echo ""
echo "📧 MANUAL PAYMENT (Until Stripe Verified):"
echo "   Venmo:     @yourusername"
echo "   PayPal:    mnguyen9@usc.edu"
echo "   Zelle:     mnguyen9@usc.edu"
echo ""
echo "📋 NEXT STEPS:"
echo "   1. Enable GitHub Pages in repository settings"
echo "   2. Test website at GitHub URL"
echo "   3. Check dashboard at localhost:8080"
echo "   4. Add your first 10 customers manually"
echo "   5. Set up Stripe account for automation"
echo ""
echo "🔧 TO STOP SERVERS:"
echo "   kill $DASHBOARD_PID"
echo "   kill $STRIPE_PID"
echo ""
echo "💰 READY TO MAKE MONEY!"
echo ""

# Save PIDs
echo $DASHBOARD_PID > .dashboard.pid
echo $STRIPE_PID > .stripe.pid
