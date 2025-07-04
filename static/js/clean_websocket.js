// Enhanced Gold Analyzer with WebSocket support
class GoldAnalyzer {
    constructor() {
        this.refreshInterval = null;
        this.isRefreshing = false;
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadGoldData();
        this.setupWebSocket();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadGoldData());
        }
    }

    // WebSocket Setup
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/gold-prices`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('🔗 WebSocket connected');
                this.updateConnectionStatus('connected');
                this.reconnectAttempts = 0;
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                this.updateConnectionStatus('disconnected');
                this.attemptReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.updateConnectionStatus('error');
            };
            
        } catch (error) {
            console.error('Error setting up WebSocket:', error);
            this.updateConnectionStatus('error');
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'gold_price_update':
                console.log('💰 Received gold price update:', data.data);
                this.updatePriceDisplay(data.data);
                this.updateLastUpdate();
                this.showLiveIndicator();
                break;
            case 'connection_status':
                console.log('📡 Connection status:', data);
                break;
            case 'pong':
                console.log('🏓 Received pong');
                break;
            default:
                console.log('📦 Unknown message type:', data.type);
        }
    }

    updateConnectionStatus(status) {
        const wsStatus = document.getElementById('ws-status');
        if (wsStatus) {
            switch (status) {
                case 'connected':
                    wsStatus.textContent = 'Live';
                    wsStatus.className = 'ws-connected';
                    break;
                case 'disconnected':
                    wsStatus.textContent = 'Disconnected';
                    wsStatus.className = 'ws-disconnected';
                    break;
                case 'error':
                    wsStatus.textContent = 'Error';
                    wsStatus.className = 'ws-error';
                    break;
                default:
                    wsStatus.textContent = 'Connecting...';
                    wsStatus.className = 'ws-connecting';
            }
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`🔄 Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.setupWebSocket();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.log('❌ Max reconnection attempts reached');
            this.updateConnectionStatus('error');
        }
    }

    showLiveIndicator() {
        const indicator = document.querySelector('.live-indicator');
        if (indicator) {
            indicator.style.animation = 'none';
            indicator.offsetHeight; // Trigger reflow
            indicator.style.animation = 'pulse 2s infinite';
        }
    }

    async loadGoldData() {
        if (this.isRefreshing) return;
        
        this.isRefreshing = true;
        this.showLoading();

        try {
            const response = await fetch('/api/gold-live');
            const result = await response.json();

            if (result.success && result.data) {
                this.updatePriceDisplay(result.data);
                this.updateLastUpdate();
                this.hideError();
            } else {
                this.showError(result.error || 'Failed to load gold data');
            }
        } catch (error) {
            console.error('Error loading gold data:', error);
            this.showError('Connection error. Please try again.');
        } finally {
            this.isRefreshing = false;
            this.hideLoading();
        }
    }

    updatePriceDisplay(data) {
        // Update current price - use mid price if available, otherwise use bid
        const currentPrice = document.getElementById('current-price');
        if (currentPrice) {
            const price = data.mid || data.bid || data.price || 0;
            currentPrice.textContent = `$${this.formatPrice(price)}`;
        }

        // Update bid price
        const bidPrice = document.getElementById('bid-price');
        if (bidPrice && data.bid) {
            bidPrice.textContent = `$${this.formatPrice(data.bid)}`;
        }

        // Update ask price
        const askPrice = document.getElementById('ask-price');
        if (askPrice && data.ask) {
            askPrice.textContent = `$${this.formatPrice(data.ask)}`;
        }

        // Update high price
        const highPrice = document.getElementById('high-price');
        if (highPrice && data.high) {
            highPrice.textContent = `$${this.formatPrice(data.high)}`;
        }

        // Update low price
        const lowPrice = document.getElementById('low-price');
        if (lowPrice && data.low) {
            lowPrice.textContent = `$${this.formatPrice(data.low)}`;
        }

        // Update price change
        const priceChange = document.getElementById('price-change');
        const priceChangePercent = document.getElementById('price-change-percent');
        
        if (priceChange && data.change !== undefined) {
            const changeValue = parseFloat(data.change);
            const changeClass = changeValue >= 0 ? 'positive' : 'negative';
            const changeSymbol = changeValue >= 0 ? '+' : '';
            
            priceChange.textContent = `${changeSymbol}$${this.formatPrice(Math.abs(changeValue))}`;
            priceChange.className = `price-change ${changeClass}`;
            
            if (priceChangePercent && data.changePercent !== undefined) {
                const percentValue = parseFloat(data.changePercent);
                priceChangePercent.textContent = `(${changeSymbol}${percentValue.toFixed(2)}%)`;
                priceChangePercent.className = `price-change-percent ${changeClass}`;
            }
        }
    }

    formatPrice(price) {
        return parseFloat(price).toFixed(2);
    }

    updateLastUpdate() {
        const lastUpdate = document.getElementById('last-update');
        if (lastUpdate) {
            const now = new Date();
            lastUpdate.textContent = `Last updated: ${now.toLocaleTimeString()}`;
        }
    }

    showLoading() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.textContent = 'Loading...';
            refreshBtn.disabled = true;
        }
    }

    hideLoading() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.innerHTML = '<span class="refresh-icon">↻</span> Refresh';
            refreshBtn.disabled = false;
        }
    }

    showError(message) {
        console.error('Error:', message);
        // You can implement error display UI here
    }

    hideError() {
        // You can implement error hiding UI here
    }

    startAutoRefresh() {
        // Less frequent polling since we have WebSocket for real-time updates
        this.refreshInterval = setInterval(() => {
            this.loadGoldData();
        }, 60000); // Refresh every minute as backup
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // Cleanup when page is closed
    destroy() {
        this.stopAutoRefresh();
        if (this.websocket) {
            this.websocket.close();
        }
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    window.goldAnalyzer = new GoldAnalyzer();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.goldAnalyzer) {
        window.goldAnalyzer.destroy();
    }
});
