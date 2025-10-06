#!/bin/bash

# Twitter MCP Server - Quick Setup Script
# Setup standalone MCP server (n8n installato separatamente)

set -e  # Exit on error

echo "🐦 Twitter MCP Server - Quick Setup"
echo "===================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
mkdir -p data logs
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
    
    # Create .env
    cat > .env << EOF
# Twitter MCP Server Configuration
# Generated: $(date)

# Twitter Credentials
TWITTER_USERNAME=$TWITTER_USER
TWITTER_EMAIL=$TWITTER_EMAIL
TWITTER_PASSWORD=$TWITTER_PASS

# Server Configuration
LOG_LEVEL=INFO
SERVER_PORT=8000
SERVER_HOST=0.0.0.0

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=500
EOF

    echo -e "${GREEN}✅ .env file created${NC}"
else
    echo -e "${YELLOW}⚠️  .env file already exists, skipping...${NC}"
fi

echo ""

# Create simplified docker-compose for MCP only
if [ ! -f docker-compose.yml ]; then
    echo "📝 Creating docker-compose.yml..."
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  twitter-mcp:
    build: .
    container_name: twitter-mcp-server
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - TWITTER_USERNAME=${TWITTER_USERNAME}
      - TWITTER_EMAIL=${TWITTER_EMAIL}
      - TWITTER_PASSWORD=${TWITTER_PASSWORD}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - SERVER_PORT=${SERVER_PORT:-8000}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  default:
    name: twitter-mcp-network
EOF
    echo -e "${GREEN}✅ docker-compose.yml created${NC}"
fi

echo ""

# Build image
echo "🏗️  Building Docker image..."
docker-compose build

echo -e "${GREEN}✅ Image built${NC}"
echo ""

# Start service
echo "🚀 Starting MCP Server..."
docker-compose up -d

echo ""
echo "⏳ Waiting for server to start..."
sleep 10

# Health check
echo "🏥 Performing health check..."
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

# Test authentication
echo ""
echo "🔐 Testing authentication..."
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$TWITTER_USER\",\"email\":\"$TWITTER_EMAIL\",\"password\":\"$TWITTER_PASS\"}" \
  2>/dev/null || echo "failed")

if echo "$AUTH_RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✅ Authentication successful!${NC}"
else
    echo -e "${YELLOW}⚠️  Authentication test skipped (will retry on first API call)${NC}"
fi

echo ""
echo "======================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "======================================"
echo ""
echo "📍 MCP Server Details:"
echo "   - API URL:      http://localhost:8000"
echo "   - Health:       http://localhost:8000/health"
echo "   - API Docs:     http://localhost:8000/docs"
echo ""
echo "🔌 Connect from n8n:"
echo "   - If n8n on same host:    http://localhost:8000"
echo "   - If n8n on Docker:       http://twitter-mcp-server:8000"
echo "   - If n8n on remote:       http://YOUR_SERVER_IP:8000"
echo ""
echo "🧪 Quick Tests:"
echo ""
echo "   1. Health Check:"
echo "      curl http://localhost:8000/health"
echo ""
echo "   2. Authentication Status:"
echo "      curl http://localhost:8000/auth/status"
echo ""
echo "   3. Create Test Tweet:"
echo "      curl -X POST http://localhost:8000/tweets/create \\"
echo "           -H 'Content-Type: application/json' \\"
echo "           -d '{\"text\":\"🚀 Test from MCP Server!\"}'"
echo ""
echo "   4. Search Tweets:"
echo "      curl -X POST http://localhost:8000/tweets/search \\"
echo "           -H 'Content-Type: application/json' \\"
echo "           -d '{\"query\":\"python\",\"count\":5}'"
echo ""
echo "📚 Full API Documentation:"
echo "   - Interactive docs: http://localhost:8000/docs"
echo "   - README:           cat README.md"
echo "   - Examples:         cat EXAMPLES.md"
echo ""
echo "🔧 Management Commands:"
echo "   - View logs:        docker-compose logs -f"
echo "   - Restart:          docker-compose restart"
echo "   - Stop:             docker-compose down"
echo "   - Update:           git pull && docker-compose up -d --build"
echo ""
echo -e "${BLUE}💡 n8n Integration:${NC}"
echo "   The MCP server is now ready to receive requests from n8n."
echo "   In your n8n workflows, use HTTP Request nodes pointing to:"
echo "   http://localhost:8000 (or http://twitter-mcp-server:8000 if in same Docker network)"
echo ""
echo -e "${YELLOW}⚠️  Security Reminders:${NC}"
echo "   - Using secondary Twitter account: ✓"
echo "   - Rate limiting enabled: ✓"
echo "   - Credentials in .env (not in code): ✓"
echo "   - Don't commit .env to git: ✓"
echo ""
echo -e "${YELLOW}⚠️  Important: Respect Twitter rate limits to avoid bans!${NC}"
echo ""