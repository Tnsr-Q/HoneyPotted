```python
"""
Middleware for Quantum Deception Nexus API.
Includes security, validation, rate limiting, and logging middleware.
"""

import functools
import time
import re
import json
import logging
from typing import Callable, Dict, Any
from flask import request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
import hashlib
import secrets
from marshmallow import Schema, fields, ValidationError
from werkzeug.exceptions import HTTPException

# Configure logging
logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Security middleware for CSRF protection and request validation."""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        self.secret_key = app.config.get('SECRET_KEY', 'default-secret-key')
        
        # Register error handlers
        app.register_error_handler(400, self.handle_bad_request)
        app.register_error_handler(401, self.handle_unauthorized)
        app.register_error_handler(403, self.handle_forbidden)
        app.register_error_handler(429, self.handle_rate_limit_exceeded)
        
    def handle_bad_request(self, e):
        """Handle 400 Bad Request errors."""
        return jsonify({'error': 'Bad Request', 'message': str(e)}), 400
        
    def handle_unauthorized(self, e):
        """Handle 401 Unauthorized errors."""
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
        
    def handle_forbidden(self, e):
        """Handle 403 Forbidden errors."""
        return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403
        
    def handle_rate_limit_exceeded(self, e):
        """Handle 429 Rate Limit Exceeded errors."""
        return jsonify({'error': 'Rate Limit Exceeded', 'message': str(e)}), 429
        
    def csrf_protect(self, f):
        """CSRF protection decorator for state-changing requests."""
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip CSRF for GET, HEAD, OPTIONS requests
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                return f(*args, **kwargs)
                
            # Check for CSRF token in headers or form data
            csrf_token = (
                request.headers.get('X-CSRF-Token') or
                request.form.get('csrf_token') or
                request.json.get('csrf_token') if request.is_json else None
            )
            
            if not csrf_token:
                logger.warning(f"CSRF token missing for {request.method} {request.path}")
                return jsonify({'error': 'CSRF token required'}), 403
                
            # Validate CSRF token
            if not self._validate_csrf_token(csrf_token):
                logger.warning(f"Invalid CSRF token for {request.method} {request.path}")
                return jsonify({'error': 'Invalid CSRF token'}), 403
                
            return f(*args, **kwargs)
        return decorated_function
        
    def _validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token."""
        # In production, use secure token generation and validation
        # This is a simplified implementation
        try:
            # Hash the token with secret key for validation
            expected_token = hashlib.sha256(
                f"{self.secret_key}{g.get('user_id', 'anonymous')}".encode()
            ).hexdigest()
            return token == expected_token
        except:
            return False
            
    def generate_csrf_token(self) -> str:
        """Generate a CSRF token for the current session."""
        return hashlib.sha256(
            f"{self.secret_key}{g.get('user_id', 'anonymous')}".encode()
        ).hexdigest()

class ValidationMiddleware:
    """Request validation middleware using Marshmallow schemas."""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        pass
        
    def validate_request(self, schema_class: Schema):
        """Validate request data against a Marshmallow schema."""
        def decorator(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                schema = schema_class()
                
                # Validate JSON data
                if request.is_json:
                    try:
                        data = schema.load(request.json)
                        g.validated_data = data
                    except ValidationError as err:
                        logger.warning(f"Validation error: {err.messages}")
                        return jsonify({'error': 'Validation failed', 'details': err.messages}), 400
                # Validate form data
                elif request.form:
                    try:
                        data = schema.load(request.form)
                        g.validated_data = data
                    except ValidationError as err:
                        logger.warning(f"Validation error: {err.messages}")
                        return jsonify({'error': 'Validation failed', 'details': err.messages}), 400
                else:
                    # No data to validate
                    g.validated_data = {}
                    
                return f(*args, **kwargs)
            return decorated_function
        return decorator

class RateLimitMiddleware:
    """Rate limiting middleware with Redis backend support."""
    
    def __init__(self, app=None, redis_client=None):
        self.app = app
        self.redis_client = redis_client
        self.limiter = None
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        # Initialize Flask-Limiter
        self.limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per minute"],
            storage_uri=app.config.get('REDIS_URL', 'memory://')
        )
        
    def limit(self, limit_value: str, per_method: bool = False):
        """Apply rate limiting to a route."""
        if self.limiter:
            return self.limiter.limit(limit_value, per_method=per_method)
        else:
            # Fallback to no-op decorator
            def noop_decorator(f):
                return f
            return noop_decorator

class APIKeyMiddleware:
    """API key authentication middleware for external integrations."""
    
    def __init__(self, app=None):
        self.app = app
        self.api_keys = {}  # In production, store in secure database
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        # Load API keys from configuration
        api_keys_config = app.config.get('API_KEYS', {})
        self.api_keys.update(api_keys_config)
        
    def authenticate_api_key(self, f):
        """API key authentication decorator."""
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for API key in headers
            api_key = (
                request.headers.get('X-API-Key') or
                request.args.get('api_key')
            )
            
            if not api_key:
                return jsonify({'error': 'API key required'}), 401
                
            if not self._validate_api_key(api_key):
                logger.warning(f"Invalid API key used: {api_key[:8]}...")
                return jsonify({'error': 'Invalid API key'}), 401
                
            # Store API key info in g
            g.api_key = api_key
            g.api_key_info = self.api_keys.get(api_key, {})
            
            return f(*args, **kwargs)
        return decorated_function
        
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        return api_key in self.api_keys
        
    def generate_api_key(self, name: str, permissions: list = None) -> str:
        """Generate a new API key."""
        key = secrets.token_urlsafe(32)
        self.api_keys[key] = {
            'name': name,
            'permissions': permissions or ['read'],
            'created_at': time.time(),
            'last_used': None
        }
        return key
        
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            return True
        return False

class LoggingMiddleware:
    """Request/response logging middleware for audit trail."""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        # Register before/after request handlers
        app.before_request(self.log_request)
        app.after_request(self.log_response)
        
    def log_request(self):
        """Log incoming request."""
        g.start_time = time.time()
        
        logger.info(
            f"Request: {request.method} {request.path} "
            f"from {request.remote_addr} "
            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
        )
        
    def log_response(self, response):
        """Log outgoing response."""
        duration = time.time() - g.get('start_time', time.time())
        
        logger.info(
            f"Response: {response.status_code} "
            f"for {request.method} {request.path} "
            f"in {duration:.3f}s"
        )
        
        return response

class CompressionMiddleware:
    """Compression middleware for large responses."""
    
    def __init__(self, app=None, min_size: int = 500):
        self.app = app
        self.min_size = min_size
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        app.after_request(self.compress_response)
        
    def compress_response(self, response):
        """Compress response if it's large enough."""
        # Check if response should be compressed
        if (response.status_code < 300 and 
            len(response.get_data()) > self.min_size and
            'gzip' in request.headers.get('Accept-Encoding', '')):
            
            # Check if already compressed
            if 'Content-Encoding' not in response.headers:
                try:
                    import gzip
                    from io import BytesIO
                    
                    # Compress response data
                    gzip_buffer = BytesIO()
                    with gzip.GzipFile(mode='wb', fileobj=gzip_buffer) as gz_file:
                        gz_file.write(response.get_data())
                    
                    response.set_data(gzip_buffer.getvalue())
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Vary'] = 'Accept-Encoding'
                    response.headers['Content-Length'] = len(response.get_data())
                except Exception as e:
                    logger.warning(f"Compression failed: {e}")
                    
        return response

# Predefined validation schemas
class FingerprintSchema(Schema):
    """Schema for fingerprint data validation."""
    fingerprint_hash = fields.Str(required=True)
    detection_score = fields.Float(required=True, validate=lambda x: 0 <= x <= 1)
    components = fields.List(fields.Str(), required=False)
    ip_address = fields.Str(required=False)
    user_agent = fields.Str(required=False)

class ChallengeResponseSchema(Schema):
    """Schema for challenge response validation."""
    challenge_id = fields.Str(required=True)
    response = fields.Raw(required=True)
    timestamp = fields.Float(required=False)

class BotVerificationSchema(Schema):
    """Schema for bot verification data validation."""
    fingerprint_hash = fields.Str(required=True)
    evidence = fields.Dict(required=True)
    confidence_threshold = fields.Float(required=False, validate=lambda x: 0 <= x <= 1)

class SettingsUpdateSchema(Schema):
    """Schema for settings update validation."""
    honeypot = fields.Dict(required=False)
    challenge = fields.Dict(required=False)
    verification = fields.Dict(required=False)
    sandbox = fields.Dict(required=False)
    alerts = fields.Dict(required=False)

# Global middleware instances
security_middleware = SecurityMiddleware()
validation_middleware = ValidationMiddleware()
rate_limit_middleware = RateLimitMiddleware()
api_key_middleware = APIKeyMiddleware()
logging_middleware = LoggingMiddleware()
compression_middleware = CompressionMiddleware()

# Export for module usage
__all__ = [
    "SecurityMiddleware", "ValidationMiddleware", "RateLimitMiddleware",
    "APIKeyMiddleware", "LoggingMiddleware", "CompressionMiddleware",
    "security_middleware", "validation_middleware", "rate_limit_middleware",
    "api_key_middleware", "logging_middleware", "compression_middleware",
    "FingerprintSchema", "ChallengeResponseSchema", "BotVerificationSchema",
    "SettingsUpdateSchema"
]
```