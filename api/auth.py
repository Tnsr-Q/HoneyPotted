```python
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.security import check_password_hash
import sqlite3
from flask import g

def token_required(f):
    """Decorator to require JWT token for protected routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # "Bearer <token>"
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode token
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = {
                'user_id': data['user_id'],
                'username': data['username'],
                'role': data['role']
            }
            
            # Add to Flask global context
            g.current_user = current_user
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if hasattr(g, 'current_user') and g.current_user.get('role') == 'admin':
            return f(*args, **kwargs)
        return jsonify({'error': 'Admin access required'}), 403
    return decorated

class AuthManager:
    """Authentication manager for JWT tokens"""
    def __init__(self, secret_key):
        self.secret_key = secret_key
    
    def generate_token(self, user_id, username, role='viewer'):
        """Generate JWT token"""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            'iat': datetime.datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return {'error': 'Token expired'}
        except jwt.InvalidTokenError:
            return {'error': 'Invalid token'}
    
    def refresh_token(self, token):
        """Refresh expired token"""
        try:
            # Check if token is valid but expired
            payload = jwt.decode(token, self.secret_key, 
                               algorithms=['HS256'], 
                               options={'verify_exp': False})
            
            # Generate new token
            return self.generate_token(
                payload['user_id'], 
                payload['username'], 
                payload['role']
            )
        except jwt.InvalidTokenError:
            return None
```

```python