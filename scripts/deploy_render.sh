#!/bin/bash
# Deploy to Render.com - Automated

set -e

echo "=========================================="
echo "Deploy to Render.com"
echo "=========================================="
echo ""

# 1. Check if render.yaml exists
if [ ! -f render.yaml ]; then
    echo "❌ render.yaml not found!"
    exit 1
fi

echo "✓ render.yaml found"
echo ""

# 2. Instructions (Render doesn't have CLI yet)
echo "📝 Manual steps required:"
echo ""
echo "1. Go to: https://render.com/login"
echo "2. Click 'New +' → 'Blueprint'"
echo "3. Connect this GitHub repo"
echo "4. Render will auto-detect render.yaml"
echo "5. Set environment variables in Render dashboard:"
echo "   - GOOGLE_CLIENT_ID"
echo "   - GOOGLE_CLIENT_SECRET"
echo "   - OPENAI_API_KEY"
echo "   - STRIPE_API_KEY"
echo "   - STRIPE_WEBHOOK_SECRET"
echo "   - STRIPE_PRICE_ID"
echo ""
echo "6. Click 'Apply'"
echo "7. Wait for deployment (~5 minutes)"
echo "8. Get your URL: https://mini-rag.onrender.com"
echo ""
echo "9. Initialize database:"
echo "   - Go to Render dashboard → mini-rag-db"
echo "   - Copy Internal Database URL"
echo "   - Run: psql <url> < db_schema.sql"
echo ""
echo "10. Test: curl https://mini-rag.onrender.com/health"
echo ""
echo "✅ Done! Your app is live."
echo ""

