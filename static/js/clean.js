// Clean JavaScript for Gold Analyzer
class GoldAnalyzer {
    constructor() {
        this.refreshInterval = null;
        this.isRefreshing = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadGoldData();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadGoldData());
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
        // Update current price
        const currentPrice = document.getElementById('current-price');
        const priceChange = document.getElementById('price-change');
        const priceChangePercent = document.getElementById('price-change-percent');
        const bidPrice = document.getElementById('bid-price');
        const askPrice = document.getElementById('ask-price');
        const highPrice = document.getElementById('high-price');
        const lowPrice = document.getElementById('low-price');
        const marketStatus = document.getElementById('market-status');

        if (currentPrice && data.offer) {
            currentPrice.textContent = `$${this.formatPrice(data.offer)}`;
        }

        if (bidPrice && data.bid) {
            bidPrice.textContent = `$${this.formatPrice(data.bid)}`;
        }

        if (askPrice && data.offer) {
            askPrice.textContent = `$${this.formatPrice(data.offer)}`;
        }

        if (highPrice && data.high) {
            highPrice.textContent = `$${this.formatPrice(data.high)}`;
        }

        if (lowPrice && data.low) {
            lowPrice.textContent = `$${this.formatPrice(data.low)}`;
        }

        // Update price change
        if (priceChange && data.price_change !== undefined) {
            const change = data.price_change;
            const changePercent = data.price_change_percent || 0;
            
            priceChange.textContent = `${change >= 0 ? '+' : ''}$${this.formatPrice(Math.abs(change))}`;
            priceChangePercent.textContent = `(${change >= 0 ? '+' : ''}${changePercent.toFixed(2)}%)`;
            
            const priceChangeContainer = priceChange.parentElement;
            priceChangeContainer.className = 'price-change ' + (change >= 0 ? 'positive' : 'negative');
        }

        // Update market status
        if (marketStatus && data.market_status) {
            const status = data.market_status.toLowerCase();
            marketStatus.textContent = this.formatMarketStatus(status);
        }
    }

    formatPrice(price) {
        return parseFloat(price).toFixed(2);
    }

    formatMarketStatus(status) {
        switch (status) {
            case 'tradeable':
                return 'Market Open';
            case 'closed':
                return 'Market Closed';
            case 'offline':
                return 'Market Offline';
            default:
                return 'Unknown';
        }
    }

    updateLastUpdate() {
        const lastUpdate = document.getElementById('last-update');
        if (lastUpdate) {
            const now = new Date();
            lastUpdate.textContent = `Updated ${now.toLocaleTimeString()}`;
        }
    }

    showLoading() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.querySelector('.refresh-icon').style.animation = 'spin 1s linear infinite';
        }
    }

    hideLoading() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.querySelector('.refresh-icon').style.animation = '';
        }
    }

    showError(message) {
        let errorDiv = document.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error error-message';
            const container = document.querySelector('.main-content');
            container.insertBefore(errorDiv, container.firstChild);
        }
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }

    hideError() {
        const errorDiv = document.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
    }

    startAutoRefresh() {
        // Refresh every 10 seconds
        this.refreshInterval = setInterval(() => {
            this.loadGoldData();
        }, 10000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.goldAnalyzer = new GoldAnalyzer();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.goldAnalyzer) {
        window.goldAnalyzer.stopAutoRefresh();
    }
});
