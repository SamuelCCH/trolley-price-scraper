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
        
        # Store name mappings for common retailers
        self.store_mappings = {
            'tesco': 'Tesco',
            'asda': 'ASDA',
            'sainsburys': 'Sainsbury\'s',
            'morrisons': 'Morrisons',
            'waitrose': 'Waitrose',
            'iceland': 'Iceland',
            'aldi': 'Aldi',
            'lidl': 'Lidl',
            'coop': 'Co-op',
            'marks': 'M&S',
            'ocado': 'Ocado'
        }
    
    def search_products(self, query: str, max_results: int = 5, store_filter: str = None) -> List[Dict]:
        """
        Search for products on trolley.co.uk and return structured data
        
        Args:
            query: Product search term
            max_results: Maximum number of results to return
            store_filter: Optional store name to filter results by
            
        Returns:
            List of dictionaries containing product information
        """
        try:
            logger.info(f"Searching for: {query}" + (f" in store: {store_filter}" if store_filter else ""))
            
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
            products = self._extract_products(soup, max_results, store_filter)
            
            logger.info(f"Found {len(products)} products")
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"Failed to fetch search results: {e}")
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise Exception(f"Failed to parse search results: {e}")
    
    def _extract_products(self, soup: BeautifulSoup, max_results: int, store_filter: str = None) -> List[Dict]:
        """
        Extract product information from the search results page
        """
        products = []
        
        # Find product containers - try multiple selectors in order of preference
        selectors_to_try = [
            'div[data-id]',  # Most specific first - this finds actual product containers
            'div.product-item',
            'div[class*="product-item"]',
            'div[class*="product"]',
            'div._product',
            'div.product'
        ]
        
        product_containers = []
        for selector in selectors_to_try:
            product_containers = soup.select(selector)
            if product_containers:
                logger.info(f"Using selector '{selector}' - found {len(product_containers)} containers")
                break
        
        if not product_containers:
            logger.warning("No product containers found with any selector")
            return products
        
        for container in product_containers[:max_results * 3]:  # Get extra to account for filtering
            try:
                product = self._extract_product_info(container)
                if product:
                    # Apply store filter if specified
                    if store_filter:
                        product_store = product['store'].lower()
                        # Check if store filter matches the extracted store name
                        if store_filter.lower() not in product_store and not any(
                            store_filter.lower() in key for key in self.store_mappings.keys() 
                            if self.store_mappings[key].lower() == product_store
                        ):
                            continue
                    
                    products.append(product)
                    
                    # Stop when we have enough results
                    if len(products) >= max_results:
                        break
                        
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
            link_element = container.find('a', href=True)
            if not link_element:
                return None
            
            # Get product name from the link text (this is where the name actually is)
            name = link_element.get_text(strip=True)
            if not name:
                return None
            
            # Clean up the name - remove price and other info, keep just the product name
            # The name often contains size, brand, and price info all together
            # Example: "800gHovisSeed Sensations Seven Seeds Medium Sliced Seeded Bread269£1.95£0.24 per 100g"
            
            # Extract price first so we can remove it from name
            price = "Price not available"
            price_match = re.search(r'£\d+\.\d+', name)
            if price_match:
                price = price_match.group()
                # Remove price and everything after it from name
                name = name[:name.find(price)].strip()
            
            # Try alternative price selectors if not found in name
            if price == "Price not available":
                price_selectors = ['[class*="price"]', '.price', '.cost']
                for selector in price_selectors:
                    price_element = container.select_one(selector)
                    if price_element:
                        price_text = price_element.get_text(strip=True)
                        price_match = re.search(r'£\d+\.\d+', price_text)
                        if price_match:
                            price = price_match.group()
                            break
            
            # Extract size from the beginning of the name (e.g., "800g")
            size = ""
            size_match = re.match(r'^(\d+(?:\.\d+)?(?:g|kg|ml|l|oz|lb))', name, re.IGNORECASE)
            if size_match:
                size = size_match.group(1)
                name = name[len(size):].strip()
            
            # Extract brand - usually the first word or two after size
            brand = ""
            # Common brand patterns
            brand_patterns = [
                r'^(Hovis|Warburtons|Kingsmill|Mother Pride|Allinson|Brennans)',
                r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'  # Generic brand pattern
            ]
            
            for pattern in brand_patterns:
                brand_match = re.match(pattern, name, re.IGNORECASE)
                if brand_match:
                    brand = brand_match.group(1)
                    name = name[len(brand):].strip()
                    break
            
            # Clean up remaining name - remove extra numbers and clean text
            name = re.sub(r'^\d+', '', name).strip()  # Remove any remaining numbers at start
            name = re.sub(r'\d+$', '', name).strip()  # Remove numbers at the end
            name = re.sub(r'\s+', ' ', name).strip()  # Clean up multiple spaces
            
            # Extract store information
            store = self._extract_store_name(container)
            
            # Extract product URL
            url = urljoin(self.base_url, link_element['href'])
            
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
    
    def _extract_store_name(self, container) -> str:
        """
        Extract the actual store name from the product container
        """
        try:
            # Get all text content from the container
            text_content = container.get_text()
            
            # Method 1: Look for store names with common patterns
            # Pattern like "Sainsbury's|Taste the Difference" or "The BAKERY at ASDA"
            store_patterns = [
                r"sainsbury'?s",
                r"tesco",
                r"asda",
                r"waitrose",
                r"morrisons",
                r"iceland",
                r"aldi",
                r"lidl",
                r"co-?op",
                r"marks?\s*&?\s*spencer",
                r"m&s"
            ]
            
            for pattern in store_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    store_found = match.group().lower()
                    # Normalize the store name
                    if 'sainsbury' in store_found:
                        return "Sainsbury's"
                    elif 'tesco' in store_found:
                        return "Tesco"
                    elif 'asda' in store_found:
                        return "ASDA"
                    elif 'waitrose' in store_found:
                        return "Waitrose"
                    elif 'morrisons' in store_found:
                        return "Morrisons"
                    elif 'iceland' in store_found:
                        return "Iceland"
                    elif 'aldi' in store_found:
                        return "Aldi"
                    elif 'lidl' in store_found:
                        return "Lidl"
                    elif 'co' in store_found and 'op' in store_found:
                        return "Co-op"
                    elif 'marks' in store_found or 'm&s' in store_found:
                        return "Marks & Spencer"
            
            # Method 2: Look for store-specific selectors
            store_selectors = [
                '.store', '.retailer', '.shop', '.vendor',
                '.store-name', '.retailer-name', '.shop-name'
            ]
            
            for selector in store_selectors:
                store_element = container.select_one(selector)
                if store_element:
                    store_name = store_element.get_text(strip=True)
                    if store_name:
                        return self._normalize_store_name(store_name)
            
            # Method 3: Extract from URL patterns
            link_element = container.find('a', href=True)
            if link_element and link_element.get('href'):
                url = link_element['href']
                for store_key, store_name in self.store_mappings.items():
                    if store_key in url.lower():
                        return store_name
            
            # Method 4: Look for store info in image alt text or data attributes
            img_element = container.find('img')
            if img_element:
                alt_text = img_element.get('alt', '').lower()
                for store_key, store_name in self.store_mappings.items():
                    if store_key in alt_text:
                        return store_name
            
            # Method 5: Look in data attributes
            for attr_name, attr_value in container.attrs.items():
                if isinstance(attr_value, str):
                    attr_value_lower = attr_value.lower()
                    for store_key, store_name in self.store_mappings.items():
                        if store_key in attr_value_lower:
                            return store_name
            
            # Method 6: Look for store info in nested elements
            all_text = container.get_text().lower()
            for store_key, store_name in self.store_mappings.items():
                if store_key in all_text:
                    return store_name
            
            # Fallback: Return "Trolley.co.uk" if no specific store found
            return "Trolley.co.uk"
            
        except Exception as e:
            logger.warning(f"Error extracting store name: {e}")
            return "Trolley.co.uk"
    
    def _normalize_store_name(self, store_name: str) -> str:
        """
        Normalize store name to standard format
        """
        store_name_lower = store_name.lower().strip()
        
        # Check against our mappings
        for store_key, normalized_name in self.store_mappings.items():
            if store_key in store_name_lower:
                return normalized_name
        
        # If no mapping found, return capitalized version
        return store_name.title()
    
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