#!/bin/bash
# Script to get the public ngrok URL from the running container

echo "🔍 Getting ngrok public URL..."
echo ""

# Try to get URL from ngrok API
URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | \
  python3 -c "import sys, json; \
  try: \
    data=json.load(sys.stdin); \
    tunnels=data.get('tunnels', []); \
    urls=[t['public_url'] for t in tunnels if 'public_url' in t]; \
    print('\n'.join(urls) if urls else 'No tunnels found') \
  except: \
    print('Error parsing JSON')" 2>/dev/null)

if [ -z "$URL" ] || [ "$URL" = "No tunnels found" ] || [ "$URL" = "Error parsing JSON" ]; then
  # Fallback: check if container is running
  if ! docker-compose ps ngrok | grep -q "Up"; then
    echo "❌ Ngrok container is not running"
    echo "   Start it with: docker-compose up -d ngrok"
    exit 1
  fi
  
  # Try alternative method
  URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | \
    grep -o '"public_url":"[^"]*"' | \
    cut -d'"' -f4 | \
    head -1)
fi

if [ -z "$URL" ]; then
  echo "❌ Could not retrieve ngrok URL"
  echo "   Make sure ngrok is running and check: http://localhost:4040"
  exit 1
fi

echo "✅ Ngrok Public URL:"
echo "   $URL"
echo ""
echo "📋 For Slack Event Subscriptions, use:"
echo "   $URL/slack/events"
echo ""
echo "🌐 Ngrok Web Interface: http://localhost:4040"

