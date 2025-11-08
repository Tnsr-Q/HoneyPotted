```python
"""
Production configuration for Quantum Deception Nexus.
Environment-based configuration loading and security settings.
"""

import os
from typing import Dict, List, Optional

class ProductionConfig:
    """Production configuration class."""
    
    # Security settings
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'change-this-in-production')
    JWT_SECRET_KEY: str = os.environ.get('JWT_SECRET_KEY', 'change-this-jwt-key-in-production')
    
    # Database configuration
    DATABASE_URL: str = os.environ.get('DATABASE_URL', 'sqlite:///quantum_nexus.db')
    DATABASE_POOL_SIZE: int = int(os.environ.get('DATABASE_POOL_SIZE', '20'))
    DATABASE_MAX_OVERFLOW: int = int(os.environ.get('DATABASE_MAX_OVERFLOW', '10'))
    
    # Redis configuration (for rate limiting and caching)
    REDIS_URL: str = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # CORS settings
    CORS_ORIGINS: List[str] = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_METHODS: List[str] = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_HEADERS: List[str] = ['Content-Type', 'Authorization', 'X-CSRF-Token']
    
    # SSL/TLS configuration
    SSL_ENABLED: bool = os.environ.get('SSL_ENABLED', 'False').lower() == 'true'
    SSL_CERT_FILE: Optional[str] = os.environ.get('SSL_CERT_FILE')
    SSL_KEY_FILE: Optional[str] = os.environ.get('SSL_KEY_FILE')
    
    # Rate limiting configuration
    RATELIMIT_DEFAULT: str = os.environ.get('RATELIMIT_DEFAULT', '200 per minute')
    RATELIMIT_STORAGE_URL: str = os.environ.get('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/1')
    
    # Logging configuration
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.environ.get(
        'LOG_FORMAT',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    LOG_FILE: Optional[str] = os.environ.get('LOG_FILE')
    LOG_MAX_BYTES: int = int(os.environ.get('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.environ.get('LOG_BACKUP_COUNT', '5'))
    
    # API settings
    API_KEYS: Dict[str, Dict] = {
        # Example API key - replace with actual keys in production
        # os.environ.get('EXAMPLE_API_KEY', 'example-key'): {
        #     'name': 'Example Integration',
        #     'permissions': ['read', 'write']
        # }
    }
    
    # Honeypot settings
    HONEYPOT_PORTS: List[int] = [int(p) for p in os.environ.get('HONEYPOT_PORTS', '80,443,22,21').split(',')]
    HONEYPOT_DOMAINS: List[str] = os.environ.get('HONEYPOT_DOMAINS', 'example.com,secure.net').split(',')
    DETECTION_THRESHOLD: float = float(os.environ.get('DETECTION_THRESHOLD', '0.7'))
    MAX_CONCURRENT_BOTS: int = int(os.environ.get('MAX_CONCURRENT_BOTS', '100'))
    
    # Challenge settings
    CHALLENGE_DIFFICULTY: str = os.environ.get('CHALLENGE_DIFFICULTY', 'medium')
    CHALLENGE_TIME_LIMIT: int = int(os.environ.get('CHALLENGE_TIME_LIMIT', '300'))
    CHALLENGE_RETRY_ATTEMPTS: int = int(os.environ.get('CHALLENGE_RETRY_ATTEMPTS', '3'))
    
    # Verification settings
    CONSENSUS_THRESHOLD: float = float(os.environ.get('CONSENSUS_THRESHOLD', '0.8'))
    WORKER_RELIABILITY_SCORE: float = float(os.environ.get('WORKER_RELIABILITY_SCORE', '0.9'))
    VERIFICATION_TIMEOUT: int = int(os.environ.get('VERIFICATION_TIMEOUT', '60'))
    MAX_VERIFICATION_WORKERS: int = int(os.environ.get('MAX_VERIFICATION_WORKERS', '10'))
    
    # Sandbox settings
    SANDBOX_CPU_LIMIT: int = int(os.environ.get('SANDBOX_CPU_LIMIT', '50'))
    SANDBOX_MEMORY_LIMIT: int = int(os.environ.get('SANDBOX_MEMORY_LIMIT', '512'))
    SANDBOX_TIMEOUT: int = int(os.environ.get('SANDBOX_TIMEOUT', '300'))
    NETWORK_ISOLATION: str = os.environ.get('NETWORK_ISOLATION', 'partial')
    
    # Alert settings
    ALERT_EMAIL: Optional[str] = os.environ.get('ALERT_EMAIL')
    ALERT_WEBHOOK_URL: Optional[str] = os.environ.get('ALERT_WEBHOOK_URL')
    ALERT_THRESHOLD: str = os.environ.get('ALERT_THRESHOLD', 'medium')
    SLACK_ENABLED: bool = os.environ.get('SLACK_ENABLED', 'False').lower() == 'true'
    
    # Backup settings
    BACKUP_ENABLED: bool = os.environ.get('BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_SCHEDULE: str = os.environ.get('BACKUP_SCHEDULE', '0 2 * * *')  # Daily at 2 AM
    BACKUP_RETENTION_DAYS: int = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
    
    @classmethod
    def validate(cls):
        """Validate configuration settings."""
        errors = []
        
        # Validate required security settings
        if cls.SECRET_KEY == 'change-this-in-production':
            errors.append("SECRET_KEY must be changed in production")
            
        if cls.JWT_SECRET_KEY == 'change-this-jwt-key-in-production':
            errors.append("JWT_SECRET_KEY must be changed in production")
            
        # Validate SSL configuration
        if cls.SSL_ENABLED and (not cls.SSL_CERT_FILE or not cls.SSL_KEY_FILE):
            errors.append("SSL_CERT_FILE and SSL_KEY_FILE must be set when SSL is enabled")
            
        # Validate honeypot settings
        if not cls.HONEYPOT_PORTS:
            errors.append("HONEYPOT_PORTS must be configured")
            
        if not cls.HONEYPOT_DOMAINS:
            errors.append("HONEYPOT_DOMAINS must be configured")
            
        # Validate thresholds
        if not 0 <= cls.DETECTION_THRESHOLD <= 1:
            errors.append("DETECTION_THRESHOLD must be between 0 and 1")
            
        if not 0 <= cls.CONSENSUS_THRESHOLD <= 1:
            errors.append("CONSENSUS_THRESHOLD must be between 0 and 1")
            
        if not 0 <= cls.WORKER_RELIABILITY_SCORE <= 1:
            errors.append("WORKER_RELIABILITY_SCORE must be between 0 and 1")
            
        return errors

# Convenience function to get configuration
def get_config() -> ProductionConfig:
    """Get production configuration instance."""
    return ProductionConfig()

# Export for module usage
__all__ = ["ProductionConfig", "get_config"]
```