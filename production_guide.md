# 🚀 Production Deployment Guide

Guida completa per il deploy in produzione del Twitter MCP Server.

## 📋 Indice

1. [Requisiti Pre-Deploy](#requisiti-pre-deploy)
2. [Architettura Production](#architettura-production)
3. [Security Hardening](#security-hardening)
4. [Deployment Options](#deployment-options)
5. [Monitoring & Observability](#monitoring--observability)
6. [Backup & Disaster Recovery](#backup--disaster-recovery)
7. [Scaling](#scaling)
8. [Maintenance](#maintenance)

---

## 🔐 Requisiti Pre-Deploy

### Checklist Pre-Production

- [ ] **Account Twitter Secondario Configurato**
  - Account dedicato per automazione
  - 2FA configurato (post-setup)
  - Email e telefono verificati

- [ ] **Infrastruttura**
  - Server Linux (Ubuntu 22.04+ / Debian 11+)
  - Docker e Docker Compose installati
  - Certificato SSL (Let's Encrypt)
  - Dominio configurato

- [ ] **Security**
  - Firewall configurato (UFW/iptables)
  - Fail2ban installato
  - SSH key-based auth
  - User non-root configurato

- [ ] **Monitoring**
  - Uptime monitoring setup
  - Log aggregation configurato
  - Alert system attivo

---

## 🏗️ Architettura Production

### Stack Completo

```
┌─────────────────────────────────────────────┐
│              Load Balancer                  │
│           (Nginx/Traefik)                   │
└────────────────┬────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────┐              ┌────▼─────┐
│  n8n   │              │   MCP    │
│ Server │◄────────────►│  Server  │
└────────┘              └──────────┘
    │                         │
    │                         │
┌───▼─────────────────────────▼────┐
│         PostgreSQL DB            │
│    (n8n data + analytics)        │
└──────────────────────────────────┘
    │
┌───▼──────────────────────────────┐
│           Redis                  │
│  (rate limiting + cache)         │
└──────────────────────────────────┘
```

### Docker Compose Production

```yaml
version: '3.8'

services:
  # Reverse Proxy
  traefik:
    image: traefik:v2.10
    container_name: traefik
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt
    networks:
      - web
    restart: unless-stopped

  # Twitter MCP Server
  twitter-mcp:
    build: .
    container_name: twitter-mcp-prod
    environment:
      - TWITTER_USERNAME=${TWITTER_USERNAME}
      - TWITTER_EMAIL=${TWITTER_EMAIL}
      - TWITTER_PASSWORD=${TWITTER_PASSWORD}
      - LOG_LEVEL=INFO
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - web
      - backend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.twitter-mcp.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.twitter-mcp.entrypoints=websecure"
      - "traefik.http.routers.twitter-mcp.tls.certresolver=letsencrypt"
      - "traefik.http.services.twitter-mcp.loadbalancer.server.port=8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # n8n
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n-prod
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=${POSTGRES_DB}
      - DB_POSTGRESDB_USER=${POSTGRES_USER}
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - N8N_HOST=n8n.yourdomain.com
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.yourdomain.com/
      - GENERIC_TIMEZONE=Europe/Rome
      - EXECUTIONS_DATA_PRUNE=true
      - EXECUTIONS_DATA_MAX_AGE=168
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - web
      - backend
    restart: unless-stopped
    depends_on:
      - postgres
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.n8n.rule=Host(`n8n.yourdomain.com`)"
      - "traefik.http.routers.n8n.entrypoints=websecure"
      - "traefik.http.routers.n8n.tls.certresolver=letsencrypt"

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    container_name: postgres-prod
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - backend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M

  # Redis
  redis:
    image: redis:7-alpine
    container_name: redis-prod
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - backend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M

  # Prometheus (Monitoring)
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - backend
    restart: unless-stopped

  # Grafana (Dashboards)
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_SERVER_ROOT_URL=https://grafana.yourdomain.com
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - web
      - backend
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.grafana.rule=Host(`grafana.yourdomain.com`)"
      - "traefik.http.routers.grafana.entrypoints=websecure"
      - "traefik.http.routers.grafana.tls.certresolver=letsencrypt"

networks:
  web:
    external: true
  backend:
    internal: true

volumes:
  n8n_data:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

---

## 🔒 Security Hardening

### 1. Firewall Configuration

```bash
# UFW Setup
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Rate limiting SSH
sudo ufw limit ssh/tcp
```

### 2. Fail2Ban Setup

```bash
# Install
sudo apt install fail2ban

# Create jail for MCP
sudo nano /etc/fail2ban/jail.local
```

```ini
[twitter-mcp]
enabled = true
port = 8000
filter = twitter-mcp
logpath = /path/to/logs/*.log
maxretry = 5
bantime = 3600
```

### 3. Environment Variables Security

```bash
# Usa secrets management
# Option 1: Docker Secrets
echo "your_password" | docker secret create twitter_password -

# Option 2: Vault (HashiCorp)
vault kv put secret/twitter username=user password=pass

# Option 3: AWS Secrets Manager
aws secretsmanager create-secret \
  --name twitter-credentials \
  --secret-string '{"username":"user","password":"pass"}'
```

### 4. HTTPS Only

```yaml
# Traefik middleware per redirect HTTP → HTTPS
labels:
  - "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"
  - "traefik.http.routers.twitter-mcp-http.middlewares=redirect-to-https"
```

### 5. Rate Limiting (Traefik)

```yaml
labels:
  - "traefik.http.middlewares.rate-limit.ratelimit.average=100"
  - "traefik.http.middlewares.rate-limit.ratelimit.burst=50"
  - "traefik.http.routers.twitter-mcp.middlewares=rate-limit"
```

---

## 🚢 Deployment Options

### Option 1: VPS (DigitalOcean, Linode, Vultr)

```bash
# 1. Provisiona server
# 2. Initial setup
ssh root@your-server-ip

# 3. Setup user
adduser deploy
usermod -aG sudo deploy
usermod -aG docker deploy

# 4. Clone repo
cd /opt
git clone https://github.com/your-repo/twitter-mcp-server.git
cd twitter-mcp-server

# 5. Configure
cp .env.example .env
nano .env  # Edit credentials

# 6. Deploy
docker-compose -f docker-compose.prod.yml up -d

# 7. Verify
docker-compose ps
curl https://api.yourdomain.com/health
```

### Option 2: AWS ECS

```bash
# 1. Build e push image
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin YOUR_ECR_URL
docker build -t twitter-mcp .
docker tag twitter-mcp:latest YOUR_ECR_URL/twitter-mcp:latest
docker push YOUR_ECR_URL/twitter-mcp:latest

# 2. Create ECS task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-def.json

# 3. Create service
aws ecs create-service --cluster twitter-mcp-cluster --service-name twitter-mcp --task-definition twitter-mcp:1 --desired-count 2
```

### Option 3: Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twitter-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: twitter-mcp
  template:
    metadata:
      labels:
        app: twitter-mcp
    spec:
      containers:
      - name: twitter-mcp
        image: your-registry/twitter-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: TWITTER_USERNAME
          valueFrom:
            secretKeyRef:
              name: twitter-secrets
              key: username
        resources:
          limits:
            memory: "512Mi"
            cpu: "1000m"
          requests:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## 📊 Monitoring & Observability

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'twitter-mcp'
    static_configs:
      - targets: ['twitter-mcp:8000']
    metrics_path: '/metrics'

  - job_name: 'n8n'
    static_configs:
      - targets: ['n8n:5678']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "Twitter MCP Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(http_requests_total[5m])"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
        }]
      },
      {
        "title": "Response Time",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
        }]
      }
    ]
  }
}
```

### Log Aggregation (ELK Stack)

```bash
# Install Filebeat
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.0.0-amd64.deb
sudo dpkg -i filebeat-8.0.0-amd64.deb

# Configure
sudo nano /etc/filebeat/filebeat.yml
```

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /opt/twitter-mcp-server/logs/*.log
  json.keys_under_root: true

output.elasticsearch:
  hosts: ["https://your-elk-host:9200"]
  username: "elastic"
  password: "your-password"
```

---

## 💾 Backup & Disaster Recovery

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/twitter-mcp"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
docker exec postgres-prod pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > ${BACKUP_DIR}/postgres_${DATE}.sql.gz

# Backup data directory
tar -czf ${BACKUP_DIR}/data_${DATE}.tar.gz /opt/twitter-mcp-server/data

# Backup configs
tar -czf ${BACKUP_DIR}/configs_${DATE}.tar.gz /opt/twitter-mcp-server/.env /opt/twitter-mcp-server/docker-compose.prod.yml

# Upload to S3
aws s3 sync ${BACKUP_DIR} s3://your-backup-bucket/twitter-mcp/

# Cleanup old backups (keep last 30 days)
find ${BACKUP_DIR} -type f -mtime +30 -delete

echo "Backup completed: ${DATE}"
```

### Restore Procedure

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore PostgreSQL
gunzip < ${BACKUP_FILE} | docker exec -i postgres-prod psql -U ${POSTGRES_USER} ${POSTGRES_DB}

# Restore data
tar -xzf data_backup.tar.gz -C /

# Restart services
docker-compose -f docker-compose.prod.yml up -d

echo "Restore completed"
```

### Cron Schedule

```cron
# Daily backup at 2 AM
0 2 * * * /opt/twitter-mcp-server/scripts/backup.sh

# Weekly full backup Sunday 3 AM
0 3 * * 0 /opt/twitter-mcp-server/scripts/backup-full.sh
```

---

## 📈 Scaling

### Horizontal Scaling

```yaml
# Docker Swarm
docker service create \
  --name twitter-mcp \
  --replicas 3 \
  --publish 8000:8000 \
  --env-file .env \
  twitter-mcp:latest

# Auto-scaling con constraints
docker service update \
  --replicas-max-per-node 1 \
  --constraint 'node.role==worker' \
  twitter-mcp
```

### Load Balancing

```nginx
# Nginx upstream
upstream twitter_mcp_backend {
    least_conn;
    server mcp1:8000 max_fails=3 fail_timeout=30s;
    server mcp2:8000 max_fails=3 fail_timeout=30s;
    server mcp3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://twitter_mcp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 🔧 Maintenance

### Update Procedure

```bash
# 1. Backup
./scripts/backup.sh

# 2. Pull latest code
git pull origin main

# 3. Build new image
docker-compose -f docker-compose.prod.yml build

# 4. Rolling update
docker-compose -f docker-compose.prod.yml up -d --no-deps --build twitter-mcp

# 5. Verify
curl https://api.yourdomain.com/health
docker-compose logs -f twitter-mcp

# 6. Rollback if needed
docker-compose -f docker-compose.prod.yml up -d twitter-mcp:previous-tag
```

### Health Checks

```bash
#!/bin/bash
# healthcheck.sh

API_URL="https://api.yourdomain.com"

# Check health endpoint
response=$(curl -s -o /dev/null -w "%{http_code}" ${API_URL}/health)

if [ $response -ne 200 ]; then
    echo "Health check failed: $response"
    # Send alert
    curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK \
      -d '{"text":"🚨 Twitter MCP Server is DOWN!"}'
    exit 1
fi

echo "Health check passed"
```

### Monitoring Checklist

- [ ] Uptime > 99.9%
- [ ] Response time < 500ms (p95)
- [ ] Error rate < 1%
- [ ] Disk usage < 80%
- [ ] Memory usage < 80%
- [ ] CPU usage < 70%
- [ ] Backup success rate 100%

---

## 🚨 Incident Response

### Response Playbook

1. **Detection**
   - Alert received
   - Identify affected service

2. **Assessment**
   ```bash
   # Check logs
   docker logs twitter-mcp --tail 100
   
   # Check resources
   docker stats
   
   # Check network
   docker network inspect backend
   ```

3. **Mitigation**
   ```bash
   # Quick restart
   docker-compose restart twitter-mcp
   
   # Rollback if needed
   docker-compose up -d twitter-mcp:stable
   ```

4. **Resolution**
   - Fix root cause
   - Deploy fix
   - Verify solution

5. **Post-mortem**
   - Document incident
   - Update runbooks
   - Improve monitoring

---

## 📞 Support

- **Emergency**: Configure PagerDuty/OpsGenie
- **Logs**: Centralized in ELK/Grafana Loki
- **Metrics**: Prometheus + Grafana
- **Alerts**: Slack/Email/SMS

---

**Production Deployment Completed! 🎉**
