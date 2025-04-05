import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
import random
import argparse
import logging
import os
import json
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("price_scraper.log"),
        logging.StreamHandler()
    ]
)

# Common User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
]

# Common request headers
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "DNT": "1",  # Do Not Track
}

class PriceScraper:
    def __init__(self, proxy=None):
        # Initialize session with custom headers and user agent
        self.session = requests.Session()
        self.headers = DEFAULT_HEADERS.copy()
        self.headers["User-Agent"] = random.choice(USER_AGENTS)
        self.session.headers.update(self.headers)
        
        # Configure proxy if provided
        self.proxy = proxy
        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }
        
        # Initialize Selenium WebDriver for JavaScript-rendered sites
        self.driver = None
        
        # Create output directory for debug files
        self.debug_dir = "debug_output"
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver when needed"""
        if self.driver is None:
            try:
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument(f"user-agent={self.headers['User-Agent']}")
                
                # Add custom headers to Chrome
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Use proxy if configured
                if self.proxy:
                    options.add_argument(f'--proxy-server={self.proxy}')
                
                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=options
                )
                
                # Extra automation hiding
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # Set initial window size, randomize to avoid fingerprinting
                width = random.randint(1050, 1200)
                height = random.randint(800, 900)
                self.driver.set_window_size(width, height)
                
            except Exception as e:
                logging.error(f"Failed to initialize Selenium: {e}")
                raise
    
    def close(self):
        """Close resources"""
        if self.driver:
            self.driver.quit()
    
    def _random_sleep(self, min_seconds=1, max_seconds=3):
        """Sleep for a random amount of time to emulate human behavior"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def _simulate_human_behavior(self):
        """Simulate human-like behavior in the browser to avoid detection"""
        try:
            # Random scrolling
            for _ in range(random.randint(2, 5)):
                scroll_amount = random.randint(100, 700)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                self._random_sleep(0.5, 1.5)
                
            # Sometimes scroll back up a bit
            if random.random() > 0.7:  # 30% chance
                self.driver.execute_script(f"window.scrollBy(0, {-random.randint(100, 300)});")
                self._random_sleep(0.5, 1)
                
        except Exception as e:
            logging.debug(f"Error during human behavior simulation: {e}")
    
    def update_user_agent(self, user_agent=None):
        """Update the user agent for both requests and selenium"""
        if user_agent:
            self.headers["User-Agent"] = user_agent
        else:
            self.headers["User-Agent"] = random.choice(USER_AGENTS)
            
        self.session.headers.update({"User-Agent": self.headers["User-Agent"]})
        logging.debug(f"Using User-Agent: {self.headers['User-Agent']}")
    
    def extract_price_static(self, url):
        """Extract product name and price using BeautifulSoup (for static sites)"""
        try:
            self._random_sleep(0.5, 1.5)
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Save the HTML for debugging if needed
            with open(os.path.join(self.debug_dir, "static_response.html"), "w", encoding="utf-8") as f:
                f.write(response.text)
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Handle different e-commerce sites
            if "books.toscrape.com" in url:
                return self._extract_from_books_toscrape(soup)
            else:
                # Try generic extraction for other static sites
                return self._extract_generic(soup)
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error accessing {url}: {e}")
            return None, None
        except Exception as e:
            logging.error(f"Error extracting from {url}: {e}")
            return None, None
    
    def extract_price_dynamic(self, url):
        """Extract product name and price using Selenium (for JavaScript-rendered sites)"""
        try:
            self._init_selenium()
            
            # Add a referer to appear more legitimate
            referer = "https://www.google.com/search?q=" + url.split("//")[1].split("/")[0]
            self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {"headers": {"Referer": referer}})
            
            # Navigate to the URL with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.driver.get(url)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logging.warning(f"Navigation attempt {attempt+1} failed: {e}. Retrying...")
                    self._random_sleep(2, 5)
            
            # Wait for page to load
            self._random_sleep(2, 4)
            
            # Simulate human behavior
            self._simulate_human_behavior()
            
            # Take screenshot for debugging
            self.driver.save_screenshot(os.path.join(self.debug_dir, "page_screenshot.png"))
            
            # Save page source for debugging
            with open(os.path.join(self.debug_dir, "page_source.html"), "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
                
            # Check for access denied or blocking
            page_source = self.driver.page_source.lower()
            page_title = self.driver.title.lower()
            
            # Check for common block indicators
            if ("access denied" in page_source or "access denied" in page_title or 
                "blocked" in page_source or "captcha" in page_source or 
                "robot" in page_source or "forbidden" in page_source):
                logging.error(f"Access denied or blocked by website: {url}")
                raise Exception(f"Website has blocked access. This is common with sites that have anti-scraping measures.")
            
            # Handle different e-commerce sites
            if "amazon" in url:
                return self._extract_from_amazon()
            elif "flipkart" in url:
                return self._extract_from_flipkart()
            elif "meesho" in url:
                return self._extract_from_meesho()
            else:
                # Try generic extraction
                return self._extract_generic_dynamic()
                
        except Exception as e:
            logging.error(f"Error extracting with Selenium from {url}: {e}")
            return None, None
    
    def extract_product_info(self, url):
        """Main method to extract product information based on the URL"""
        logging.info(f"Extracting product info from: {url}")
        
        # First try static extraction
        logging.debug("Attempting static extraction...")
        product_name, price = self.extract_price_static(url)
        
        # If static extraction fails, try dynamic extraction
        if product_name is None or price is None:
            logging.info("Static extraction failed or incomplete, trying dynamic extraction")
            try:
                product_name, price = self.extract_price_dynamic(url)
            except Exception as e:
                logging.error(f"Dynamic extraction failed with error: {e}")
                # Try again with a different user agent
                logging.info("Retrying with a different user agent...")
                self.update_user_agent()
                self.close()
                self.driver = None
                try:
                    product_name, price = self.extract_price_dynamic(url)
                except Exception as retry_error:
                    logging.error(f"Retry also failed: {retry_error}")
        
        # Format the results
        if product_name and price:
            product_name = product_name.strip()
            # Remove currency symbols and clean price
            original_price = price
            price = self._clean_price(price)
            logging.info(f"Found product: {product_name}")
            logging.info(f"Original price format: {original_price}, Cleaned price: {price}")
            return product_name, price
        else:
            logging.error("Failed to extract product information")
            return None, None
    
    def _clean_price(self, price_str):
        """Clean price string to standard format"""
        if price_str:
            # Remove non-numeric characters except for decimals
            price_str = re.sub(r'[^\d.,]', '', price_str.strip())
            return price_str
        return None
    
    def _extract_from_books_toscrape(self, soup):
        """Extract from books.toscrape.com"""
        try:
            # Try to find the product name with multiple possible selectors
            product_name = None
            name_selectors = [
                "div.product_main h1",
                "h1",
                ".product_main h1",
                "[class*='product_title']",
                ".product-title"
            ]
            
            for selector in name_selectors:
                name_element = soup.select_one(selector)
                if name_element and name_element.text.strip():
                    product_name = name_element.text.strip()
                    break
            
            # Try to find the price with multiple possible selectors
            price = None
            price_selectors = [
                "p.price_color",
                ".price_color",
                ".product_price .price_color",
                "[class*='price']"
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element and price_element.text.strip():
                    price = price_element.text.strip()
                    break
            
            # If we couldn't find product name or price with specific selectors,
            # log the issue and return None so we can try using Selenium instead
            if not product_name or not price:
                logging.warning("Could not find product name or price with specific selectors")
                return None, None
                
            return product_name, price
        except (AttributeError, Exception) as e:
            logging.error(f"Error extracting from books.toscrape: {e}")
            return None, None
    
    def _extract_from_amazon(self):
        """Extract from Amazon using Selenium"""
        try:
            # Wait for the product title to be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
            
            # Extract product name
            product_name = self.driver.find_element(By.ID, "productTitle").text
            
            # Try different price selectors
            price_selectors = [
                "span.a-price-whole",
                "span#priceblock_ourprice",
                "span#priceblock_dealprice",
                "span.a-offscreen",
                ".a-price .a-offscreen",
                "#corePrice_feature_div .a-price .a-offscreen",
                "#price_inside_buybox",
                ".priceToPay span.a-offscreen",
                ".apexPriceToPay span.a-offscreen"
            ]
            
            price = None
            for selector in price_selectors:
                try:
                    price_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for price_element in price_elements:
                        potential_price = price_element.text or price_element.get_attribute("innerHTML")
                        if potential_price and re.search(r'[$₹£€]|\d', potential_price):
                            price = potential_price
                            break
                    if price:
                        break
                except:
                    continue
            
            return product_name, price
        except Exception as e:
            logging.error(f"Error extracting from Amazon: {e}")
            return None, None
    
    def _extract_from_flipkart(self):
        """Extract from Flipkart using Selenium"""
        try:
            # Try multiple selectors for product name
            name_selectors = [
                "span.B_NuCI",
                "h1.yhB1nd",
                ".G6XhRU",
                "h1._9E25nV",
                "h1"
            ]
            
            product_name = None
            for selector in name_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.text.strip():
                            product_name = element.text.strip()
                            break
                    if product_name:
                        break
                except:
                    continue
            
            # Try multiple selectors for price
            price_selectors = [
                "div._30jeq3._16Jk6d",
                "div._30jeq3",
                ".CEmiEU div._30jeq3",
                "div.dyC4hf",
                "div._25b18c div._30jeq3",
                "[class*='price']"
            ]
            
            price = None
            for selector in price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.text.strip():
                            price = element.text.strip()
                            break
                    if price:
                        break
                except:
                    continue
            
            return product_name, price
        except Exception as e:
            logging.error(f"Error extracting from Flipkart: {e}")
            return None, None
    
    def _extract_from_meesho(self):
        """Extract from Meesho using Selenium"""
        try:
            # Wait for page content to load (longer wait time for Meesho)
            self._random_sleep(5, 8)
            
            # Try multiple approaches for product name
            product_name = None
            name_selectors = [
                "h1.SC_dBUnr",                # Original selector
                "h1[class*='ProductName']",   # Pattern-based selector
                "h1[class*='product']",       # Generic product class
                "h1[class*='name']",          # Name in class
                "h1[class*='title']",         # Title in class
                "h1",                         # Any h1 element
                ".product-title",             # Common class name
                "[class*='productName']",     # Case-insensitive class name fragment
                "[class*='title']",           # Generic title classes
                ".header-title"               # Header title
            ]
            
            for selector in name_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.text.strip():
                            product_name = element.text.strip()
                            logging.info(f"Found product name with selector: {selector}")
                            break
                    if product_name:
                        break
                except Exception as selector_error:
                    logging.debug(f"Selector {selector} failed: {selector_error}")
            
            # Try multiple approaches for price
            price = None
            price_selectors = [
                "h4.SC_dBUnr",                # Original selector
                "span[class*='price']",       # Pattern-based price selector
                "div[class*='price']",        # Price div
                "h4[class*='price']",         # Price heading
                "h3[class*='price']",         # Alternative price heading
                "[class*='finalPrice']",      # Final price classes
                "[class*='discounted']",      # Discounted price classes
                "[class*='selling']",         # Selling price classes
                "span[class*='amount']",      # Amount-based classes
                ".product-price",             # Common price class
                "[class*='productPrice']",    # Case-insensitive price class
                ".pricing",                   # Pricing container
                ".actual-price"               # Actual price
            ]
            
            for selector in price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.text.strip():
                            text = element.text.strip()
                            # Verify it looks like a price (contains currency symbols or digits)
                            if re.search(r'[$£€₹]|\d', text):
                                price = text
                                logging.info(f"Found price with selector: {selector}")
                                break
                    if price:
                        break
                except Exception as selector_error:
                    logging.debug(f"Price selector {selector} failed: {selector_error}")
            
            # If specific selectors failed, try finding price with XPath containing ₹ symbol
            if price is None:
                try:
                    # Look for any element containing ₹ symbol
                    rupee_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '₹')]")
                    for element in rupee_elements:
                        if element.is_displayed():
                            text = element.text.strip()
                            # Extract just the price part with currency
                            match = re.search(r'₹\s*[\d,]+(?:\.\d+)?', text)
                            if match:
                                price = match.group(0)
                                logging.info(f"Found price with rupee symbol search: {price}")
                                break
                except Exception as xpath_error:
                    logging.debug(f"XPath price search failed: {xpath_error}")
            
            # If price is still not found, try OCR on the screenshot (would need pytesseract)
            # This is left as a comment as it requires additional dependencies
            # if price is None:
            #     try:
            #         price = self._extract_price_from_screenshot()
            #     except Exception as ocr_error:
            #         logging.debug(f"OCR price extraction failed: {ocr_error}")
            
            # If we still don't have both name and price, try generic extraction
            if product_name is None or price is None:
                logging.info("Specific Meesho extraction failed, trying generic approach")
                
                # If specific extraction failed, fall back to generic extraction
                name_fallback, price_fallback = self._extract_generic_dynamic()
                if product_name is None:
                    product_name = name_fallback
                if price is None:
                    price = price_fallback
            
            return product_name, price
            
        except Exception as e:
            logging.error(f"Error extracting from Meesho: {e}")
            # Handle specific Meesho errors
            if "ChromeDriver" in str(e) or "session" in str(e).lower():
                logging.info("Browser issue detected. Trying to reinitialize...")
                self.close()
                self.driver = None
                self._init_selenium()
            return None, None
    
    def _extract_generic(self, soup):
        """Generic extraction logic for static sites"""
        # Try common patterns for product names
        product_name = None
        name_selectors = [
            'h1', 'h2.product-title', 'div.product-title', 'div.product-name',
            'span.product-title', '.product-name', '.product_title', '.product-title',
            '[itemprop="name"]', '[data-testid="product-name"]'
        ]
        
        for selector in name_selectors:
            try:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    product_name = element.text.strip()
                    break
            except:
                continue
        
        # Try common patterns for prices
        price = None
        price_selectors = [
            'span.price', 'div.price', 'p.price', 'span.offer-price',
            '[itemprop="price"]', '.product-price', '.price-box', '.price_box',
            '.product_price', '[data-testid="price"]', '.price-current', 
            '.sales-price', '.current-price'
        ]
        
        for selector in price_selectors:
            try:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    text = element.text.strip()
                    if re.search(r'[$£€₹]|\d', text):
                        price = text
                        break
            except:
                continue
        
        # If still no price, look for any element that might contain a price format
        if price is None:
            price_regex = r'[$£€₹]\s*[\d,]+(?:\.\d+)?|\d+[\.,]\d{2}'
            for tag in soup.find_all(['span', 'div', 'p']):
                if tag.text and re.search(price_regex, tag.text):
                    match = re.search(price_regex, tag.text)
                    if match:
                        price = match.group(0)
                        break
        
        return product_name, price
    
    def _extract_generic_dynamic(self):
        """Generic extraction logic for dynamic sites using Selenium"""
        product_name = None
        price = None
        
        # Try to find product name
        name_selectors = [
            'h1', 'h2.product-title', 'div.product-title', 'div.product-name',
            'span.product-title', '.product-name', '.product_title', '.product-title',
            '[itemprop="name"]', '[data-testid="product-name"]'
        ]
        
        for selector in name_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.text.strip():
                        product_name = element.text.strip()
                        break
                if product_name:
                    break
            except:
                continue
        
        # Try to find price
        price_patterns = [
            'span.price', 'div.price', 'p.price', 'span.offer-price', 
            '[class*="price"]', '[id*="price"]', '[itemprop="price"]',
            '.product-price', '.price-box', '.price_box', '.product_price',
            '[data-testid="price"]', '.price-current', '.sales-price', '.current-price'
        ]
        
        for pattern in price_patterns:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                for element in elements:
                    if element.is_displayed() and element.text.strip():
                        text = element.text.strip()
                        # Check if text contains currency symbols or digits
                        if re.search(r'[$£€₹]|\d', text):
                            price = text
                            break
                if price:
                    break
            except:
                continue
        
        # If still no price, look for any element that might contain a price format using XPath
        if price is None:
            try:
                # Look for elements with price format using XPath
                price_xpath = "//*[contains(text(), '$') or contains(text(), '₹') or contains(text(), '£') or contains(text(), '€')]"
                price_elements = self.driver.find_elements(By.XPATH, price_xpath)
                
                price_regex = r'[$£€₹]\s*[\d,]+(?:\.\d+)?|\d+[\.,]\d{2}'
                for element in price_elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        match = re.search(price_regex, text)
                        if match:
                            price = match.group(0)
                            break
            except:
                pass
        
        return product_name, price


def main():
    parser = argparse.ArgumentParser(description='Scrape product name and price from e-commerce sites')
    parser.add_argument('url', help='URL of the product page')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose output')
    parser.add_argument('--user-agent', help='Custom user agent to use for requests')
    parser.add_argument('--proxy', help='Proxy to use (format: protocol://host:port)')
    args = parser.parse_args()
    
    # Adjust logging level based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
        
    print(f"\nFetching product information from: {args.url}\n")
    print("This may take a moment, especially for JavaScript-heavy sites...\n")
    
    scraper = PriceScraper(proxy=args.proxy)
    try:
        # Set custom user agent if provided
        if args.user_agent:
            scraper.update_user_agent(args.user_agent)
            
        product_name, price = scraper.extract_product_info(args.url)
        
        if product_name and price:
            print("\n" + "="*60)
            print(f"PRODUCT: {product_name}")
            print(f"PRICE: {price}")
            print("="*60 + "\n")
        else:
            print("\n" + "="*60)
            print("ERROR: Failed to extract product information")
            print("Please check the following:")
            print("1. The URL is correct and accessible")
            print("2. The website may be using anti-scraping techniques")
            print("3. Check the log file 'price_scraper.log' for detailed errors")
            print("="*60 + "\n")
            
            # Provide more specific advice for each site
            site_name = ""
            if "meesho" in args.url:
                site_name = "Meesho"
                print(f"NOTE: {site_name} is known to have strong anti-scraping measures.")
                print("You might want to try with a custom user agent:")
                print(f'python level-1.py "{args.url}" --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"')
                print("\nOr use a proxy server:")
                print(f'python level-1.py "{args.url}" --proxy "http://your-proxy-server:port"')
                
            elif "amazon" in args.url:
                site_name = "Amazon"
                print(f"NOTE: {site_name} frequently blocks scraping attempts.")
                print("Try using a custom user agent or consider using their official API.")
                
            elif "flipkart" in args.url:
                site_name = "Flipkart"
                print(f"NOTE: {site_name} may implement rate limiting and other protections.")
                print("Try again with a proxy or different user agent.")
            
            # Provide more details for debugging
            print("\nFor more detailed diagnostic information, run with --debug flag:")
            print(f'python level-1.py "{args.url}" --debug\n')
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Check 'price_scraper.log' for more details.")
    finally:
        scraper.close()
        if not args.debug:
            print("\nNote: Run with --debug flag for more detailed output.")

if __name__ == "__main__":
    main()
