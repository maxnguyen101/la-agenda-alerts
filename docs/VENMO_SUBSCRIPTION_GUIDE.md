# Venmo Subscription Process

## How It Works (Manual but Simple)

Since you're using Venmo (not Stripe), subscriptions work on an **honor system** with monthly reminders:

---

## Free Tier ($0)

✅ **No payment needed**
- User signs up via website form
- You receive email notification
- Add them to your database
- They get alerts forever free

---

## Pro Tier ($5/month)

### Step 1: User Pays
1. User clicks "Get Pro" on website
2. Payment modal opens with:
   - Venmo: @la_agenda_alerts
   - Zelle: 714-800-4033
3. User sends $5 with note: **"Pro - their@email.com"**

### Step 2: You Receive Payment
- Venmo notification on your phone
- Shows: "$5 from [Name] - Pro - their@email.com"

### Step 3: You Upgrade Them (2 minutes)
```bash
# Add to database
sqlite3 data/v2/la_agenda_v2.db
UPDATE users SET plan='pro', billing_status='active' WHERE email='their@email.com';
.quit

# Or manually track in a spreadsheet
```

### Step 4: Send Welcome Email
```
Subject: Welcome to LA Agenda Alerts Pro!

Hi [Name],

Thanks for upgrading to Pro! You're now getting:
✓ SMS alerts
✓ Calendar .ics files
✓ Advanced keyword filters

Your next payment of $5 is due: [Date + 1 month]
We'll send you a reminder 3 days before.

Questions? Reply to this email.

Thanks!
Max
```

---

## Monthly Renewal (Manual)

### Automated Reminder System (Simple)

**Option A: Calendar Reminders**
- Set Google Calendar event recurring monthly
- Title: "Check Pro Renewals"
- Check who paid last month
- Send Venmo request to those who haven't

**Option B: Simple Spreadsheet**
```
Email              | Plan | Started    | Last Paid  | Next Due   | Status
------------------|------|------------|------------|------------|----------
john@example.com  | Pro  | 2026-02-01 | 2026-02-01 | 2026-03-01 | Active
jane@example.com  | Pro  | 2026-01-15 | 2026-01-15 | 2026-02-15 | Active
```

**Option C: Automated Script (Later)**
```python
# Check daily who needs renewal
# Send email reminder 3 days before
# If not paid after 5 days, downgrade to free
```

---

## Handling Non-Payment

### Grace Period (5 days)
- Pro features continue
- Send friendly reminder

### After 5 days
- Downgrade to Free
- Send: "Your Pro subscription has expired. Reply to resubscribe."
- Keep them on free tier

### They Want to Resubscribe
- They send $5 again
- You reactivate in 30 seconds
- Everyone's happy

---

## The Reality

**Most users will:**
- Start with Free (90%)
- Some upgrade to Pro (10%)
- Of those Pro users, most pay monthly (80%)
- Some forget and get downgraded (20%)

**Your monthly routine (15 minutes):**
1. Check Venmo for payments
2. Update 3-5 subscribers in database
3. Send welcome emails to new Pro users
4. Send renewal reminders to expiring users

---

## Benefits of Manual System

✅ **No fees** - Venmo is free (unlike Stripe's 2.9%)
✅ **Personal touch** - Users feel connected
✅ **No chargebacks** - Venmo payments are final
✅ **Simple** - No complex billing system
✅ **Works immediately** - No waiting for Stripe approval

---

## When to Switch to Stripe

Switch when you have:
- 20+ paying Pro users
- Spending 30+ min/month on billing
- Users asking for "automatic" payments

Until then, manual Venmo is **faster, cheaper, and more personal**.

---

## Pro Tips

1. **Always get email in Venmo note** - Critical for matching
2. **Screenshot payments** - Backup record
3. **Send thank you message** - Builds loyalty
4. **Offer annual discount** - "$50/year instead of $60/month" for easy math
5. **Track in Google Sheets** - Share with yourself for access anywhere
