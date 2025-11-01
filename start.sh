#!/bin/bash

echo "🚀 Starting Walkability Network Builder"
echo "======================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it and try again."
    exit 1
fi

echo "✓ Docker is running"
echo "✓ docker-compose is available"

# Start the services
echo ""
echo "🐳 Starting Docker services..."
docker-compose up --build -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo ""
echo "🔍 Checking service status..."
if docker-compose ps | grep -q "Up"; then
    echo "✓ Services are running"
else
    echo "❌ Some services failed to start"
    docker-compose logs
    exit 1
fi

# Initialize database
echo ""
echo "🗄️  Initializing database..."
docker-compose exec backend flask db upgrade

echo ""
echo "🎉 System is ready!"
echo ""
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo ""
echo "To stop the system, run: docker-compose down"
echo "To view logs, run: docker-compose logs -f"
