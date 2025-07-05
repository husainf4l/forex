// TradingView-style Gold Trading Platform with Real-time WebSocket
class GoldTradingPlatform {
    constructor() {
        this.websocket = null;
        this.chart = null;
        this.candlestickSeries = null;
        this.lineSeries = null;
        this.areaSeries = null;
        this.volumeSeries = null;
        this.currentSeries = null;
        this.currentChartType = 'candlestick';
        this.priceData = [];
        this.candleData = [];
        this.volumeData = [];
        this.rawTickData = []; // Store raw tick data for aggregation
        this.candleData1m = []; // 1-minute candles
        this.candleData5m = []; // 5-minute candles
        this.volumeData1m = []; // 1-minute volume
        this.volumeData5m = []; // 5-minute volume
        this.maxDataPoints = 200;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.lastPriceUpdate = null;
        this.currentTheme = 'dark';
        this.showVolume = false;
        this.currentTimeframe = '1m';
        this.isRealDataActive = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initChart();
        this.connectWebSocket(); // Connect first to get real data
        this.startClockUpdate();
        this.initTradeCalculator();
        
        // Add initial sample data to show chart immediately, then replace with real data
        setTimeout(() => {
            this.addSampleData();
        }, 100);
    }

    setupEventListeners() {
        // Chart type controls
        document.querySelectorAll('.chart-type-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const chartType = e.currentTarget.dataset.type;
                this.switchChartType(chartType);
            });
        });

        // Chart controls
        const resetZoomBtn = document.getElementById('reset-zoom');
        if (resetZoomBtn) {
            resetZoomBtn.addEventListener('click', () => this.resetChartZoom());
        }

        const toggleGridBtn = document.getElementById('toggle-grid');
        if (toggleGridBtn) {
            toggleGridBtn.addEventListener('click', () => this.toggleGrid());
        }

        const toggleVolumeBtn = document.getElementById('toggle-volume');
        if (toggleVolumeBtn) {
            toggleVolumeBtn.addEventListener('click', () => this.toggleVolume());
        }

        // Timeframe buttons
        document.querySelectorAll('.timeframe-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTimeframe(e.target.textContent));
        });

        // Trade tabs
        document.querySelectorAll('.trade-tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTradeMode(e.target.textContent.toLowerCase()));
        });

        // Window events
        window.addEventListener('beforeunload', () => {
            if (this.websocket) {
                this.websocket.close();
            }
        });

        // Visibility change - reconnect when tab becomes visible
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !this.isConnected) {
                this.connectWebSocket();
            }
        });

        // Resize handler
        window.addEventListener('resize', () => {
            if (this.chart) {
                this.chart.applyOptions({
                    width: this.chart.options().width,
                    height: this.chart.options().height
                });
            }
        });
    }

    initChart() {
        const chartContainer = document.getElementById('tradingview-chart');
        const loadingElement = document.getElementById('chart-loading');
        
        if (!chartContainer) {
            console.error('❌ Chart container not found');
            return;
        }

        // Show loading state
        if (loadingElement) {
            loadingElement.style.display = 'flex';
        }

        try {
            // Create the chart with TradingView styling
            this.chart = LightweightCharts.createChart(chartContainer, {
                width: chartContainer.clientWidth,
                height: 600,
                layout: {
                    background: {
                        type: 'solid',
                        color: '#131722'
                    },
                    textColor: '#d1d4dc',
                    fontSize: 12,
                    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                },
                grid: {
                    vertLines: {
                        color: '#2a2e39',
                        style: 1,
                        visible: true
                    },
                    horzLines: {
                        color: '#2a2e39',
                        style: 1,
                        visible: true
                    }
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                    vertLine: {
                        color: '#787b86',
                        width: 1,
                        style: 3,
                        visible: true,
                        labelVisible: true
                    },
                    horzLine: {
                        color: '#787b86',
                        width: 1,
                        style: 3,
                        visible: true,
                        labelVisible: true
                    }
                },
                rightPriceScale: {
                    visible: true,
                    borderColor: '#2a2e39',
                    textColor: '#d1d4dc',
                    entireTextOnly: false,
                    ticksVisible: true,
                    scaleMargins: {
                        top: 0.1,
                        bottom: 0.1
                    }
                },
                timeScale: {
                    visible: true,
                    borderColor: '#2a2e39',
                    textColor: '#d1d4dc',
                    timeVisible: true,
                    secondsVisible: true,
                    ticksVisible: true,
                    barSpacing: 12,
                    rightOffset: 12,
                    lockVisibleTimeRangeOnResize: true
                },
                handleScroll: {
                    mouseWheel: true,
                    pressedMouseMove: true,
                    horzTouchDrag: true,
                    vertTouchDrag: true
                },
                handleScale: {
                    axisPressedMouseMove: true,
                    mouseWheel: true,
                    pinch: true,
                    axisDoubleClickReset: true
                }
            });

            // Initialize chart series
            this.initChartSeries();

            // Set up chart event handlers
            this.setupChartEventHandlers();

            // Hide loading state
            if (loadingElement) {
                loadingElement.style.display = 'none';
            }

            console.log('✅ TradingView Lightweight Chart initialized successfully');
            
        } catch (error) {
            console.error('❌ Error initializing chart:', error);
            
            // Hide loading and show error
            if (loadingElement) {
                loadingElement.innerHTML = '<i class="fas fa-exclamation-triangle"></i><span>Error loading chart</span>';
            }
        }
    }

    initChartSeries() {
        console.log('📊 Initializing chart series...');
        
        // Candlestick series
        this.candlestickSeries = this.chart.addCandlestickSeries({
            upColor: '#00d4aa',
            downColor: '#ff6b6b',
            borderDownColor: '#ff6b6b',
            borderUpColor: '#00d4aa',
            wickDownColor: '#ff6b6b',
            wickUpColor: '#00d4aa',
            visible: true,
            priceFormat: {
                type: 'price',
                precision: 2,
                minMove: 0.01
            }
        });

        // Line series
        this.lineSeries = this.chart.addLineSeries({
            color: '#f7931a',
            lineWidth: 2,
            visible: false,
            priceFormat: {
                type: 'price',
                precision: 2,
                minMove: 0.01
            }
        });

        // Area series
        this.areaSeries = this.chart.addAreaSeries({
            topColor: 'rgba(247, 147, 26, 0.3)',
            bottomColor: 'rgba(247, 147, 26, 0.05)',
            lineColor: '#f7931a',
            lineWidth: 2,
            visible: false,
            priceFormat: {
                type: 'price',
                precision: 2,
                minMove: 0.01
            }
        });

        // Volume series (histogram)
        this.volumeSeries = this.chart.addHistogramSeries({
            color: '#787b86',
            priceFormat: {
                type: 'volume'
            },
            priceScaleId: 'volume',
            visible: false,
            scaleMargins: {
                top: 0.7,
                bottom: 0
            }
        });

        // Set initial series
        this.currentSeries = this.candlestickSeries;
        
        console.log('✅ Chart series initialized successfully');
    }

    setupChartEventHandlers() {
        // Crosshair move handler for displaying price info
        this.chart.subscribeCrosshairMove((param) => {
            if (param.time) {
                const data = param.seriesData.get(this.currentSeries);
                if (data) {
                    this.updatePriceInfo(data);
                }
            }
        });

        // Click handler
        this.chart.subscribeClick((param) => {
            if (param.time) {
                console.log('Chart clicked at time:', param.time);
            }
        });
    }

    switchChartType(chartType) {
        // Update button states
        document.querySelectorAll('.chart-type-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.type === chartType) {
                btn.classList.add('active');
            }
        });

        // Hide all series
        this.candlestickSeries.applyOptions({ visible: false });
        this.lineSeries.applyOptions({ visible: false });
        this.areaSeries.applyOptions({ visible: false });

        // Show selected series
        switch (chartType) {
            case 'candlestick':
                this.candlestickSeries.applyOptions({ visible: true });
                this.currentSeries = this.candlestickSeries;
                break;
            case 'line':
                this.lineSeries.applyOptions({ visible: true });
                this.currentSeries = this.lineSeries;
                break;
            case 'area':
                this.areaSeries.applyOptions({ visible: true });
                this.currentSeries = this.areaSeries;
                break;
        }

        this.currentChartType = chartType;
        console.log(`📊 Chart type switched to: ${chartType}`);
    }

    toggleVolume() {
        this.showVolume = !this.showVolume;
        this.volumeSeries.applyOptions({ visible: this.showVolume });
        
        const toggleBtn = document.getElementById('toggle-volume');
        if (toggleBtn) {
            toggleBtn.classList.toggle('active', this.showVolume);
        }
        
        console.log(`📊 Volume ${this.showVolume ? 'enabled' : 'disabled'}`);
    }

    resetChartZoom() {
        if (this.chart) {
            this.chart.timeScale().fitContent();
        }
    }

    toggleGrid() {
        if (this.chart) {
            const currentOptions = this.chart.options();
            const gridVisible = currentOptions.grid.vertLines.visible;
            
            this.chart.applyOptions({
                grid: {
                    vertLines: { visible: !gridVisible },
                    horzLines: { visible: !gridVisible }
                }
            });
            
            const toggleBtn = document.getElementById('toggle-grid');
            if (toggleBtn) {
                toggleBtn.classList.toggle('active', !gridVisible);
            }
        }
    }

    connectWebSocket() {
        if (this.websocket) {
            this.websocket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/gold-prices`;
        
        console.log('🔗 Connecting to WebSocket:', wsUrl);
        this.updateConnectionStatus('Connecting', 'connecting');

        try {
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('✅ WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('Connected', 'connected');
                
                // Request current price data and start streaming
                this.websocket.send(JSON.stringify({
                    type: 'get_current_price'
                }));
                
                // Also request to start real-time streaming
                this.websocket.send(JSON.stringify({
                    type: 'start_streaming',
                    symbol: 'GOLD'
                }));
                
                console.log('📡 Requested real-time gold price streaming');
            };

            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('❌ Error parsing WebSocket message:', error);
                }
            };

            this.websocket.onclose = (event) => {
                console.log('🔌 WebSocket disconnected:', event.code, event.reason);
                this.isConnected = false;
                this.updateConnectionStatus('Disconnected', 'disconnected');
                
                if (event.code !== 1000) { // Not a normal closure
                    this.attemptReconnect();
                }
            };

            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.updateConnectionStatus('Connection Error', 'disconnected');
            };

        } catch (error) {
            console.error('❌ WebSocket connection failed:', error);
            this.updateConnectionStatus('Connection Failed', 'disconnected');
            this.attemptReconnect();
        }
    }

    handleWebSocketMessage(message) {
        console.log('📨 Received WebSocket message:', message.type);
        
        switch (message.type) {
            case 'gold_price_update':
                console.log('💰 Gold price update:', message.data);
                this.updatePriceDisplay(message.data);
                this.addPriceToChart(message.data);
                this.updateTradePrice(message.data);
                break;
            case 'price_data':
                // Handle real-time price data from Capital.com
                if (message.data && message.data.bid && message.data.ask) {
                    const priceData = {
                        bid: message.data.bid,
                        ask: message.data.ask,
                        mid: (message.data.bid + message.data.ask) / 2,
                        spread: message.data.ask - message.data.bid,
                        timestamp: message.data.timestamp || Date.now()
                    };
                    
                    console.log('📊 Real-time price data:', priceData);
                    this.updatePriceDisplay(priceData);
                    this.addPriceToChart(priceData);
                    this.updateTradePrice(priceData);
                }
                break;
            case 'connection_status':
                console.log('📡 Connection status:', message);
                break;
            case 'pong':
                console.log('🏓 Received pong');
                break;
            case 'error':
                console.error('❌ WebSocket error:', message.message);
                break;
            default:
                console.log('📨 Unknown message type:', message.type, message);
        }
    }

    updatePriceDisplay(data) {
        this.lastPriceUpdate = new Date();
        
        // Update main price display
        const mainPrice = document.getElementById('main-price');
        const mainChange = document.getElementById('main-change');
        
        if (mainPrice && data.mid) {
            const price = data.mid.toFixed(2);
            mainPrice.textContent = `$${this.formatPrice(price)}`;
            
            // Add flash animation
            mainPrice.classList.add('updated');
            setTimeout(() => mainPrice.classList.remove('updated'), 300);
        }

        // Update price change
        if (mainChange && data.change !== undefined) {
            const changeAmount = mainChange.querySelector('.change-amount');
            const changePercent = mainChange.querySelector('.change-percent');
            
            if (changeAmount && changePercent) {
                changeAmount.textContent = `${data.change >= 0 ? '+' : ''}$${Math.abs(data.change).toFixed(2)}`;
                changePercent.textContent = `(${data.changePercent >= 0 ? '+' : ''}${data.changePercent.toFixed(2)}%)`;
                
                mainChange.className = 'price-change ' + (data.change >= 0 ? 'positive' : 'negative');
            }
        }

        // Update market details
        const updates = {
            'bid-price': data.bid ? `$${data.bid.toFixed(2)}` : null,
            'ask-price': data.ask ? `$${data.ask.toFixed(2)}` : null,
            'spread': data.spread ? `$${data.spread.toFixed(2)}` : null,
            'high-price': data.high ? `$${data.high.toFixed(2)}` : null,
            'low-price': data.low ? `$${data.low.toFixed(2)}` : null
        };

        for (const [id, value] of Object.entries(updates)) {
            const element = document.getElementById(id);
            if (element && value) {
                element.textContent = value;
            }
        }

        // Update last update time
        this.updateLastUpdate();
    }

    addPriceToChart(data) {
        if (!this.chart || !this.candlestickSeries) {
            console.log('⚠️ Chart not ready for data updates');
            return;
        }

        const timestamp = Math.floor(Date.now() / 1000);
        const price = data.mid || data.bid || data.ask;
        
        if (!price) {
            console.log('⚠️ No price data available');
            return;
        }

        console.log('📊 Adding real price to chart:', price.toFixed(2));
        
        // Store raw tick data
        this.rawTickData.push({
            time: timestamp,
            price: price,
            volume: Math.floor(Math.random() * 1000) + 500, // Simulate tick volume
            bid: data.bid,
            ask: data.ask,
            mid: data.mid
        });
        
        // Keep only recent tick data (last 24 hours)
        const oneDayAgo = timestamp - (24 * 60 * 60);
        this.rawTickData = this.rawTickData.filter(tick => tick.time >= oneDayAgo);
        
        // If this is the first real data, clear sample data
        if (this.candleData.length > 0 && data.timestamp) {
            this.clearSampleData();
        }
        
        // Aggregate tick data into candles
        this.aggregateTickData();
        
        // For real-time updates, also update the current candle in the active timeframe
        this.updateCurrentCandle(timestamp, price);
        
        console.log('✅ Price data processed and chart updated');
    }

    updateCurrentCandle(timestamp, price) {
        let currentCandles, currentVolumes;
        let candleInterval;
        
        // Determine which timeframe data to update
        switch (this.currentTimeframe) {
            case '1m':
                currentCandles = this.candleData1m;
                currentVolumes = this.volumeData1m;
                candleInterval = 60; // 1 minute
                break;
            case '5m':
                currentCandles = this.candleData5m;
                currentVolumes = this.volumeData5m;
                candleInterval = 300; // 5 minutes
                break;
            default:
                return;
        }
        
        if (currentCandles.length === 0) return;
        
        const lastCandle = currentCandles[currentCandles.length - 1];
        const candleStartTime = Math.floor(timestamp / candleInterval) * candleInterval;
        
        // Check if we need to update the current candle or create a new one
        if (lastCandle.time === candleStartTime) {
            // Update existing candle
            const updatedCandle = {
                time: lastCandle.time,
                open: lastCandle.open,
                high: Math.max(lastCandle.high, price),
                low: Math.min(lastCandle.low, price),
                close: price
            };
            
            currentCandles[currentCandles.length - 1] = updatedCandle;
            
            // Update the chart with real-time data
            this.candlestickSeries.update(updatedCandle);
            
            const lineData = {
                time: updatedCandle.time,
                value: price
            };
            
            this.lineSeries.update(lineData);
            this.areaSeries.update(lineData);
            
            // Auto-scroll to latest data
            this.chart.timeScale().scrollToRealTime();
        }
    }

    updatePriceInfo(data) {
        // Update crosshair price info if needed
        if (this.currentChartType === 'candlestick' && data.open !== undefined) {
            const info = `O: ${data.open.toFixed(2)} H: ${data.high.toFixed(2)} L: ${data.low.toFixed(2)} C: ${data.close.toFixed(2)}`;
            // Update price info display if you have one
        } else if (data.value !== undefined) {
            const info = `Price: ${data.value.toFixed(2)}`;
            // Update price info display if you have one
        }
    }

    updateConnectionStatus(status, className) {
        const statusElement = document.getElementById('connection-status');
        const dotElement = document.getElementById('connection-dot');
        
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = className;
        }
        
        if (dotElement) {
            dotElement.className = `status-dot ${className}`;
        }
    }

    updateLastUpdate() {
        const lastUpdate = document.getElementById('last-update');
        if (lastUpdate && this.lastPriceUpdate) {
            lastUpdate.textContent = `Updated ${this.lastPriceUpdate.toLocaleTimeString()}`;
        }
    }

    updateTradePrice(data) {
        const tradePriceInput = document.getElementById('trade-price');
        const totalValueSpan = document.getElementById('total-value');
        
        if (tradePriceInput && data.ask) {
            tradePriceInput.value = data.ask.toFixed(2);
        }
        
        // Update total value calculation
        if (totalValueSpan) {
            const amountInput = document.querySelector('.trade-input[step="0.1"]');
            const amount = amountInput ? parseFloat(amountInput.value) || 1 : 1;
            const price = data.ask || data.mid || 0;
            const total = amount * price;
            totalValueSpan.textContent = `$${total.toFixed(2)}`;
        }
    }

    formatPrice(price) {
        return parseFloat(price).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    switchTimeframe(timeframe) {
        // Update active timeframe button
        document.querySelectorAll('.timeframe-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent === timeframe) {
                btn.classList.add('active');
            }
        });
        
        this.currentTimeframe = timeframe;
        
        // Update chart data based on selected timeframe
        this.updateChartForTimeframe(timeframe);
        
        console.log(`📊 Switched to ${timeframe} timeframe`);
    }

    switchTradeMode(mode) {
        // Update active trade tab
        document.querySelectorAll('.trade-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        event.target.classList.add('active');
        
        // Update trade button
        const tradeButton = document.querySelector('.trade-button');
        if (tradeButton) {
            if (mode === 'buy') {
                tradeButton.className = 'trade-button buy-button';
                tradeButton.innerHTML = '<i class="fas fa-arrow-up"></i> Buy XAU/USD';
            } else {
                tradeButton.className = 'trade-button sell-button';
                tradeButton.innerHTML = '<i class="fas fa-arrow-down"></i> Sell XAU/USD';
            }
        }
    }

    initTradeCalculator() {
        const amountInput = document.querySelector('.trade-input[step="0.1"]');
        if (amountInput) {
            amountInput.addEventListener('input', () => {
                this.calculateTradeValue();
            });
        }
    }

    calculateTradeValue() {
        const amountInput = document.querySelector('.trade-input[step="0.1"]');
        const priceInput = document.getElementById('trade-price');
        const totalValueSpan = document.getElementById('total-value');
        
        if (amountInput && priceInput && totalValueSpan) {
            const amount = parseFloat(amountInput.value) || 0;
            const price = parseFloat(priceInput.value) || 0;
            const total = amount * price;
            totalValueSpan.textContent = `$${total.toFixed(2)}`;
        }
    }

    startClockUpdate() {
        const updateClock = () => {
            const serverTimeElement = document.getElementById('server-time');
            const liveTimeElement = document.getElementById('live-time');
            const now = new Date();
            const timeString = now.toLocaleTimeString('en-US', { 
                hour12: false, 
                timeZone: 'UTC' 
            }) + ' UTC';
            
            if (serverTimeElement) {
                serverTimeElement.textContent = timeString;
            }
            
            if (liveTimeElement) {
                liveTimeElement.textContent = now.toLocaleTimeString();
            }
        };
        
        updateClock();
        setInterval(updateClock, 1000);
    }

    resetChartZoom() {
        if (this.chart) {
            this.chart.timeScale().fitContent();
        }
    }

    toggleGrid() {
        if (this.chart) {
            const currentOptions = this.chart.options();
            const gridVisible = currentOptions.grid.vertLines.visible;
            
            this.chart.applyOptions({
                grid: {
                    vertLines: { visible: !gridVisible },
                    horzLines: { visible: !gridVisible }
                }
            });
            
            const toggleBtn = document.getElementById('toggle-grid');
            if (toggleBtn) {
                toggleBtn.classList.toggle('active', !gridVisible);
            }
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('❌ Max reconnection attempts reached');
            this.updateConnectionStatus('Connection Failed', 'disconnected');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.updateConnectionStatus(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'connecting');

        setTimeout(() => {
            this.connectWebSocket();
        }, delay);
    }

    // Ping to keep connection alive
    startPingInterval() {
        setInterval(() => {
            if (this.websocket && this.isConnected) {
                this.websocket.send(JSON.stringify({
                    type: 'ping'
                }));
            }
        }, 30000); // Ping every 30 seconds
    }

    addSampleData() {
        // Add sample data for both 1m and 5m timeframes
        const now = Math.floor(Date.now() / 1000);
        const sampleData1m = [];
        const sampleData5m = [];
        const lineData1m = [];
        const lineData5m = [];
        const volumeData1m = [];
        const volumeData5m = [];
        
        let basePrice = 3339.50;
        
        // Generate 1-minute sample data (last 100 minutes)
        for (let i = 0; i < 100; i++) {
            const time = now - (100 - i) * 60; // 1 minute intervals
            const open = basePrice + (Math.random() - 0.5) * 2;
            const close = open + (Math.random() - 0.5) * 3;
            const high = Math.max(open, close) + Math.random() * 1.5;
            const low = Math.min(open, close) - Math.random() * 1.5;
            
            sampleData1m.push({
                time: time,
                open: parseFloat(open.toFixed(2)),
                high: parseFloat(high.toFixed(2)),
                low: parseFloat(low.toFixed(2)),
                close: parseFloat(close.toFixed(2))
            });
            
            lineData1m.push({
                time: time,
                value: parseFloat(close.toFixed(2))
            });
            
            volumeData1m.push({
                time: time,
                value: Math.floor(Math.random() * 5000) + 1000,
                color: close > open ? '#00d4aa' : '#ff6b6b'
            });
            
            basePrice = close;
        }
        
        // Generate 5-minute sample data from 1-minute data
        for (let i = 0; i < sampleData1m.length; i += 5) {
            const fiveMinGroup = sampleData1m.slice(i, i + 5);
            if (fiveMinGroup.length === 5) {
                const fiveMinTime = fiveMinGroup[0].time;
                const open = fiveMinGroup[0].open;
                const close = fiveMinGroup[4].close;
                const high = Math.max(...fiveMinGroup.map(d => d.high));
                const low = Math.min(...fiveMinGroup.map(d => d.low));
                
                sampleData5m.push({
                    time: fiveMinTime,
                    open: parseFloat(open.toFixed(2)),
                    high: parseFloat(high.toFixed(2)),
                    low: parseFloat(low.toFixed(2)),
                    close: parseFloat(close.toFixed(2))
                });
                
                lineData5m.push({
                    time: fiveMinTime,
                    value: parseFloat(close.toFixed(2))
                });
                
                const volumeSum = volumeData1m.slice(i, i + 5).reduce((sum, vol) => sum + vol.value, 0);
                volumeData5m.push({
                    time: fiveMinTime,
                    value: volumeSum,
                    color: close > open ? '#00d4aa' : '#ff6b6b'
                });
            }
        }
        
        // Store sample data for both timeframes
        this.candleData1m = sampleData1m;
        this.candleData5m = sampleData5m;
        this.volumeData1m = volumeData1m;
        this.volumeData5m = volumeData5m;
        
        // Set the chart to show 1m data initially (since currentTimeframe is '1m')
        this.updateChartForTimeframe(this.currentTimeframe);
        
        // Update UI with latest price
        const latestCandle = sampleData1m[sampleData1m.length - 1];
        this.updatePriceDisplay({
            mid: latestCandle.close,
            bid: latestCandle.close - 0.15,
            ask: latestCandle.close + 0.15,
            spread: 0.30,
            high: Math.max(...sampleData1m.map(d => d.high)),
            low: Math.min(...sampleData1m.map(d => d.low)),
            change: latestCandle.close - sampleData1m[0].close,
            changePercent: ((latestCandle.close - sampleData1m[0].close) / sampleData1m[0].close) * 100
        });
        
        console.log('📊 Sample data loaded for both 1m and 5m timeframes');
        console.log(`   - 1m candles: ${sampleData1m.length}`);
        console.log(`   - 5m candles: ${sampleData5m.length}`);
    }

    generateInitialData() {
        if (!this.chart) {
            console.error('❌ Chart not initialized when trying to generate data');
            return;
        }
        
        if (!this.candlestickSeries) {
            console.error('❌ Chart series not initialized when trying to generate data');
            return;
        }
        
        console.log('📊 Generating initial chart data...');
        
        // Generate sample historical data for the past 24 hours
        const now = Math.floor(Date.now() / 1000);
        const basePrice = 2050.00; // Starting gold price
        const dataPoints = 100;
        
        const candleData = [];
        const lineData = [];
        const volumeData = [];
        
        for (let i = dataPoints; i > 0; i--) {
            const timestamp = now - (i * 60); // 1-minute intervals
            const volatility = Math.random() * 2 - 1; // -1 to 1
            const price = basePrice + (volatility * 5) + (Math.sin(i / 10) * 10); // Some price movement
            
            const open = price + (Math.random() * 2 - 1);
            const close = price + (Math.random() * 2 - 1);
            const high = Math.max(open, close) + Math.random() * 2;
            const low = Math.min(open, close) - Math.random() * 2;
            
            // Candlestick data
            candleData.push({
                time: timestamp,
                open: parseFloat(open.toFixed(2)),
                high: parseFloat(high.toFixed(2)),
                low: parseFloat(low.toFixed(2)),
                close: parseFloat(close.toFixed(2))
            });
            
            // Line/Area data
            lineData.push({
                time: timestamp,
                value: parseFloat(close.toFixed(2))
            });
            
            // Volume data
            volumeData.push({
                time: timestamp,
                value: Math.floor(Math.random() * 10000) + 1000,
                color: close > open ? '#00d4aa' : '#ff6b6b'
            });
        }
        
        try {
            // Set data to all series
            this.candlestickSeries.setData(candleData);
            this.lineSeries.setData(lineData);
            this.areaSeries.setData(lineData);
            this.volumeSeries.setData(volumeData);
            
            // Store the data
            this.candleData = candleData;
            this.priceData = lineData.map(d => ({ x: d.time, y: d.value }));
            this.volumeData = volumeData;
            
            // Fit the chart to show all data
            this.chart.timeScale().fitContent();
            
            console.log('✅ Initial chart data generated successfully:', candleData.length, 'data points');
            console.log('📊 Sample candle data:', candleData.slice(0, 3));
            
        } catch (error) {
            console.error('❌ Error setting chart data:', error);
        }
    }

    // Test method to add a simple data point
    testChartData() {
        console.log('🧪 Testing chart with simple data...');
        
        if (!this.chart || !this.candlestickSeries) {
            console.error('❌ Chart or series not available for testing');
            return;
        }
        
        const now = Math.floor(Date.now() / 1000);
        const testData = [
            { time: now - 120, open: 2045, high: 2048, low: 2042, close: 2047 },
            { time: now - 60, open: 2047, high: 2050, low: 2045, close: 2049 },
            { time: now, open: 2049, high: 2052, low: 2046, close: 2051 }
        ];
        
        try {
            this.candlestickSeries.setData(testData);
            this.chart.timeScale().fitContent();
            console.log('✅ Test data added successfully:', testData);
        } catch (error) {
            console.error('❌ Error adding test data:', error);
        }
    }

    clearSampleData() {
        // Clear existing sample data when real data starts coming
        if (this.candleData.length > 0) {
            console.log('🧹 Clearing sample data to show real data');
            this.candleData = [];
            this.priceData = [];
            this.volumeData = [];
            
            // Clear chart series
            this.candlestickSeries.setData([]);
            this.lineSeries.setData([]);
            this.areaSeries.setData([]);
            this.volumeSeries.setData([]);
        }
    }

    updateChartForTimeframe(timeframe) {
        if (!this.chart) return;
        
        let candleData, volumeData, lineData;
        
        switch (timeframe) {
            case '1m':
                candleData = this.candleData1m;
                volumeData = this.volumeData1m;
                break;
            case '5m':
                candleData = this.candleData5m;
                volumeData = this.volumeData5m;
                break;
            default:
                // For other timeframes, use 1m data for now
                candleData = this.candleData1m;
                volumeData = this.volumeData1m;
                break;
        }
        
        if (candleData.length === 0) {
            console.log(`⚠️ No data available for ${timeframe} timeframe`);
            return;
        }
        
        // Convert candle data to line data
        lineData = candleData.map(candle => ({
            time: candle.time,
            value: candle.close
        }));
        
        // Update all series with the new timeframe data
        this.candlestickSeries.setData(candleData);
        this.lineSeries.setData(lineData);
        this.areaSeries.setData(lineData);
        this.volumeSeries.setData(volumeData);
        
        // Update stored data references
        this.candleData = candleData;
        this.priceData = lineData.map(d => ({ x: d.time, y: d.value }));
        this.volumeData = volumeData;
        
        // Fit chart to show all data
        this.chart.timeScale().fitContent();
        
        console.log(`✅ Chart updated for ${timeframe} timeframe with ${candleData.length} candles`);
    }

    aggregateTickData() {
        if (this.rawTickData.length === 0) return;
        
        // Aggregate 1-minute candles
        this.aggregate1MinuteCandles();
        
        // Aggregate 5-minute candles from 1-minute data
        this.aggregate5MinuteCandles();
        
        // Update chart if we're viewing current timeframe
        if (this.currentTimeframe === '1m' || this.currentTimeframe === '5m') {
            this.updateChartForTimeframe(this.currentTimeframe);
        }
    }

    aggregate1MinuteCandles() {
        const groupedData = {};
        
        // Group ticks by minute
        this.rawTickData.forEach(tick => {
            const minuteTimestamp = Math.floor(tick.time / 60) * 60; // Round down to minute
            
            if (!groupedData[minuteTimestamp]) {
                groupedData[minuteTimestamp] = {
                    time: minuteTimestamp,
                    prices: [],
                    volumes: []
                };
            }
            
            groupedData[minuteTimestamp].prices.push(tick.price);
            groupedData[minuteTimestamp].volumes.push(tick.volume || 1000);
        });
        
        // Convert grouped data to candles
        const newCandles = [];
        const newVolumes = [];
        
        Object.keys(groupedData).sort().forEach(timestamp => {
            const minuteData = groupedData[timestamp];
            const prices = minuteData.prices;
            
            if (prices.length > 0) {
                const open = prices[0];
                const close = prices[prices.length - 1];
                const high = Math.max(...prices);
                const low = Math.min(...prices);
                const volume = minuteData.volumes.reduce((sum, vol) => sum + vol, 0);
                
                newCandles.push({
                    time: parseInt(timestamp),
                    open: parseFloat(open.toFixed(2)),
                    high: parseFloat(high.toFixed(2)),
                    low: parseFloat(low.toFixed(2)),
                    close: parseFloat(close.toFixed(2))
                });
                
                newVolumes.push({
                    time: parseInt(timestamp),
                    value: volume,
                    color: close > open ? '#00d4aa' : '#ff6b6b'
                });
            }
        });
        
        // Update or append to existing 1m data
        this.candleData1m = this.mergeCandles(this.candleData1m, newCandles);
        this.volumeData1m = this.mergeVolumes(this.volumeData1m, newVolumes);
        
        // Keep only last N data points
        if (this.candleData1m.length > this.maxDataPoints) {
            this.candleData1m = this.candleData1m.slice(-this.maxDataPoints);
            this.volumeData1m = this.volumeData1m.slice(-this.maxDataPoints);
        }
        
        console.log(`📊 Aggregated ${newCandles.length} new 1-minute candles`);
    }

    aggregate5MinuteCandles() {
        if (this.candleData1m.length === 0) return;
        
        const groupedData = {};
        
        // Group 1-minute candles by 5-minute periods
        this.candleData1m.forEach(candle => {
            const fiveMinuteTimestamp = Math.floor(candle.time / 300) * 300; // Round down to 5 minutes
            
            if (!groupedData[fiveMinuteTimestamp]) {
                groupedData[fiveMinuteTimestamp] = {
                    time: fiveMinuteTimestamp,
                    candles: []
                };
            }
            
            groupedData[fiveMinuteTimestamp].candles.push(candle);
        });
        
        // Convert grouped data to 5-minute candles
        const newCandles = [];
        const newVolumes = [];
        
        Object.keys(groupedData).sort().forEach(timestamp => {
            const fiveMinuteData = groupedData[timestamp];
            const candles = fiveMinuteData.candles;
            
            if (candles.length > 0) {
                const open = candles[0].open;
                const close = candles[candles.length - 1].close;
                const high = Math.max(...candles.map(c => c.high));
                const low = Math.min(...candles.map(c => c.low));
                
                // Calculate volume from corresponding 1m volume data
                const volumeInPeriod = this.volumeData1m
                    .filter(v => v.time >= parseInt(timestamp) && v.time < parseInt(timestamp) + 300)
                    .reduce((sum, vol) => sum + vol.value, 0);
                
                newCandles.push({
                    time: parseInt(timestamp),
                    open: parseFloat(open.toFixed(2)),
                    high: parseFloat(high.toFixed(2)),
                    low: parseFloat(low.toFixed(2)),
                    close: parseFloat(close.toFixed(2))
                });
                
                newVolumes.push({
                    time: parseInt(timestamp),
                    value: volumeInPeriod,
                    color: close > open ? '#00d4aa' : '#ff6b6b'
                });
            }
        });
        
        // Update or append to existing 5m data
        this.candleData5m = this.mergeCandles(this.candleData5m, newCandles);
        this.volumeData5m = this.mergeVolumes(this.volumeData5m, newVolumes);
        
        // Keep only last N data points
        if (this.candleData5m.length > this.maxDataPoints) {
            this.candleData5m = this.candleData5m.slice(-this.maxDataPoints);
            this.volumeData5m = this.volumeData5m.slice(-this.maxDataPoints);
        }
        
        console.log(`📊 Aggregated ${newCandles.length} new 5-minute candles`);
    }

    mergeCandles(existingCandles, newCandles) {
        const merged = [...existingCandles];
        
        newCandles.forEach(newCandle => {
            const existingIndex = merged.findIndex(candle => candle.time === newCandle.time);
            
            if (existingIndex >= 0) {
                // Update existing candle
                merged[existingIndex] = newCandle;
            } else {
                // Add new candle
                merged.push(newCandle);
            }
        });
        
        // Sort by time
        return merged.sort((a, b) => a.time - b.time);
    }

    mergeVolumes(existingVolumes, newVolumes) {
        const merged = [...existingVolumes];
        
        newVolumes.forEach(newVolume => {
            const existingIndex = merged.findIndex(volume => volume.time === newVolume.time);
            
            if (existingIndex >= 0) {
                // Update existing volume
                merged[existingIndex] = newVolume;
            } else {
                // Add new volume
                merged.push(newVolume);
            }
        });
        
        // Sort by time
        return merged.sort((a, b) => a.time - b.time);
    }

    // ...existing code...
}

// Data Fetching Manager
class DataFetchingManager {
    constructor() {
        this.isLoading = false;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Recent data button
        document.getElementById('fetch-recent')?.addEventListener('click', () => {
            this.fetchRecentData();
        });

        // Daily data button
        document.getElementById('fetch-daily')?.addEventListener('click', () => {
            this.fetchDailyData();
        });

        // Historical data button
        document.getElementById('fetch-historical')?.addEventListener('click', () => {
            this.fetchHistoricalData();
        });

        // All data button (with confirmation)
        document.getElementById('fetch-all')?.addEventListener('click', () => {
            this.fetchAllData();
        });
    }

    async fetchRecentData(hours = 24) {
        if (this.isLoading) return;

        try {
            this.setLoadingState(true, `Fetching recent ${hours} hours of data...`);

            const response = await fetch(`/api/fetch-recent-data?hours=${hours}`);
            const result = await response.json();

            if (result.success) {
                this.showSuccess(`✅ Fetched ${result.data_count} recent records`);
                console.log('Recent data:', result);
                
                // Update chart if needed
                if (result.sample_data && result.sample_data.length > 0) {
                    this.processAndDisplayData(result.sample_data);
                }
            } else {
                this.showError(`❌ Failed to fetch recent data: ${result.error}`);
            }
        } catch (error) {
            this.showError(`❌ Network error: ${error.message}`);
        } finally {
            this.setLoadingState(false);
        }
    }

    async fetchDailyData(days = 30) {
        if (this.isLoading) return;

        try {
            this.setLoadingState(true, `Fetching ${days} days of daily data...`);

            const response = await fetch(`/api/fetch-daily-data?days=${days}`);
            const result = await response.json();

            if (result.success) {
                this.showSuccess(`✅ Fetched ${result.data_count} daily records`);
                console.log('Daily data:', result);
                
                // Process daily data for chart
                if (result.data && result.data.length > 0) {
                    this.processAndDisplayData(result.data);
                }
            } else {
                this.showError(`❌ Failed to fetch daily data: ${result.error}`);
            }
        } catch (error) {
            this.showError(`❌ Network error: ${error.message}`);
        } finally {
            this.setLoadingState(false);
        }
    }

    async fetchHistoricalData(days = 30, resolution = 'MINUTE_5') {
        if (this.isLoading) return;

        try {
            this.setLoadingState(true, `Fetching ${days} days of ${resolution} data...`);

            const response = await fetch(`/api/fetch-historical-data?days=${days}&resolution=${resolution}&max_pages=20`);
            const result = await response.json();

            if (result.success) {
                this.showSuccess(`✅ Fetched ${result.data_count} historical records`);
                console.log('Historical data:', result);
                
                // Process historical data for chart
                if (result.sample_data && result.sample_data.length > 0) {
                    this.processAndDisplayData(result.sample_data);
                }
            } else {
                this.showError(`❌ Failed to fetch historical data: ${result.error}`);
            }
        } catch (error) {
            this.showError(`❌ Network error: ${error.message}`);
        } finally {
            this.setLoadingState(false);
        }
    }

    async fetchAllData() {
        // Show confirmation dialog for all data
        const confirmed = confirm(
            '⚠️ This will fetch ALL available historical data which may:\n' +
            '• Take several minutes\n' +
            '• Use significant API quota\n' +
            '• Return large amounts of data\n\n' +
            'Are you sure you want to continue?'
        );

        if (!confirmed) return;

        if (this.isLoading) return;

        try {
            this.setLoadingState(true, 'Fetching ALL available data... This may take several minutes.');

            const response = await fetch('/api/fetch-all-data', {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                this.showSuccess(`✅ Fetched ${result.data_count} total records! Warning: Large dataset received.`);
                console.log('All data:', result);
                
                // Process sample of all data for chart
                if (result.sample_data && result.sample_data.length > 0) {
                    this.processAndDisplayData(result.sample_data);
                }
            } else {
                this.showError(`❌ Failed to fetch all data: ${result.error}`);
            }
        } catch (error) {
            this.showError(`❌ Network error: ${error.message}`);
        } finally {
            this.setLoadingState(false);
        }
    }

    processAndDisplayData(data) {
        // Convert API data to chart format
        try {
            const chartData = data.map(item => {
                const timestamp = new Date(item.timestamp).getTime() / 1000;
                
                return {
                    time: timestamp,
                    open: item.open_mid || item.close_mid || 2000,
                    high: item.high_mid || item.close_mid || 2000,
                    low: item.low_mid || item.close_mid || 2000,
                    close: item.close_mid || 2000,
                    value: item.close_mid || 2000, // For line charts
                    volume: item.volume || Math.random() * 1000 + 500
                };
            }).sort((a, b) => a.time - b.time);

            console.log('📊 Processed chart data:', chartData.slice(0, 5));

            // Update the main chart if available
            if (window.goldTradingPlatform && window.goldTradingPlatform.chart) {
                // Clear existing data
                window.goldTradingPlatform.candleData = chartData;
                window.goldTradingPlatform.priceData = chartData;
                
                // Update chart series
                if (window.goldTradingPlatform.candlestickSeries) {
                    window.goldTradingPlatform.candlestickSeries.setData(chartData);
                }
                if (window.goldTradingPlatform.lineSeries) {
                    window.goldTradingPlatform.lineSeries.setData(chartData);
                }
                if (window.goldTradingPlatform.areaSeries) {
                    window.goldTradingPlatform.areaSeries.setData(chartData);
                }

                console.log('✅ Chart updated with fetched data');
            }
        } catch (error) {
            console.error('❌ Error processing data for chart:', error);
            this.showError('❌ Error processing data for display');
        }
    }

    setLoadingState(isLoading, message = '') {
        this.isLoading = isLoading;
        const statusElement = document.getElementById('data-status');
        const statusText = statusElement?.querySelector('.status-text');
        const progressBar = document.getElementById('progress-bar');
        const buttons = document.querySelectorAll('.data-btn');

        if (isLoading) {
            statusElement?.classList.add('loading');
            statusElement?.classList.remove('success', 'error');
            if (statusText) statusText.textContent = message;
            progressBar?.style.setProperty('display', 'block');
            buttons.forEach(btn => btn.disabled = true);
        } else {
            statusElement?.classList.remove('loading');
            progressBar?.style.setProperty('display', 'none');
            buttons.forEach(btn => btn.disabled = false);
        }
    }

    showSuccess(message) {
        const statusElement = document.getElementById('data-status');
        const statusText = statusElement?.querySelector('.status-text');
        
        statusElement?.classList.add('success');
        statusElement?.classList.remove('loading', 'error');
        if (statusText) statusText.textContent = message;
        
        // Clear success message after 5 seconds
        setTimeout(() => {
            statusElement?.classList.remove('success');
            if (statusText) statusText.textContent = 'Ready to fetch data';
        }, 5000);
    }

    showError(message) {
        const statusElement = document.getElementById('data-status');
        const statusText = statusElement?.querySelector('.status-text');
        
        statusElement?.classList.add('error');
        statusElement?.classList.remove('loading', 'success');
        if (statusText) statusText.textContent = message;
        
        // Clear error message after 10 seconds
        setTimeout(() => {
            statusElement?.classList.remove('error');
            if (statusText) statusText.textContent = 'Ready to fetch data';
        }, 10000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 DOM loaded, initializing TradingView-style Gold Trading Platform...');
    
    // Check if TradingView library is loaded
    if (typeof LightweightCharts === 'undefined') {
        console.error('❌ TradingView Lightweight Charts library not loaded!');
        return;
    }
    
    console.log('✅ TradingView Lightweight Charts library loaded successfully');
    
    window.goldTradingPlatform = new GoldTradingPlatform();
    window.dataFetchingManager = new DataFetchingManager();
    
    console.log('🚀 Gold Trading Platform initialized with data fetching capabilities');
    
    // Start ping interval
    window.goldTradingPlatform.startPingInterval();
    
    console.log('🎯 TradingView-style Gold Trading Platform initialized');
    
    // Test chart after 2 seconds
    setTimeout(() => {
        if (window.goldTradingPlatform.chart) {
            console.log('✅ Chart object exists:', window.goldTradingPlatform.chart);
            console.log('📊 Chart data points:', window.goldTradingPlatform.candleData?.length || 0);
            
            // Check if real data is coming through WebSocket
            if (window.goldTradingPlatform.isConnected) {
                console.log('📡 WebSocket connected, waiting for real data...');
            } else {
                console.log('⚠️ WebSocket not connected, using sample data');
            }
        } else {
            console.error('❌ Chart object not found!');
        }
    }, 2000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.goldTradingPlatform && window.goldTradingPlatform.websocket) {
        window.goldTradingPlatform.websocket.close();
    }
});
