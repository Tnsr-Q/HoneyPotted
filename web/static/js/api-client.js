/**
 * API Client for Quantum Deception Nexus
 * Provides wrapper for HTTP requests and WebSocket management
 */

class APIClient {
    constructor() {
        this.baseURL = '/api';
        this.token = localStorage.getItem('token');
        this.refreshToken = localStorage.getItem('refresh_token');
        this.maxRetries = 3;
        this.retryDelay = 1000;
        this.eventListeners = new Map();
        this.socket = null;
        this.socketConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
    }

    /**
     * HTTP Request Wrapper with Error Handling and Retry Logic
     */
    async request(endpoint, options = {}, retryCount = 0) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        // Add authentication token if available
        if (this.token) {
            config.headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, config);
            
            // Handle unauthorized responses
            if (response.status === 401 && retryCount < this.maxRetries) {
                const refreshed = await this.refreshAuthToken();
                if (refreshed) {
                    config.headers['Authorization'] = `Bearer ${this.token}`;
                    return this.request(endpoint, options, retryCount + 1);
                }
            }

            // Handle rate limiting
            if (response.status === 429) {
                if (retryCount < this.maxRetries) {
                    await this.delay(this.retryDelay * Math.pow(2, retryCount));
                    return this.request(endpoint, options, retryCount + 1);
                }
            }

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Request failed');
            }
            
            return data;
        } catch (error) {
            if (retryCount < this.maxRetries) {
                await this.delay(this.retryDelay);
                return this.request(endpoint, options, retryCount + 1);
            }
            throw error;
        }
    }

    /**
     * GET Request
     */
    get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET' });
    }

    /**
     * POST Request
     */
    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT Request
     */
    put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE Request
     */
    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    /**
     * Authentication Methods
     */
    async login(username, password, rememberMe = false) {
        try {
            const response = await this.post('/login', { username, password });
            
            this.token = response.token;
            localStorage.setItem('token', this.token);
            
            if (rememberMe) {
                localStorage.setItem('remember_me', 'true');
            }
            
            this.broadcastEvent('authChange', { authenticated: true, user: response.user });
            return response;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    }

    async register(username, email, password) {
        return this.post('/register', { username, email, password });
    }

    logout() {
        this.token = null;
        localStorage.removeItem('token');
        localStorage.removeItem('remember_me');
        this.disconnectSocket();
        this.broadcastEvent('authChange', { authenticated: false });
    }

    isAuthenticated() {
        return !!this.token;
    }

    async refreshAuthToken() {
        try {
            // In production, implement proper token refresh logic
            this.logout();
            return false;
        } catch (error) {
            console.error('Token refresh failed:', error);
            this.logout();
            return false;
        }
    }

    /**
     * API Methods for Dashboard
     */
    async getStats() {
        return this.get('/stats');
    }

    async getBotActivity() {
        return this.get('/bot-activity');
    }

    async getSystemMetrics() {
        return this.get('/system-metrics');
    }

    async getBots(page = 1, perPage = 10, status = 'all') {
        return this.get('/bots', { page, per_page: perPage, status });
    }

    async getBotDetails(botId) {
        return this.get(`/bots/${botId}`);
    }

    async getLogs(level = 'all', component = 'all', search = '', limit = 100) {
        return this.get('/logs', { level, component, search, limit });
    }

    async getSettings() {
        return this.get('/settings');
    }

    async updateSettings(settings) {
        return this.put('/settings', settings);
    }

    /**
     * WebSocket Management
     */
    connectSocket() {
        if (this.socket?.connected) return;

        this.socket = io({
            transports: ['websocket', 'polling'],
            auth: {
                token: this.token
            }
        });

        this.setupSocketHandlers();
    }

    disconnectSocket() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
            this.socketConnected = false;
        }
    }

    setupSocketHandlers() {
        if (!this.socket) return;

        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.socketConnected = true;
            this.reconnectAttempts = 0;
            this.broadcastEvent('socketChange', { connected: true });
            
            // Subscribe to dashboard updates
            this.socket.emit('subscribe', { room: 'dashboard' });
        });

        this.socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            this.socketConnected = false;
            this.broadcastEvent('socketChange', { connected: false });
            
            // Attempt reconnection
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                setTimeout(() => this.connectSocket(), this.reconnectDelay);
            }
        });

        this.socket.on('bot_detection', (data) => {
            this.broadcastEvent('botDetection', data);
        });

        this.socket.on('dashboard_update', (data) => {
            this.broadcastEvent('dashboardUpdate', data);
        });

        this.socket.on('system_alert', (data) => {
            this.broadcastEvent('systemAlert', data);
        });

        this.socket.on('log_entry', (data) => {
            this.broadcastEvent('logEntry', data);
        });

        this.socket.on('heartbeat_ack', (data) => {
            this.broadcastEvent('heartbeatAck', data);
        });

        // Start heartbeat
        setInterval(() => {
            if (this.socket?.connected) {
                this.socket.emit('heartbeat', { timestamp: Date.now() });
            }
        }, 30000);
    }

    /**
     * Event System
     */
    on(event, callback) {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, new Set());
        }
        this.eventListeners.get(event).add(callback);
    }

    off(event, callback) {
        if (this.eventListeners.has(event)) {
            this.eventListeners.get(event).delete(callback);
        }
    }

    broadcastEvent(event, data) {
        const listeners = this.eventListeners.get(event);
        if (listeners) {
            listeners.forEach(callback => callback(data));
        }
    }

    /**
     * Utility Methods
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Create global instance
const apiClient = new APIClient();

// Auto-connect WebSocket if authenticated
if (apiClient.isAuthenticated()) {
    apiClient.connectSocket();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIClient;
}