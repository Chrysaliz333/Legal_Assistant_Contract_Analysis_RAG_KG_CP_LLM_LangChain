#!/bin/bash

# Demo Setup and Execution Script
# This script checks dependencies and runs the contract analysis demo

set -e  # Exit on error

echo "=================================="
echo "Contract Analysis Demo Setup"
echo "=================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated"
    echo ""
fi

# Check Python version
echo "Checking Python version..."
python3 --version || {
    echo "❌ Python 3 not found. Please install Python 3.8+."
    exit 1
}
echo "✅ Python 3 found"
echo ""

# Check if ANTHROPIC_API_KEY is set
echo "Checking ANTHROPIC_API_KEY..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set"
    echo ""
    echo "Please set your API key:"
    echo "  export ANTHROPIC_API_KEY='your-key-here'"
    echo ""
    echo "Or create a .env file with:"
    echo "  ANTHROPIC_API_KEY=your-key-here"
    exit 1
fi
echo "✅ ANTHROPIC_API_KEY found"
echo ""

# Check if database exists
echo "Checking database..."
if [ ! -f "legal_assistant.db" ]; then
    echo "⚠️  Database not found. Creating it now..."
    cd "Supply Agreement Schema"
    python3 setup_sqlite.py
    cd ..
    echo "✅ Database created"
else
    echo "✅ Database exists"
fi
echo ""

# Check required Python packages
echo "Checking Python dependencies..."

MISSING_DEPS=()

python3 -c "import anthropic" 2>/dev/null || MISSING_DEPS+=("anthropic")
python3 -c "import langchain" 2>/dev/null || MISSING_DEPS+=("langchain")
python3 -c "import langchain_anthropic" 2>/dev/null || MISSING_DEPS+=("langchain-anthropic")
python3 -c "import langgraph" 2>/dev/null || MISSING_DEPS+=("langgraph")
python3 -c "import textblob" 2>/dev/null || MISSING_DEPS+=("textblob")

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "⚠️  Missing dependencies: ${MISSING_DEPS[*]}"
    echo ""
    echo "Installing missing packages..."
    pip install anthropic langchain langchain-anthropic langgraph textblob
    echo "✅ Dependencies installed"
else
    echo "✅ All dependencies found"
fi
echo ""

# Run demo
echo "=================================="
echo "Running Contract Analysis Demo"
echo "=================================="
echo ""

if [ "$1" == "--stream" ]; then
    echo "Running in STREAMING mode..."
    python3 demo_workflow.py --stream
else
    echo "Running in STANDARD mode..."
    echo "(Use './run_demo.sh --stream' for real-time updates)"
    echo ""
    python3 demo_workflow.py
fi
