```python
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import datetime
import logging

class WebSocketServer:
    """WebSocket server for real-time updates"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.connected_clients = set()
        self.logger = logging.getLogger(__name__)
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up Socket.IO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            try:
                # Client authentication would go here
                self.connected_clients.add(request.sid)
                self.logger.info(f"Client connected: {request.sid}")
                emit('connected', {'status': 'connected', 'client_id': request.sid})
            except Exception as e:
                self.logger.error(f"Connection error: {str(e)}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            try:
                self.connected_clients.discard(request.sid)
                self.logger.info(f"Client disconnected: {request.sid}")
            except Exception as e:
                self.logger.error(f"Disconnection error: {str(e)}")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Handle subscription to events"""
            try:
                room = data.get('room', 'dashboard')
                join_room(room)
                self.logger.info(f"Client {request.sid} joined room: {room}")
                emit('subscribed', {'room': room}, room=request.sid)
            except Exception as e:
                self.logger.error(f"Subscription error: {str(e)}")
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """Handle unsubscription from events"""
            try:
                room = data.get('room', 'dashboard')
                leave_room(room)
                self.logger.info(f"Client {request.sid} left room: {room}")
                emit('unsubscribed', {'room': room}, room=request.sid)
            except Exception as e:
                self.logger.error(f"Unsubscription error: {str(e)}")
        
        @self.socketio.on('heartbeat')
        def handle_heartbeat(data):
            """Handle client heartbeat"""
            try:
                emit('heartbeat_ack', {'timestamp': datetime.datetime.utcnow().isoformat()})
            except Exception as e:
                self.logger.error(f"Heartbeat error: {str(e)}")
        
        @self.socketio.on('request_update')
        def handle_request_update(data):
            """Handle manual update requests"""
            try:
                update_type = data.get('type', 'all')
                room = data.get('room', 'dashboard')
                
                # Broadcast update to all clients in the room
                self.emit_dashboard_update(room=room)
                self.logger.info(f"Update requested by {request.sid} for room: {room}")
            except Exception as e:
                self.logger.error(f"Update request error: {str(e)}")
    
    def emit_bot_detection(self, bot_data):
        """Emit new bot detection to all dashboard subscribers"""
        try:
            event_data = {
                'type': 'bot_detection',
                'data': bot_data,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
            self.socketio.emit('bot_detection', event_data, room='dashboard')
            self.logger.info(f"Emitted bot detection: {bot_data['fingerprint_hash']}")
        except Exception as e:
            self.logger.error(f"Bot detection emission error: {str(e)}")
    
    def emit_dashboard_update(self, room='dashboard'):
        """Emit comprehensive dashboard update"""
        try:
            update_data = {
                'type': 'dashboard_update',
                'data': {
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }
            }
            self.socketio.emit('dashboard_update', update_data, room=room)
            self.logger.info(f"Dashboard update emitted to room: {room}")
        except Exception as e:
            self.logger.error(f"Dashboard update emission error: {str(e)}")
    
    def emit_system_alert(self, alert_data):
        """Emit system alert"""
        try:
            event_data = {
                'type': 'system_alert',
                'data': alert_data,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
            self.socketio.emit('system_alert', event_data, room='dashboard')
            self.logger.info(f"System alert emitted: {alert_data.get('message')}")
        except Exception as e:
            self.logger.error(f"System alert emission error: {str(e)}")
    
    def emit_log_entry(self, log_data):
        """Emit new log entry"""
        try:
            event_data = {
                'type': 'log_entry',
                'data': log_data,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
            self.socketio.emit('log_entry', event_data, room='logs')
            self.logger.debug(f"Log entry emitted: {log_data.get('message')}")
        except Exception as e:
            self.logger.error(f"Log entry emission error: {str(e)}")
    
    def broadcast_connection_count(self):
        """Broadcast current connection count"""
        try:
            count_data = {
                'connected_clients': len(self.connected_clients),
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
            self.socketio.emit('connection_count', count_data, room='dashboard')
        except Exception as e:
            self.logger.error(f"Connection count broadcast error: {str(e)}")
```

```javascript