#!/bin/bash
# Start ngrok tunnel for Urban Network Mapper

echo "🚀 Starting ngrok tunnel..."

# Kill existing ngrok if running
if [ -f ngrok.pid ]; then
    kill $(cat ngrok.pid) 2>/dev/null
    rm ngrok.pid
fi

# Start ngrok
ngrok http 5173 --log stdout > ngrok.log 2>&1 &
echo $! > ngrok.pid

# Wait for ngrok to start
sleep 3

# Get the public URL
PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data.get('tunnels', []):
        if tunnel['proto'] == 'https':
            print(tunnel['public_url'])
            break
except:
    pass
")

if [ -z "$PUBLIC_URL" ]; then
    echo "⚠️  ngrok starting... URL will be available soon"
    echo "📋 Check ngrok dashboard: http://localhost:4040"
else
    echo "✅ ngrok tunnel active!"
    echo ""
    echo "📍 Your public URL: $PUBLIC_URL"
    echo ""
    echo "📋 Dashboard: http://localhost:4040"
    echo "🛑 Stop tunnel: kill \$(cat ngrok.pid)"
fi

