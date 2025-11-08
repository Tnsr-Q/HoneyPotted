/**
 * Chart Components for Quantum Deception Nexus
 * Reusable Chart.js configurations with consistent styling
 */

class ChartManager {
    constructor() {
        this.charts = new Map();
        this.defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#9ca3af',
                        font: {
                            family: 'Inter',
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#f3f4f6',
                    bodyColor: '#d1d5db',
                    borderColor: 'rgba(55, 65, 81, 0.5)',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        borderColor: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        font: {
                            family: 'Inter',
                            size: 11
                        }
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        borderColor: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        font: {
                            family: 'Inter',
                            size: 11
                        }
                    }
                }
            },
            animation: {
                duration: 750,
                easing: 'easeInOutQuart'
            }
        };
    }

    /**
     * Create Bot Activity Timeline Chart
     */
    createBotActivityChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const config = {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Bot Detections',
                    data: data.values,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#1e40af',
                    pointBorderWidth: 2
                }]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: { display: false }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    y: {
                        ...this.defaultOptions.scales.y,
                        beginAtZero: true,
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: function(value) {
                                return Math.round(value);
                            }
                        }
                    }
                }
            }
        };

        return this.createChart(canvasId, config);
    }

    /**
     * Create Challenge Success Rate Pie Chart
     */
    createChallengeSuccessChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const config = {
            type: 'doughnut',
            data: {
                labels: ['Successful', 'Failed', 'Timeout'],
                datasets: [{
                    data: [data.success, data.failed, data.timeout],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
                    borderColor: ['#059669', '#dc2626', '#d97706'],
                    borderWidth: 2,
                    hoverOffset: 10
                }]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: {
                        ...this.defaultOptions.plugins.legend,
                        position: 'right'
                    }
                },
                cutout: '60%'
            }
        };

        return this.createChart(canvasId, config);
    }

    /**
     * Create Resource Utilization Chart
     */
    createResourceUtilizationChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const config = {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'CPU Usage (%)',
                        data: data.cpu,
                        backgroundColor: 'rgba(239, 68, 68, 0.8)',
                        borderColor: 'rgba(239, 68, 68, 1)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Memory Usage (MB)',
                        data: data.memory,
                        backgroundColor: 'rgba(59, 130, 246, 0.8)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    ...this.defaultOptions.scales,
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    }
                }
            }
        };

        return this.createChart(canvasId, config);
    }

    /**
     * Create Geographic Distribution Map (using Chart.js bubble chart)
     */
    createGeographicDistribution(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const config = {
            type: 'bubble',
            data: {
                datasets: [{
                    label: 'Bot Origins',
                    data: data.points,
                    backgroundColor: 'rgba(168, 85, 247, 0.6)',
                    borderColor: 'rgba(168, 85, 247, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ...this.defaultOptions.scales.x,
                        type: 'linear',
                        position: 'bottom',
                        title: {
                            display: true,
                            text: 'Longitude',
                            color: '#9ca3af'
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Latitude',
                            color: '#9ca3af'
                        }
                    }
                }
            }
        };

        return this.createChart(canvasId, config);
    }

    /**
     * Create System Load Timeline Chart
     */
    createSystemLoadChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const config = {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'System Load',
                        data: data.load,
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        tension: 0.4,
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Network I/O',
                        data: data.network,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: false,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    ...this.defaultOptions.scales,
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    }
                }
            }
        };

        return this.createChart(canvasId, config);
    }

    /**
     * Create Detection Score Distribution Histogram
     */
    createDetectionScoreChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const config = {
            type: 'bar',
            data: {
                labels: data.bins,
                datasets: [{
                    label: 'Bot Count',
                    data: data.counts,
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: { display: false }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    x: {
                        ...this.defaultOptions.scales.x,
                        title: {
                            display: true,
                            text: 'Detection Score Range',
                            color: '#9ca3af'
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Number of Bots',
                            color: '#9ca3af'
                        },
                        beginAtZero: true
                    }
                }
            }
        };

        return this.createChart(canvasId, config);
    }

    /**
     * Generic chart creation method
     */
    createChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        // Destroy existing chart if it exists
        if (this.charts.has(canvasId)) {
            this.charts.get(canvasId).destroy();
        }

        const chart = new Chart(canvas, config);
        this.charts.set(canvasId, chart);
        
        return chart;
    }

    /**
     * Update existing chart data
     */
    updateChart(canvasId, newData) {
        const chart = this.charts.get(canvasId);
        if (!chart) return false;

        if (newData.labels) chart.data.labels = newData.labels;
        if (newData.values) chart.data.datasets[0].data = newData.values;
        
        chart.update('active');
        return true;
    }

    /**
     * Destroy all charts
     */
    destroyAllCharts() {
        this.charts.forEach(chart => chart.destroy());
        this.charts.clear();
    }

    /**
     * Resize all charts (call on window resize)
     */
    resizeCharts() {
        this.charts.forEach(chart => chart.resize());
    }
}

// Initialize chart manager
const chartManager = new ChartManager();

// Handle window resize
window.addEventListener('resize', () => {
    chartManager.resizeCharts();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartManager;
}