# LA Agenda Alerts - Website Architecture Guide

## GitHub Pages Limitations

**GitHub Pages is STATIC HOSTING ONLY:**
- ✅ Can serve HTML, CSS, JavaScript files
- ❌ CANNOT run Python/Node.js backend
- ❌ CANNOT process payments
- ❌ CANNOT handle database queries
- ❌ CANNOT generate magic links
- ❌ CANNOT manage user sessions

**What this means:**
- Landing page: ✅ Works on GitHub Pages
- Payment processing: ❌ Needs external service
- User logins: ❌ Needs backend server
- Database: ❌ Needs backend server

---

## Your Two Options

### OPTION 1: Hybrid Architecture (RECOMMENDED)

**Static Landing Page (GitHub Pages):**
- Beautiful marketing site
- Pricing information
- Signup form (sends data to your backend)
- "Upgrade" buttons link to Stripe Checkout

**Backend Server (Your Mac Mini):**
- V2 dashboard (already built)
- User authentication (magic links)
- Database (SQLite)
- Alert processing
- Webhook endpoint for Stripe

**How it works:**
1. User visits GitHub Page → sees pricing
2. Clicks "Get Started" → fills form
3. Form submits to your Mac Mini backend
4. Backend creates user, sends welcome email
5. Free users get alerts immediately
6. To upgrade: Button → Stripe Checkout → Payment → Webhook → Upgrade account

**Pros:**
- Landing page loads fast (GitHub CDN)
- Free hosting for frontend
- Full control over backend
- Works with current setup

**Cons:**
- Mac Mini must stay online
- Need to handle Stripe webhooks

---

### OPTION 2: Serverless with Netlify/Vercel

**Use serverless functions for backend:**
- Hosting: Netlify or Vercel (free tier)
- Backend: Serverless functions (Node.js/Python)
- Database: Supabase or PlanetScale (free tier)
- Auth: Auth0 or Supabase Auth
- Payments: Stripe

**Pros:**
- No Mac Mini needed 24/7
- Scales automatically
- Professional setup

**Cons:**
- More complex
- Multiple vendors
- Higher learning curve
- Costs money at scale

---

## Your Current 2 Users

**From V1 subscribers.json migration:**

1. **howtopc2101@gmail.com**
   - Plan: Free
   - Status: Active
   - Keywords: ["agenda", "meeting", "supervisor", "council", "housing", "zoning", "development", "transit", "transportation", "environment", "air quality", "sanitation"]
   - Sources: All 13 sources
   - Frequency: instant

2. **mnguyen9@usc.edu**
   - Plan: Free
   - Status: Active
   - Keywords: ["agenda", "meeting", "supervisor", "council"]
   - Sources: 3 core sources
   - Frequency: daily_digest

These are YOUR accounts for testing and receiving alerts.

---

## Recommended: Stripe Checkout Links (EASIEST)

**Step 1: Create Stripe Account**
- Go to stripe.com
- Create free account
- No coding required

**Step 2: Create Products**
```
Product: LA Agenda Alerts Pro
Price: $9/month
```

**Step 3: Get Checkout Link**
Stripe generates a unique URL:
```
https://buy.stripe.com/xxxxx
```

**Step 4: Add to Website**
```html
<a href="https://buy.stripe.com/xxxxx" class="cta-button">
  Upgrade to Pro - $9/month
</a>
```

**Step 5: Handle Webhook**
When someone pays, Stripe sends webhook to your backend:
```python
@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    # Upgrade user to Pro
    # Send confirmation email
```

**Pros:**
- No complex coding
- Stripe handles everything
- Secure payments
- Automatic invoicing

---

## Simplest Working Solution (DO THIS)

**For Now (Beta Launch):**

1. **Landing Page** (GitHub Pages)
   - Beautiful static site
   - Signup form → sends email to you
   - Manual account creation
   - "Contact for Pro" button

2. **Backend** (Mac Mini)
   - Handles free users
   - Sends alerts
   - Dashboard for monitoring

3. **Pro Upgrades** (Manual)
   - User emails: "I want to upgrade"
   - You send Stripe payment link
   - After payment, manually upgrade in database

**When you have 10+ paying customers:**
- Automate with Stripe Checkout
- Add webhook handling
- Build self-service upgrade

---

## Files You Need

**Current Setup:**
- `web/index.html` - Landing page (GitHub Pages)
- `v2/dashboard.py` - Backend server (Mac Mini)
- `data/v2/la_agenda_v2.db` - User database

**To Add:**
- Stripe webhook handler (when ready)
- Self-service signup form
- Payment integration

---

## My Recommendation

**Launch TODAY with this flow:**

1. Deploy landing page to GitHub Pages ✅
2. Start V2 dashboard on Mac Mini ✅
3. Manual signup process (you create accounts)
4. Get 5-10 beta users
5. Then add Stripe automation

**Don't let perfect be the enemy of good.**

Get users first, automate later.

---

Want me to:
1. Create Stripe checkout links for you?
2. Add webhook handler to V2 backend?
3. Build self-service signup form?
4. Or keep it simple for now?
