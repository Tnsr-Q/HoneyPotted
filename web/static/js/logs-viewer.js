/**
 * Logs Viewer for Quantum Deception Nexus
 * Handles real-time log streaming, filtering, and export functionality
 */

class LogsViewer {
    constructor() {
        this.logs = [];
        this.filteredLogs = [];
        this.currentPage = 1;
        this.logsPerPage = 50;
        this.isAutoScrolling = true;
        this.isStreaming = false;
        this.filters = {
            level: 'all',
            component: 'all',
            search: '',
            startDate: null,
            endDate: null,
            useRegex: false
        };
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeDatePickers();
        this.connectToWebSocket();
        this.loadInitialLogs();
    }

    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.filters.search = e.target.value;
                this.applyFilters();
            }, 300));
        }

        // Level filter
        const levelFilter = document.getElementById('level-filter');
        if (levelFilter) {
            levelFilter.addEventListener('change', (e) => {
                this.filters.level = e.target.value;
                this.applyFilters();
            });
        }

        // Component filter
        const componentFilter = document.getElementById('component-filter');
        if (componentFilter) {
            componentFilter.addEventListener('change', (e) => {
                this.filters.component = e.target.value;
                this.applyFilters();
            });
        }

        // Auto-scroll toggle
        const autoScrollToggle = document.getElementById('auto-scroll');
        if (autoScrollToggle) {
            autoScrollToggle.addEventListener('change', (e) => {
                this.isAutoScrolling = e.target.checked;
                if (this.isAutoScrolling) {
                    this.scrollToBottom();
                }
            });
        }

        // Regex toggle
        const regexToggle = document.getElementById('regex-toggle');
        if (regexToggle) {
            regexToggle.addEventListener('change', (e) => {
                this.filters.useRegex = e.target.checked;
                this.applyFilters();
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadInitialLogs();
            });
        }

        // Clear filters button
        const clearBtn = document.getElementById('clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearFilters();
            });
        }

        // Export buttons
        const exportCsvBtn = document.getElementById('export-csv');
        if (exportCsvBtn) {
            exportCsvBtn.addEventListener('click', () => {
                this.exportLogs('csv');
            });
        }

        const exportJsonBtn = document.getElementById('export-json');
        if (exportJsonBtn) {
            exportJsonBtn.addEventListener('click', () => {
                this.exportLogs('json');
            });
        }

        const exportTxtBtn = document.getElementById('export-txt');
        if (exportTxtBtn) {
            exportTxtBtn.addEventListener('click', () => {
                this.exportLogs('txt');
            });
        }

        // Pagination
        const prevPageBtn = document.getElementById('prev-page');
        if (prevPageBtn) {
            prevPageBtn.addEventListener('click', () => {
                this.previousPage();
            });
        }

        const nextPageBtn = document.getElementById('next-page');
        if (nextPageBtn) {
            nextPageBtn.addEventListener('click', () => {
                this.nextPage();
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'f':
                        e.preventDefault();
                        document.getElementById('search-input')?.focus();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.loadInitialLogs();
                        break;
                }
            }
        });
    }

    initializeDatePickers() {
        const dateRangeInput = document.getElementById('date-range');
        if (dateRangeInput && typeof flatpickr !== 'undefined') {
            flatpickr(dateRangeInput, {
                mode: 'range',
                dateFormat: 'Y-m-d',
                onChange: (selectedDates) => {
                    if (selectedDates.length === 2) {
                        this.filters.startDate = selectedDates[0];
                        this.filters.endDate = selectedDates[1];
                    } else {
                        this.filters.startDate = null;
                        this.filters.endDate = null;
                    }
                    this.applyFilters();
                }
            });
        }
    }

    connectToWebSocket() {
        if (!apiClient.socketConnected) {
            apiClient.connectSocket();
        }

        // Subscribe to log events
        apiClient.on('logEntry', (data) => {
            this.addLogEntry(data.data);
        });

        apiClient.on('socketChange', (data) => {
            this.updateConnectionStatus(data.connected);
        });

        // Subscribe to logs room
        if (apiClient.socket) {
            apiClient.socket.emit('subscribe', { room: 'logs' });
        }
    }

    updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('connection-status');
        if (statusIndicator) {
            statusIndicator.className = `w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`;
            statusIndicator.title = connected ? 'Connected' : 'Disconnected';
        }
    }

    async loadInitialLogs() {
        try {
            const logs = await apiClient.getLogs('all', 'all', '', 1000);
            this.logs = logs.logs || [];
            this.applyFilters();
            this.updatePagination();
            this.renderLogs();
            
            if (this.isAutoScrolling) {
                this.scrollToBottom();
            }
        } catch (error) {
            console.error('Failed to load logs:', error);
            this.showError('Failed to load logs');
        }
    }

    addLogEntry(logEntry) {
        // Add to logs array
        this.logs.unshift(logEntry);
        
        // Keep only recent logs in memory
        if (this.logs.length > 10000) {
            this.logs = this.logs.slice(0, 5000);
        }
        
        // Apply current filters
        this.applyFilters();
        
        // Update display if on first page
        if (this.currentPage === 1) {
            this.renderLogs();
            
            if (this.isAutoScrolling) {
                this.scrollToBottom();
            }
        }
        
        this.updatePagination();
    }

    applyFilters() {
        this.filteredLogs = this.logs.filter(log => {
            // Level filter
            if (this.filters.level !== 'all' && log.level !== this.filters.level) {
                return false;
            }
            
            // Component filter
            if (this.filters.component !== 'all' && log.component !== this.filters.component) {
                return false;
            }
            
            // Search filter
            if (this.filters.search) {
                const searchText = this.filters.search.toLowerCase();
                const logText = `${log.message} ${log.component} ${log.level}`.toLowerCase();
                
                if (this.filters.useRegex) {
                    try {
                        const regex = new RegExp(searchText, 'i');
                        if (!regex.test(logText)) {
                            return false;
                        }
                    } catch (e) {
                        // Invalid regex, treat as normal search
                        if (!logText.includes(searchText)) {
                            return false;
                        }
                    }
                } else {
                    if (!logText.includes(searchText)) {
                        return false;
                    }
                }
            }
            
            // Date range filter
            if (this.filters.startDate && this.filters.endDate) {
                const logDate = new Date(log.timestamp);
                if (logDate < this.filters.startDate || logDate > this.filters.endDate) {
                    return false;
                }
            }
            
            return true;
        });
        
        this.currentPage = 1;
        this.updatePagination();
        this.renderLogs();
    }

    renderLogs() {
        const container = document.getElementById('logs-container');
        const noLogsElement = document.getElementById('no-logs');
        
        if (!container) return;
        
        // Calculate pagination
        const startIndex = (this.currentPage - 1) * this.logsPerPage;
        const endIndex = startIndex + this.logsPerPage;
        const pageLogs = this.filteredLogs.slice(startIndex, endIndex);
        
        if (pageLogs.length === 0) {
            container.innerHTML = '<div id="no-logs" class="text-center py-12 text-gray-500"><i data-feather="info" class="w-12 h-12 mx-auto text-gray-600 mb-4"></i><p>No logs match current filters.</p></div>';
            feather.replace();
            return;
        }
        
        // Remove no-logs element if it exists
        if (noLogsElement) {
            noLogsElement.remove();
        }
        
        // Render logs
        container.innerHTML = pageLogs.map(log => this.renderLogEntry(log)).join('');
        
        // Initialize feather icons
        feather.replace();
        
        // Apply syntax highlighting
        this.applySyntaxHighlighting();
    }

    renderLogEntry(log) {
        const timestamp = new Date(log.timestamp).toLocaleString();
        const levelClass = this.getLevelClass(log.level);
        const componentClass = this.getComponentClass(log.component);
        
        return `
            <div class="border-b border-gray-700 hover:bg-gray-750 transition-colors">
                <div class="px-6 py-3 flex items-center">
                    <div class="w-1/12 text-xs text-gray-400">${timestamp}</div>
                    <div class="w-2/12">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${levelClass}">
                            ${log.level}
                        </span>
                    </div>
                    <div class="w-2/12">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${componentClass}">
                            ${log.component}
                        </span>
                    </div>
                    <div class="w-7/12 text-sm font-mono break-words">
                        ${this.formatLogMessage(log.message, log.metadata)}
                    </div>
                </div>
            </div>
        `;
    }

    getLevelClass(level) {
        const classes = {
            'DEBUG': 'bg-gray-700 text-gray-300',
            'INFO': 'bg-blue-900 text-blue-200',
            'WARNING': 'bg-yellow-900 text-yellow-200',
            'ERROR': 'bg-red-900 text-red-200',
            'CRITICAL': 'bg-purple-900 text-purple-200'
        };
        return classes[level] || 'bg-gray-700 text-gray-300';
    }

    getComponentClass(component) {
        const classes = {
            'fingerprinting': 'bg-green-900 text-green-200',
            'challenge': 'bg-blue-900 text-blue-200',
            'verification': 'bg-purple-900 text-purple-200',
            'sandbox': 'bg-yellow-900 text-yellow-200',
            'api': 'bg-indigo-900 text-indigo-200',
            'websocket': 'bg-pink-900 text-pink-200',
            'scheduler': 'bg-teal-900 text-teal-200'
        };
        return classes[component] || 'bg-gray-700 text-gray-300';
    }

    formatLogMessage(message, metadata) {
        // Check if message contains JSON
        if (typeof message === 'string' && message.trim().startsWith('{')) {
            try {
                const obj = JSON.parse(message);
                return `<pre class="json-log">${JSON.stringify(obj, null, 2)}</pre>`;
            } catch (e) {
                // Not valid JSON, return as-is
            }
        }
        
        // Format message with metadata if present
        let formattedMessage = this.escapeHtml(message);
        
        if (metadata) {
            formattedMessage += ` <span class="text-gray-500 text-xs">[${JSON.stringify(metadata)}]</span>`;
        }
        
        return formattedMessage;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    applySyntaxHighlighting() {
        // Simple JSON syntax highlighting
        const jsonElements = document.querySelectorAll('.json-log');
        jsonElements.forEach(element => {
            const text = element.textContent;
            const highlighted = text
                .replace(/"([^"]*)":/g, '<span class="text-yellow-400">"$1"</span>:')
                .replace(/: (true|false|null|\d+)/g, ': <span class="text-blue-400">$1</span>')
                .replace(/: "([^"]*)"/g, ': <span class="text-green-400">"$1"</span>');
            element.innerHTML = highlighted;
        });
    }

    scrollToBottom() {
        const container = document.getElementById('logs-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    updatePagination() {
        const showingCount = document.getElementById('showing-count');
        const totalCount = document.getElementById('total-count');
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        
        if (showingCount) {
            const startIndex = (this.currentPage - 1) * this.logsPerPage + 1;
            const endIndex = Math.min(startIndex + this.logsPerPage - 1, this.filteredLogs.length);
            showingCount.textContent = `${startIndex}-${endIndex}`;
        }
        
        if (totalCount) {
            totalCount.textContent = this.filteredLogs.length;
        }
        
        if (prevBtn) {
            prevBtn.disabled = this.currentPage <= 1;
        }
        
        if (nextBtn) {
            const maxPage = Math.ceil(this.filteredLogs.length / this.logsPerPage);
            nextBtn.disabled = this.currentPage >= maxPage || maxPage === 0;
        }
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderLogs();
            this.updatePagination();
        }
    }

    nextPage() {
        const maxPage = Math.ceil(this.filteredLogs.length / this.logsPerPage);
        if (this.currentPage < maxPage) {
            this.currentPage++;
            this.renderLogs();
            this.updatePagination();
        }
    }

    clearFilters() {
        // Reset filter values
        this.filters = {
            level: 'all',
            component: 'all',
            search: '',
            startDate: null,
            endDate: null,
            useRegex: false
        };
        
        // Reset UI elements
        document.getElementById('level-filter').value = 'all';
        document.getElementById('component-filter').value = 'all';
        document.getElementById('search-input').value = '';
        document.getElementById('date-range').value = '';
        document.getElementById('regex-toggle').checked = false;
        
        // Apply filters
        this.applyFilters();
    }

    exportLogs(format) {
        const data = this.filteredLogs;
        
        switch (format) {
            case 'csv':
                this.exportAsCSV(data);
                break;
            case 'json':
                this.exportAsJSON(data);
                break;
            case 'txt':
                this.exportAsText(data);
                break;
        }
    }

    exportAsCSV(data) {
        const headers = ['Timestamp', 'Level', 'Component', 'Message'];
        const csvContent = [
            headers.join(','),
            ...data.map(log => [
                `"${log.timestamp}"`,
                `"${log.level}"`,
                `"${log.component}"`,
                `"${log.message.replace(/"/g, '""')}"`
            ].join(','))
        ].join('\n');
        
        this.downloadFile('logs.csv', csvContent, 'text/csv');
    }

    exportAsJSON(data) {
        const jsonContent = JSON.stringify(data, null, 2);
        this.downloadFile('logs.json', jsonContent, 'application/json');
    }

    exportAsText(data) {
        const textContent = data.map(log => 
            `[${log.timestamp}] ${log.level} ${log.component}: ${log.message}`
        ).join('\n');
        
        this.downloadFile('logs.txt', textContent, 'text/plain');
    }

    downloadFile(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    showError(message) {
        // Create error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fixed top-4 right-4 bg-red-900 border border-red-700 text-red-100 px-6 py-4 rounded-lg shadow-lg z-50 max-w-md';
        errorDiv.innerHTML = `
            <div class="flex items-start">
                <i data-feather="alert-triangle" class="w-5 h-5 mr-3 mt-0.5 flex-shrink-0"></i>
                <div>
                    <div class="font-semibold">Error</div>
                    <div class="text-sm opacity-90">${message}</div>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
                    <i data-feather="x" class="w-4 h-4"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(errorDiv);
        feather.replace();
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LogsViewer;
}