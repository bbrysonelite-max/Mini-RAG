#!/bin/bash
# Deploy to Fly.io - Fully Automated

set -e

echo "=========================================="
echo "Deploy to Fly.io"
echo "=========================================="
echo ""

# 1. Check flyctl installed
if ! command -v flyctl &> /dev/null; then
    echo "Installing flyctl..."
    brew install flyctl || curl -L https://fly.io/install.sh | sh
fi

# 2. Login
echo "Logging in to Fly.io..."
flyctl auth login

# 3. Launch (creates app)
echo ""
echo "Creating app..."
flyctl launch --no-deploy --copy-config --name mini-rag

# 4. Create PostgreSQL
echo ""
echo "Creating PostgreSQL database..."
flyctl postgres create --name mini-rag-db --vm-size shared-cpu-1x --volume-size 10

# Attach to app
flyctl postgres attach mini-rag-db

# 5. Create Redis
echo ""
echo "Creating Redis..."
flyctl redis create --name mini-rag-redis --plan free

# Get Redis URL
REDIS_URL=$(flyctl redis status mini-rag-redis --json | jq -r '.PrivateUrl')

# 6. Set secrets
echo ""
echo "Setting secrets..."
echo "Enter your credentials:"

read -p "GOOGLE_CLIENT_ID: " GOOGLE_CLIENT_ID
read -sp "GOOGLE_CLIENT_SECRET: " GOOGLE_CLIENT_SECRET
echo ""
read -sp "OPENAI_API_KEY: " OPENAI_API_KEY
echo ""
read -p "STRIPE_API_KEY (or press Enter to skip): " STRIPE_API_KEY
read -p "STRIPE_WEBHOOK_SECRET (or press Enter to skip): " STRIPE_WEBHOOK_SECRET
read -p "STRIPE_PRICE_ID (or press Enter to skip): " STRIPE_PRICE_ID

# Generate SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Set all secrets
flyctl secrets set \
  SECRET_KEY="$SECRET_KEY" \
  GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
  GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  REDIS_URL="$REDIS_URL"

if [ -n "$STRIPE_API_KEY" ]; then
    flyctl secrets set \
      STRIPE_API_KEY="$STRIPE_API_KEY" \
      STRIPE_WEBHOOK_SECRET="$STRIPE_WEBHOOK_SECRET" \
      STRIPE_PRICE_ID="$STRIPE_PRICE_ID"
fi

# 7. Deploy
echo ""
echo "Deploying..."
flyctl deploy

# 8. Initialize database
echo ""
echo "Initializing database schema..."
flyctl proxy 5432 -a mini-rag-db &
PROXY_PID=$!
sleep 5

psql postgresql://postgres:password@localhost:5432/rag_brain < db_schema.sql

kill $PROXY_PID

# 9. Open app
echo ""
echo "=========================================="
echo "✅ Deployment complete!"
echo "=========================================="
echo ""
echo "Your app is live at:"
flyctl status | grep "Hostname"
echo ""
echo "Next steps:"
echo "1. Visit your app URL"
echo "2. Sign in with Google"
echo "3. Upload a document"
echo "4. Ask a question"
echo ""
echo "Monitor with: flyctl logs"
echo "Check health: curl https://your-app.fly.dev/health"
echo ""

