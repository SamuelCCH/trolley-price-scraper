import requests
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin, quote_plus
from typing import List, Dict, Optional
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrolleyScraper:
    def __init__(self):
        self.base_url = "https://www.trolley.co.uk"
        self.search_url = f"{self.base_url}/search"
        self.session = requests.Session()
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def search_products(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search for products on trolley.co.uk and return structured data
        
        Args:
            query: Product search term
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing product information
        """
        try:
            logger.info(f"Searching for: {query}")
            
            # Prepare search parameters
            params = {
                'q': query,
                'sort': 'relevance'
            }
            
            # Make the search request
            response = self.session.get(
                self.search_url, 
                params=params, 
                timeout=10
            )
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product information
            products = self._extract_products(soup, max_results)
            
            logger.info(f"Found {len(products)} products")
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"Failed to fetch search results: {e}")
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise Exception(f"Failed to parse search results: {e}")
    
    def _extract_products(self, soup: BeautifulSoup, max_results: int) -> List[Dict]:
        """
        Extract product information from the search results page
        """
        products = []
        
        # Look for product containers using the actual trolley.co.uk structure
        product_containers = soup.find_all('div', class_='product-item')
        
        logger.info(f"Found {len(product_containers)} product containers")
        
        for container in product_containers[:max_results]:
            try:
                product = self._extract_product_info(container)
                if product:
                    products.append(product)
            except Exception as e:
                logger.warning(f"Failed to extract product info: {e}")
                continue
        
        return products
    
    def _extract_product_info(self, container) -> Optional[Dict]:
        """
        Extract individual product information from a container element
        """
        try:
            # Extract product link and name from the anchor tag
            link_element = container.find('a')
            if not link_element:
                return None
            
            # Get product name from title attribute or _desc element
            name = link_element.get('title', '').strip()
            if not name:
                desc_element = container.find('div', class_='_desc')
                if desc_element:
                    name = desc_element.get_text(strip=True)
            
            if not name:
                return None
            
            # Extract price from _price div
            price_element = container.find('div', class_='_price')
            if price_element:
                price_text = price_element.get_text(strip=True)
                # Extract main price (£X.XX format)
                price_match = re.search(r'£\d+\.\d+', price_text)
                if price_match:
                    price = price_match.group()
                else:
                    price = "Price not available"
            else:
                price = "Price not available"
            
            # Extract brand from _brand div
            brand_element = container.find('div', class_='_brand')
            brand = brand_element.get_text(strip=True) if brand_element else ""
            
            # Extract size from _size div
            size_element = container.find('div', class_='_size')
            size = size_element.get_text(strip=True) if size_element else ""
            
            # For trolley.co.uk, the "store" is actually the brand/retailer
            # Since trolley aggregates from multiple stores, we'll use "Trolley.co.uk" as the store
            store = "Trolley.co.uk"
            
            # Extract product URL
            url = urljoin(self.base_url, link_element['href']) if link_element.get('href') else ""
            
            return {
                'name': name,
                'price': price,
                'brand': brand,
                'size': size,
                'store': store,
                'url': url
            }
            
        except Exception as e:
            logger.warning(f"Error extracting product info: {e}")
            return None
    
    def get_product_details(self, product_url: str) -> Dict:
        """
        Get detailed information about a specific product
        """
        try:
            response = self.session.get(product_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract additional details if needed
            # This can be expanded based on requirements
            
            return {"status": "success", "url": product_url}
            
        except Exception as e:
            logger.error(f"Failed to get product details: {e}")
            return {"status": "error", "message": str(e)}

# Example usage and testing
if __name__ == "__main__":
    scraper = TrolleyScraper()
    
    # Test search
    try:
        results = scraper.search_products("coca cola", max_results=3)
        print(f"Found {len(results)} products:")
        for product in results:
            print(f"- {product['name']} - {product['price']} at {product['store']}")
            print(f"  URL: {product['url']}")
    except Exception as e:
        print(f"Error: {e}")