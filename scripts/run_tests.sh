#!/usr/bin/env bash
# Run unit tests for QueenBee

set -e

echo "🐝 QueenBee Test Suite"
echo "======================"
echo ""

# Check if pytest is installed
if ! python -m pytest --version &> /dev/null; then
    echo "❌ pytest not found. Installing dev dependencies..."
    pip install -e ".[dev]"
fi

# Run tests
echo "Running unit tests..."
echo ""

python -m pytest tests/ -v "$@"

echo ""
echo "✅ Test suite complete!"
