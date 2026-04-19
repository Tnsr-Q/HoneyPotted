# HoneyPotted - Quantum Deception Nexus

A next-generation honeypot system with advanced bot manipulation and deception capabilities. HoneyPotted provides a sophisticated framework for detecting, analyzing, and trapping malicious bots while gathering valuable threat intelligence.

## Features

### Core Capabilities
- **Advanced Bot Detection**: Multi-layered fingerprinting and behavioral analysis
- **Real-time Monitoring**: Live dashboard with WebSocket-powered updates
- **Threat Intelligence**: Automated threat scoring and pattern recognition
- **Challenge System**: Dynamic verification challenges to identify and trap bots
- **Sandbox Environment**: Safe execution environment for analyzing malicious payloads
- **Machine Learning**: Integrated ML models for bot fingerprinting and classification
- **RESTful API**: Comprehensive API for integration and automation
- **Database Integration**: SQLite-based storage with migration support

### Security Features
- JWT-based authentication
- Rate limiting and CORS protection
- Session management
- Alert system with multiple notification channels (Email, Slack, Webhooks)
- SSL/TLS support
- Configurable security thresholds

### Integrations
- Redis for caching and message queuing
- Docker support for containerized deployment
- External threat intelligence APIs
- Geolocation services
- WebSocket real-time communication

## Architecture

```
HoneyPotted/
├── api/                    # Core API and backend logic
│   ├── app.py             # Flask application and routes
│   ├── auth.py            # Authentication handlers
│   ├── integrations.py    # External service integrations
│   ├── middleware.py      # Request/response middleware
│   ├── scheduler.py       # Background task scheduler
│   └── websocket_server.py # Real-time WebSocket server
├── honeypot/              # Honeypot modules
│   ├── challenge/         # Bot challenge system
│   ├── fingerprinting/    # Bot fingerprinting logic
│   ├── migrations/        # Database migrations
│   ├── sandbox/           # Sandboxed execution environment
│   └── verification/      # Bot verification system
├── web/                   # Frontend web interface
├── config/                # Configuration files
├── docker/                # Docker deployment files
├── components/            # Reusable UI components
├── main.py               # Application entry point
├── index.html            # Web dashboard
└── requirements.txt      # Python dependencies
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Redis server (for caching and messaging)
- Optional: Docker and Docker Compose

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Tnsr-Q/HoneyPotted.git
   cd HoneyPotted
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and configure your settings
   ```

4. **Initialize the database**
   ```bash
   python main.py --init-only
   ```

5. **Start the application**
   ```bash
   python main.py
   ```

The system will start on `http://localhost:5000` by default.

### Docker Deployment

```bash
docker-compose up -d
```

## Configuration

The application is configured via environment variables. Copy `.env.example` to `.env` and customize:

### Essential Settings
- `SECRET_KEY`: Application secret key
- `JWT_SECRET_KEY`: JWT authentication secret
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis server URL

### Honeypot Settings
- `HONEYPOT_PUBLIC_DOMAIN`: Public domain for the honeypot
- `HONEYPOT_LISTEN_PORT`: Port for honeypot services
- `HONEYPOT_SIGNAL_SAMPLE_RATE`: Signal sampling rate (0-1)

### Alerting
- `ALERT_EMAIL_ENABLED`: Enable email alerts
- `ALERT_SLACK_WEBHOOK`: Slack webhook URL
- `ALERT_WEBHOOK_URL`: Generic webhook endpoint
- `ALERT_THRESHOLD_SCORE`: Minimum threat score for alerts

See `.env.example` for complete configuration options.

## Usage

### Starting the Server

```bash
# Standard mode
python main.py

# Development mode with debug
python main.py --debug

# Custom host and port
python main.py --host 0.0.0.0 --port 8080

# Initialize components only
python main.py --init-only
```

### Accessing the Dashboard

Open your browser to `http://localhost:5000` to access the web dashboard where you can:
- Monitor active threats in real-time
- View bot statistics and analytics
- Configure honeypot modules
- Review captured data and logs
- Manage alerts and notifications

### API Endpoints

The RESTful API provides programmatic access:

- `GET /api/stats` - System statistics
- `GET /api/threats` - Recent threats
- `POST /api/challenge` - Create bot challenge
- `GET /api/fingerprints` - Bot fingerprints
- WebSocket at `/events` for real-time updates

Authentication required for most endpoints via JWT tokens.

## Development

### Running Tests

```bash
pytest
```

### Code Structure

- **main.py**: Application entry point and system orchestration
- **api/**: Backend API and business logic
- **honeypot/**: Core honeypot modules and detection systems
- **web/**: Frontend assets and dashboard
- **config/**: Configuration management

### Background Tasks

The system runs several background tasks:
- Database cleanup (hourly)
- Statistics aggregation (every 5 minutes)
- System health monitoring (every minute)

## Machine Learning

HoneyPotted includes ML-based bot detection:
- Fingerprint classification models
- Behavioral pattern recognition
- Anomaly detection
- Configurable model paths via `MACHINE_LEARNING_MODEL_PATH`

## Security Considerations

- **Change default secrets**: Update all keys in `.env`
- **Use HTTPS in production**: Configure SSL certificates
- **Secure Redis**: Protect Redis with password authentication
- **API key rotation**: Regularly rotate API keys
- **Monitor logs**: Review `quantum_nexus.log` regularly
- **Network isolation**: Deploy in isolated network segments

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

See LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/Tnsr-Q/HoneyPotted/issues
- Documentation: See inline code documentation

## Acknowledgments

Built with Flask, SocketIO, Redis, and modern web technologies.
