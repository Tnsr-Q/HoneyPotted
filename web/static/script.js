// Main JavaScript for Quantum Deception Nexus

class QuantumDeceptionSystem {
    constructor() {
        this.modules = [
            'quantum_resistant_deception',
            'behavior_prediction_engine', 
            'deceptive_computational_tasks',
            'collaborative_defense_network',
            'psychological_manipulation'
        ];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeDashboard();
        this.startRealTimeUpdates();
    }

    setupEventListeners() {
        // Smooth scrolling for navigation links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        // Module card interactions
        document.querySelectorAll('.bg-gray-800.rounded-2xl').forEach(card => {
            card.addEventListener('mouseenter', this.handleCardHover);
            card.addEventListener('mouseleave', this.handleCardLeave);
        });

        // Mobile menu toggle
        const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
        const mobileMenu = document.querySelector('.mobile-menu');
        
        if (mobileMenuBtn && mobileMenu) {
            mobileMenuBtn.addEventListener('click', () => {
                mobileMenu.classList.toggle('hidden');
            });
        }
    }

    handleCardHover(e) {
        const card = e.currentTarget;
        card.style.transform = 'translateY(-10px) scale(1.02)';
        card.style.boxShadow = '0 25px 50px -12px rgba(0, 0, 0, 0.25)';
    }

    handleCardLeave(e) {
        const card = e.currentTarget;
        card.style.transform = 'translateY(0) scale(1)';
        card.style.boxShadow = '0 1px 3px 0 rgba(0, 0, 0, 0.1)';
    }

    initializeDashboard() {
        // Initialize real-time data visualization
        this.updateSystemMetrics();
        this.startPerformanceMonitoring();
    }

    updateSystemMetrics() {
        // Simulate real-time data updates
        setInterval(() => {
            this.updateActiveBotsCount();
            this.updateDetectionAccuracy();
            this.updateEngagementMetrics();
        }, 3000);
    }

    updateActiveBotsCount() {
        const countElement = document.querySelector('.text-green-400');
        if (countElement) {
            const currentCount = parseInt(countElement.textContent.replace(',', ''));
            const newCount = currentCount + Math.floor(Math.random() * 3) - 1;
            countElement.textContent = Math.max(1, newCount).toLocaleString();
        }
    }

    updateDetectionAccuracy() {
        const accuracyElement = document.querySelector('.text-blue-400');
        if (accuracyElement) {
            const currentAccuracy = parseFloat(accuracyElement.textContent.replace('%', ''));
            const variation = (Math.random() - 0.5) * 0.2;
            const newAccuracy = Math.min(99.9, Math.max(99.5, currentAccuracy + variation));
            accuracyElement.textContent = newAccuracy.toFixed(1) + '%';
        }
    }

    updateEngagementMetrics() {
        const engagementElement = document.querySelector('.text-purple-400');
        if (engagementElement) {
            const currentTime = parseFloat(engagementElement.textContent.replace('h', ''));
            const variation = (Math.random() - 0.5) * 2;
            const newTime = Math.max(40, Math.min(44, currentTime + variation));
            engagementElement.textContent = newTime.toFixed(0) + 'h';
        }
    }

    startPerformanceMonitoring() {
        // Monitor and update performance bars
        const performanceBars = document.querySelectorAll('.bg-gray-700.rounded-full > div');
        
        setInterval(() => {
            performanceBars.forEach(bar => {
                const currentWidth = parseFloat(bar.style.width);
                const variation = (Math.random() - 0.5) * 4;
                const newWidth = Math.max(80, Math.min(100, currentWidth + variation));
                bar.style.width = newWidth + '%';
                
                // Update percentage text
                const percentageElement = bar.parentElement.parentElement.querySelector('span:last-child');
                if (percentageElement) {
                    percentageElement.textContent = newWidth.toFixed(0) + '%';
                }
            });
        }, 2000);
    }

    startRealTimeUpdates() {
        // Simulate real-time system events
        this.simulateBotInteractions();
        this.updateSecurityEvents();
    }

    simulateBotInteractions() {
        setInterval(() => {
            // Randomly update engagement metrics
            const randomUpdate = Math.random();
            if (randomUpdate > 0.7) {
                this.triggerSecurityAlert();
            }
        }, 5000);
    }

    triggerSecurityAlert() {
        // Create a temporary alert notification
        const alert = document.createElement('div');
        alert.className = 'fixed top-4 right-4 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg transform transition-all duration-300';
        alert.innerHTML = `
            <div class="flex items-center">
                <i data-feather="alert-triangle" class="w-5 h-5 mr-2"></i>
            New bot detected in Quantum-Resistant Deception module
        `;
        
        document.body.appendChild(alert);
        
        // Remove alert after 5 seconds
        setTimeout(() => {
            alert.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 300);
        }, 5000);
        
        feather.replace();
    }

    updateSecurityEvents() {
        // Update security event counters
        const eventCounters = document.querySelectorAll('.text-red-400');
        eventCounters.forEach(counter => {
            setInterval(() => {
                const currentValue = parseFloat(counter.textContent.replace('%', ''));
                const variation = (Math.random() - 0.5) * 0.01;
                const newValue = Math.max(0.01, Math.min(0.05, currentValue + variation));
                counter.textContent = newValue.toFixed(2) + '%';
            }, 4000);
        });
    }
}

// Initialize the system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new QuantumDeceptionSystem();
});

// Utility functions
const utils = {
    formatNumber: (num) => {
        return new Intl.NumberFormat().format(num);
    },
    
    getRandomInRange: (min, max) => {
        return Math.random() * (max - min) + min;
    },
    
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    throttle: (func, limit) => {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { QuantumDeceptionSystem, utils };
}