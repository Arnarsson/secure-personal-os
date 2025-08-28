# 🚀 Deploy to Vercel - Quick Guide

## Option 1: One-Click Deploy (Easiest)

Click this button to deploy directly to Vercel:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Arnarsson/secure-personal-os&env=PERSONAL_OS_WEB_TOKEN&envDescription=Security%20token%20for%20API%20access&project-name=secure-personal-os&repository-name=secure-personal-os)

This will:
1. Fork the repository to your GitHub
2. Create a new Vercel project
3. Deploy automatically

## Option 2: Using Setup Script

```bash
# Run the interactive setup script
./setup_vercel.sh
```

This script will:
1. Guide you through getting a Vercel token
2. Link your project
3. Deploy to Vercel
4. Save your token for future use

## Option 3: Manual Setup

### Step 1: Get a Vercel Token
1. Go to https://vercel.com/account/tokens
2. Click "Create" to generate a new token
3. Copy the token

### Step 2: Deploy with Token

```bash
# Export your token
export VERCEL_TOKEN="your-token-here"

# Link the project (first time only)
npx vercel link --yes --token=$VERCEL_TOKEN

# Deploy to preview
npx vercel --token=$VERCEL_TOKEN

# Or deploy to production
npx vercel --prod --token=$VERCEL_TOKEN
```

## Option 4: GitHub Integration

1. Go to https://vercel.com/dashboard
2. Click "Import Project"
3. Select "Import Git Repository"
4. Choose `Arnarsson/secure-personal-os`
5. Click "Deploy"

Vercel will automatically deploy on every push to main.

## What Gets Deployed

✅ **Working Features on Vercel:**
- Web API endpoints
- Demo mode UI
- Status endpoints
- Health checks

⚠️ **Limited on Vercel (Serverless):**
- Playwright browser automation (needs persistent server)
- Long-running sessions
- File system writes

## Environment Variables

Set these in Vercel Dashboard → Settings → Environment Variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `PERSONAL_OS_WEB_TOKEN` | API authentication token | Yes |
| `PERSONAL_OS_DEMO_MODE` | Set to `1` for demo mode | No (auto-detected) |

## Testing Your Deployment

Once deployed, test your endpoints:

```bash
# Check health
curl https://your-app.vercel.app/health

# Check API info
curl https://your-app.vercel.app/api/info

# Check status (with token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-app.vercel.app/api/status
```

## Troubleshooting

### "No credentials found" Error
Run: `vercel login` or use `--token` flag

### "Project already linked" Error
Remove existing link: `rm -rf .vercel/`

### Deployment Fails
Check `vercel.json` is present and Python version is 3.11

### Browser Automation Not Working
Vercel is serverless - use a VPS for full Playwright features

## Local Development vs Vercel

| Feature | Local | Vercel |
|---------|-------|--------|
| Web UI | ✅ | ✅ |
| API Endpoints | ✅ | ✅ |
| Browser Automation | ✅ | ❌ |
| Gmail/Calendar/WhatsApp | ✅ | ❌ |
| Persistent Sessions | ✅ | ❌ |
| File Storage | ✅ | ❌ |

For full functionality, deploy to a VPS or use local development.