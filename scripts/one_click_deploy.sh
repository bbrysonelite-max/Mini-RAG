#!/bin/bash
# ONE COMMAND TO DEPLOY EVERYTHING
# Usage: ./scripts/one_click_deploy.sh [platform]
# Platforms: heroku | render | fly | local

set -e

PLATFORM=${1:-local}

echo "=========================================="
echo "🚀 ONE-CLICK DEPLOY: $PLATFORM"
echo "=========================================="
echo ""

case $PLATFORM in
  heroku)
    echo "Deploying to Heroku..."
    echo ""
    
    # Check Heroku CLI
    if ! command -v heroku &> /dev/null; then
        echo "Installing Heroku CLI..."
        brew tap heroku/brew && brew install heroku
    fi
    
    # Login
    heroku login
    
    # Create app
    APP_NAME="mini-rag-$(date +%s)"
    heroku create $APP_NAME
    
    # Add addons
    heroku addons:create heroku-postgresql:essential-0
    heroku addons:create heroku-redis:mini
    
    # Set buildpack
    heroku buildpacks:set heroku/python
    
    # Generate and set secrets
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    echo "Setting environment variables..."
    heroku config:set \
      SECRET_KEY="$SECRET_KEY" \
      REDIS_ENABLED=true \
      BACKGROUND_JOBS_ENABLED=true \
      ALLOW_INSECURE_DEFAULTS=false
    
    echo ""
    echo "⚠️  YOU MUST SET THESE MANUALLY:"
    echo "heroku config:set GOOGLE_CLIENT_ID=your-id"
    echo "heroku config:set GOOGLE_CLIENT_SECRET=your-secret"
    echo "heroku config:set OPENAI_API_KEY=your-key"
    echo ""
    read -p "Press Enter after setting credentials..."
    
    # Deploy
    git push heroku main || git push heroku HEAD:main
    
    # Initialize DB
    echo "Initializing database..."
    heroku run "cat db_schema.sql | psql \$DATABASE_URL"
    
    # Open
    heroku open
    ;;
    
  fly)
    ./scripts/deploy_fly.sh
    ;;
    
  render)
    ./scripts/deploy_render.sh
    ;;
    
  local)
    echo "Local deployment with Docker Compose..."
    echo ""
    
    # Check .env exists
    if [ ! -f .env ]; then
        echo "⚠️  .env file not found!"
        echo ""
        echo "For local dev with dummy secrets:"
        echo "  export ALLOW_INSECURE_DEFAULTS=true"
        echo ""
        echo "For production-like local testing:"
        echo "  cp PRODUCTION_ENV_TEMPLATE .env"
        echo "  # Edit .env with real credentials"
        echo ""
        read -p "Press Enter to continue with ALLOW_INSECURE_DEFAULTS=true for demo..."
        export ALLOW_INSECURE_DEFAULTS=true
    else
        echo "✓ .env file found"
    fi
    
    # Start services
    echo "Starting services..."
    docker-compose down -v  # Clean slate
    docker-compose up -d db redis
    
    echo "Waiting for database..."
    sleep 15
    
    # Initialize DB
    echo "Loading schema..."
    docker exec -i mini-rag-db psql -U postgres -d rag_brain < db_schema.sql 2>&1 | grep -v "already exists" || true
    
    # Start app
    echo "Starting application..."
    docker-compose up -d app
    
    echo ""
    echo "Waiting for app to be healthy..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ App is healthy!"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    echo ""
    echo ""
    echo "=========================================="
    echo "✅ Local deployment complete!"
    echo "=========================================="
    echo ""
    echo "Access your app:"
    echo "  Web UI: http://localhost:8000/app"
    echo "  React UI: http://localhost:8000/app-react"
    echo "  API docs: http://localhost:8000/docs"
    echo "  Health: http://localhost:8000/health"
    echo "  Metrics: http://localhost:8000/metrics"
    echo ""
    echo "View logs:"
    echo "  docker-compose logs -f app"
    echo ""
    echo "Run smoke tests:"
    echo "  ./scripts/smoke_test.sh"
    echo ""
    ;;
    
  *)
    echo "❌ Unknown platform: $PLATFORM"
    echo ""
    echo "Usage: $0 [platform]"
    echo "Platforms: local | heroku | render | fly"
    exit 1
    ;;
esac

echo "🎉 Deployment complete!"

