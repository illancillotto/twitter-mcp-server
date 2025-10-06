"""
Test Suite per Twitter MCP Server
Usa pytest per testing automatizzato
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json

# Assumendo che il server sia importabile
from mcp_server.server import app
from mcp_server.twitter_client import TwitterClient
from mcp_server.utils import RateLimiter, ErrorHandler, validate_tweet_text

# ============ FIXTURES ============

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def mock_twitter_client():
    """Mock Twitter client per testing"""
    with patch('mcp_server.server.twitter_client') as mock:
        mock_instance = Mock(spec=TwitterClient)
        mock_instance.is_authenticated.return_value = True
        mock_instance.login = AsyncMock(return_value=True)
        mock_instance.create_tweet = AsyncMock(return_value={
            'id': '1234567890',
            'text': 'Test tweet',
            'created_at': '2025-01-01T00:00:00Z',
            'user': 'test_user'
        })
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def sample_tweet_data():
    """Sample tweet data per testing"""
    return {
        'text': 'This is a test tweet #testing',
        'media_paths': None,
        'reply_to': None
    }

# ============ HEALTH CHECK TESTS ============

class TestHealthEndpoint:
    """Test suite per health check"""
    
    def test_health_check_success(self, client):
        """Test health endpoint risponde correttamente"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'healthy'
        assert 'version' in data
    
    def test_health_check_structure(self, client):
        """Test struttura risposta health check"""
        response = client.get("/health")
        data = response.json()
        
        required_fields = ['status', 'authenticated', 'version']
        for field in required_fields:
            assert field in data

# ============ AUTHENTICATION TESTS ============

class TestAuthentication:
    """Test suite per autenticazione"""
    
    def test_login_success(self, client, mock_twitter_client):
        """Test login con credenziali valide"""
        payload = {
            'username': 'test_user',
            'email': 'test@example.com',
            'password': 'test_password'
        }
        
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.post("/auth/login", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'message' in data
    
    def test_login_missing_credentials(self, client):
        """Test login con credenziali mancanti"""
        payload = {
            'username': 'test_user'
            # Missing email and password
        }
        
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 422  # Validation error
    
    def test_auth_status_authenticated(self, client, mock_twitter_client):
        """Test auth status quando autenticato"""
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.get("/auth/status")
        
        assert response.status_code == 200
        data = response.json()
        assert 'authenticated' in data
    
    def test_logout_success(self, client, mock_twitter_client):
        """Test logout"""
        mock_twitter_client.logout = AsyncMock()
        
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.post("/auth/logout")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

# ============ TWEET OPERATIONS TESTS ============

class TestTweetOperations:
    """Test suite per operazioni tweet"""
    
    def test_create_tweet_success(self, client, mock_twitter_client, sample_tweet_data):
        """Test creazione tweet con successo"""
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.post("/tweets/create", json=sample_tweet_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'tweet_id' in data
    
    def test_create_tweet_not_authenticated(self, client):
        """Test creazione tweet senza autenticazione"""
        with patch('mcp_server.server.twitter_client', None):
            response = client.post("/tweets/create", json={'text': 'Test'})
        
        assert response.status_code == 401
    
    def test_create_tweet_empty_text(self, client, mock_twitter_client):
        """Test creazione tweet con testo vuoto"""
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.post("/tweets/create", json={'text': ''})
        
        # Dovrebbe fallire la validazione
        assert response.status_code in [400, 422, 500]
    
    def test_search_tweets_success(self, client, mock_twitter_client):
        """Test ricerca tweets"""
        mock_twitter_client.search_tweets = AsyncMock(return_value=[
            {
                'id': '123',
                'text': 'Test tweet',
                'user': {'name': 'Test User', 'screen_name': 'testuser'},
                'created_at': '2025-01-01T00:00:00Z',
                'favorite_count': 10,
                'retweet_count': 5
            }
        ])
        
        payload = {
            'query': 'python',
            'product': 'Latest',
            'count': 20
        }
        
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.post("/tweets/search", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'tweets' in data
        assert isinstance(data['tweets'], list)
    
    def test_like_tweet_success(self, client, mock_twitter_client):
        """Test like tweet"""
        mock_twitter_client.like_tweet = AsyncMock(return_value={'success': True})
        
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.post("/tweets/like?tweet_id=1234567890")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
    
    def test_delete_tweet_success(self, client, mock_twitter_client):
        """Test eliminazione tweet"""
        mock_twitter_client.delete_tweet = AsyncMock(return_value={'success': True})
        
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.delete("/tweets/1234567890")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

# ============ USER OPERATIONS TESTS ============

class TestUserOperations:
    """Test suite per operazioni utente"""
    
    def test_get_user_profile_success(self, client, mock_twitter_client):
        """Test recupero profilo utente"""
        mock_twitter_client.get_user_profile = AsyncMock(return_value={
            'id': '123',
            'name': 'Test User',
            'screen_name': 'testuser',
            'followers_count': 1000,
            'following_count': 500
        })
        
        payload = {'username': 'testuser'}
        
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.post("/users/profile", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'profile' in data
    
    def test_follow_user_success(self, client, mock_twitter_client):
        """Test follow utente"""
        mock_twitter_client.follow_user = AsyncMock(return_value={'success': True})
        
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            response = client.post("/users/follow?user_id=123")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

# ============ UTILS TESTS ============

class TestRateLimiter:
    """Test suite per rate limiter"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        """Test rate limiter permette requests entro limiti"""
        limiter = RateLimiter(requests_per_minute=10)
        
        # First request should be allowed
        assert await limiter.allow_request() == True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess(self):
        """Test rate limiter blocca requests in eccesso"""
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=5)
        
        # Allow first 2 requests
        for _ in range(2):
            assert await limiter.allow_request() == True
        
        # Third should be blocked
        assert await limiter.allow_request() == False
    
    def test_rate_limiter_get_stats(self):
        """Test statistiche rate limiter"""
        limiter = RateLimiter(requests_per_minute=30)
        stats = limiter.get_stats()
        
        assert 'requests_last_minute' in stats
        assert 'requests_last_hour' in stats
        assert 'minute_limit' in stats
        assert 'hour_limit' in stats

class TestErrorHandler:
    """Test suite per error handler"""
    
    def test_categorize_auth_error(self):
        """Test categorizzazione errori autenticazione"""
        handler = ErrorHandler()
        
        error = Exception("Unauthorized access")
        category = handler.categorize_error(error)
        
        assert category == 'AUTH'
    
    def test_categorize_rate_limit_error(self):
        """Test categorizzazione rate limit errors"""
        handler = ErrorHandler()
        
        error = Exception("Rate limit exceeded")
        category = handler.categorize_error(error)
        
        assert category == 'RATE_LIMIT'
    
    def test_format_error_structure(self):
        """Test struttura errore formattato"""
        handler = ErrorHandler()
        
        error = Exception("Test error")
        formatted = handler.format_error(error)
        
        required_fields = ['error', 'category', 'type', 'message', 'timestamp']
        for field in required_fields:
            assert field in formatted

class TestValidation:
    """Test suite per validazione"""
    
    def test_validate_tweet_text_valid(self):
        """Test validazione testo tweet valido"""
        text = "This is a valid tweet"
        is_valid, message = validate_tweet_text(text)
        
        assert is_valid == True
        assert message == ""
    
    def test_validate_tweet_text_empty(self):
        """Test validazione testo vuoto"""
        text = ""
        is_valid, message = validate_tweet_text(text)
        
        assert is_valid == False
        assert "empty" in message.lower()
    
    def test_validate_tweet_text_too_long(self):
        """Test validazione testo troppo lungo"""
        text = "x" * 300  # Over 280 chars
        is_valid, message = validate_tweet_text(text)
        
        assert is_valid == False
        assert "long" in message.lower()

# ============ INTEGRATION TESTS ============

class TestIntegration:
    """Test suite per integration testing"""
    
    @pytest.mark.integration
    def test_full_workflow_create_and_like(self, client, mock_twitter_client):
        """Test workflow completo: crea tweet e like"""
        # Setup mocks
        tweet_id = '1234567890'
        mock_twitter_client.create_tweet = AsyncMock(return_value={
            'id': tweet_id,
            'text': 'Test tweet',
            'created_at': '2025-01-01T00:00:00Z'
        })
        mock_twitter_client.like_tweet = AsyncMock(return_value={'success': True})
        
        with patch('mcp_server.server.twitter_client', mock_twitter_client):
            # 1. Create tweet
            create_response = client.post(
                "/tweets/create",
                json={'text': 'Test tweet'}
            )
            assert create_response.status_code == 200
            created_id = create_response.json()['tweet_id']
            
            # 2. Like the tweet
            like_response = client.post(f"/tweets/like?tweet_id={created_id}")
            assert like_response.status_code == 200

# ============ PERFORMANCE TESTS ============

class TestPerformance:
    """Test suite per performance"""
    
    @pytest.mark.performance
    def test_health_check_response_time(self, client):
        """Test tempo risposta health check"""
        import time
        
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 0.1  # Should respond in < 100ms

# ============ FIXTURES CLEANUP ============

@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup after each test"""
    yield
    # Cleanup code here if needed

# ============ RUN CONFIGURATION ============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=mcp_server"])
