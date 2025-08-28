#!/bin/bash

echo "========================================="
echo "🚀 Vercel Setup Script for Secure Personal OS"
echo "========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo -e "${YELLOW}📦 Installing Vercel CLI...${NC}"
    npm install -g vercel
fi

echo "This script will help you deploy to Vercel."
echo ""
echo -e "${GREEN}Step 1: Get your Vercel Token${NC}"
echo "----------------------------------------"
echo "1. Go to: https://vercel.com/account/tokens"
echo "2. Click 'Create' to generate a new token"
echo "3. Copy the token (you'll need it in the next step)"
echo ""
read -p "Press Enter when you have your token ready..."

echo ""
echo -e "${GREEN}Step 2: Set Token and Deploy${NC}"
echo "----------------------------------------"
read -s -p "Paste your Vercel token here: " VERCEL_TOKEN
echo ""

if [ -z "$VERCEL_TOKEN" ]; then
    echo -e "${RED}❌ No token provided. Exiting.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}🔗 Linking project with Vercel...${NC}"

# Set the token and link the project
export VERCEL_TOKEN="$VERCEL_TOKEN"

# Try to link the project
vercel link --yes --token="$VERCEL_TOKEN" 2>&1 | tee vercel_link.log

# Check if linking was successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Project linked successfully!${NC}"
    echo ""
    echo -e "${GREEN}Step 3: Deploy to Vercel${NC}"
    echo "----------------------------------------"
    echo "Choose deployment type:"
    echo "1) Development deployment (preview)"
    echo "2) Production deployment"
    read -p "Enter choice (1 or 2): " choice

    case $choice in
        1)
            echo -e "${YELLOW}🚀 Deploying to Vercel (Preview)...${NC}"
            vercel --token="$VERCEL_TOKEN" 2>&1 | tee vercel_deploy.log
            ;;
        2)
            echo -e "${YELLOW}🚀 Deploying to Vercel (Production)...${NC}"
            vercel --prod --token="$VERCEL_TOKEN" 2>&1 | tee vercel_deploy.log
            ;;
        *)
            echo -e "${RED}Invalid choice. Running preview deployment...${NC}"
            vercel --token="$VERCEL_TOKEN" 2>&1 | tee vercel_deploy.log
            ;;
    esac

    # Extract URL from deployment
    DEPLOY_URL=$(grep -oE 'https://[^ ]+\.vercel\.app' vercel_deploy.log | head -1)
    
    if [ ! -z "$DEPLOY_URL" ]; then
        echo ""
        echo -e "${GREEN}✅ Deployment successful!${NC}"
        echo -e "${GREEN}🌐 Your app is live at: $DEPLOY_URL${NC}"
        echo ""
        echo "You can also manage your deployment at:"
        echo "https://vercel.com/dashboard"
    else
        echo ""
        echo -e "${YELLOW}⚠️  Deployment completed. Check the logs above for the URL.${NC}"
    fi

    # Save token for future use (optional)
    echo ""
    read -p "Save token for future deployments? (y/n): " save_token
    if [ "$save_token" = "y" ]; then
        echo "export VERCEL_TOKEN='$VERCEL_TOKEN'" > ~/.vercel_token
        chmod 600 ~/.vercel_token
        echo -e "${GREEN}✅ Token saved to ~/.vercel_token${NC}"
        echo "To use in future: source ~/.vercel_token"
    fi

else
    echo -e "${RED}❌ Failed to link project. Check vercel_link.log for details.${NC}"
    echo ""
    echo "Common issues:"
    echo "1. Invalid token - Generate a new one at https://vercel.com/account/tokens"
    echo "2. Network issues - Check your internet connection"
    echo "3. Project already linked - Try: rm -rf .vercel/"
    exit 1
fi

echo ""
echo "========================================="
echo -e "${GREEN}📝 Notes:${NC}"
echo "- Playwright won't run on Vercel (serverless limitation)"
echo "- The app will run in demo mode on Vercel"
echo "- For full browser automation, use a VPS or local development"
echo "========================================="