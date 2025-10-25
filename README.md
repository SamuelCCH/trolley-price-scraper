# Trolley Price Scraper API

A Python web scraper that fetches live product prices from trolley.co.uk and exposes them through a REST API with CORS support for frontend integration.

## Features

- 🔍 **Product Search**: Search for products on trolley.co.uk
- 📊 **Price Comparison**: Get prices from multiple stores (Tesco, Sainsbury's, Asda, etc.)
- 🚀 **REST API**: Simple HTTP endpoints with JSON responses
- 🌐 **CORS Enabled**: Ready for frontend integration
- ⚡ **Caching**: Built-in caching to reduce scraping frequency
- 🛡️ **Rate Limiting**: Prevents overloading the target website
- 📦 **Batch Queries**: Support for multiple products in one request
- 🔧 **Error Handling**: Comprehensive error handling and logging

## API Endpoints

### 1. Search Products
```
GET /api/price?query=<product>&max_results=<number>
```

**Parameters:**
- `query` (required): Product search term (e.g., "coca cola")
- `max_results` (optional): Maximum results to return (default: 5, max: 20)

**Example:**
```bash
GET /api/price?query=coca%20cola&max_results=5
```

**Response:**
```json
{
  "query": "coca cola",
  "results": [
    {
      "store": "Trolley.co.uk",
      "name": "Coca Cola Original",
      "price": "£1.85",
      "brand": "Coca Cola",
      "size": "1L",
      "url": "https://www.trolley.co.uk/product/coca-cola-original/ABC123"
    },
    {
      "store": "Trolley.co.uk",
      "name": "Coca Cola Zero Sugar",
      "price": "£1.75",
      "brand": "Coca Cola",
      "size": "1L",
      "url": "https://www.trolley.co.uk/product/coca-cola-zero/DEF456"
    }
  ],
  "metadata": {
    "total_results": 2,
    "max_results": 5,
    "scrape_time_seconds": 1.23,
    "timestamp": "2025-10-25T16:20:00.000000",
    "cached": false
  }
}
```

### 2. Batch Search
```
POST /api/batch
```

**Request Body:**
```json
{
  "queries": ["coca cola", "pepsi", "sprite"],
  "max_results_per_query": 3
}
```

### 3. Health Check
```
GET /api/health
```

### 4. Service Info
```
GET /
```

## Installation & Setup

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Local Development

1. **Clone/Download the project:**
```bash
cd trolley-price-scraper
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the application:**
```bash
python app.py
```

The API will be available at `http://localhost:5000`

### Environment Configuration

Create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

Edit the `.env` file to customize settings:
```env
HOST=0.0.0.0
PORT=5000
DEBUG=False
CACHE_DURATION_SECONDS=3600
```

## Deployment

### Option 1: Render.com

1. **Create a new Web Service on Render**
2. **Connect your GitHub repository**
3. **Configure the service:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -c gunicorn.conf.py app:app`
   - **Environment:** Python 3

4. **Set environment variables:**
   ```
   PORT=10000
   DEBUG=False
   HOST=0.0.0.0
   ```

### Option 2: Railway

1. **Install Railway CLI:**
```bash
npm install -g @railway/cli
```

2. **Deploy:**
```bash
railway login
railway init
railway up
```

3. **Set environment variables in Railway dashboard**

### Option 3: VPS/Server with Gunicorn

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run with Gunicorn:**
```bash
gunicorn -c gunicorn.conf.py app:app
```

3. **Or run in background:**
```bash
nohup gunicorn -c gunicorn.conf.py app:app &
```

4. **With systemd service (recommended):**

Create `/etc/systemd/system/trolley-scraper.service`:
```ini
[Unit]
Description=Trolley Price Scraper API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/trolley-price-scraper
Environment=PATH=/path/to/venv/bin
ExecStart=/path/to/venv/bin/gunicorn -c gunicorn.conf.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable trolley-scraper
sudo systemctl start trolley-scraper
```

### Option 4: Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
```

Build and run:
```bash
docker build -t trolley-scraper .
docker run -p 5000:5000 trolley-scraper
```

## Usage Examples

### JavaScript/TypeScript (Frontend)

```javascript
// Fetch product prices
async function searchProducts(query) {
  try {
    const response = await fetch(`http://your-api-url/api/price?query=${encodeURIComponent(query)}`);
    const data = await response.json();
    return data.results;
  } catch (error) {
    console.error('Error fetching prices:', error);
    return [];
  }
}

// Usage
const products = await searchProducts('coca cola');
console.log(products);
```

### Python

```python
import requests

def get_prices(query, max_results=5):
    url = f"http://your-api-url/api/price"
    params = {"query": query, "max_results": max_results}
    
    response = requests.get(url, params=params)
    return response.json()

# Usage
results = get_prices("coca cola")
print(results)
```

### cURL

```bash
# Single product search
curl "http://your-api-url/api/price?query=coca%20cola"

# Batch search
curl -X POST "http://your-api-url/api/batch" \
  -H "Content-Type: application/json" \
  -d '{"queries": ["coca cola", "pepsi"], "max_results_per_query": 3}'
```

## Configuration

### Rate Limiting
- Default: 100 requests per hour, 20 per minute
- Batch endpoint: 5 requests per minute
- Configurable via environment variables

### Caching
- Default cache duration: 1 hour
- In-memory cache (for production, consider Redis)
- Automatic cache invalidation

### Logging
- Structured logging with timestamps
- Configurable log levels
- Request/response logging

## Limitations

### Store Information
**Important**: Currently, all products return `"store": "Trolley.co.uk"` in the API response. This is because:

- **Trolley.co.uk is an aggregator site** that displays products from multiple retailers (Tesco, Sainsbury's, ASDA, etc.)
- **Store information is loaded dynamically** via JavaScript after the initial page load
- **Static HTML scraping cannot access** the dynamically loaded store data
- **Store filtering by specific retailers** (e.g., `?store=sainsbury`) will return 0 results

**Workaround**: The API still provides valuable product information including:
- ✅ Product names, prices, brands, and sizes
- ✅ Direct links to products on Trolley.co.uk
- ✅ Fast, cached responses for price comparison

**Future Enhancement**: To get actual store information, the scraper would need to:
- Use a headless browser (Selenium/Playwright) to wait for JavaScript execution
- Make additional API calls to Trolley.co.uk's internal endpoints
- Parse the dynamically loaded content

## Error Handling

The API returns appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request (missing/invalid parameters)
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

Error responses include helpful messages:
```json
{
  "error": "Missing required parameter 'query'",
  "example": "/api/price?query=coca cola"
}
```

## Performance Considerations

- **Caching**: Results are cached for 1 hour by default
- **Rate Limiting**: Prevents overwhelming the target website
- **Timeouts**: 10-second timeout for web requests
- **Batch Processing**: Includes delays between requests
- **Error Recovery**: Automatic retries for failed requests

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Formatting
```bash
black app.py scraper.py
```

### Linting
```bash
flake8 app.py scraper.py
```

## Troubleshooting

### Common Issues

1. **Empty Results**: The website structure may have changed. Check the scraper selectors.
2. **Rate Limiting**: Reduce request frequency or implement longer delays.
3. **Timeout Errors**: Increase timeout values in scraper configuration.
4. **CORS Issues**: Ensure the API is running with CORS enabled.

### Debugging

Enable debug mode:
```bash
export DEBUG=True
python app.py
```

Check logs for detailed error information.

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues or questions, please create an issue in the repository or contact the maintainer.