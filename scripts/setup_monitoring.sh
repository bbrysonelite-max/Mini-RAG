#!/bin/bash
# Quick monitoring setup - FREE options

echo "=========================================="
echo "📊 Monitoring Setup (Free Tier)"
echo "=========================================="
echo ""

echo "Choose your monitoring stack:"
echo "1. UptimeRobot (simplest - uptime only)"
echo "2. Grafana Cloud (comprehensive - metrics + logs)"
echo "3. Better Stack (modern - logs + uptime)"
echo "4. Skip for now"
echo ""
read -p "Choice [1-4]: " CHOICE

case $CHOICE in
  1)
    echo ""
    echo "=== UptimeRobot Setup ==="
    echo ""
    echo "1. Go to: https://uptimerobot.com/signUp"
    echo "2. Create free account"
    echo "3. Add New Monitor:"
    echo "   - Type: HTTP(s)"
    echo "   - URL: https://yourdomain.com/health"
    echo "   - Interval: 5 minutes"
    echo "   - Alert Contacts: Your email"
    echo ""
    echo "✅ You'll get email if your site goes down"
    ;;
    
  2)
    echo ""
    echo "=== Grafana Cloud Setup ==="
    echo ""
    echo "1. Go to: https://grafana.com/auth/sign-up/create-user"
    echo "2. Create free account (14-day trial, then free tier)"
    echo "3. Skip the onboarding wizard"
    echo ""
    echo "4. Add Prometheus Data Source:"
    echo "   - Configuration → Data Sources → Add"
    echo "   - Choose: Prometheus"
    echo "   - URL: https://yourdomain.com/metrics"
    echo "   - Save & Test"
    echo ""
    echo "5. Import Dashboard:"
    echo "   - Dashboards → Import"
    echo "   - Upload: docs/infra/metrics_alerts/mini-rag-dashboard.json"
    echo "   - Select Prometheus data source"
    echo "   - Import"
    echo ""
    echo "6. Set Up Alerts:"
    echo "   - Alerting → Alert rules → New alert rule"
    echo "   - Name: Mini-RAG Service Down"
    echo "   - Query: up{job=\"mini-rag\"} == 0"
    echo "   - Threshold: Alert when no data for 2 minutes"
    echo "   - Contact point: Your email"
    echo ""
    echo "✅ You now have full metrics + alerting!"
    ;;
    
  3)
    echo ""
    echo "=== Better Stack (formerly Logtail) Setup ==="
    echo ""
    echo "1. Go to: https://betterstack.com/signup"
    echo "2. Create free account"
    echo "3. Create Uptime Monitor:"
    echo "   - URL: https://yourdomain.com/health"
    echo "   - Check interval: 30 seconds"
    echo ""
    echo "4. (Optional) Send logs:"
    echo "   - Get source token from Better Stack"
    echo "   - Install: pip install logtail-python"
    echo "   - Add to server.py logging config"
    echo ""
    echo "✅ Modern monitoring + incident management"
    ;;
    
  4)
    echo ""
    echo "Skipping monitoring setup."
    echo "⚠️  STRONGLY recommend setting up at least uptime monitoring!"
    ;;
    
  *)
    echo "Invalid choice"
    exit 1
    ;;
esac

echo ""
echo "=========================================="
echo "Next: Run smoke tests"
echo "  ./scripts/smoke_test.sh"
echo "=========================================="

