# LA Agenda Alerts - Customer Outreach System

## Your Role vs My Role

**You do:**
- Find potential customers through research (LinkedIn, community groups, etc.)
- Verify they're relevant (live in LA, care about local government)
- Get their email addresses

**I do:**
- Write personalized, short outreach emails
- Help you track who you've contacted
- Manage follow-ups

## Email Outreach Rules (To Not Be Spam)

### ✅ DO:
- Target people who would genuinely benefit
- Keep it short (under 100 words)
- Personalize each email
- Include clear unsubscribe option
- Only email once (no follow-up unless they reply)

### ❌ DON'T:
- Email the same person multiple times
- Use misleading subject lines
- Hide who it's from
- Email more than 50 people/day (triggers spam filters)

## Outreach Email Template

**Subject:** Quick question about LA government meetings

**Body:**
```
Hi [Name],

I saw you're [specific reason - e.g., "active in the LA housing advocacy space"]. 

I built a simple tool that monitors LA City Council, PLUM Committee, and County Board agendas and sends email alerts when things change.

It's free during the beta. Would this be useful for you?

https://[YOUR_GITHUB_USERNAME].github.io/la-agenda-alerts/

If not, no worries - just reply STOP and I won't email again.

Best,
Max
```

## How This Works

1. **You find leads** and add them to `outreach/leads.json`
2. **I draft emails** for each lead
3. **You review** and approve
4. **I send** via Agent Mail API
5. **We track** responses in `outreach/responses.json`

## Next Steps

When you have your first batch of leads (10-20 people):

1. Send me the list with:
   - Email address
   - Name (if available)
   - Why they're a good fit (1 sentence)

2. I'll:
   - Draft personalized emails
   - Show you the drafts
   - Send only after you approve

3. We'll track:
   - Who was contacted
   - Who replied
   - Who subscribed

## Ready?

Send me your first batch of leads and I'll draft the outreach emails for you.

Format:
```
1. john@example.com - John, housing activist in Echo Park
2. sarah@example.com - Sarah, urban planning student at USC
3. etc...
```
