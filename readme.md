# 🐦 Twitter MCP Server + n8n Integration

**Personal Twitter API** tramite scraping con Twikit, esposto come MCP server per automazioni n8n.

## 📋 Indice

- [Features](#features)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Configurazione](#configurazione)
- [Utilizzo](#utilizzo)
- [API Endpoints](#api-endpoints)
- [n8n Workflows](#n8n-workflows)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## ✨ Features

### Operazioni Tweet
- ✅ Creare tweet con media (foto/video)
- ✅ Cercare tweet (Latest/Top/Media)
- ✅ Like e Retweet
- ✅ Reply a tweet
- ✅ Eliminare tweet

### Operazioni Utente
- ✅ Profilo utente completo
- ✅ Timeline utente
- ✅ Follow/Unfollow
- ✅ Followers e Following

### Direct Messages
- ✅ Inviare DM
- ✅ Inbox DM (limitato)

### Discovery
- ✅ Trending topics
- ✅ Home timeline
- ✅ Notifiche

### Gestione Avanzata
- ✅ Rate limiting intelligente
- ✅ Error handling con retry
- ✅ Cookie management automatico
- ✅ Logging completo
- ✅ Health checks

---

## 🔧 Requisiti

### Software
- Docker & Docker Compose (raccomandato)
- Python 3.11+ (se installazione locale)
- n8n (incluso in docker-compose)

### Account Twitter
⚠️ **IMPORTANTE**: Usa un **account secondario** per sicurezza!
- Username
- Email
- Password

Non usare il tuo account principale per evitare ban.

---

## 📦 Installazione

### Opzione 1: Docker (Raccomandato)

```bash
# 1. Clone repository
git clone <your-repo>
cd twitter-mcp-server

# 2. Crea file .env
cp .env.example .env
# Edita .env con le tue credenziali

# 3. Build e start
docker-compose up -d

# 4. Check logs
docker-compose logs -f twitter-mcp
```

### Opzione 2: Installazione Locale

```bash
# 1. Clone repository
git clone <your-repo>
cd twitter-mcp-server

# 2. Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup .env
cp .env.example .env
# Edita .env

# 5. Run server
python -m uvicorn mcp_server.server:app --host 0.0.0.0 --port 8000 --reload
```

---

## ⚙️ Configurazione

### File .env

```bash
# Twitter Credentials
TWITTER_USERNAME=your_secondary_account
TWITTER_EMAIL=secondary@email.com
TWITTER_PASSWORD=secure_password

# n8n Credentials
N8N_USER=admin
N8N_PASSWORD=strong_password_here

# Server Config
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=500
```

### Struttura Directory

```
twitter-mcp-server/
├── mcp_server/          # Server code
│   ├── server.py        # FastAPI server
│   ├── twitter_client.py # Twikit wrapper
│   └── utils.py         # Utilities
├── data/                # Cookies & data (auto-created)
├── logs/                # Server logs (auto-created)
├── workflows/           # n8n workflows
├── docker-compose.yml   # Docker orchestration
├── Dockerfile           # Container definition
└── requirements.txt     # Python dependencies
```

---

## 🚀 Utilizzo

### 1. Verifica Health Check

```bash
curl http://localhost:8000/health
```

Risposta attesa:
```json
{
  "status": "healthy",
  "authenticated": false,
  "version": "1.0.0"
}
```

### 2. Autenticazione

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "email": "your_email@example.com",
    "password": "your_password"
  }'
```

### 3. Crea un Tweet

```bash
curl -X POST http://localhost:8000/tweets/create \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from MCP Server! 🚀"
  }'
```

### 4. Cerca Tweet

```bash
curl -X POST http://localhost:8000/tweets/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python automation",
    "product": "Latest",
    "count": 20
  }'
```

### 5. Like un Tweet

```bash
curl -X POST "http://localhost:8000/tweets/like?tweet_id=1234567890"
```

---

## 📡 API Endpoints

### Authentication

| Endpoint | Method | Descrizione |
|----------|--------|-------------|
| `/auth/login` | POST | Login con credenziali |
| `/auth/logout` | POST | Logout e cleanup |
| `/auth/status` | GET | Stato autenticazione |

### Tweets

| Endpoint | Method | Descrizione |
|----------|--------|-------------|
| `/tweets/create` | POST | Crea nuovo tweet |
| `/tweets/search` | POST | Cerca tweets |
| `/tweets/like` | POST | Like tweet |
| `/tweets/retweet` | POST | Retweet |
| `/tweets/{id}` | DELETE | Elimina tweet |

### Users

| Endpoint | Method | Descrizione |
|----------|--------|-------------|
| `/users/profile` | POST | Profilo utente |
| `/users/tweets` | POST | Timeline utente |
| `/users/follow` | POST | Follow utente |
| `/users/unfollow` | POST | Unfollow utente |

### Direct Messages

| Endpoint | Method | Descrizione |
|----------|--------|-------------|
| `/dm/send` | POST | Invia DM |
| `/dm/inbox` | GET | Inbox DM |

### Discovery

| Endpoint | Method | Descrizione |
|----------|--------|-------------|
| `/trends/{location}` | GET | Trending topics |
| `/timeline/home` | GET | Home timeline |
| `/notifications` | GET | Notifiche |

### System

| Endpoint | Method | Descrizione |
|----------|--------|-------------|
| `/health` | GET | Health check |

---

## 🔄 n8n Workflows

### Accesso n8n

1. Apri browser: `http://localhost:5678`
2. Login con credenziali da `.env`:
   - User: `admin` (default)
   - Password: quella impostata in `.env`

### Import Workflow

1. In n8n, vai su **Workflows** → **Import from File**
2. Seleziona `workflows/n8n_twitter_workflow.json`
3. Salva

### Configurazione Workflow

Il workflow include:

**Trigger:**
- Webhook per richieste esterne
- Manual trigger per test

**Nodi Principali:**
1. **Authentication** - Login automatico
2. **Create Tweet** - Pubblica tweet
3. **Search Tweets** - Ricerca contenuti
4. **Get User Profile** - Info utente
5. **Get Trends** - Trending topics
6. **Like/Retweet** - Interazioni
7. **Send DM** - Messaggi diretti

**Nodi Utility:**
- **Switch Action** - Router per azioni
- **Rate Limiter** - Gestione rate limits
- **Error Handler** - Retry logic
- **Data Transformer** - Pulizia dati

### Esempi Webhook

**Crea Tweet:**
```bash
curl -X POST http://localhost:5678/webhook/twitter-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_tweet",
    "text": "Automated tweet from n8n! 🤖"
  }'
```

**Cerca Tweet:**
```bash
curl -X POST http://localhost:5678/webhook/twitter-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "action": "search",
    "query": "n8n automation",
    "count": 10
  }'
```

---

## 📚 Best Practices

### Sicurezza

1. **Account Secondario**
   - Usa sempre account diverso dal principale
   - Attiva 2FA dopo configurazione iniziale

2. **Credentials**
   - Mai committare `.env` su Git
   - Usa password manager
   - Ruota password regolarmente

3. **Rate Limiting**
   - Rispetta limiti configurati (30/min, 500/hour)
   - Monitora logs per rate limit warnings
   - Implementa backoff esponenziale

### Performance

1. **Cookies Management**
   - Cookies salvati automaticamente in `data/cookies.json`
   - Validità ~30 giorni
   - Re-login automatico se scaduti

2. **Batch Operations**
   - Per operazioni massive, usa rate limiter
   - Chunking di 10-20 items per batch
   - Sleep tra batch (2-5 secondi)

3. **Logging**
   - Logs in `logs/` directory
   - Rotazione automatica giornaliera
   - Level INFO per produzione, DEBUG per dev

### Error Handling

1. **Retry Logic**
   - Retry automatico per errori temporanei
   - Max 3 retry con backoff esponenziale
   - Log dettagliato degli errori

2. **Monitoring**
   - Health check ogni 30 secondi
   - Alert su errori consecutivi
   - Dashboard Grafana (optional)

---

## 🐛 Troubleshooting

### Errore: "Login failed"

**Cause:**
- Credenziali errate
- 2FA attivo (non supportato)
- Account bloccato

**Soluzioni:**
```bash
# Verifica credenziali
docker-compose logs twitter-mcp | grep "Login"

# Reset cookies
rm data/cookies.json
docker-compose restart twitter-mcp

# Test login manuale
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"...","email":"...","password":"..."}'
```

### Errore: "Rate limit exceeded"

**Cause:**
- Troppi requests
- Ban temporaneo Twitter

**Soluzioni:**
```bash
# Aumenta delay in .env
RATE_LIMIT_PER_MINUTE=20
RATE_LIMIT_PER_HOUR=300

# Restart
docker-compose restart

# Attendi 15-30 minuti per reset Twitter rate limit
```

### Errore: "Connection refused"

**Cause:**
- Server non avviato
- Porta occupata
- Network issues

**Soluzioni:**
```bash
# Check containers
docker-compose ps

# Check logs
docker-compose logs twitter-mcp

# Restart tutto
docker-compose down
docker-compose up -d

# Check ports
netstat -tulpn | grep 8000
```

### n8n non si connette a MCP Server

**Soluzioni:**
```bash
# Verifica network
docker network inspect twitter-network

# Test connettività
docker exec n8n ping twitter-mcp

# Usa hostname corretto in n8n:
# http://twitter-mcp:8000 (dentro Docker)
# http://localhost:8000 (host system)
```

### Tweet non viene pubblicato

**Debug steps:**
```bash
# 1. Verifica auth
curl http://localhost:8000/auth/status

# 2. Test diretto
curl -X POST http://localhost:8000/tweets/create \
  -H "Content-Type: application/json" \
  -d '{"text":"Test tweet"}'

# 3. Check logs
docker-compose logs twitter-mcp | tail -50

# 4. Verifica lunghezza tweet (max 280 chars)
```

---

## 📊 Monitoring

### Health Dashboard

Crea un workflow n8n per monitoring:

```json
{
  "nodes": [
    {
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.cron",
      "parameters": {
        "cronExpression": "*/5 * * * *"
      }
    },
    {
      "name": "Health Check",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://twitter-mcp:8000/health"
      }
    },
    {
      "name": "Alert on Error",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "boolean": [{
            "value1": "={{$json.status !== 'healthy'}}"
          }]
        }
      }
    }
  ]
}
```

### Logs Monitoring

```bash
# Real-time logs
docker-compose logs -f twitter-mcp

# Error logs only
docker-compose logs twitter-mcp | grep ERROR

# Last 100 lines
docker-compose logs --tail=100 twitter-mcp
```

---

## 🤝 Contributing

Contributi benvenuti! Per nuove feature:

1. Fork repository
2. Crea branch: `git checkout -b feature/nome-feature`
3. Commit: `git commit -m 'Add feature'`
4. Push: `git push origin feature/nome-feature`
5. Pull Request

---

## 📄 License

MIT License - vedi LICENSE file

---

## ⚠️ Disclaimer

Questo progetto è per **uso educativo e personale**. 

- Rispetta i Terms of Service di Twitter/X
- Non usare per spam o attività illecite
- Usa con moderazione per evitare ban
- L'autore non è responsabile per uso improprio

---

## 🆘 Support

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Email: your@email.com

---

## 🎯 Roadmap

- [ ] Support proxy rotation
- [ ] Redis caching
- [ ] Webhook notifications
- [ ] Grafana dashboard
- [ ] Auto-scaling rate limits
- [ ] Multi-account support
- [ ] Advanced analytics

---

**Made with ❤️ for the n8n community**
