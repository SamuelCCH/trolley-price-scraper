from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import json
import hashlib

from scraper import TrolleyScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all routes
CORS(app, origins="*")

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour", "20 per minute"]
)

# Initialize scraper
scraper = TrolleyScraper()

# Simple in-memory cache (for production, use Redis)
cache = {}
CACHE_DURATION = 3600  # 1 hour in seconds

def get_cache_key(query: str, max_results: int = 5) -> str:
    """Generate a cache key for the query"""
    return hashlib.md5(f"{query.lower()}_{max_results}".encode()).hexdigest()

def is_cache_valid(timestamp: float) -> bool:
    """Check if cached data is still valid"""
    return time.time() - timestamp < CACHE_DURATION

def get_cached_result(cache_key: str) -> Dict:
    """Get cached result if valid"""
    if cache_key in cache:
        cached_data = cache[cache_key]
        if is_cache_valid(cached_data['timestamp']):
            logger.info(f"Cache hit for key: {cache_key}")
            return cached_data['data']
        else:
            # Remove expired cache entry
            del cache[cache_key]
            logger.info(f"Cache expired for key: {cache_key}")
    return None

def set_cache(cache_key: str, data: Dict):
    """Store data in cache"""
    cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }
    logger.info(f"Data cached for key: {cache_key}")

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "service": "Trolley Price Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/api/price": "GET - Search for product prices",
            "/api/health": "GET - Health check"
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Detailed health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache),
        "uptime": "Service is running"
    })

@app.route('/api/price', methods=['GET'])
@limiter.limit("10 per minute")
def get_prices():
    """
    Get product prices from trolley.co.uk
    
    Query Parameters:
    - query (required): Product search term
    - max_results (optional): Maximum number of results (default: 5, max: 20)
    """
    try:
        # Get query parameters
        query = request.args.get('query', '').strip()
        max_results = min(int(request.args.get('max_results', 5)), 20)
        
        # Validate input
        if not query:
            return jsonify({
                "error": "Missing required parameter 'query'",
                "example": "/api/price?query=coca cola"
            }), 400
        
        if len(query) < 2:
            return jsonify({
                "error": "Query must be at least 2 characters long"
            }), 400
        
        logger.info(f"Processing request for query: '{query}' with max_results: {max_results}")
        
        # Check cache first
        cache_key = get_cache_key(query, max_results)
        cached_result = get_cached_result(cache_key)
        
        if cached_result:
            return jsonify(cached_result)
        
        # Scrape fresh data
        start_time = time.time()
        products = scraper.search_products(query, max_results)
        scrape_time = time.time() - start_time
        
        # Format response
        response_data = {
            "query": query,
            "results": products,
            "metadata": {
                "total_results": len(products),
                "max_results": max_results,
                "scrape_time_seconds": round(scrape_time, 2),
                "timestamp": datetime.now().isoformat(),
                "cached": False
            }
        }
        
        # Cache the result
        set_cache(cache_key, response_data)
        
        logger.info(f"Successfully scraped {len(products)} products in {scrape_time:.2f}s")
        
        return jsonify(response_data)
        
    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        return jsonify({
            "error": "Invalid parameter value",
            "message": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return jsonify({
            "error": "Failed to fetch product data",
            "message": str(e),
            "query": query if 'query' in locals() else None
        }), 500

@app.route('/api/batch', methods=['POST'])
@limiter.limit("5 per minute")
def batch_prices():
    """
    Get prices for multiple products in one request
    
    Request Body (JSON):
    {
        "queries": ["coca cola", "pepsi", "sprite"],
        "max_results_per_query": 3
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'queries' not in data:
            return jsonify({
                "error": "Missing 'queries' in request body",
                "example": {"queries": ["coca cola", "pepsi"]}
            }), 400
        
        queries = data['queries']
        max_results_per_query = min(int(data.get('max_results_per_query', 3)), 10)
        
        if not isinstance(queries, list) or len(queries) == 0:
            return jsonify({
                "error": "'queries' must be a non-empty list"
            }), 400
        
        if len(queries) > 5:
            return jsonify({
                "error": "Maximum 5 queries allowed per batch request"
            }), 400
        
        results = {}
        total_time = 0
        
        for query in queries:
            if not query or len(query.strip()) < 2:
                results[query] = {
                    "error": "Query must be at least 2 characters long"
                }
                continue
            
            try:
                start_time = time.time()
                
                # Check cache
                cache_key = get_cache_key(query.strip(), max_results_per_query)
                cached_result = get_cached_result(cache_key)
                
                if cached_result:
                    results[query] = cached_result
                else:
                    products = scraper.search_products(query.strip(), max_results_per_query)
                    query_time = time.time() - start_time
                    total_time += query_time
                    
                    query_result = {
                        "query": query,
                        "results": products,
                        "metadata": {
                            "total_results": len(products),
                            "scrape_time_seconds": round(query_time, 2),
                            "cached": False
                        }
                    }
                    
                    # Cache individual result
                    set_cache(cache_key, query_result)
                    results[query] = query_result
                
                # Add small delay between requests to be respectful
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
                results[query] = {
                    "error": str(e)
                }
        
        return jsonify({
            "batch_results": results,
            "metadata": {
                "total_queries": len(queries),
                "successful_queries": len([r for r in results.values() if 'error' not in r]),
                "total_scrape_time_seconds": round(total_time, 2),
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return jsonify({
            "error": "Failed to process batch request",
            "message": str(e)
        }), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the cache (useful for development/testing)"""
    global cache
    cache_size = len(cache)
    cache.clear()
    
    return jsonify({
        "message": f"Cache cleared. Removed {cache_size} entries.",
        "timestamp": datetime.now().isoformat()
    })

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please try again later.",
        "retry_after": str(e.retry_after) if hasattr(e, 'retry_after') else "60 seconds"
    }), 429

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": [
            "/api/price?query=<product>",
            "/api/batch (POST)",
            "/api/health",
            "/"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on our end. Please try again later."
    }), 500

if __name__ == '__main__':
    # Get configuration from environment variables
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting Trolley Price Scraper API on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )