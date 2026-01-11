#!/bin/bash

# Quick Start Script for AI Workflow Automation Agent (Ollama Edition)
# This script sets up and runs the entire project

set -e

echo "🦙 AI Workflow Automation Agent - Quick Start (Ollama Edition)"
echo "=============================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}❌ Ollama is not installed${NC}"
    echo ""
    echo "Please install Ollama first:"
    echo "  macOS/Linux: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "  Windows: https://ollama.ai/download"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} Ollama is installed"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Ollama server is not running${NC}"
    echo ""
    echo "Starting Ollama server in background..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
    
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Ollama server started"
    else
        echo -e "${RED}❌ Failed to start Ollama server${NC}"
        echo "Please start manually: ollama serve"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} Ollama server is running"
fi

# Check available models
echo ""
echo -e "${BLUE}Checking installed models...${NC}"
MODELS=$(ollama list | tail -n +2 | awk '{print $1}')

echo "Available models:"
echo "$MODELS" | while read model; do
    echo "  • $model"
done

# Check for recommended models
HAS_MISTRAL=$(echo "$MODELS" | grep -c "mistral:latest" || true)
HAS_DEEPSEEK=$(echo "$MODELS" | grep -c "deepseek-coder:6.7b" || true)
HAS_GEMMA=$(echo "$MODELS" | grep -c "gemma3:270m" || true)

if [ "$HAS_MISTRAL" -eq 0 ] && [ "$HAS_DEEPSEEK" -eq 0 ] && [ "$HAS_GEMMA" -eq 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  No recommended models found${NC}"
    echo ""
    echo "Recommended models:"
    echo "  1. mistral:latest (4.4GB) - Best for production"
    echo "  2. deepseek-coder:6.7b (3.8GB) - Good for structured tasks"
    echo "  3. gemma3:270m (291MB) - Fastest, lightweight"
    echo ""
    read -p "Would you like to pull mistral:latest now? (y/n): " pull_model
    
    if [ "$pull_model" = "y" ]; then
        echo ""
        echo "Pulling mistral:latest (this may take a while)..."
        ollama pull mistral:latest
        echo -e "${GREEN}✓${NC} Model downloaded"
    fi
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python is installed"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
echo ""
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo -e "${YELLOW}Creating .env file...${NC}"
    
    # Select model
    echo ""
    echo "Select Ollama model to use:"
    echo "1) mistral:latest (RECOMMENDED)"
    echo "2) deepseek-coder:6.7b"
    echo "3) gemma3:270m"
    echo "4) Custom"
    read -p "Enter choice (1-4, default: 1): " model_choice
    
    case $model_choice in
        2)
            SELECTED_MODEL="deepseek-coder:6.7b"
            ;;
        3)
            SELECTED_MODEL="gemma3:270m"
            ;;
        4)
            read -p "Enter custom model name: " SELECTED_MODEL
            ;;
        *)
            SELECTED_MODEL="mistral:latest"
            ;;
    esac
    
    cat > .env << EOF
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=$SELECTED_MODEL
TEMPERATURE=0.1

# Storage
STORAGE_FILE=tasks_db.json
LOGS_FILE=execution_logs.json
EOF
    
    echo -e "${GREEN}✓${NC} .env file created with model: $SELECTED_MODEL"
else
    echo -e "${GREEN}✓${NC} .env file exists"
    SELECTED_MODEL=$(grep OLLAMA_MODEL .env | cut -d'=' -f2)
fi

# Menu
echo ""
echo "=================================================="
echo "What would you like to do?"
echo "=================================================="
echo "1) Run command-line examples"
echo "2) Start API server"
echo "3) Run tests"
echo "4) Check Ollama status"
echo "5) Change model"
echo "6) Exit"
echo ""

read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}Running command-line examples...${NC}"
        echo -e "${BLUE}Using model: $SELECTED_MODEL${NC}"
        echo ""
        python workflow_agent.py
        ;;
    2)
        echo ""
        echo -e "${YELLOW}Starting API server...${NC}"
        echo -e "${BLUE}Using model: $SELECTED_MODEL${NC}"
        echo ""
        echo "Server will start on http://localhost:8000"
        echo "API docs: http://localhost:8000/docs"
        echo "Health check: http://localhost:8000/health"
        echo "Press Ctrl+C to stop"
        echo ""
        sleep 2
        python webhook_server.py
        ;;
    3)
        echo ""
        echo -e "${YELLOW}Running test suite...${NC}"
        echo ""
        
        # Run server in background
        python webhook_server.py > /dev/null 2>&1 &
        SERVER_PID=$!
        
        # Wait for server to start
        sleep 3
        
        # Run tests
        python test_agent.py
        
        # Kill server
        kill $SERVER_PID 2>/dev/null
        ;;
    4)
        echo ""
        echo -e "${BLUE}Ollama Status:${NC}"
        echo "=================================================="
        
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Server: Running on http://localhost:11434"
        else
            echo -e "${RED}✗${NC} Server: Not running"
        fi
        
        echo ""
        echo "Installed models:"
        ollama list
        
        echo ""
        echo "Current configuration:"
        cat .env
        ;;
    5)
        echo ""
        echo "Available models:"
        ollama list
        echo ""
        read -p "Enter model name to use: " new_model
        
        # Update .env
        sed -i.bak "s/OLLAMA_MODEL=.*/OLLAMA_MODEL=$new_model/" .env
        rm .env.bak 2>/dev/null || true
        
        echo -e "${GREEN}✓${NC} Model changed to: $new_model"
        echo "Restart the application to use the new model"
        ;;
    6)
        echo ""
        echo "Goodbye! 👋"
        exit 0
        ;;
    *)
        echo ""
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Done!${NC}"