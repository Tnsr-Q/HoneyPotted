/**
 * Settings Manager for Quantum Deception Nexus
 * Handles configuration management, validation, and UI interactions
 */

class SettingsManager {
    constructor() {
        this.currentSettings = {};
        this.originalSettings = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadCurrentSettings();
        this.initializeTabs();
        this.initializeSliders();
    }

    setupEventListeners() {
        // Tab switching
        const tabs = document.querySelectorAll('.settings-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Form submissions
        const forms = document.querySelectorAll('form[id$="-form"]');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveSettings(form.id.replace('-form', ''));
            });
        });

        // API Key actions
        const generateApiKeyBtn = document.getElementById('generate-api-key');
        if (generateApiKeyBtn) {
            generateApiKeyBtn.addEventListener('click', () => {
                this.generateApiKey();
            });
        }

        // User actions
        const addUserBtn = document.getElementById('add-user');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => {
                this.addUser();
            });
        }

        // Backup actions
        const createBackupBtn = document.getElementById('create-backup');
        if (createBackupBtn) {
            createBackupBtn.addEventListener('click', () => {
                this.createBackup();
            });
        }

        const restoreFileInput = document.getElementById('restore-file');
        if (restoreFileInput) {
            restoreFileInput.addEventListener('change', (e) => {
                this.handleRestoreFileSelect(e);
            });
        }

        const restoreBackupBtn = document.getElementById('restore-backup');
        if (restoreBackupBtn) {
            restoreBackupBtn.addEventListener('click', () => {
                this.restoreBackup();
            });
        }
    }

    initializeTabs() {
        // Set first tab as active
        const firstTab = document.querySelector('.settings-tab');
        if (firstTab) {
            this.switchTab(firstTab.dataset.tab);
        }
    }

    initializeSliders() {
        // Detection threshold slider
        const thresholdSlider = document.getElementById('detection-threshold');
        const thresholdValue = document.getElementById('threshold-value');
        if (thresholdSlider && thresholdValue) {
            thresholdSlider.addEventListener('input', (e) => {
                thresholdValue.textContent = parseFloat(e.target.value).toFixed(2);
            });
        }

        // Consensus threshold slider
        const consensusSlider = document.getElementById('consensus-threshold');
        const consensusValue = document.getElementById('consensus-value');
        if (consensusSlider && consensusValue) {
            consensusSlider.addEventListener('input', (e) => {
                consensusValue.textContent = parseFloat(e.target.value).toFixed(2);
            });
        }

        // Worker reliability slider
        const reliabilitySlider = document.getElementById('worker-reliability');
        const reliabilityValue = document.getElementById('reliability-value');
        if (reliabilitySlider && reliabilityValue) {
            reliabilitySlider.addEventListener('input', (e) => {
                reliabilityValue.textContent = parseFloat(e.target.value).toFixed(2);
            });
        }
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.settings-tab').forEach(tab => {
            tab.classList.remove('active', 'text-white', 'border-b-2', 'border-blue-500');
            tab.classList.add('text-gray-400', 'hover:text-white');
        });

        const activeTab = document.querySelector(`.settings-tab[data-tab="${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active', 'text-white', 'border-b-2', 'border-blue-500');
            activeTab.classList.remove('text-gray-400');
        }

        // Update content panels
        document.querySelectorAll('.settings-content').forEach(content => {
            content.classList.add('hidden');
        });

        const activeContent = document.getElementById(`${tabName}-content`);
        if (activeContent) {
            activeContent.classList.remove('hidden');
            activeContent.classList.add('active');
        }
    }

    async loadCurrentSettings() {
        try {
            const settings = await apiClient.getSettings();
            this.currentSettings = settings;
            this.originalSettings = { ...settings };
            this.populateSettingsForm(settings);
        } catch (error) {
            console.error('Failed to load settings:', error);
            this.showError('Failed to load settings');
        }
    }

    populateSettingsForm(settings) {
        // Honeypot settings
        if (settings.honeypot) {
            document.getElementById('honeypot-ports').value = settings.honeypot.ports?.join(',') || '';
            document.getElementById('honeypot-domains').value = settings.honeypot.domains?.join(',') || '';
            document.getElementById('detection-threshold').value = settings.honeypot.detection_threshold || 0.5;
            document.getElementById('threshold-value').textContent = (settings.honeypot.detection_threshold || 0.5).toFixed(2);
            document.getElementById('max-concurrent-bots').value = settings.honeypot.max_concurrent_bots || 100;
        }

        // Challenge settings
        if (settings.challenge) {
            document.getElementById('challenge-difficulty').value = settings.challenge.difficulty || 'medium';
            document.getElementById('challenge-time-limit').value = settings.challenge.time_limit || 300;
            document.getElementById('challenge-retries').value = settings.challenge.retry_attempts || 3;
        }

        // Verification settings
        if (settings.verification) {
            document.getElementById('consensus-threshold').value = settings.verification.consensus_threshold || 0.8;
            document.getElementById('consensus-value').textContent = (settings.verification.consensus_threshold || 0.8).toFixed(2);
            document.getElementById('worker-reliability').value = settings.verification.worker_reliability || 0.9;
            document.getElementById('reliability-value').textContent = (settings.verification.worker_reliability || 0.9).toFixed(2);
            document.getElementById('verification-timeout').value = settings.verification.timeout || 60;
            document.getElementById('max-verification-workers').value = settings.verification.max_workers || 10;
        }

        // Sandbox settings
        if (settings.sandbox) {
            document.getElementById('sandbox-cpu-limit').value = settings.sandbox.cpu_limit || 50;
            document.getElementById('sandbox-memory-limit').value = settings.sandbox.memory_limit || 512;
            document.getElementById('sandbox-timeout').value = settings.sandbox.timeout || 300;
            document.getElementById('network-isolation').value = settings.sandbox.network_isolation || 'partial';
        }

        // Alerts settings
        if (settings.alerts) {
            document.getElementById('alert-email').value = settings.alerts.email || '';
            document.getElementById('alert-webhook').value = settings.alerts.webhook_url || '';
            document.getElementById('alert-threshold').value = settings.alerts.threshold || 'medium';
            document.getElementById('enable-slack').checked = settings.alerts.slack_enabled || false;
        }

        // API keys and users would be loaded separately
        this.loadApiKeys();
        this.loadUsers();
        this.loadBackups();
    }

    async saveSettings(section) {
        try {
            const settingsData = this.getSettingsFromForm(section);
            
            // Show confirmation for critical changes
            if (section === 'honeypot' || section === 'sandbox') {
                if (!confirm(`Are you sure you want to save ${section} settings? This may affect system behavior.`)) {
                    return;
                }
            }
            
            // Show loading state
            this.setSaveButtonState(section, true);
            
            await apiClient.updateSettings({ [section]: settingsData });
            
            // Update local settings
            this.currentSettings[section] = settingsData;
            
            this.showSuccess(`Settings saved successfully`);
        } catch (error) {
            console.error(`Failed to save ${section} settings:`, error);
            this.showError(`Failed to save ${section} settings: ${error.message}`);
        } finally {
            this.setSaveButtonState(section, false);
        }
    }

    getSettingsFromForm(section) {
        const form = document.getElementById(`${section}-form`);
        if (!form) return {};

        const formData = new FormData(form);
        const settings = {};

        for (const [key, value] of formData.entries()) {
            // Handle special cases
            if (key === 'honeypot-ports') {
                settings.ports = value.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
            } else if (key === 'honeypot-domains') {
                settings.domains = value.split(',').map(d => d.trim()).filter(d => d);
            } else if (key.endsWith('-threshold') || key.endsWith('-reliability')) {
                settings[key.replace('-', '_')] = parseFloat(value);
            } else if (key.includes('-')) {
                settings[key.replace('-', '_')] = value;
            } else {
                settings[key] = value;
            }
        }

        return settings;
    }

    setSaveButtonState(section, isLoading) {
        const button = document.querySelector(`#${section}-form button[type="submit"]`);
        if (button) {
            if (isLoading) {
                button.disabled = true;
                button.innerHTML = '<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>Saving...';
            } else {
                button.disabled = false;
                button.innerHTML = '<i data-feather="save" class="w-4 h-4 mr-2"></i>Save Changes';
                feather.replace();
            }
        }
    }

    async loadApiKeys() {
        try {
            // In a real implementation, this would fetch API keys from the server
            const apiKeys = [
                { name: 'Integration Key 1', key: 'sk_****abcd', created: '2024-01-15', permissions: ['read', 'write'] },
                { name: 'Monitoring Key', key: 'sk_****efgh', created: '2024-01-10', permissions: ['read'] }
            ];
            
            this.renderApiKeys(apiKeys);
        } catch (error) {
            console.error('Failed to load API keys:', error);
        }
    }

    renderApiKeys(apiKeys) {
        const container = document.getElementById('api-keys-list');
        if (!container) return;

        if (apiKeys.length === 0) {
            container.innerHTML = '<div class="px-4 py-6 text-center text-gray-500">No API keys found. Generate one to get started.</div>';
            return;
        }

        container.innerHTML = apiKeys.map(key => `
            <div class="px-4 py-4 flex items-center">
                <div class="w-1/3">
                    <div class="font-medium">${key.name}</div>
                    <div class="text-sm text-gray-400">${key.key}</div>
                </div>
                <div class="w-1/3 text-sm text-gray-400">${key.created}</div>
                <div class="w-1/3 text-right">
                    <button class="text-red-400 hover:text-red-300 text-sm" onclick="settingsManager.revokeApiKey('${key.key}')">
                        Revoke
                    </button>
                </div>
            </div>
        `).join('');
    }

    async generateApiKey() {
        try {
            // In a real implementation, this would call the API to generate a new key
            this.showSuccess('API key generated successfully');
            this.loadApiKeys(); // Refresh the list
        } catch (error) {
            console.error('Failed to generate API key:', error);
            this.showError('Failed to generate API key');
        }
    }

    async revokeApiKey(key) {
        if (!confirm('Are you sure you want to revoke this API key?')) {
            return;
        }

        try {
            // In a real implementation, this would call the API to revoke the key
            this.showSuccess('API key revoked successfully');
            this.loadApiKeys(); // Refresh the list
        } catch (error) {
            console.error('Failed to revoke API key:', error);
            this.showError('Failed to revoke API key');
        }
    }

    async loadUsers() {
        try {
            // In a real implementation, this would fetch users from the server
            const users = [
                { username: 'admin', email: 'admin@example.com', role: 'admin' },
                { username: 'viewer', email: 'viewer@example.com', role: 'viewer' }
            ];
            
            this.renderUsers(users);
        } catch (error) {
            console.error('Failed to load users:', error);
        }
    }

    renderUsers(users) {
        const container = document.getElementById('users-list');
        if (!container) return;

        if (users.length === 0) {
            container.innerHTML = '<div class="px-4 py-6 text-center text-gray-500">No users found.</div>';
            return;
        }

        container.innerHTML = users.map(user => `
            <div class="px-4 py-4 flex items-center">
                <div class="w-1/4">
                    <div class="font-medium">${user.username}</div>
                </div>
                <div class="w-1/4 text-gray-400">${user.email}</div>
                <div class="w-1/4">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-900 text-blue-200">
                        ${user.role}
                    </span>
                </div>
                <div class="w-1/4 text-right">
                    <button class="text-blue-400 hover:text-blue-300 text-sm mr-3">Edit</button>
                    <button class="text-red-400 hover:text-red-300 text-sm">Delete</button>
                </div>
            </div>
        `).join('');
    }

    addUser() {
        // In a real implementation, this would show a modal to add a new user
        this.showSuccess('Add user functionality would be implemented here');
    }

    async loadBackups() {
        try {
            // In a real implementation, this would fetch backups from the server
            const backups = [
                { name: 'backup_20240115_1430.zip', date: '2024-01-15 14:30', size: '15.2 MB' },
                { name: 'backup_20240114_0200.zip', date: '2024-01-14 02:00', size: '14.8 MB' }
            ];
            
            this.renderBackups(backups);
        } catch (error) {
            console.error('Failed to load backups:', error);
        }
    }

    renderBackups(backups) {
        const container = document.getElementById('backups-list');
        if (!container) return;

        if (backups.length === 0) {
            container.innerHTML = '<div class="px-4 py-6 text-center text-gray-500">No backups found.</div>';
            return;
        }

        container.innerHTML = backups.map(backup => `
            <div class="px-4 py-4 flex items-center">
                <div class="w-1/3">
                    <div class="font-medium">${backup.name}</div>
                    <div class="text-sm text-gray-400">${backup.size}</div>
                </div>
                <div class="w-1/3 text-gray-400">${backup.date}</div>
                <div class="w-1/3 text-right">
                    <button class="text-green-400 hover:text-green-300 text-sm mr-3" onclick="settingsManager.downloadBackup('${backup.name}')">
                        Download
                    </button>
                    <button class="text-yellow-400 hover:text-yellow-300 text-sm" onclick="settingsManager.restoreBackup('${backup.name}')">
                        Restore
                    </button>
                </div>
            </div>
        `).join('');
    }

    async createBackup() {
        try {
            // In a real implementation, this would call the API to create a backup
            this.showSuccess('Backup creation started. This may take a few minutes.');
            this.loadBackups(); // Refresh the list
        } catch (error) {
            console.error('Failed to create backup:', error);
            this.showError('Failed to create backup');
        }
    }

    async downloadBackup(backupName) {
        try {
            // In a real implementation, this would download the backup file
            this.showSuccess(`Downloading backup: ${backupName}`);
        } catch (error) {
            console.error('Failed to download backup:', error);
            this.showError('Failed to download backup');
        }
    }

    async restoreBackup(backupName) {
        if (!confirm(`Are you sure you want to restore backup ${backupName}? This will replace current data.`)) {
            return;
        }

        try {
            // In a real implementation, this would call the API to restore the backup
            this.showSuccess(`Backup restoration started: ${backupName}. System will restart when complete.`);
        } catch (error) {
            console.error('Failed to restore backup:', error);
            this.showError('Failed to restore backup');
        }
    }

    handleRestoreFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            document.querySelector('label[for="restore-file"]').textContent = file.name;
        }
    }

    async restoreBackupFromFile() {
        const fileInput = document.getElementById('restore-file');
        const file = fileInput.files[0];
        
        if (!file) {
            this.showError('Please select a backup file');
            return;
        }

        if (!confirm(`Are you sure you want to restore from ${file.name}? This will replace current data.`)) {
            return;
        }

        try {
            // In a real implementation, this would upload and restore the backup file
            this.showSuccess(`Backup restoration started from file: ${file.name}. System will restart when complete.`);
        } catch (error) {
            console.error('Failed to restore backup from file:', error);
            this.showError('Failed to restore backup from file');
        }
    }

    showSuccess(message) {
        // Create success notification
        const successDiv = document.createElement('div');
        successDiv.className = 'fixed top-4 right-4 bg-green-900 border border-green-700 text-green-100 px-6 py-4 rounded-lg shadow-lg z-50 max-w-md';
        successDiv.innerHTML = `
            <div class="flex items-start">
                <i data-feather="check-circle" class="w-5 h-5 mr-3 mt-0.5 flex-shrink-0"></i>
                <div>
                    <div class="font-semibold">Success</div>
                    <div class="text-sm opacity-90">${message}</div>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
                    <i data-feather="x" class="w-4 h-4"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(successDiv);
        feather.replace();
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (successDiv.parentElement) {
                successDiv.remove();
            }
        }, 5000);
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
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsManager;
}