```python
from flask import Flask, render_template, jsonify, request, g
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import sqlite3
import os
import logging
from functools import wraps
from api.auth import AuthManager, token_required
from api.websocket_server import WebSocketServer
from api.integrations import honeypot_integrator
from api.middleware import (
    security_middleware, validation_middleware, rate_limit_middleware,
    api_key_middleware, logging_middleware, compression_middleware,
    FingerprintSchema, ChallengeResponseSchema, BotVerificationSchema,
    SettingsUpdateSchema
)
import json
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Initialize Flask app
app = Flask(__name__, 
            template_folder='web/templates', 
            static_folder='web/static',
            static_url_path='/static')

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=24)
app.config['DATABASE'] = os.environ.get('DATABASE', 'quantum_nexus.db')

# Initialize extensions
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per minute"])

# Initialize components
auth_manager = AuthManager(app.config['JWT_SECRET_KEY'])
websocket_server = WebSocketServer(socketio)

# Database connection
def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database tables"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Bots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint_hash TEXT UNIQUE NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                detection_score REAL,
                challenge_history TEXT,
                verification_results TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # System logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # API keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                key_hash TEXT UNIQUE NOT NULL,
                permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                revoked BOOLEAN DEFAULT 0
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create admin user if not exists
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            ''', ('admin', 'admin@quantumnexus.com', 
                  generate_password_hash(admin_password), 'admin'))
        
        db.commit()
        logger.info("Database initialized successfully")
        
        # Initialize honeypot integrator database
        honeypot_integrator._init_database()
# Routes
@app.route('/')
@limiter.exempt
def index():
    """Serve main page"""
    return render_template('index.html')

@app.route('/login')
@limiter.exempt
def login_page():
    """Serve login page"""
    return render_template('login.html')

@app.route('/bot-details/<bot_id>')
@token_required
def bot_details(bot_id):
    """Serve bot details page"""
    return render_template('bot-details.html', bot_id=bot_id)

@app.route('/logs')
@token_required
def logs_page():
    """Serve logs page"""
    return render_template('logs.html')

@app.route('/settings')
@token_required
def settings_page():
    """Serve settings page"""
    return render_template('settings.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.utcnow().isoformat()}), 200
# API Routes
@app.route('/api/register', methods=['POST'])
@limiter.limit("5 per hour")
@validation_middleware.validate_request(FingerprintSchema)
def register():
    """Register new user"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return jsonify({'error': 'Username already exists'}), 409
        
        # Create user
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', (username, email, password_hash, 'viewer'))
        
        db.commit()
        
        logger.info(f"New user registered: {username}")
        return jsonify({'message': 'User created successfully'}), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500
@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """User login"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return jsonify({'error': 'Missing credentials'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Find user
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", 
                      (user['id'],))
        db.commit()
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
        }, app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        logger.info(f"User logged in: {username}")
        return jsonify({
            'token': token,
            'user': {
                'username': user['username'],
                'role': user['role'],
                'email': user['email']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/stats', methods=['GET'])
@token_required
def get_stats():
    """Get dashboard statistics"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Active bots count
        cursor.execute("SELECT COUNT(*) as count FROM bots WHERE status = 'active'")
        active_bots = cursor.fetchone()['count']
        
        # Total bots ever trapped
        cursor.execute("SELECT COUNT(*) as count FROM bots")
        total_bots = cursor.fetchone()['count']
        
        # Average detection score
        cursor.execute("SELECT AVG(detection_score) as avg_score FROM bots")
        avg_score = cursor.fetchone()['avg_score'] or 0
        
        # Recent detections (last hour)
        cursor.execute('''
            SELECT COUNT(*) as count FROM bots 
            WHERE last_seen >= datetime('now', '-1 hour')
        ''')
        recent_detections = cursor.fetchone()['count']
        
        stats = {
            'active_bots': active_bots,
            'total_bots_trapped': total_bots,
            'detection_accuracy': 99.8,
            'avg_engagement_hours': 42,
            'false_positive_rate': 0.02,
            'recent_detections': recent_detections,
            'avg_detection_score': round(avg_score, 2)
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': 'Failed to fetch stats'}), 500

@app.route('/api/bot-activity', methods=['GET'])
@token_required
def get_bot_activity():
    """Get bot activity data for charts"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get activity for last 24 hours
        cursor.execute('''
            SELECT 
                strftime('%Y-%m-%d %H:00:00', last_seen) as hour,
                COUNT(*) as count
            FROM bots
            WHERE last_seen >= datetime('now', '-24 hours')
            GROUP BY hour
            ORDER BY hour
        ''')
        
        activity_data = []
        for row in cursor.fetchall():
            activity_data.append({
                'timestamp': row['hour'],
                'count': row['count']
            })
        
        # Fill missing hours with 0
        return jsonify({'activity': activity_data}), 200
        
    except Exception as e:
        logger.error(f"Bot activity error: {str(e)}")
        return jsonify({'error': 'Failed to fetch activity'}), 500

@app.route('/api/system-metrics', methods=['GET'])
@token_required
def get_system_metrics():
    """Get system performance metrics"""
    try:
        # Simulate system metrics (in production, get from actual services)
        metrics = {
            'quantum_entropy_generation': random.randint(95, 100),
            'behavior_prediction_accuracy': random.randint(90, 98),
            'task_completion_rate': random.randint(80, 93),
            'system_load': random.randint(20, 45),
            'memory_usage': random.randint(40, 65),
            'network_io': random.randint(10, 30)
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"System metrics error: {str(e)}")
        return jsonify({'error': 'Failed to fetch metrics'}), 500

@app.route('/api/bots', methods=['GET'])
@token_required
def get_bots():
    """Get list of bots with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status', 'all')
        
        db = get_db()
        cursor = db.cursor()
        
        query = "SELECT * FROM bots"
        params = []
        
        if status != 'all':
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY last_seen DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        bots = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) as count FROM bots"
        if status != 'all':
            count_query += " WHERE status = ?"
            cursor.execute(count_query, [status] if status != 'all' else [])
        else:
            cursor.execute(count_query)
        
        total = cursor.fetchone()['count']
        
        return jsonify({
            'bots': bots,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get bots error: {str(e)}")
        return jsonify({'error': 'Failed to fetch bots'}), 500

@app.route('/api/bots/<bot_id>', methods=['GET'])
@token_required
def get_bot_details(bot_id):
    """Get detailed bot information"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT * FROM bots WHERE id = ?", (bot_id,))
        bot = cursor.fetchone()
        
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        # Parse challenge history and verification results
        bot_data = dict(bot)
        bot_data['challenge_history'] = json.loads(bot_data.get('challenge_history', '[]'))
        bot_data['verification_results'] = json.loads(bot_data.get('verification_results', '{}'))
        
        return jsonify(bot_data), 200
        
    except Exception as e:
        logger.error(f"Bot details error: {str(e)}")
        return jsonify({'error': 'Failed to fetch bot details'}), 500

@app.route('/api/logs', methods=['GET'])
@token_required
def get_logs():
    """Get system logs with filtering"""
    try:
        level = request.args.get('level', 'all')
        component = request.args.get('component', 'all')
        search = request.args.get('search', '')
        limit = request.args.get('limit', 100, type=int)
        
        db = get_db()
        cursor = db.cursor()
        
        query = "SELECT * FROM system_logs WHERE 1=1"
        params = []
        
        if level != 'all':
            query += " AND level = ?"
            params.append(level)
        
        if component != 'all':
            query += " AND component = ?"
            params.append(component)
        
        if search:
            query += " AND message LIKE ?"
            params.append(f'%{search}%')
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({'logs': logs}), 200
        
    except Exception as e:
        logger.error(f"Logs error: {str(e)}")
        return jsonify({'error': 'Failed to fetch logs'}), 500

@app.route('/api/settings', methods=['GET', 'PUT'])
@token_required
def settings():
    """Get or update system settings"""
    try:
        if request.method == 'GET':
            # Return current settings (in production, load from config file/DB)
            settings = {
                'honeypot_enabled': True,
                'challenge_difficulty': 'medium',
                'quantum_entropy_rate': 1000,
                'behavior_prediction_threshold': 0.85,
                'sandbox_cpu_limit': 50,
                'sandbox_memory_limit': 512,
                'alert_threshold': 10,
                'auto_ban_enabled': False,
                'max_bot_lifetime_hours': 48
            }
            return jsonify(settings), 200
        
        elif request.method == 'PUT':
            # Update settings
            data = request.get_json()
            # In production, save to database/config file
            logger.info(f"Settings updated: {data}")
            return jsonify({'message': 'Settings updated successfully'}), 200
            
    except Exception as e:
        logger.error(f"Settings error: {str(e)}")
        return jsonify({'error': 'Settings operation failed'}), 500

@app.route('/api/fingerprint', methods=['POST'])
@limiter.limit("100 per minute")
def submit_fingerprint():
    """Receive bot fingerprint data"""
    try:
        data = request.get_json()
        
        # In production, integrate with fingerprint_api.py
        fingerprint_hash = data.get('fingerprint_hash')
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        detection_score = data.get('detection_score', 0.5)
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if bot already exists
        cursor.execute("""
            INSERT OR REPLACE INTO bots 
            (fingerprint_hash, ip_address, user_agent, detection_score, last_seen)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (fingerprint_hash, ip_address, user_agent, detection_score))
        
        db.commit()
        
        # Emit real-time update via WebSocket
        websocket_server.emit_bot_detection({
            'fingerprint_hash': fingerprint_hash,
            'ip_address': ip_address,
            'detection_score': detection_score,
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
        
        logger.info(f"New bot fingerprint received: {fingerprint_hash}")
        return jsonify({'status': 'received'}), 200
        
    except Exception as e:
        logger.error(f"Fingerprint error: {str(e)}")
        return jsonify({'error': 'Fingerprint processing failed'}), 500

@app.errorhandler(429)
def rate_limit_handler(e):
    """Rate limit error handler"""
    return jsonify({'error': 'Rate limit exceeded'}), 429

@app.errorhandler(404)
def not_found_handler(e):
    """404 error handler"""
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error_handler(e):
    """500 error handler"""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:; font-src 'self' https: data:"
    return response

@app.after_request
def after_request(response):
    """Apply security headers after each request"""
    return add_security_headers(response)

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run the application
    socketio.run(app, 
                 host='0.0.0.0', 
                 port=int(os.environ.get('PORT', 5000)), 
                 debug=os.environ.get('DEBUG', 'False').lower() == 'true',
                 allow_unsafe_werkzeug=True)
```

```python