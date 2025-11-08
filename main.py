```python
#!/usr/bin/env python3
"""
Main entry point for Quantum Deception Nexus honeypot system.
Initializes all components and starts the application.
"""

import os
import sys
import signal
import logging
import argparse
from typing import Optional
import threading
import time

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import application components
from api.app import app, init_db, socketio
from api.integrations import honeypot_integrator
from api.scheduler import TaskScheduler
from api.websocket_server import WebSocketServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('quantum_nexus.log')
    ]
)
logger = logging.getLogger(__name__)

class QuantumNexusSystem:
    """Main system class for Quantum Deception Nexus."""
    
    def __init__(self):
        self.scheduler: Optional[TaskScheduler] = None
        self.websocket_server: Optional[WebSocketServer] = None
        self.shutdown_event = threading.Event()
        self.components = {}
        
    def initialize_components(self):
        """Initialize all honeypot components."""
        logger.info("Initializing honeypot components...")
        
        try:
            # Initialize database
            init_db()
            logger.info("Database initialized successfully")
            
            # Initialize integrator
            honeypot_integrator  # This ensures the global instance is created
            logger.info("Honeypot integrator initialized")
            
            # Initialize scheduler
            self.scheduler = TaskScheduler()
            self.scheduler.start()
            logger.info("Task scheduler started")
            
            # Initialize WebSocket server
            self.websocket_server = WebSocketServer(socketio)
            logger.info("WebSocket server initialized")
            
            # Store component references
            self.components = {
                'database': 'initialized',
                'integrator': honeypot_integrator,
                'scheduler': self.scheduler,
                'websocket': self.websocket_server
            }
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            return False
            
    def start_background_tasks(self):
        """Start background maintenance tasks."""
        logger.info("Starting background tasks...")
        
        try:
            # Start periodic database cleanup
            self.scheduler.add_task(
                'database_cleanup',
                self._cleanup_database,
                interval=3600  # Every hour
            )
            
            # Start statistics aggregation
            self.scheduler.add_task(
                'stats_aggregation',
                self._aggregate_statistics,
                interval=300  # Every 5 minutes
            )
            
            # Start system health monitoring
            self.scheduler.add_task(
                'health_monitor',
                self._monitor_system_health,
                interval=60  # Every minute
            )
            
            logger.info("Background tasks started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start background tasks: {e}")
            
    def _cleanup_database(self):
        """Clean up old database records."""
        try:
            logger.info("Running database cleanup...")
            # Implementation would go here
            # Remove old logs, expired sessions, etc.
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            
    def _aggregate_statistics(self):
        """Aggregate system statistics."""
        try:
            logger.info("Aggregating system statistics...")
            # Implementation would go here
            # Calculate daily/monthly stats, etc.
        except Exception as e:
            logger.error(f"Statistics aggregation failed: {e}")
            
    def _monitor_system_health(self):
        """Monitor system health and emit alerts."""
        try:
            logger.info("Monitoring system health...")
            # Implementation would go here
            # Check resource usage, component status, etc.
        except Exception as e:
            logger.error(f"Health monitoring failed: {e}")
            
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        logger.info("Signal handlers registered")
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
        
    def start_api_server(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """Start the Flask API server."""
        logger.info(f"Starting API server on {host}:{port}")
        
        try:
            # Run the Flask app with SocketIO
            socketio.run(
                app, 
                host=host, 
                port=port, 
                debug=debug,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            logger.error(f"API server failed to start: {e}")
            raise
            
    def health_check(self) -> dict:
        """Perform system health check."""
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'components': {}
        }
        
        # Check each component
        for name, component in self.components.items():
            try:
                if hasattr(component, 'health_check'):
                    health_status['components'][name] = component.health_check()
                else:
                    health_status['components'][name] = 'OK'
            except Exception as e:
                health_status['components'][name] = f'ERROR: {str(e)}'
                health_status['status'] = 'degraded'
                
        return health_status
        
    def shutdown(self):
        """Gracefully shutdown the system."""
        logger.info("Initiating system shutdown...")
        
        # Set shutdown event
        self.shutdown_event.set()
        
        try:
            # Stop scheduler
            if self.scheduler:
                self.scheduler.stop()
                logger.info("Scheduler stopped")
                
            # Close integrator connections
            honeypot_integrator.close()
            logger.info("Integrator connections closed")
            
            # Stop WebSocket server
            if self.websocket_server:
                # WebSocket will be stopped when Flask shuts down
                pass
                
            logger.info("System shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            # Force exit if needed
            sys.exit(0)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Quantum Deception Nexus Honeypot System')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--init-only', action='store_true', help='Initialize components and exit')
    
    args = parser.parse_args()
    
    # Create system instance
    system = QuantumNexusSystem()
    
    try:
        # Setup signal handlers
        system.setup_signal_handlers()
        
        # Initialize components
        if not system.initialize_components():
            logger.error("Failed to initialize components")
            sys.exit(1)
            
        # If init-only flag is set, exit after initialization
        if args.init_only:
            logger.info("Initialization complete, exiting due to --init-only flag")
            sys.exit(0)
            
        # Start background tasks
        system.start_background_tasks()
        
        # Start API server
        system.start_api_server(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        system.shutdown()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        system.shutdown()
        sys.exit(1)

if __name__ == '__main__':
    main()
```