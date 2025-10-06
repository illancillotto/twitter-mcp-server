# ⚡ Quick Reference Guide

Comandi rapidi e troubleshooting per Twitter MCP Server.

---

## 🚀 Quick Start Commands

```bash
# Setup completo (prima volta)
chmod +x setup.sh && ./setup.sh

# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart single service
docker-compose restart twitter-mcp

# View logs
docker-compose logs -f twitter-mcp

# Check status
docker-compose ps
```

---

## 📡 API Quick Test

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"USER","email":"EMAIL","password":"PASS"}'

# Create tweet
curl -X POST http://localhost:8000/tweets/create \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello Twitter! 🚀"}'

# Search tweets
curl -X POST http://localhost:8000/tweets/search \
  -H "Content-Type: application/json" \
  -d '{"query":"python","count":10}'

# Get user profile
curl -X POST http://localhost:8000/users/profile \
  -H "Content-Type: application/json" \
  -d '{"username":"elonmusk"}'
```

---

## 🐛 Common Issues & Fixes

### Issue: "Connection refused"

```bash
# Check if container is running
docker ps | grep twitter-mcp

# Restart container
docker-compose restart twitter-mcp

# Check logs for errors
docker-compose logs twitter-mcp | tail -50
```

### Issue: "Login failed"

```bash
# Reset cookies
rm data/cookies.json

# Check credentials in .env
cat .env | grep TWITTER

# Test login directly
docker-compose exec twitter-mcp python -c "
from mcp_server.twitter_client import TwitterClient
import asyncio
client = TwitterClient()
asyncio.run(client.login('USER', 'EMAIL', 'PASS'))
"
```

### Issue: "Rate limit exceeded"

```bash
# Check rate limit stats
curl http://localhost:8000/stats/rate-limit

# Wait 15 minutes
sleep 900

# Reduce rate in .env
RATE_LIMIT_PER_MINUTE=20
docker-compose restart twitter-mcp
```

### Issue: "Out of memory"

```bash
# Check memory usage
docker stats twitter-mcp

# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G

# Restart
docker-compose up -d twitter-mcp
```

---

## 🔍 Debugging Commands

```bash
# Enter container shell
docker-compose exec twitter-mcp /bin/bash

# Check Python version
docker-compose exec twitter-mcp python --version

# List installed packages
docker-compose exec twitter-mcp pip list

# Test imports
docker-compose exec twitter-mcp python -c "import twikit; print(twikit.__version__)"

# Check environment variables
docker-compose exec twitter-mcp env | grep TWITTER

# Network test
docker-compose exec twitter-mcp ping -c 3 twitter.com
```

---

## 📊 Monitoring Commands

```bash
# Real-time logs
docker-compose logs -f --tail=100 twitter-mcp

# Container stats
docker stats twitter-mcp --no-stream

# Disk usage
docker system df

# Check all containers
docker-compose ps

# View resource limits
docker inspect twitter-mcp | grep -A 10 Resources
```

---

## 🗄️ Database Commands

```bash
# PostgreSQL backup
docker exec postgres-prod pg_dump -U user dbname > backup.sql

# Restore backup
cat backup.sql | docker exec -i postgres-prod psql -U user dbname

# Connect to DB
docker-compose exec postgres psql -U user -d dbname

# List tables
docker-compose exec postgres psql -U user -d dbname -c "\dt"

# Query data
docker-compose exec postgres psql -U user -d dbname -c "SELECT * FROM tweets LIMIT 10;"
```

---

## 🔄 Update Commands

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker-compose build twitter-mcp

# Update without downtime
docker-compose up -d --no-deps --build twitter-mcp

# Rollback to previous version
git checkout HEAD~1
docker-compose up -d --build twitter-mcp
```

---

## 🧹 Cleanup Commands

```bash
# Remove stopped containers
docker-compose rm

# Clean old images
docker image prune -a

# Clean volumes (CAUTION: data loss!)
docker volume prune

# Full cleanup
docker system prune -a --volumes

# Clean logs
truncate -s 0 logs/*.log
```

---

## 📦 Backup & Restore

```bash
# Quick backup
tar -czf backup-$(date +%Y%m%d).tar.gz data/ .env docker-compose.yml

# Backup database
docker exec postgres pg_dump -U user dbname | gzip > db-backup.sql.gz

# Restore database
gunzip < db-backup.sql.gz | docker exec -i postgres psql -U user dbname

# Copy data out
docker cp twitter-mcp:/app/data ./backup-data

# Copy data in
docker cp ./backup-data twitter-mcp:/app/data
```

---

## 🔐 Security Commands

```bash
# Generate strong password
openssl rand -base64 32

# Check open ports
sudo netstat -tulpn | grep LISTEN

# View firewall status
sudo ufw status

# Check SSL cert expiry
echo | openssl s_client -servername api.yourdomain.com -connect api.yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# Scan for vulnerabilities
docker scan twitter-mcp:latest
```

---

## 🌐 Network Commands

```bash
# List networks
docker network ls

# Inspect network
docker network inspect twitter-network

# Test connectivity
docker-compose exec twitter-mcp ping n8n

# Check DNS
docker-compose exec twitter-mcp nslookup twitter.com

# Test port
docker-compose exec twitter-mcp nc -zv twitter-mcp 8000
```

---

## 📈 Performance Tuning

```bash
# Check slow queries (PostgreSQL)
docker-compose exec postgres psql -U user -d dbname -c "
SELECT query, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;"

# Optimize database
docker-compose exec postgres psql -U user -d dbname -c "VACUUM ANALYZE;"

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Restart for memory cleanup
docker-compose restart twitter-mcp
```

---

## 🧪 Testing Commands

```bash
# Run tests
docker-compose exec twitter-mcp pytest tests/

# Run with coverage
docker-compose exec twitter-mcp pytest --cov=mcp_server tests/

# Run specific test
docker-compose exec twitter-mcp pytest tests/test_server.py::TestHealthEndpoint

# Run integration tests
docker-compose exec twitter-mcp pytest -m integration

# Load testing
ab -n 1000 -c 10 http://localhost:8000/health
```

---

## 📝 Useful Aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Twitter MCP aliases
alias mcp-start='docker-compose up -d'
alias mcp-stop='docker-compose down'
alias mcp-logs='docker-compose logs -f twitter-mcp'
alias mcp-restart='docker-compose restart twitter-mcp'
alias mcp-shell='docker-compose exec twitter-mcp /bin/bash'
alias mcp-status='docker-compose ps'
alias mcp-health='curl -s http://localhost:8000/health | jq'
alias mcp-backup='tar -czf backup-$(date +%Y%m%d).tar.gz data/ .env'
```

---

## 🎯 One-liners

```bash
# Find large log files
find logs/ -type f -size +100M -exec ls -lh {} \;

# Count total tweets posted
grep "Tweet created" logs/*.log | wc -l

# Most active hours
grep "Tweet created" logs/*.log | cut -d' ' -f2 | cut -d':' -f1 | sort | uniq -c | sort -rn

# Error rate last hour
grep ERROR logs/*.log | tail -60 | wc -l

# Check if any container restarted
docker ps -a --filter "status=restarted"

# Kill zombie processes
docker-compose exec twitter-mcp ps aux | grep defunct | awk '{print $2}' | xargs kill -9

# Generate random test tweet
echo "Test tweet $(date +%s) #testing" | curl -X POST http://localhost:8000/tweets/create -H "Content-Type: application/json" -d @-
```

---

## 🚨 Emergency Procedures

### Complete Service Restart

```bash
# Save current state
docker-compose logs twitter-mcp > emergency-logs.txt

# Full restart
docker-compose down
docker system prune -f
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

### Rollback to Last Working Version

```bash
# Find last working commit
git log --oneline -n 10

# Checkout
git checkout <commit-hash>

# Rebuild
docker-compose build twitter-mcp
docker-compose up -d twitter-mcp
```

### Data Recovery

```bash
# Stop service
docker-compose stop twitter-mcp

# Copy current data
cp -r data/ data-backup-$(date +%Y%m%d)

# Restore from backup
cp -r /backups/latest/* data/

# Restart
docker-compose start twitter-mcp
```

---

## 📞 Getting Help

```bash
# Check version
docker-compose exec twitter-mcp python -c "import mcp_server; print(mcp_server.__version__)"

# Generate diagnostic report
cat <<EOF > diagnostic-report.txt
Date: $(date)
OS: $(uname -a)
Docker: $(docker --version)
Python: $(docker-compose exec twitter-mcp python --version)
Containers: $(docker-compose ps)
Logs: $(docker-compose logs twitter-mcp --tail=50)
EOF

# Share diagnostic report with support
cat diagnostic-report.txt
```

---

## 📚 Useful Links

- **Documentation**: `/docs`
- **Health Check**: `http://localhost:8000/health`
- **n8n Dashboard**: `http://localhost:5678`
- **API Docs**: `http://localhost:8000/docs` (FastAPI auto-docs)

---

**Keep this handy! Bookmark for quick reference 🔖**
