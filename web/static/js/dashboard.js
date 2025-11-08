/**
 * Dashboard Controller for Quantum Deception Nexus
 * Handles all dashboard data fetching, visualization, and real-time updates
 */

class DashboardController {
    constructor() {
        this.charts = {};
        this.isLoading = false;
        this.updateInterval = null;
        this.init();
    }

    /**
     * Initialize dashboard
     */
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startRealTimeUpdates();
    }

    /**
     * Setup event listeners for API and UI events
     */
    setupEventListeners() {
        // Auth state changes
        apiClient.on('authChange', (data) => {
            if (data.authenticated) {
                this.loadInitialData();
                apiClient.connectSocket();
            } else {
                this.stopRealTimeUpdates();
                apiClient.disconnectSocket();
            }
        });

        // Socket connection changes
        apiClient.on('socketChange', (data) => {
            this.updateConnectionStatus(data.connected);
        });

        // Real-time bot detection
        apiClient.on('botDetection', (data) => {
            this.handleBotDetection(data);
        });

        // Dashboard updates
        apiClient.on('dashboardUpdate', (data) => {
            this.refreshData();
        });

        // System alerts
        apiClient.on('systemAlert', (data) => {
            this.showSystemAlert(data);
        });

        // Navigation events
        document.addEventListener('DOMContentLoaded', () => {
            const modulesLink = document.querySelector('a[href="#modules"]');
            const dashboardLink = document.querySelector('a[href="#dashboard"]');
            
            if (modulesLink) modulesLink.addEventListener('click', this.handleSmoothScroll);
            if (dashboardLink) dashboardLink.addEventListener('click', this.handleSmoothScroll);
        });
    }

    /**
     * Load initial dashboard data
     */
    async loadInitialData() {
        if (!apiClient.isAuthenticated()) return;

        this.showLoadingState();
        
        try {
            await Promise.all([
                this.loadStats(),
                this.loadBotActivity(),
                this.loadSystemMetrics(),
                this.loadBotList()
            ]);
            
            this.hideLoadingState();
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showErrorMessage('Failed to load dashboard data. Please refresh the page.');
            this.hideLoadingState();
        }
    }

    /**
     * Load and display statistics
     */
    async loadStats() {
        try {
            const stats = await apiClient.getStats();
            
            // Update stats cards
            this.updateStatCard('active-bots', stats.active_bots, 'Active Bots Trapped');
            this.updateStatCard('detection-accuracy', `${stats.detection_accuracy}%`, 'Detection Accuracy');
            this.updateStatCard('engagement-time', `${stats.avg_engagement_hours}h`, 'Avg Engagement Time');
            this.updateStatCard('false-positives', `${stats.false_positive_rate}%`, 'False Positives');
            
            // Update hero section stats
            const heroStats = document.querySelector('#hero-stats');
            if (heroStats) {
                heroStats.innerHTML = `
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
                        <div class="text-center">
                            <div class="text-2xl font-bold text-green-400">${stats.active_bots}</div>
                            <div class="text-sm text-gray-400">Active Bots</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-blue-400">${stats.total_bots_trapped}</div>
                            <div class="text-sm text-gray-400">Total Trapped</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-purple-400">${stats.avg_detection_score}</div>
                            <div class="text-sm text-gray-400">Avg Score</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-yellow-400">${stats.recent_detections}</div>
                            <div class="text-sm text-gray-400">Recent</div>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
            throw error;
        }
    }

    /**
     * Update individual stat card
     */
    updateStatCard(id, value, label) {
        const card = document.querySelector(`[data-stat="${id}"]`);
        if (card) {
            const valueElement = card.querySelector('.stat-value');
            const labelElement = card.querySelector('.stat-label');
            
            if (valueElement) valueElement.textContent = value;
            if (labelElement) labelElement.textContent = label;
        }
    }

    /**
     * Load bot activity chart data
     */
    async loadBotActivity() {
        try {
            const activityData = await apiClient.getBotActivity();
            
            if (window.Chart && activityData.activity) {
                this.renderBotActivityChart(activityData.activity);
            }
        } catch (error) {
            console.error('Failed to load bot activity:', error);
        }
    }

    /**
     * Render bot activity chart
     */
    renderBotActivityChart(activityData) {
        const ctx = document.getElementById('bot-activity-chart');
        if (!ctx) return;

        const chartData = this.prepareChartData(activityData);
        
        if (this.charts.activity) {
            this.charts.activity.destroy();
        }

        this.charts.activity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Bot Detections',
                    data: chartData.values,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    }
                }
            }
        });
    }

    /**
     * Load system metrics
     */
    async loadSystemMetrics() {
        try {
            const metrics = await apiClient.getSystemMetrics();
            this.updatePerformanceBars(metrics);
        } catch (error) {
            console.error('Failed to load system metrics:', error);
        }
    }

    /**
     * Update performance bars
     */
    updatePerformanceBars(metrics) {
        const bars = [
            { key: 'quantum_entropy_generation', selector: '.bg-green-500', value: metrics.quantum_entropy_generation },
            { key: 'behavior_prediction_accuracy', selector: '.bg-blue-500', value: metrics.behavior_prediction_accuracy },
            { key: 'task_completion_rate', selector: '.bg-purple-500', value: metrics.task_completion_rate }
        ];

        bars.forEach(bar => {
            const element = document.querySelector(bar.selector);
            const valueElement = element?.parentElement?.parentElement?.querySelector('.text-right span');
            
            if (element) {
                element.style.width = `${bar.value}%`;
            }
            if (valueElement) {
                valueElement.textContent = `${bar.value}%`;
            }
        });
    }

    /**
     * Load bot list
     */
    async loadBotList() {
        try {
            const botData = await apiClient.getBots(1, 5);
            this.renderBotList(botData.bots);
        } catch (error) {
            console.error('Failed to load bot list:', error);
        }
    }

    /**
     * Render bot list
     */
    renderBotList(bots) {
        const container = document.querySelector('#recent-bots-list');
        if (!container) return;

        container.innerHTML = bots.map(bot => `
            <div class="bg-gray-800 rounded-lg p-4 flex items-center justify-between hover:bg-gray-700 transition-colors">
                <div>
                    <div class="text-sm font-medium text-white">${bot.fingerprint_hash.substring(0, 16)}...</div>
                    <div class="text-xs text-gray-400">${bot.ip_address || 'Unknown IP'}</div>
                    <div class="text-xs text-gray-500">${new Date(bot.last_seen).toLocaleString()}</div>
                </div>
                <div class="text-right">
                    <div class="text-sm font-bold ${this.getScoreColor(bot.detection_score || 0.5)}">
                        ${Math.round((bot.detection_score || 0.5) * 100)}%
                    </div>
                    <div class="text-xs text-gray-400 capitalize">${bot.status}</div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Get color based on detection score
     */
    getScoreColor(score) {
        if (score >= 0.8) return 'text-red-400';
        if (score >= 0.5) return 'text-yellow-400';
        return 'text-green-400';
    }

    /**
     * Prepare chart data from API response
     */
    prepareChartData(activityData) {
        const labels = [];
        const values = [];
        
        activityData.forEach(item => {
            const date = new Date(item.timestamp);
            labels.push(date.toLocaleDateString() + ' ' + date.getHours() + ':00');
            values.push(item.count);
        });
        
        return { labels, values };
    }

    /**
     * Handle real-time bot detection
     */
    handleBotDetection(data) {
        this.showNotification(
            'New Bot Detected',
            `Detection Score: ${Math.round(data.detection_score * 100)}%`,
            'info'
        );
        
        // Refresh stats and bot list
        this.loadStats();
        this.loadBotList();
    }

    /**
     * Show system alert
     */
    showSystemAlert(data) {
        const alertElement = document.createElement('div');
        alertElement.className = 'fixed top-4 right-4 bg-red-600 text-white px-6 py-4 rounded-lg shadow-lg z-50 max-w-md';
        alertElement.innerHTML = `
            <div class="flex items-start">
                <i data-feather="alert-triangle" class="w-5 h-5 mr-3 mt-0.5 flex-shrink-0"></i>
                <div>
                    <div class="font-semibold">${data.title || 'System Alert'}</div>
                    <div class="text-sm opacity-90">${data.message}</div>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
                    <i data-feather="x" class="w-4 h-4"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(alertElement);
        feather.replace();
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (alertElement.parentElement) {
                alertElement.remove();
            }
        }, 10000);
    }

    /**
     * Show notification
     */
    showNotification(title, message, type = 'info') {
        const colors = {
            info: 'bg-blue-600',
            success: 'bg-green-600',
            warning: 'bg-yellow-600',
            error: 'bg-red-600'
        };
        
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50`;
        notification.innerHTML = `
            <div class="flex items-center">
                <i data-feather="info" class="w-5 h-5 mr-2"></i>
                <div>
                    <div class="font-semibold">${title}</div>
                    <div class="text-sm opacity-90">${message}</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        feather.replace();
        
        setTimeout(() => notification.remove(), 5000);
    }

    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        // Refresh data every 30 seconds
        this.updateInterval = setInterval(() => {
            if (apiClient.isAuthenticated() && apiClient.socketConnected) {
                this.refreshData();
            }
        }, 30000);
    }

    /**
     * Stop real-time updates
     */
    stopRealTimeUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Refresh all dashboard data
     */
    async refreshData() {
        try {
            await Promise.all([
                this.loadStats(),
                this.loadSystemMetrics()
            ]);
        } catch (error) {
            console.error('Refresh failed:', error);
        }
    }

    /**
     * Handle smooth scrolling
     */
    handleSmoothScroll(e) {
        e.preventDefault();
        const targetId = e.currentTarget.getAttribute('href');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }

    /**
     * Loading states
     */
    showLoadingState() {
        this.isLoading = true;
        document.body.classList.add('loading');
        
        // Add loading skeletons to stats cards
        const statsCards = document.querySelectorAll('.bg-gray-700');
        statsCards.forEach(card => {
            if (!card.querySelector('.skeleton')) {
                card.innerHTML = '<div class="skeleton h-8 w-24 mx-auto mb-2"></div>' +
                               '<div class="skeleton h-4 w-32 mx-auto"></div>';
            }
        });
    }

    hideLoadingState() {
        this.isLoading = false;
        document.body.classList.remove('loading');
        
        // Remove skeletons
        const skeletons = document.querySelectorAll('.skeleton');
        skeletons.forEach(skeleton => skeleton.remove());
    }

    /**
     * Show error message
     */
    showErrorMessage(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded fixed top-20 left-1/2 transform -translate-x-1/2 z-50';
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(connected) {
        const indicator = document.querySelector('#connection-status');
        if (indicator) {
            indicator.className = connected ? 'bg-green-500' : 'bg-red-500';
            indicator.title = connected ? 'Connected' : 'Disconnected';
        }
    }
}

// Initialize dashboard controller when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardController = new DashboardController();
});