#!/bin/bash

echo "🚀 Installing FULL Twitter MCP Server with Twikit..."

# === SERVER.PY - VERSIONE COMPLETA CON TWIKIT ===
cat > mcp_server/server.py << 'PYEOF'
"""
Twitter MCP Server - FULL VERSION
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from .twitter_client import TwitterClient
from .utils import RateLimiter, ErrorHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Twitter MCP Server",
    description="Personal Twitter API via MCP Protocol",
    version="1.0.0"
)

twitter_client: Optional[TwitterClient] = None
rate_limiter = RateLimiter(requests_per_minute=30)
error_handler = ErrorHandler()

class AuthRequest(BaseModel):
    username: str
    email: str
    password: str

class TweetRequest(BaseModel):
    text: str
    media_paths: Optional[List[str]] = None
    reply_to: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    product: str = "Latest"
    count: int = 20

class UserRequest(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None

class DMRequest(BaseModel):
    user_id: str
    message: str

@app.get("/health")
async def health_check():
    is_authenticated = twitter_client is not None and twitter_client.is_authenticated()
    return {
        "status": "healthy",
        "authenticated": is_authenticated,
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    return {
        "message": "Twitter MCP Server - FULL VERSION",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.post("/auth/login")
async def login(auth: AuthRequest):
    global twitter_client
    
    try:
        twitter_client = TwitterClient()
        await twitter_client.login(
            username=auth.username,
            email=auth.email,
            password=auth.password
        )
        
        logger.info(f"Login successful for user: {auth.username}")
        return {
            "status": "success",
            "message": "Authenticated successfully",
            "cookies_saved": True
        }
    
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/logout")
async def logout():
    global twitter_client
    if twitter_client:
        await twitter_client.logout()
        twitter_client = None
    return {"status": "success", "message": "Logged out"}

@app.get("/auth/status")
async def auth_status():
    is_authenticated = twitter_client is not None and twitter_client.is_authenticated()
    has_cookies = twitter_client.has_cookies() if twitter_client else False
    return {
        "authenticated": is_authenticated,
        "cookies_exist": has_cookies
    }

@app.post("/tweets/create")
async def create_tweet(tweet: TweetRequest):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        media_ids = []
        if tweet.media_paths:
            for media_path in tweet.media_paths:
                media_id = await twitter_client.upload_media(media_path)
                media_ids.append(media_id)
        
        result = await twitter_client.create_tweet(
            text=tweet.text,
            media_ids=media_ids if media_ids else None,
            reply_to=tweet.reply_to
        )
        
        logger.info(f"Tweet created: {result.get('id')}")
        return {
            "status": "success",
            "tweet_id": result.get('id'),
            "data": result
        }
    
    except Exception as e:
        logger.error(f"Tweet creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tweets/search")
async def search_tweets(search: SearchRequest):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        tweets = await twitter_client.search_tweets(
            query=search.query,
            product=search.product,
            count=search.count
        )
        
        logger.info(f"Found {len(tweets)} tweets for query: {search.query}")
        return {
            "status": "success",
            "count": len(tweets),
            "tweets": tweets
        }
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tweets/like")
async def like_tweet(tweet_id: str):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.like_tweet(tweet_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tweets/retweet")
async def retweet(tweet_id: str):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.retweet(tweet_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tweets/{tweet_id}")
async def delete_tweet(tweet_id: str):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.delete_tweet(tweet_id)
        return {"status": "success", "deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/profile")
async def get_user_profile(user: UserRequest):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        profile = await twitter_client.get_user_profile(
            user_id=user.user_id,
            username=user.username
        )
        
        return {
            "status": "success",
            "profile": profile
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/tweets")
async def get_user_tweets(user: UserRequest, count: int = 20):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        tweets = await twitter_client.get_user_tweets(
            user_id=user.user_id,
            username=user.username,
            count=count
        )
        
        return {
            "status": "success",
            "count": len(tweets),
            "tweets": tweets
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/follow")
async def follow_user(user_id: str):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.follow_user(user_id)
        return {"status": "success", "following": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/unfollow")
async def unfollow_user(user_id: str):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.unfollow_user(user_id)
        return {"status": "success", "following": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dm/send")
async def send_dm(dm: DMRequest):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.send_dm(
            user_id=dm.user_id,
            message=dm.message
        )
        
        return {
            "status": "success",
            "message_sent": True,
            "data": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dm/inbox")
async def get_inbox(count: int = 20):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        messages = await twitter_client.get_dm_inbox(count=count)
        return {
            "status": "success",
            "count": len(messages),
            "messages": messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trends/{location}")
async def get_trends(location: str = "trending"):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        trends = await twitter_client.get_trends(location)
        return {
            "status": "success",
            "location": location,
            "trends": trends
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/timeline/home")
async def get_home_timeline(count: int = 20):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        tweets = await twitter_client.get_home_timeline(count=count)
        return {
            "status": "success",
            "count": len(tweets),
            "tweets": tweets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notifications")
async def get_notifications(count: int = 20):
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        notifications = await twitter_client.get_notifications(count=count)
        return {
            "status": "success",
            "count": len(notifications),
            "notifications": notifications
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "mcp_server.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
PYEOF

echo "✅ server.py updated!"
echo "⚠️  Now rebuild: docker-compose build && docker-compose up -d"
