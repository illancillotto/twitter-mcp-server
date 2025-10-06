#!/bin/bash

# Twitter MCP Server - Quick Setup Script
# Automatizza la configurazione iniziale

set -e  # Exit on error

echo "🐦 Twitter MCP Server - Quick Setup"
echo "===================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
echo "📦 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found!${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found!${NC}"
    echo "Please install Docker Compose"
    exit 1
fi

echo -e "${GREEN}✅ Docker OK${NC}"
echo ""

# Create directories
echo "📁 Creating directories..."
mkdir -p data logs workflows
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Setup .env
if [ ! -f .env ]; then
    echo "⚙️  Setting up .env file..."
    
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Use a SECONDARY Twitter account!${NC}"
    echo -e "${YELLOW}   Do NOT use your main account!${NC}"
    echo ""
    
    read -p "Twitter Username: " TWITTER_USER
    read -p "Twitter Email: " TWITTER_EMAIL
    read -sp "Twitter Password: " TWITTER_PASS
    echo ""
    echo ""
    read -p "n8n Username (default: admin): " N8N_USER
    N8N_USER=${N8N_USER:-admin}
    read -sp "n8n Password: " N8N_PASS
    echo ""
    echo ""
    
    # Create .env
    cat > .env << EOF
# Twitter MCP Server Configuration
# Generated: $(date)

# Twitter Credentials
TWITTER_USERNAME=$TWITTER_USER
TWITTER_EMAIL=$TWITTER_EMAIL
TWITTER_PASSWORD=$TWITTER_PASS

# n8n Configuration
N8N_USER=$N8N_USER
N8N_PASSWORD=$N8N_PASS

# Server Configuration
LOG_LEVEL=INFO
SERVER_PORT=8000

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=500
EOF

    echo -e "${GREEN}✅ .env file created${NC}"
else
    echo -e "${YELLOW}⚠️  .env file already exists, skipping...${NC}"
fi

echo ""

# Build images
echo "🏗️  Building Docker images..."
docker-compose build

echo -e "${GREEN}✅ Images built${NC}"
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Health check
echo "🏥 Health check..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ MCP Server is healthy!${NC}"
        break
    fi
    
    if [ $i -eq 10 ]; then
        echo -e "${RED}❌ MCP Server not responding${NC}"
        echo "Check logs with: docker-compose logs twitter-mcp"
        exit 1
    fi
    
    echo "   Attempt $i/10..."
    sleep 3
done

echo ""
echo "======================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "======================================"
echo ""
echo "📍 Access Points:"
echo "   - MCP Server:  http://localhost:8000"
echo "   - n8n:         http://localhost:5678"
echo "   - Health:      http://localhost:8000/health"
echo ""
echo "🔑 n8n Credentials:"
echo "   - Username: $N8N_USER"
echo "   - Password: (the one you entered)"
echo ""
echo "📖 Next Steps:"
echo "   1. Test health: curl http://localhost:8000/health"
echo "   2. Authenticate: curl -X POST http://localhost:8000/auth/login \\"
echo "                       -H 'Content-Type: application/json' \\"
echo "                       -d '{\"username\":\"$TWITTER_USER\",...}'"
echo "   3. Open n8n:    http://localhost:5678"
echo "   4. Import workflow from: workflows/n8n_twitter_workflow.json"
echo ""
echo "📚 Documentation: See README.md"
echo ""
echo "🐛 Troubleshooting:"
echo "   - View logs:    docker-compose logs -f twitter-mcp"
echo "   - Restart:      docker-compose restart"
echo "   - Stop:         docker-compose down"
echo ""
echo -e "${YELLOW}⚠️  Remember: Use rate limiting to avoid Twitter ban!${NC}"
echo ""
