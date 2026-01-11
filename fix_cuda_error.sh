#!/bin/bash

# Quick Fix Script for CUDA Error
# Fixes "llama runner process has terminated: CUDA error (status code: 500)"

set -e

echo "🔧 CUDA Error Fix Script"
echo "======================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Stop Ollama if running
echo -e "${YELLOW}Stopping Ollama...${NC}"
pkill ollama 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓${NC} Ollama stopped"
echo ""

# Check if gemma3 is installed
echo -e "${YELLOW}Checking for lightweight model...${NC}"
if ollama list | grep -q "gemma3:270m"; then
    echo -e "${GREEN}✓${NC} gemma3:270m already installed"
else
    echo -e "${YELLOW}Pulling gemma3:270m (fastest model for CPU)...${NC}"
    OLLAMA_NUM_GPU=0 ollama serve > /dev/null 2>&1 &
    OLLAMA_PID=$!
    sleep 3
    ollama pull gemma3:270m
    kill $OLLAMA_PID 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✓${NC} Model downloaded"
fi
echo ""

# Update .env file
echo -e "${YELLOW}Updating .env configuration...${NC}"
if [ -f ".env" ]; then
    # Backup existing .env
    cp .env .env.backup
    echo -e "${GREEN}✓${NC} Backed up existing .env to .env.backup"
fi

cat > .env << EOF
# Ollama Configuration (CPU Mode - Fixed CUDA Error)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:270m
OLLAMA_NUM_GPU=0
TEMPERATURE=0.1
OLLAMA_TIMEOUT=120

# Storage
STORAGE_FILE=tasks_db.json
LOGS_FILE=execution_logs.json
EOF

echo -e "${GREEN}✓${NC} Updated .env with CPU-only configuration"
echo ""

# Start Ollama with CPU mode
echo -e "${YELLOW}Starting Ollama in CPU-only mode...${NC}"
echo "This will run in the background..."
OLLAMA_NUM_GPU=0 ollama serve > ollama.log 2>&1 &
OLLAMA_PID=$!
echo $OLLAMA_PID > ollama.pid

# Wait for Ollama to be ready
echo -n "Waiting for Ollama to start"
for i in {1..15}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✓${NC} Ollama is ready!"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Test the fix
echo -e "${YELLOW}Testing the fix...${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Ollama API is responding"
    
    # Quick test inference
    echo -e "${YELLOW}Testing model inference...${NC}"
    RESPONSE=$(ollama run gemma3:270m "Hello" 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Model inference working!"
    else
        echo -e "${RED}✗${NC} Model inference failed"
        echo "Response: $RESPONSE"
    fi
else
    echo -e "${RED}✗${NC} Ollama is not responding"
    echo "Check ollama.log for details"
fi

echo ""
echo "======================================"
echo -e "${GREEN}Fix Applied!${NC}"
echo "======================================"
echo ""
echo "Configuration:"
echo "  • Model: gemma3:270m (fastest on CPU)"
echo "  • GPU: Disabled (CPU only)"
echo "  • Timeout: 120 seconds"
echo ""
echo "Ollama is now running in background (PID: $OLLAMA_PID)"
echo "  • Logs: ollama.log"
echo "  • Stop: kill \$(cat ollama.pid)"
echo ""
echo "Next steps:"
echo "  1. Test the agent: python workflow_agent.py"
echo "  2. Start API server: python webhook_server.py"
echo ""
echo "If you still get errors, see: CUDA_TROUBLESHOOTING.md"
echo ""
