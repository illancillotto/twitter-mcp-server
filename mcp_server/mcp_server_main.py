"""
Twitter MCP Server
Espone tutte le funzionalità Twitter tramite MCP protocol per n8n
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from .twitter_client import TwitterClient
from .utils import RateLimiter, ErrorHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Twitter MCP Server",
    description="Personal Twitter API via MCP Protocol",
    version="1.0.0"
)

# Global Twitter client
twitter_client: Optional[TwitterClient] = None
rate_limiter = RateLimiter(requests_per_minute=30)
error_handler = ErrorHandler()

# ============ PYDANTIC MODELS ============

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
    product: str = "Latest"  # Latest, Top, Media, etc.
    count: int = 20

class UserRequest(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None

class DMRequest(BaseModel):
    user_id: str
    message: str

class MediaUploadRequest(BaseModel):
    media_path: str

# ============ MIDDLEWARE ============

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    if not await rate_limiter.allow_request():
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Try again later."}
        )
    response = await call_next(request)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global error handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=error_handler.format_error(exc)
    )

# ============ AUTHENTICATION ENDPOINTS ============

@app.post("/auth/login")
async def login(auth: AuthRequest):
    """Autenticazione Twitter con gestione cookies"""
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
    """Logout e cleanup"""
    global twitter_client
    if twitter_client:
        await twitter_client.logout()
        twitter_client = None
    return {"status": "success", "message": "Logged out"}

@app.get("/auth/status")
async def auth_status():
    """Check authentication status"""
    is_authenticated = twitter_client is not None and twitter_client.is_authenticated()
    return {
        "authenticated": is_authenticated,
        "cookies_exist": twitter_client.has_cookies() if twitter_client else False
    }

# ============ TWEET OPERATIONS ============

@app.post("/tweets/create")
async def create_tweet(tweet: TweetRequest):
    """Crea un nuovo tweet con optional media"""
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        media_ids = []
        
        # Upload media se presenti
        if tweet.media_paths:
            for media_path in tweet.media_paths:
                media_id = await twitter_client.upload_media(media_path)
                media_ids.append(media_id)
        
        # Crea tweet
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
    """Cerca tweets per keyword"""
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
    """Like a tweet"""
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.like_tweet(tweet_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tweets/retweet")
async def retweet(tweet_id: str):
    """Retweet"""
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.retweet(tweet_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tweets/{tweet_id}")
async def delete_tweet(tweet_id: str):
    """Elimina un tweet"""
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.delete_tweet(tweet_id)
        return {"status": "success", "deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ USER OPERATIONS ============

@app.post("/users/profile")
async def get_user_profile(user: UserRequest):
    """Ottieni profilo utente completo"""
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
    """Ottieni tweets di un utente"""
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
    """Follow un utente"""
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.follow_user(user_id)
        return {"status": "success", "following": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/unfollow")
async def unfollow_user(user_id: str):
    """Unfollow un utente"""
    if not twitter_client:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await twitter_client.unfollow_user(user_id)
        return {"status": "success", "following": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ DIRECT MESSAGES ============

@app.post("/dm/send")
async def send_dm(dm: DMRequest):
    """Invia un DM"""
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
    """Ottieni inbox DM"""
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

# ============ TRENDS & DISCOVERY ============

@app.get("/trends/{location}")
async def get_trends(location: str = "trending"):
    """Ottieni trending topics"""
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
    """Ottieni home timeline"""
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

# ============ NOTIFICATIONS ============

@app.get("/notifications")
async def get_notifications(count: int = 20):
    """Ottieni notifiche"""
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

# ============ HEALTH CHECK ============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "authenticated": twitter_client is not None and twitter_client.is_authenticated(),
        "version": "1.0.0"
    }

# ============ SERVER STARTUP ============

if __name__ == "__main__":
    uvicorn.run(
        "mcp_server.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
