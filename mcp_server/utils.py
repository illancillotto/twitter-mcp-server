"""
Utilities per il Twitter MCP Server
Rate limiting, error handling, logging
"""

import time
import logging
from typing import Dict, Any
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter con sliding window
    Previene troppi requests in poco tempo
    """
    
    def __init__(self, requests_per_minute: int = 30, requests_per_hour: int = 500):
        """
        Args:
            requests_per_minute: Max requests al minuto
            requests_per_hour: Max requests all'ora
        """
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour
        
        # Sliding windows
        self.minute_window = deque(maxlen=requests_per_minute)
        self.hour_window = deque(maxlen=requests_per_hour)
        
        logger.info(f"Rate limiter initialized: {requests_per_minute}/min, {requests_per_hour}/hour")
    
    async def allow_request(self) -> bool:
        """
        Check se il request è permesso
        
        Returns:
            True se permesso, False se rate limit exceeded
        """
        now = time.time()
        
        # Pulisci finestre vecchie
        self._clean_windows(now)
        
        # Check limits
        if len(self.minute_window) >= self.rpm_limit:
            logger.warning("Rate limit exceeded: requests per minute")
            return False
        
        if len(self.hour_window) >= self.rph_limit:
            logger.warning("Rate limit exceeded: requests per hour")
            return False
        
        # Aggiungi timestamp
        self.minute_window.append(now)
        self.hour_window.append(now)
        
        return True
    
    def _clean_windows(self, now: float):
        """Rimuovi timestamps vecchi dalle finestre"""
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # Pulisci minute window
        while self.minute_window and self.minute_window[0] < minute_ago:
            self.minute_window.popleft()
        
        # Pulisci hour window
        while self.hour_window and self.hour_window[0] < hour_ago:
            self.hour_window.popleft()
    
    def get_stats(self) -> Dict[str, int]:
        """Ottieni statistiche correnti"""
        return {
            "requests_last_minute": len(self.minute_window),
            "requests_last_hour": len(self.hour_window),
            "minute_limit": self.rpm_limit,
            "hour_limit": self.rph_limit
        }
    
    def reset(self):
        """Reset rate limiter"""
        self.minute_window.clear()
        self.hour_window.clear()
        logger.info("Rate limiter reset")


class ErrorHandler:
    """
    Centralizzato error handling con categorizzazione
    """
    
    ERROR_CATEGORIES = {
        'AUTH': 'Authentication Error',
        'RATE_LIMIT': 'Rate Limit Exceeded',
        'NOT_FOUND': 'Resource Not Found',
        'VALIDATION': 'Validation Error',
        'NETWORK': 'Network Error',
        'TWITTER': 'Twitter API Error',
        'INTERNAL': 'Internal Server Error'
    }
    
    def __init__(self):
        self.error_counts = {cat: 0 for cat in self.ERROR_CATEGORIES}
        logger.info("Error handler initialized")
    
    def categorize_error(self, error: Exception) -> str:
        """Categorizza l'errore per tipo"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        if 'auth' in error_str or 'unauthorized' in error_str:
            return 'AUTH'
        elif 'rate' in error_str or 'too many' in error_str:
            return 'RATE_LIMIT'
        elif 'not found' in error_str or '404' in error_str:
            return 'NOT_FOUND'
        elif 'validation' in error_str or 'invalid' in error_str:
            return 'VALIDATION'
        elif 'network' in error_str or 'connection' in error_str:
            return 'NETWORK'
        elif 'twitter' in error_str:
            return 'TWITTER'
        else:
            return 'INTERNAL'
    
    def format_error(self, error: Exception) -> Dict[str, Any]:
        """
        Formatta l'errore in risposta standard
        
        Args:
            error: Exception da formattare
        
        Returns:
            Dict con info errore
        """
        category = self.categorize_error(error)
        self.error_counts[category] += 1
        
        error_response = {
            "error": True,
            "category": category,
            "type": type(error).__name__,
            "message": str(error),
            "description": self.ERROR_CATEGORIES.get(category, 'Unknown Error'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.error(f"Error [{category}]: {error}", exc_info=True)
        
        return error_response
    
    def get_error_stats(self) -> Dict[str, int]:
        """Ottieni statistiche errori"""
        return self.error_counts.copy()
    
    def reset_stats(self):
        """Reset statistiche"""
        self.error_counts = {cat: 0 for cat in self.ERROR_CATEGORIES}
        logger.info("Error stats reset")


class RequestLogger:
    """
    Logger per tracking requests e performance
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.request_history = deque(maxlen=max_history)
        self.total_requests = 0
        self.start_time = time.time()
    
    def log_request(
        self, 
        endpoint: str, 
        method: str,
        status_code: int,
        duration: float,
        error: bool = False
    ):
        """Log un request"""
        self.total_requests += 1
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration_ms': round(duration * 1000, 2),
            'error': error
        }
        
        self.request_history.append(entry)
        
        log_msg = f"{method} {endpoint} - {status_code} - {entry['duration_ms']}ms"
        if error:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    def get_stats(self) -> Dict[str, Any]:
        """Ottieni statistiche requests"""
        if not self.request_history:
            return {
                "total_requests": self.total_requests,
                "recent_requests": 0,
                "avg_duration_ms": 0,
                "error_rate": 0
            }
        
        recent = list(self.request_history)
        durations = [r['duration_ms'] for r in recent]
        errors = sum(1 for r in recent if r['error'])
        
        return {
            "total_requests": self.total_requests,
            "recent_requests": len(recent),
            "avg_duration_ms": round(sum(durations) / len(durations), 2),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "error_rate": round(errors / len(recent) * 100, 2),
            "uptime_hours": round((time.time() - self.start_time) / 3600, 2)
        }
    
    def get_recent_requests(self, count: int = 50) -> list:
        """Ottieni ultimi N requests"""
        return list(self.request_history)[-count:]


def validate_tweet_text(text: str) -> tuple[bool, str]:
    """
    Valida testo tweet
    
    Returns:
        (is_valid, error_message)
    """
    if not text or not text.strip():
        return False, "Tweet text cannot be empty"
    
    if len(text) > 280:
        return False, f"Tweet too long: {len(text)}/280 characters"
    
    return True, ""


def sanitize_username(username: str) -> str:
    """Sanitizza username rimuovendo @ se presente"""
    return username.lstrip('@')


def format_timestamp(dt: datetime) -> str:
    """Formatta timestamp in formato ISO"""
    return dt.isoformat() if dt else None


def parse_tweet_id(tweet_id: str) -> str:
    """
    Estrai tweet ID da URL o ID diretto
    
    Args:
        tweet_id: ID o URL
    
    Returns:
        Tweet ID pulito
    """
    if 'twitter.com' in tweet_id or 'x.com' in tweet_id:
        # Extract ID from URL
        parts = tweet_id.split('/')
        for i, part in enumerate(parts):
            if part == 'status' and i + 1 < len(parts):
                return parts[i + 1].split('?')[0]
    
    return tweet_id
