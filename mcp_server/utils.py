"""
Utilities per il Twitter MCP Server
Rate limiting, error handling, logging
"""

import time
import logging
from typing import Dict, Any
from collections import deque

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter con sliding window"""
    
    def __init__(self, requests_per_minute: int = 30, requests_per_hour: int = 500):
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour
        self.minute_window = deque(maxlen=requests_per_minute)
        self.hour_window = deque(maxlen=requests_per_hour)
        logger.info(f"Rate limiter: {requests_per_minute}/min, {requests_per_hour}/hour")
    
    async def allow_request(self) -> bool:
        """Check se il request è permesso"""
        now = time.time()
        self._clean_windows(now)
        
        if len(self.minute_window) >= self.rpm_limit:
            logger.warning("Rate limit exceeded: requests per minute")
            return False
        
        if len(self.hour_window) >= self.rph_limit:
            logger.warning("Rate limit exceeded: requests per hour")
            return False
        
        self.minute_window.append(now)
        self.hour_window.append(now)
        return True
    
    def _clean_windows(self, now: float):
        """Rimuovi timestamps vecchi"""
        minute_ago = now - 60
        hour_ago = now - 3600
        
        while self.minute_window and self.minute_window[0] < minute_ago:
            self.minute_window.popleft()
        
        while self.hour_window and self.hour_window[0] < hour_ago:
            self.hour_window.popleft()

class ErrorHandler:
    """Centralizzato error handling"""
    
    def __init__(self):
        logger.info("Error handler initialized")
    
    def format_error(self, error: Exception) -> Dict[str, Any]:
        """Formatta errore in risposta standard"""
        return {
            "error": True,
            "type": type(error).__name__,
            "message": str(error)
        }
