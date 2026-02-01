# 🚀 DEPLOYMENT GUIDE - Host LA Agenda Alerts Online

## Step 1: Create GitHub Repository (5 minutes)

1. Go to https://github.com/new
2. Repository name: `la-agenda-alerts`
3. Make it **Public** (required for free GitHub Pages)
4. Click **Create repository**

## Step 2: Push Code to GitHub (2 minutes)

```bash
cd /Users/maxwellnguyen/.openclaw/workspace/la-agenda-alerts

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - LA Agenda Alerts v1.0"

# Connect to GitHub (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/la-agenda-alerts.git

# Push
git push -u origin main
```

## Step 3: Enable GitHub Pages (2 minutes)

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Click **Pages** in left sidebar
4. Under "Build and deployment":
   - Source: **GitHub Actions**
5. Click Save

## Step 4: Deploy Website (Automatic)

The GitHub Action will automatically:
1. Build the site from `web/` folder
2. Deploy to GitHub Pages
3. Give you a URL like: `https://YOUR_USERNAME.github.io/la-agenda-alerts/`

**To check deployment status:**
- Go to **Actions** tab in your repo
- Look for "Deploy to GitHub Pages" workflow
- Green checkmark = deployed ✅

## Step 5: Verify Website (1 minute)

Visit: `https://YOUR_USERNAME.github.io/la-agenda-alerts/`

You should see the LA Agenda Alerts landing page!

## Step 6: Custom Domain (Optional, Free)

If you have a domain (e.g., from Namecheap for $9/year):

1. In your repo: Settings → Pages
2. Under "Custom domain", enter: `laagendaalerts.com`
3. Click Save
4. DNS settings will be shown - add them to your domain provider
5. Wait 5-10 minutes for DNS to propagate

**Free subdomain option:**
Use `la-agenda-alerts.YOUR_USERNAME.github.io` - it's already working!

## 🎉 DONE!

Your website is now live at:
```
https://YOUR_USERNAME.github.io/la-agenda-alerts/
```

Share this link with customers!

---

## What You Get For Free

✅ **Website hosting** - Unlimited traffic  
✅ **HTTPS/SSL** - Secure connection  
✅ **99.9% uptime** - Very reliable  
✅ **Automatic deploys** - Push to main = instant update  
✅ **Custom domain support** - Use your own domain  
✅ **No ads** - Clean professional look  

---

## Next Steps

1. **Share the URL** with potential customers
2. **Add to your email signature**
3. **Post on social media**
4. **Track subscribers** in `data/subscribers.json`

---

## Troubleshooting

**Site not showing?**
- Check Actions tab for errors
- Make sure repo is Public
- Wait 2-3 minutes after first push

**Want to update?**
```bash
git add .
git commit -m "Update content"
git push
```
Site updates automatically in ~1 minute!
