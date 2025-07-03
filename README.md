# Forex Analyzer AI Dashboard

A modern, AI-powered forex analysis dashboard built with FastAPI and featuring real-time market data, technical analysis, and LangGraph integration for intelligent trading insights.

## Features

- 🚀 **Real-time Forex Data**: Live currency pair prices and market data
- 📊 **Interactive Charts**: Dynamic price charts with Chart.js
- 🤖 **AI Analysis**: LangGraph-powered intelligent market analysis
- 📱 **Responsive Design**: Modern Bootstrap-based UI that works on all devices
- ⚡ **Fast API Backend**: High-performance REST API with automatic documentation
- 🔄 **Auto-refresh**: Real-time data updates every 30 seconds
- 📈 **Technical Indicators**: RSI, MACD, Bollinger Bands, Moving Averages
- 💡 **Smart Recommendations**: AI-generated buy/sell/hold recommendations

## Technology Stack

- **Backend**: FastAPI, Python 3.12+
- **AI/ML**: LangChain, LangGraph
- **Data**: yfinance, pandas, numpy
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI Framework**: Bootstrap 5
- **Charts**: Chart.js
- **Icons**: Font Awesome

## Installation

1. **Clone the repository** (if needed):
   ```bash
   cd /home/husain/forex
   ```

2. **Activate virtual environment** (already set up):
   ```bash
   source .venv/bin/activate
   ```

3. **Install dependencies** (already installed):
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

Start the FastAPI server:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at:
- **Dashboard**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

### API Endpoints

#### Get Forex Data
```http
GET /api/forex-data
```
Returns current market data for all supported currency pairs.

#### Get Pair History
```http
GET /api/pair-history/{pair}?period=1mo
```
Returns historical data for a specific currency pair.

#### Get AI Analysis
```http
GET /api/analysis/{pair}
```
Returns AI-powered analysis and recommendations for a currency pair.

#### Health Check
```http
GET /health
```
Returns application health status.

## Supported Currency Pairs

- EUR/USD (EURUSD)
- GBP/USD (GBPUSD)
- USD/JPY (USDJPY)
- USD/CHF (USDCHF)
- AUD/USD (AUDUSD)
- USD/CAD (USDCAD)
- NZD/USD (NZDUSD)
- EUR/GBP (EURGBP)

## Project Structure

```
forex/
├── main.py                 # FastAPI application
├── forex_ai.py            # LangGraph AI analysis module
├── requirements.txt        # Python dependencies
├── templates/
│   └── dashboard.html      # Main dashboard template
├── static/
│   ├── css/
│   │   └── dashboard.css   # Custom styles
│   └── js/
│       └── dashboard.js    # Dashboard JavaScript
└── .venv/                  # Virtual environment
```

## Features in Detail

### Real-time Market Data
- Live currency pair prices from Yahoo Finance
- 24-hour high/low values
- Price change and percentage change
- Volume data where available

### Interactive Dashboard
- Responsive card layout for currency pairs
- Click-to-select pair functionality
- Real-time price charts
- Auto-refreshing data every 30 seconds

### AI Analysis (LangGraph Integration)
- Technical indicator analysis
- Market sentiment assessment
- Risk level evaluation
- Smart trading recommendations
- Support and resistance level detection

### Technical Indicators
- **RSI (Relative Strength Index)**: Momentum oscillator
- **MACD**: Moving Average Convergence Divergence
- **Bollinger Bands**: Volatility indicator
- **Moving Averages**: 50-day and 200-day MAs

## Customization

### Adding New Currency Pairs
Edit the `FOREX_PAIRS` list in `main.py`:
```python
FOREX_PAIRS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X",
    "AUDUSD=X", "USDCAD=X", "NZDUSD=X", "EURGBP=X",
    "EURJPY=X"  # Add new pairs here
]
```

### Modifying AI Analysis
Update the LangGraph workflow in `forex_ai.py` to customize the AI analysis logic.

### Styling Changes
Modify `static/css/dashboard.css` to customize the appearance.

## Development

### Running in Development Mode
```bash
python main.py
```

The server will automatically reload when you make changes to the code.

### API Testing
Visit http://localhost:8000/docs for interactive API documentation.

## Future Enhancements

- [ ] User authentication and portfolio tracking
- [ ] Advanced charting with candlestick charts
- [ ] Email/SMS alerts for price movements
- [ ] Historical backtesting capabilities
- [ ] More sophisticated AI models
- [ ] WebSocket for real-time updates
- [ ] Mobile app integration
- [ ] Multi-language support

## Performance Notes

- The application fetches data from Yahoo Finance API
- Chart rendering is optimized for smooth performance
- Auto-refresh can be customized in `dashboard.js`
- Consider implementing caching for production use

## Troubleshooting

### Common Issues

1. **Port already in use**: Change the port in `main.py` or kill the existing process
2. **Missing data**: Some currency pairs may have limited data availability
3. **Slow loading**: Check internet connection and Yahoo Finance API status

### Logs
Check the console output for detailed error messages and API responses.

## License

This project is open source and available under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions, please check the console logs first, then create an issue with detailed information about the problem.
# Forex Trading API
