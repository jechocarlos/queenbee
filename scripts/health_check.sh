#!/bin/bash
# Quick system health check for QueenBee

set -e

echo "🐝 QueenBee System Health Check"
echo "================================"
echo ""

# Check Python
echo "✓ Checking Python..."
python3 --version || { echo "❌ Python not found"; exit 1; }
echo ""

# Check Docker
echo "✓ Checking Docker..."
docker --version || { echo "❌ Docker not found"; exit 1; }
echo ""

# Check if containers are running
echo "✓ Checking Docker containers..."
if docker ps | grep -q "queenbee-postgres"; then
    echo "  ✓ PostgreSQL is running"
else
    echo "  ❌ PostgreSQL is not running"
    echo "     Run: docker-compose -f docker-compose.local.yml up -d"
fi

if docker ps | grep -q "queenbee-ollama"; then
    echo "  ✓ Ollama is running"
else
    echo "  ❌ Ollama is not running"
    echo "     Run: docker-compose -f docker-compose.local.yml up -d"
fi
echo ""

# Check Ollama health
echo "✓ Checking Ollama API..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "  ✓ Ollama API is accessible"
    
    # Check for model
    if docker exec queenbee-ollama ollama list | grep -q "llama3.1:8b"; then
        echo "  ✓ Model llama3.1:8b is available"
    else
        echo "  ⚠️  Model llama3.1:8b not found"
        echo "     Run: docker exec -it queenbee-ollama ollama pull llama3.1:8b"
    fi
else
    echo "  ❌ Ollama API is not accessible"
fi
echo ""

# Check PostgreSQL health
echo "✓ Checking PostgreSQL..."
if docker exec queenbee-postgres pg_isready -U queenbee > /dev/null 2>&1; then
    echo "  ✓ PostgreSQL is ready"
    
    # Check if database exists
    if docker exec queenbee-postgres psql -U queenbee -lqt | cut -d \| -f 1 | grep -qw queenbee; then
        echo "  ✓ Database 'queenbee' exists"
        
        # Check if tables exist
        TABLE_COUNT=$(docker exec queenbee-postgres psql -U queenbee -d queenbee -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")
        if [ "$TABLE_COUNT" -gt "0" ]; then
            echo "  ✓ Database has $TABLE_COUNT tables (migrations applied)"
        else
            echo "  ⚠️  Database has no tables"
            echo "     Run: python scripts/migrate.py"
        fi
    else
        echo "  ⚠️  Database 'queenbee' not found"
    fi
else
    echo "  ❌ PostgreSQL is not ready"
fi
echo ""

# Check configuration
echo "✓ Checking configuration..."
if [ -f "config.yaml" ]; then
    echo "  ✓ config.yaml exists"
else
    echo "  ❌ config.yaml not found"
fi

if [ -f ".env" ]; then
    echo "  ✓ .env exists"
else
    echo "  ⚠️  .env not found (copy from .env.example)"
fi
echo ""

# Check Python dependencies
echo "✓ Checking Python dependencies..."
if python3 -c "import queenbee" 2>/dev/null; then
    echo "  ✓ QueenBee package installed"
else
    echo "  ❌ QueenBee package not installed"
    echo "     Run: pip install -e ."
fi
echo ""

echo "================================"
echo "Health check complete!"
echo ""
echo "To start QueenBee:"
echo "  queenbee"
echo ""
echo "Or:"
echo "  python -m queenbee.cli.main"
