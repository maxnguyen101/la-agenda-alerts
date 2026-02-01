# COMPLETE SETUP GUIDE - From Zero to Live Website

This guide assumes you've NEVER used GitHub or Stripe before.

---

## PART 1: GITHUB SETUP (30 minutes)

### Step 1: Create GitHub Account

1. Go to https://github.com
2. Click **"Sign up"** (top right)
3. Enter your email: `howtopc2101@gmail.com`
4. Create a password (save it in your password manager)
5. Choose username: `maxnguyen` (or whatever you want)
6. Complete the verification puzzles
7. Verify your email (check inbox for GitHub email)
8. Click **"Create account"**

### Step 2: Create Repository

1. Once logged in, click **green "New"** button (or go to https://github.com/new)
2. **Repository name**: `la-agenda-alerts`
3. **Description**: `Automated LA government agenda monitoring with email alerts`
4. Choose **"Public"** (or Private if you prefer)
5. **Check** "Add a README file"
6. Click **"Create repository"**

### Step 3: Configure Git on Your Mac

Open Terminal (CMD+Space, type "Terminal", press Enter)

```bash
# Set your name (will appear on commits)
git config --global user.name "Max Nguyen"

# Set your email (use your GitHub email)
git config --global user.email "howtopc2101@gmail.com"

# Check it worked
git config --list
```

### Step 4: Connect Your Local Project to GitHub

In Terminal:

```bash
# Go to your project
cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts

# Initialize Git (if not already done)
git init

# Add GitHub as remote (replace 'maxnguyen' with your actual username)
git remote add origin https://github.com/maxnguyen/la-agenda-alerts.git

# Check connection
git remote -v
```

### Step 5: Push Your Code to GitHub

```bash
# Add all files to Git
git add .

# Commit with a message
git commit -m "Initial launch - V2 with Stripe payments"

# Push to GitHub (first time needs -u flag)
git push -u origin main

# If you get an error about 'main', try:
git push -u origin master
```

**You'll be asked to log in:**
- Use your GitHub username and password
- OR create a Personal Access Token (recommended)

### Step 6: Create Personal Access Token (Recommended)

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token"** → "Generate new token (classic)"
3. **Note**: `Git Push Token`
4. **Expiration**: 90 days (or No expiration)
5. **Scopes**: Check only `repo`
6. Click **"Generate token"**
7. **COPY THE TOKEN IMMEDIATELY** (you won't see it again!)
8. Save it somewhere safe (password manager)

When pushing code, use this token instead of your password.

### Step 7: Enable GitHub Pages

1. Go to your repository: `https://github.com/maxnguyen/la-agenda-alerts`
2. Click **"Settings"** tab (top of page)
3. Scroll down left sidebar to **"Pages"**
4. Under "Source", select **"Deploy from a branch"**
5. Under "Branch", select **"main"** and folder **"/(root)"**
6. Click **"Save"**
7. Wait 2-5 minutes
8. Visit: `https://maxnguyen.github.io/la-agenda-alerts`

🎉 **Your website is now LIVE!**

---

## PART 2: STRIPE SETUP (45 minutes)

### Step 1: Create Stripe Account

1. Go to https://stripe.com
2. Click **"Sign up"** (top right)
3. Enter email: `howtopc2101@gmail.com`
4. Create password
5. Verify email address
6. Complete profile:
   - Business name: "LA Agenda Alerts"
   - Business website: `https://maxnguyen.github.io/la-agenda-alerts`
   - Industry: "Technology / Software"
   - Business type: "Individual"

### Step 2: Activate Your Account

**You need to provide:**
1. **Legal name**: Your full legal name
2. **Date of birth**
3. **Home address**
4. **Last 4 digits of SSN** (for tax purposes)
5. **Bank account** (where payments go)
   - Routing number
   - Account number

**This is required by law for payment processing.**

### Step 3: Create Products

1. In Stripe Dashboard, click **"Products"** (left sidebar)
2. Click **"+ Add product"**
3. **Product name**: `LA Agenda Alerts Pro`
4. **Description**: `Email + SMS alerts, advanced keywords, calendar integration`
5. Click **"Save"**
6. Under "Pricing", click **"+ Add pricing"**
7. **Price**: `$9.00`
8. **Billing period**: `Monthly`
9. Click **"Save"**

Repeat for Organization plan:
- **Name**: `LA Agenda Alerts Organization`
- **Price**: `$39.00/month`

### Step 4: Get API Keys

1. In Stripe Dashboard, click **"Developers"** (top right)
2. Click **"API keys"**
3. You'll see:
   - **Publishable key**: `pk_test_xxxxx` (safe to share)
   - **Secret key**: `sk_test_xxxxx` (KEEP SECRET!)
4. Click **"Reveal test key token"** next to Secret key
5. **Copy both keys**

### Step 5: Get Webhook Secret

1. In Stripe Dashboard, click **"Developers"**
2. Click **"Webhooks"**
3. Click **"+ Add endpoint"**
4. **Endpoint URL**: `http://your-public-ip:8081/stripe/webhook`
   - (You'll need to expose your Mac Mini publicly - see below)
5. Click **"+ Select events"**
6. Select these events:
   - `checkout.session.completed`
   - `invoice.payment_failed`
   - `customer.subscription.deleted`
7. Click **"Add endpoint"**
8. Click on your new endpoint
9. Click **"Reveal"** under "Signing secret"
10. **Copy the webhook secret** (`whsec_xxxxx`)

### Step 6: Update Your Environment File

On your Mac, edit the `.env` file:

```bash
# Open in TextEdit
open -e /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts/.env
```

Add these lines at the bottom:

```
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_actual_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_actual_webhook_secret_here
STRIPE_PRO_PRICE_ID=price_your_pro_product_id
STRIPE_ORG_PRICE_ID=price_your_org_product_id
```

**Replace with your actual keys from Stripe dashboard!**

### Step 7: Expose Your Mac Mini Publicly (Required for Webhooks)

Stripe webhooks need to reach your Mac Mini from the internet.

**Option A: ngrok (Easiest - Free)**

```bash
# Install ngrok
brew install ngrok

# Sign up at ngrok.com
# Get authtoken from dashboard
ngrok config add-authtoken YOUR_TOKEN

# Expose port 8081
ngrok http 8081
```

You'll get a public URL like: `https://abc123.ngrok.io`

Update Stripe webhook URL to: `https://abc123.ngrok.io/stripe/webhook`

**Option B: Cloudflare Tunnel**

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8081
```

### Step 8: Test Payment Flow

1. Restart your Stripe server:
```bash
pkill -f stripe_server.py
cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts
export $(grep -v '^#' .env | xargs)
python3 v2/stripe_server.py
```

2. Create test checkout:
```bash
curl -X POST http://localhost:8081/stripe/checkout \
  -d "email=test@example.com" \
  -d "plan=pro"
```

3. In Stripe Dashboard, go to "Payments"
4. You should see test payment (if using test keys)

---

## PART 3: PUTTING IT ALL TOGETHER

### Test Complete Flow

1. **Visit your website**: `https://maxnguyen.github.io/la-agenda-alerts`
2. **Click "Upgrade to Pro"**
3. **Enter test email**
4. **Complete payment** (use Stripe test card: `4242 4242 4242 4242`, any future date, any CVC)
5. **Check your dashboard**: `http://localhost:8080`
6. **User should appear as "Pro" tier**

### Manual Payment Fallback (While Stripe Verifies)

Since Stripe account verification takes 1-2 days, use this for now:

**On your website**, users see:
```
To upgrade:
1. Send $9 to:
   - Venmo: @yourusername
   - PayPal: mnguyen9@usc.edu
   - Zelle: mnguyen9@usc.edu

2. Email receipt to: mnguyen9@usc.edu

3. Your account will be upgraded within 24 hours.
```

**You manually upgrade them:**
```bash
# Connect to database
sqlite3 data/v2/la_agenda_v2.db

# Upgrade user
UPDATE users SET plan = 'pro', billing_status = 'active' WHERE email = 'user@example.com';
.quit
```

---

## TROUBLESHOOTING

### GitHub Push Fails
```bash
# Check remote
git remote -v

# If wrong, fix it:
git remote set-url origin https://github.com/YOUR_USERNAME/la-agenda-alerts.git
```

### Stripe Webhook Not Receiving
```bash
# Check ngrok is running
ngrok http 8081

# Test webhook locally
curl -X POST http://localhost:8081/stripe/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"test"}'
```

### Website Not Showing
- Wait 5 minutes after enabling GitHub Pages
- Clear browser cache (CMD+Shift+R)
- Check repository Settings → Pages for errors

---

## CHECKLIST

**GitHub:**
- [ ] Account created
- [ ] Repository created
- [ ] Git configured on Mac
- [ ] Code pushed to GitHub
- [ ] GitHub Pages enabled
- [ ] Website loads at your URL

**Stripe:**
- [ ] Account created
- [ ] Identity verified
- [ ] Bank account linked
- [ ] Products created (Pro $9, Org $39)
- [ ] API keys copied
- [ ] Webhook endpoint created
- [ ] Webhook secret copied
- [ ] .env file updated
- [ ] ngrok installed (optional)

**Local:**
- [ ] Dashboard running (localhost:8080)
- [ ] Stripe server running (localhost:8081)
- [ ] Test payment works

---

**Total Time: ~1-2 hours**

**Questions? Message me at each step and I'll help!**
