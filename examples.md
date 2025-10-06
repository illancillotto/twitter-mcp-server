# 📘 Esempi Pratici - Twitter MCP Server

Questa guida contiene esempi pratici e use cases comuni per il Twitter MCP Server.

## 🎯 Indice

1. [Setup e Test Iniziali](#setup-e-test-iniziali)
2. [Automazioni Base](#automazioni-base)
3. [Automazioni Avanzate](#automazioni-avanzate)
4. [Monitoring e Analytics](#monitoring-e-analytics)
5. [Integrations](#integrations)

---

## 🚀 Setup e Test Iniziali

### Test 1: Verifica Connessione

```bash
# Health check
curl http://localhost:8000/health

# Risposta attesa:
# {
#   "status": "healthy",
#   "authenticated": false,
#   "version": "1.0.0"
# }
```

### Test 2: Autenticazione

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "email": "your_email@example.com",
    "password": "your_password"
  }'

# Check auth status
curl http://localhost:8000/auth/status

# Risposta attesa:
# {
#   "authenticated": true,
#   "cookies_exist": true
# }
```

### Test 3: Primo Tweet

```bash
curl -X POST http://localhost:8000/tweets/create \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🎉 My first automated tweet from MCP Server! #automation #n8n"
  }'
```

---

## 🤖 Automazioni Base

### 1. Auto-Poster da RSS Feed

**Workflow n8n:**

```json
{
  "name": "RSS to Twitter",
  "nodes": [
    {
      "name": "RSS Feed Reader",
      "type": "n8n-nodes-base.rssFeedRead",
      "parameters": {
        "url": "https://blog.example.com/feed.xml"
      }
    },
    {
      "name": "Filter New Items",
      "type": "n8n-nodes-base.filter",
      "parameters": {
        "conditions": {
          "dateTime": [{
            "value1": "={{$json.pubDate}}",
            "operation": "afterDate",
            "value2": "={{$now.minus({hours: 24})}}"
          }]
        }
      }
    },
    {
      "name": "Format Tweet",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "return {\n  text: `📰 ${items[0].json.title}\\n\\n${items[0].json.link} #news`\n};"
      }
    },
    {
      "name": "Post to Twitter",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://twitter-mcp:8000/tweets/create",
        "method": "POST",
        "jsonParameters": true,
        "body": {
          "text": "={{$json.text}}"
        }
      }
    }
  ]
}
```

**cURL Test:**

```bash
# Test singolo post
curl -X POST http://localhost:8000/tweets/create \
  -H "Content-Type: application/json" \
  -d '{
    "text": "📰 New blog post: How to automate Twitter\n\nhttps://blog.example.com/post #automation"
  }'
```

### 2. Auto-Reply ai Mentions

**Python Script (per n8n Code node):**

```python
import requests
import time

MCP_URL = "http://twitter-mcp:8000"

def get_mentions():
    """Get recent mentions"""
    response = requests.get(f"{MCP_URL}/notifications")
    return response.json().get('notifications', [])

def auto_reply(tweet_id, username):
    """Auto reply to mention"""
    reply_text = f"@{username} Thanks for mentioning us! 🙏"
    
    data = {
        "text": reply_text,
        "reply_to": tweet_id
    }
    
    response = requests.post(
        f"{MCP_URL}/tweets/create",
        json=data
    )
    
    return response.json()

# Main loop
mentions = get_mentions()

for mention in mentions:
    if not mention.get('replied', False):
        result = auto_reply(
            mention['id'],
            mention['user']['username']
        )
        
        print(f"Replied to {mention['user']['username']}")
        time.sleep(5)  # Rate limiting
```

### 3. Scheduled Daily Summary

**Workflow n8n (Schedule):**

```bash
# cURL per testare manualmente
curl -X POST http://localhost:8000/tweets/create \
  -H "Content-Type: application/json" \
  -d '{
    "text": "📊 Daily Summary - '$(date +%Y-%m-%d)'\n\n✅ Tasks completed: 12\n⏳ In progress: 5\n📈 Growth: +2.5%\n\n#ProductivityStats"
  }'
```

---

## 🎨 Automazioni Avanzate

### 4. Content Curation Bot

Cerca tweet rilevanti, analizzali e retweetta i migliori.

**Workflow Completo:**

```python
import requests
from datetime import datetime

MCP_URL = "http://twitter-mcp:8000"

def search_relevant_tweets(query, count=50):
    """Cerca tweet rilevanti"""
    data = {
        "query": query,
        "product": "Latest",
        "count": count
    }
    
    response = requests.post(
        f"{MCP_URL}/tweets/search",
        json=data
    )
    
    return response.json().get('tweets', [])

def analyze_tweet(tweet):
    """Analizza qualità tweet"""
    score = 0
    
    # Engagement
    engagement = (
        tweet.get('favorite_count', 0) +
        tweet.get('retweet_count', 0) * 2
    )
    score += min(engagement / 100, 10)
    
    # Lunghezza testo
    text_length = len(tweet.get('text', ''))
    if 50 < text_length < 200:
        score += 5
    
    # Ha media
    if tweet.get('metadata', {}).get('has_media'):
        score += 3
    
    return score

def retweet_best_tweets(tweets, threshold=8, max_retweets=5):
    """Retweet dei migliori tweet"""
    # Analizza e ordina
    scored_tweets = [
        (tweet, analyze_tweet(tweet))
        for tweet in tweets
    ]
    
    scored_tweets.sort(key=lambda x: x[1], reverse=True)
    
    # Retweet top N
    retweeted = 0
    for tweet, score in scored_tweets:
        if score >= threshold and retweeted < max_retweets:
            try:
                requests.post(
                    f"{MCP_URL}/tweets/retweet?tweet_id={tweet['id']}"
                )
                print(f"Retweeted: {tweet['text'][:50]}... (score: {score})")
                retweeted += 1
                
                import time
                time.sleep(10)  # Rate limiting
                
            except Exception as e:
                print(f"Error retweeting: {e}")
    
    return retweeted

# Main execution
queries = ["#n8n", "#automation", "#nocode"]

for query in queries:
    print(f"\n🔍 Searching: {query}")
    tweets = search_relevant_tweets(query)
    print(f"Found {len(tweets)} tweets")
    
    retweeted = retweet_best_tweets(tweets)
    print(f"✅ Retweeted: {retweeted} tweets")
```

### 5. Competitor Monitoring

Monitora competitors e salva insights.

```python
import requests
import json
from datetime import datetime

MCP_URL = "http://twitter-mcp:8000"

COMPETITORS = [
    "competitor1",
    "competitor2",
    "competitor3"
]

def monitor_competitor(username):
    """Monitora un competitor"""
    # Get profile
    profile_response = requests.post(
        f"{MCP_URL}/users/profile",
        json={"username": username}
    )
    profile = profile_response.json().get('profile', {})
    
    # Get recent tweets
    tweets_response = requests.post(
        f"{MCP_URL}/users/tweets",
        json={"username": username, "count": 10}
    )
    tweets = tweets_response.json().get('tweets', [])
    
    # Analyze
    analysis = {
        "username": username,
        "timestamp": datetime.now().isoformat(),
        "followers": profile.get('followers_count', 0),
        "recent_tweets": len(tweets),
        "avg_engagement": sum(
            t.get('favorite_count', 0) + t.get('retweet_count', 0)
            for t in tweets
        ) / len(tweets) if tweets else 0,
        "top_tweet": max(
            tweets,
            key=lambda t: t.get('favorite_count', 0)
        ) if tweets else None
    }
    
    return analysis

# Monitor all competitors
results = []
for competitor in COMPETITORS:
    print(f"📊 Analyzing @{competitor}...")
    analysis = monitor_competitor(competitor)
    results.append(analysis)
    print(f"   Followers: {analysis['followers']}")
    print(f"   Avg Engagement: {analysis['avg_engagement']:.1f}")

# Save to file
with open(f"competitor_analysis_{datetime.now().strftime('%Y%m%d')}.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\n✅ Analysis saved!")
```

### 6. Thread Publisher

Pubblica thread multi-tweet.

```python
import requests
import time

MCP_URL = "http://twitter-mcp:8000"

def publish_thread(tweets_list):
    """
    Pubblica thread di tweet
    
    Args:
        tweets_list: Lista di testi per ogni tweet
    """
    previous_tweet_id = None
    published_ids = []
    
    for i, tweet_text in enumerate(tweets_list):
        # Aggiungi numero thread
        numbered_text = f"{i+1}/{len(tweets_list)} {tweet_text}"
        
        data = {
            "text": numbered_text
        }
        
        # Se non è il primo tweet, è una reply
        if previous_tweet_id:
            data["reply_to"] = previous_tweet_id
        
        # Pubblica
        response = requests.post(
            f"{MCP_URL}/tweets/create",
            json=data
        )
        
        result = response.json()
        tweet_id = result.get('tweet_id')
        
        if tweet_id:
            published_ids.append(tweet_id)
            previous_tweet_id = tweet_id
            print(f"✅ Published tweet {i+1}/{len(tweets_list)}")
        else:
            print(f"❌ Failed to publish tweet {i+1}")
            break
        
        # Rate limiting
        time.sleep(3)
    
    return published_ids

# Example thread
thread = [
    "🧵 How to build a Twitter automation bot (Thread)\n\nLet me show you the complete process...",
    
    "Step 1: Choose your tools 🛠️\n\nI use n8n for workflows and a custom MCP server for Twitter API access. This combo gives you unlimited flexibility.",
    
    "Step 2: Set up authentication 🔐\n\nUse a secondary account for safety. The MCP server handles cookies automatically, so you don't need API keys!",
    
    "Step 3: Build your workflows ⚙️\n\nStart simple: auto-posting, then add complexity like auto-replies, content curation, etc.",
    
    "Step 4: Add rate limiting ⏱️\n\nCrucial! Respect Twitter's limits to avoid bans. My setup does 30 requests/min max.",
    
    "That's it! 🎉\n\nCheck out the full code on GitHub: [link]\n\n#automation #n8n #twitter"
]

# Publish thread
tweet_ids = publish_thread(thread)
print(f"\n✅ Thread published! {len(tweet_ids)} tweets")
```

---

## 📊 Monitoring e Analytics

### 7. Real-time Dashboard

**Python Script per raccogliere metriche:**

```python
import requests
import time
from collections import defaultdict

MCP_URL = "http://twitter-mcp:8000"

def get_stats():
    """Raccolta stats"""
    stats = {
        "timestamp": time.time(),
        "health": requests.get(f"{MCP_URL}/health").json(),
        "auth_status": requests.get(f"{MCP_URL}/auth/status").json()
    }
    
    return stats

def monitor_loop(interval=300):
    """Loop di monitoring ogni 5 minuti"""
    metrics = defaultdict(list)
    
    while True:
        try:
            stats = get_stats()
            
            print(f"\n📊 Stats @ {time.strftime('%H:%M:%S')}")
            print(f"   Health: {stats['health']['status']}")
            print(f"   Authenticated: {stats['auth_status']['authenticated']}")
            
            # Store metrics
            metrics['timestamps'].append(stats['timestamp'])
            metrics['health'].append(stats['health'])
            
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

# Start monitoring
monitor_loop()
```

### 8. Weekly Report

Genera report settimanale automatico:

```python
import requests
from datetime import datetime, timedelta

MCP_URL = "http://twitter-mcp:8000"

def generate_weekly_report():
    """Genera report settimanale"""
    # Get own profile
    profile_response = requests.post(
        f"{MCP_URL}/users/profile",
        json={"username": "your_username"}
    )
    profile = profile_response.json().get('profile', {})
    
    # Get recent tweets
    tweets_response = requests.post(
        f"{MCP_URL}/users/tweets",
        json={"username": "your_username", "count": 50}
    )
    tweets = tweets_response.json().get('tweets', [])
    
    # Analyze last week
    week_ago = datetime.now() - timedelta(days=7)
    recent_tweets = [
        t for t in tweets
        if datetime.fromisoformat(t['created_at'].replace('Z', '+00:00')) > week_ago
    ]
    
    # Calculate metrics
    total_likes = sum(t.get('favorite_count', 0) for t in recent_tweets)
    total_retweets = sum(t.get('retweet_count', 0) for t in recent_tweets)
    
    report = f"""📊 Weekly Twitter Report
    
📅 Period: {week_ago.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}

👥 Followers: {profile.get('followers_count', 0):,}
📝 Tweets Published: {len(recent_tweets)}
❤️  Total Likes: {total_likes:,}
🔄 Total Retweets: {total_retweets:,}
📈 Avg Engagement: {(total_likes + total_retweets) / len(recent_tweets):.1f} per tweet

🏆 Best Tweet:
"""
    
    # Find best tweet
    if recent_tweets:
        best_tweet = max(
            recent_tweets,
            key=lambda t: t.get('favorite_count', 0) + t.get('retweet_count', 0)
        )
        report += f"   {best_tweet['text'][:100]}...\n"
        report += f"   Engagement: {best_tweet.get('favorite_count', 0)} likes, {best_tweet.get('retweet_count', 0)} RTs"
    
    return report

# Generate and print report
report = generate_weekly_report()
print(report)

# Optionally tweet it
# requests.post(f"{MCP_URL}/tweets/create", json={"text": report})
```

---

## 🔗 Integrations

### 9. Slack Notifications

Invia notifiche Slack per eventi Twitter:

```python
import requests

SLACK_WEBHOOK = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
MCP_URL = "http://twitter-mcp:8000"

def send_slack_notification(message):
    """Invia notifica a Slack"""
    requests.post(SLACK_WEBHOOK, json={"text": message})

# Monitor mentions and notify Slack
def monitor_mentions():
    response = requests.get(f"{MCP_URL}/notifications")
    notifications = response.json().get('notifications', [])
    
    for notif in notifications:
        if notif.get('type') == 'mention':
            message = f"🐦 New Twitter mention from @{notif['user']['username']}:\n{notif['text']}"
            send_slack_notification(message)

monitor_mentions()
```

### 10. Google Sheets Logger

Loga attività su Google Sheets:

```python
import requests
from datetime import datetime

# Usa n8n Google Sheets node per questo
# Ecco la struttura dati da passare

def log_to_sheets(action, details):
    """Prepara dati per Google Sheets"""
    return {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details,
        "success": True
    }

# Example usage
data = log_to_sheets(
    "create_tweet",
    "Published automated tweet about product launch"
)

# In n8n, usa il nodo Google Sheets per appendere questa riga
```

---

## 🎓 Best Practices negli Esempi

### Rate Limiting

```python
import time
from functools import wraps

def rate_limit(calls_per_minute=30):
    """Decorator per rate limiting"""
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        
        return wrapper
    return decorator

# Usage
@rate_limit(calls_per_minute=30)
def create_tweet(text):
    return requests.post(f"{MCP_URL}/tweets/create", json={"text": text})
```

### Error Handling

```python
import requests
from requests.exceptions import RequestException

def safe_api_call(func, *args, **kwargs):
    """Wrapper sicuro per chiamate API"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        
        except RequestException as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"All attempts failed: {e}")
                raise

# Usage
response = safe_api_call(
    requests.post,
    f"{MCP_URL}/tweets/create",
    json={"text": "Hello"}
)
```

---

## 🚨 Note Importanti

1. **Rate Limits**: Tutti gli esempi includono rate limiting appropriato
2. **Error Handling**: Usa sempre try-except per chiamate API
3. **Logging**: Implementa logging per debugging
4. **Testing**: Testa sempre su account secondario
5. **Monitoring**: Monitora health e metriche regolarmente

---

**Happy Automating! 🚀**
