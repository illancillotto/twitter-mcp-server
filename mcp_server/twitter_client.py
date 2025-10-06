"""
Twitter Client - Wrapper per Twikit
Gestisce tutte le operazioni Twitter con error handling e retry logic
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from twikit import Client
from twikit.errors import TwitterException, Unauthorized, TooManyRequests

logger = logging.getLogger(__name__)

class TwitterClient:
    """Wrapper asincrono per Twikit con gestione avanzata"""
    
    def __init__(self, cookies_path: str = "data/cookies.json"):
        """
        Initialize Twitter client
        
        Args:
            cookies_path: Path dove salvare/caricare i cookies
        """
        self.client = Client('en-US')
        self.cookies_path = Path(cookies_path)
        self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
        self._authenticated = False
        
        # Rate limiting tracking
        self._request_count = 0
        self._last_request_time = None
        
        logger.info(f"Twitter client initialized. Cookies path: {self.cookies_path}")
    
    # ============ AUTHENTICATION ============
    
    async def login(
        self, 
        username: str, 
        email: str, 
        password: str,
        force_new: bool = False
    ) -> bool:
        """
        Login con gestione cookies automatica
        
        Args:
            username: Twitter username
            email: Email dell'account
            password: Password
            force_new: Se True, ignora cookies esistenti
        
        Returns:
            True se login successful
        """
        try:
            # Prova a caricare cookies esistenti se non force_new
            if not force_new and self.cookies_path.exists():
                logger.info("Loading existing cookies...")
                self.client.load_cookies(str(self.cookies_path))
                
                # Verifica se i cookies sono ancora validi
                if await self._verify_cookies():
                    logger.info("Cookies valid, login successful")
                    self._authenticated = True
                    return True
                else:
                    logger.warning("Cookies expired, performing new login")
            
            # Login completo
            logger.info(f"Performing login for user: {username}")
            await self.client.login(
                auth_info_1=username,
                auth_info_2=email,
                password=password
            )
            
            # Salva cookies
            self.client.save_cookies(str(self.cookies_path))
            logger.info(f"Cookies saved to {self.cookies_path}")
            
            self._authenticated = True
            return True
            
        except Unauthorized as e:
            logger.error(f"Login unauthorized: {e}")
            raise ValueError("Invalid credentials") from e
        except TwitterException as e:
            logger.error(f"Twitter error during login: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            raise
    
    async def logout(self):
        """Logout e cleanup"""
        self._authenticated = False
        if self.cookies_path.exists():
            self.cookies_path.unlink()
        logger.info("Logged out successfully")
    
    async def _verify_cookies(self) -> bool:
        """Verifica se i cookies sono validi provando una request semplice"""
        try:
            # Prova a ottenere il proprio profilo
            await self.client.user()
            return True
        except:
            return False
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self._authenticated
    
    def has_cookies(self) -> bool:
        """Check if cookies file exists"""
        return self.cookies_path.exists()
    
    # ============ RATE LIMITING ============
    
    async def _rate_limit_check(self):
        """Internal rate limiting con backoff esponenziale"""
        self._request_count += 1
        
        # Ogni 100 requests, pausa breve
        if self._request_count % 100 == 0:
            logger.info(f"Rate limit pause after {self._request_count} requests")
            await asyncio.sleep(2)
    
    async def _handle_rate_limit(self, retry_count: int = 0, max_retries: int = 3):
        """Gestione rate limit con retry exponential backoff"""
        if retry_count >= max_retries:
            raise TooManyRequests("Max retries exceeded")
        
        wait_time = 2 ** retry_count * 60  # 1min, 2min, 4min
        logger.warning(f"Rate limited. Waiting {wait_time}s before retry {retry_count + 1}/{max_retries}")
        await asyncio.sleep(wait_time)
    
    # ============ TWEET OPERATIONS ============
    
    async def create_tweet(
        self, 
        text: str, 
        media_ids: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crea un tweet
        
        Args:
            text: Testo del tweet (max 280 chars)
            media_ids: Lista di media IDs (max 4)
            reply_to: Tweet ID a cui rispondere
        
        Returns:
            Dict con info del tweet creato
        """
        await self._rate_limit_check()
        
        try:
            tweet = await self.client.create_tweet(
                text=text,
                media_ids=media_ids,
                reply_to=reply_to
            )
            
            return {
                'id': tweet.id,
                'text': tweet.text,
                'created_at': str(tweet.created_at),
                'user': tweet.user.screen_name if tweet.user else None
            }
            
        except TooManyRequests:
            await self._handle_rate_limit()
            return await self.create_tweet(text, media_ids, reply_to)
        except Exception as e:
            logger.error(f"Failed to create tweet: {e}")
            raise
    
    async def search_tweets(
        self, 
        query: str, 
        product: str = "Latest",
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Cerca tweets
        
        Args:
            query: Keyword di ricerca
            product: "Latest", "Top", "Media", "People"
            count: Numero di risultati
        
        Returns:
            Lista di tweets
        """
        await self._rate_limit_check()
        
        try:
            tweets = await self.client.search_tweet(query, product=product)
            
            results = []
            for tweet in tweets[:count]:
                results.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': str(tweet.created_at),
                    'user': {
                        'name': tweet.user.name,
                        'screen_name': tweet.user.screen_name,
                        'id': tweet.user.id
                    },
                    'favorite_count': tweet.favorite_count,
                    'retweet_count': tweet.retweet_count,
                    'reply_count': tweet.reply_count,
                    'view_count': getattr(tweet, 'view_count', 0)
                })
            
            return results
            
        except TooManyRequests:
            await self._handle_rate_limit()
            return await self.search_tweets(query, product, count)
        except Exception as e:
            logger.error(f"Failed to search tweets: {e}")
            raise
    
    async def like_tweet(self, tweet_id: str) -> Dict[str, Any]:
        """Like a tweet"""
        await self._rate_limit_check()
        
        try:
            tweet = await self.client.get_tweet_by_id(tweet_id)
            await tweet.favorite()
            return {'success': True, 'tweet_id': tweet_id}
        except Exception as e:
            logger.error(f"Failed to like tweet: {e}")
            raise
    
    async def retweet(self, tweet_id: str) -> Dict[str, Any]:
        """Retweet"""
        await self._rate_limit_check()
        
        try:
            tweet = await self.client.get_tweet_by_id(tweet_id)
            await tweet.retweet()
            return {'success': True, 'tweet_id': tweet_id}
        except Exception as e:
            logger.error(f"Failed to retweet: {e}")
            raise
    
    async def delete_tweet(self, tweet_id: str) -> Dict[str, Any]:
        """Elimina un tweet"""
        await self._rate_limit_check()
        
        try:
            tweet = await self.client.get_tweet_by_id(tweet_id)
            await tweet.delete()
            return {'success': True, 'deleted': True}
        except Exception as e:
            logger.error(f"Failed to delete tweet: {e}")
            raise
    
    # ============ USER OPERATIONS ============
    
    async def get_user_profile(
        self, 
        user_id: Optional[str] = None,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ottieni profilo utente
        
        Args:
            user_id: ID utente
            username: Username (alternative a user_id)
        
        Returns:
            Dict con info profilo
        """
        await self._rate_limit_check()
        
        try:
            if username:
                user = await self.client.get_user_by_screen_name(username)
            elif user_id:
                user = await self.client.get_user_by_id(user_id)
            else:
                raise ValueError("Provide either user_id or username")
            
            return {
                'id': user.id,
                'name': user.name,
                'screen_name': user.screen_name,
                'description': user.description,
                'location': user.location,
                'followers_count': user.followers_count,
                'following_count': user.following_count,
                'tweet_count': user.statuses_count,
                'created_at': str(user.created_at),
                'verified': user.verified,
                'profile_image_url': user.profile_image_url
            }
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            raise
    
    async def get_user_tweets(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """Ottieni tweets di un utente"""
        await self._rate_limit_check()
        
        try:
            if username:
                user_id = (await self.client.get_user_by_screen_name(username)).id
            elif not user_id:
                raise ValueError("Provide either user_id or username")
            
            tweets = await self.client.get_user_tweets(user_id, 'Tweets')
            
            results = []
            for tweet in tweets[:count]:
                results.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': str(tweet.created_at),
                    'favorite_count': tweet.favorite_count,
                    'retweet_count': tweet.retweet_count
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get user tweets: {e}")
            raise
    
    async def follow_user(self, user_id: str) -> Dict[str, Any]:
        """Follow un utente"""
        await self._rate_limit_check()
        
        try:
            user = await self.client.get_user_by_id(user_id)
            await user.follow()
            return {'success': True, 'following': True}
        except Exception as e:
            logger.error(f"Failed to follow user: {e}")
            raise
    
    async def unfollow_user(self, user_id: str) -> Dict[str, Any]:
        """Unfollow un utente"""
        await self._rate_limit_check()
        
        try:
            user = await self.client.get_user_by_id(user_id)
            await user.unfollow()
            return {'success': True, 'following': False}
        except Exception as e:
            logger.error(f"Failed to unfollow user: {e}")
            raise
    
    # ============ DIRECT MESSAGES ============
    
    async def send_dm(self, user_id: str, message: str) -> Dict[str, Any]:
        """Invia DM"""
        await self._rate_limit_check()
        
        try:
            await self.client.send_dm(user_id, message)
            return {
                'success': True,
                'recipient_id': user_id,
                'message': message
            }
        except Exception as e:
            logger.error(f"Failed to send DM: {e}")
            raise
    
    async def get_dm_inbox(self, count: int = 20) -> List[Dict[str, Any]]:
        """Ottieni inbox DM (placeholder - da implementare con Twikit)"""
        # Nota: Twikit potrebbe non supportare questa feature nativamente
        # Implementazione custom richiesta
        logger.warning("DM inbox retrieval not fully implemented in Twikit")
        return []
    
    # ============ TRENDS & DISCOVERY ============
    
    async def get_trends(self, location: str = "trending") -> List[Dict[str, Any]]:
        """Ottieni trending topics"""
        await self._rate_limit_check()
        
        try:
            trends = await self.client.get_trends(location)
            
            results = []
            for trend in trends:
                results.append({
                    'name': trend.name if hasattr(trend, 'name') else str(trend),
                    'url': getattr(trend, 'url', ''),
                    'tweet_count': getattr(trend, 'tweet_count', 0)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get trends: {e}")
            raise
    
    async def get_home_timeline(self, count: int = 20) -> List[Dict[str, Any]]:
        """Ottieni home timeline"""
        await self._rate_limit_check()
        
        try:
            # Usa search per simulare timeline se necessario
            tweets = await self.client.get_timeline('Home', count=count)
            
            results = []
            for tweet in tweets:
                results.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'user': tweet.user.screen_name,
                    'created_at': str(tweet.created_at)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get timeline: {e}")
            raise
    
    # ============ MEDIA UPLOAD ============
    
    async def upload_media(self, media_path: str) -> str:
        """
        Upload media file
        
        Args:
            media_path: Path al file media
        
        Returns:
            Media ID
        """
        await self._rate_limit_check()
        
        try:
            if not os.path.exists(media_path):
                raise FileNotFoundError(f"Media file not found: {media_path}")
            
            media_id = await self.client.upload_media(media_path)
            logger.info(f"Media uploaded: {media_id}")
            return media_id
            
        except Exception as e:
            logger.error(f"Failed to upload media: {e}")
            raise
    
    # ============ NOTIFICATIONS ============
    
    async def get_notifications(self, count: int = 20) -> List[Dict[str, Any]]:
        """Ottieni notifiche (placeholder)"""
        # Implementazione custom richiesta
        logger.warning("Notifications not fully implemented")
        return []
