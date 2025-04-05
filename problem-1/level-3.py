#!/usr/bin/env python3
"""
Stealth Price Tracker - E-commerce CAPTCHA Bypass Solution

This script tracks product prices from e-commerce sites that use CAPTCHA protection,
using sophisticated techniques to mimic human behavior and bypass detection.
"""

import os
import re
import csv
import json
import time
import random
import logging
import argparse
from datetime import datetime
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

# Stealth browsing imports
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# List of common user agents for rotation
USER_AGENTS = [
    # Chrome on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    # Firefox on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    # Chrome on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    # Firefox on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0',
    # Edge on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
    # Safari on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
]

class StealthPriceTracker:
    """Tracks product prices while bypassing CAPTCHA and anti-bot measures."""
    
    def __init__(self, output_dir, use_proxy=False, proxy_list=None, headless=False):
        """Initialize the stealth price tracker."""
        self.output_dir = output_dir
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list or []
        self.headless = headless
        self.current_proxy = None
        self.driver = None
        self.captcha_retry_limit = 3
        self.human_like_delays = True
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Track CAPTCHA encounters
        self.captcha_encounters = 0
        self.successful_bypasses = 0
        
        # CSV headers for price records
        self.csv_headers = [
            "product_url", "product_name", "price", "currency", 
            "timestamp", "retailer", "status", "captcha_encountered"
        ]
        
        # Initialize CSV file if it doesn't exist
        self._init_csv_file()
    
    def _init_csv_file(self):
        """Initialize the CSV file with headers if it doesn't exist."""
        csv_file = os.path.join(self.output_dir, 'price_history.csv')
        if not os.path.exists(csv_file):
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.csv_headers)
    
    def _get_random_user_agent(self):
        """Get a random user agent from the list or generate one using fake_useragent."""
        try:
            # Try to use fake_useragent library for more variety
            ua = UserAgent()
            return ua.random
        except:
            # Fall back to our predefined list
            return random.choice(USER_AGENTS)
    
    def _get_random_proxy(self):
        """Get a random proxy from the proxy list if available."""
        if not self.use_proxy or not self.proxy_list:
            return None
        return random.choice(self.proxy_list)
    
    def _init_driver(self, retry=0):
        """Initialize the undetected ChromeDriver with stealth settings."""
        if retry >= 3:
            logger.error("Failed to initialize driver after multiple attempts")
            raise Exception("Driver initialization failed repeatedly")
        
        try:
            # Close existing driver if any
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            # Configure options
            options = uc.ChromeOptions()
            
            # Set user agent
            user_agent = self._get_random_user_agent()
            options.add_argument(f'--user-agent={user_agent}')
            logger.debug(f"Using User-Agent: {user_agent}")
            
            # Configure proxy if needed
            if self.use_proxy and self.proxy_list:
                self.current_proxy = self._get_random_proxy()
                if self.current_proxy:
                    options.add_argument(f'--proxy-server={self.current_proxy}')
                    logger.debug(f"Using proxy: {self.current_proxy}")
            
            # Headless mode if requested
            if self.headless:
                options.add_argument('--headless')
            
            # Stealth settings
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-browser-side-navigation')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            options.add_argument('--disable-site-isolation-trials')
            
            # Add random window size to appear more human-like
            window_sizes = [(1366, 768), (1920, 1080), (1536, 864), (1440, 900)]
            window_size = random.choice(window_sizes)
            options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')
            
            # Initialize the undetected ChromeDriver
            self.driver = uc.Chrome(options=options)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(30)
            
            # Additional stealth settings after driver initialization
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
            
            # Execute JavaScript to mask automation
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error initializing driver: {e}")
            time.sleep(2 + random.random() * 3)  # Random delay before retry
            return self._init_driver(retry + 1)
    
    def _human_like_scroll(self):
        """Perform human-like scrolling on the page."""
        try:
            # Get page height
            page_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Scroll down in random chunks with random delays
            current_position = 0
            while current_position < page_height:
                # Random scroll amount between 100 and 800 pixels
                scroll_amount = random.randint(100, 800)
                current_position += scroll_amount
                
                # Sometimes overshoot and scroll back a bit (very human-like behavior)
                if random.random() < 0.2:  # 20% chance
                    overshoot = random.randint(40, 100)
                    self.driver.execute_script(f"window.scrollTo(0, {current_position + overshoot});")
                    time.sleep(0.1 + random.random() * 0.3)
                    self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                else:
                    self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                
                # Random delay between scrolls
                time.sleep(0.1 + random.random() * 1.5)
            
            # Sometimes scroll back up a bit
            if random.random() < 0.3:  # 30% chance
                scroll_up = random.randint(100, 500)
                self.driver.execute_script(f"window.scrollTo(0, {current_position - scroll_up});")
        
        except Exception as e:
            logger.debug(f"Error during human-like scrolling: {e}")
    
    def _random_mouse_movement(self):
        """Simulate random mouse movements using JavaScript."""
        try:
            # Use JavaScript to simulate mouse movements
            script = """
            var event = new MouseEvent('mousemove', {
                'view': window,
                'bubbles': true,
                'cancelable': true,
                'clientX': arguments[0],
                'clientY': arguments[1]
            });
            document.dispatchEvent(event);
            """
            
            # Perform random mouse movements
            screen_width = self.driver.execute_script("return window.innerWidth;")
            screen_height = self.driver.execute_script("return window.innerHeight;")
            
            for _ in range(random.randint(5, 15)):
                x = random.randint(0, screen_width)
                y = random.randint(0, screen_height)
                self.driver.execute_script(script, x, y)
                time.sleep(0.05 + random.random() * 0.2)
        
        except Exception as e:
            logger.debug(f"Error during random mouse movement: {e}")
    
    def _human_delay(self, min_seconds=0.5, max_seconds=3.0):
        """Wait for a random human-like delay."""
        if not self.human_like_delays:
            return
        
        delay = min_seconds + random.random() * (max_seconds - min_seconds)
        time.sleep(delay)
    
    def _is_captcha_present(self):
        """Check if a CAPTCHA is present on the current page."""
        captcha_indicators = [
            # Text indicators
            "captcha", "robot", "verify you're human", "verify your identity", 
            "security check", "prove you're not a robot", "verify your browser",
            # Element IDs and classes
            "g-recaptcha", "recaptcha", "captcha-container", "bot-check",
            # Images
            "captcha.jpg", "captcha.png", "recaptcha_logo", "captcha_challenge"
        ]
        
        try:
            # Check page source for captcha indicators
            page_source = self.driver.page_source.lower()
            for indicator in captcha_indicators:
                if indicator.lower() in page_source:
                    return True
            
            # Check for reCAPTCHA iframe
            try:
                recaptcha_frame = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                if recaptcha_frame:
                    return True
            except:
                pass
            
            # Check for Cloudflare captcha
            try:
                cloudflare_captcha = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='cloudflare']")
                if cloudflare_captcha:
                    return True
            except:
                pass
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking for CAPTCHA: {e}")
            return False
    
    def _handle_captcha(self):
        """Handle CAPTCHA challenges."""
        self.captcha_encounters += 1
        logger.warning(f"CAPTCHA detected! Encounter #{self.captcha_encounters}")
        
        # Record the CAPTCHA page for analysis
        captcha_screenshot_path = os.path.join(self.output_dir, f"captcha_encounter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        try:
            self.driver.save_screenshot(captcha_screenshot_path)
            logger.info(f"CAPTCHA screenshot saved to {captcha_screenshot_path}")
        except:
            pass
        
        # Strategy 1: Wait longer to see if CAPTCHA times out or session refreshes
        logger.info("Waiting to see if CAPTCHA resolves automatically...")
        self._human_delay(20, 30)
        
        # Check if CAPTCHA is still present
        if not self._is_captcha_present():
            logger.info("CAPTCHA appears to have been resolved automatically!")
            self.successful_bypasses += 1
            return True
        
        # Strategy 2: Refresh the page and try again
        logger.info("Refreshing page to attempt CAPTCHA bypass...")
        try:
            self.driver.refresh()
            self._human_delay(5, 10)
        except:
            pass
        
        # Check if CAPTCHA is still present
        if not self._is_captcha_present():
            logger.info("CAPTCHA bypassed after page refresh!")
            self.successful_bypasses += 1
            return True
        
        # Strategy 3: Reinitialize driver with new identity
        logger.info("Reinitializing driver with new identity...")
        self._init_driver()
        current_url = self.driver.current_url
        
        # Navigate back to the page
        try:
            self.driver.get(current_url)
            self._human_delay(5, 10)
        except:
            return False
        
        # Check if CAPTCHA is still present
        if not self._is_captcha_present():
            logger.info("CAPTCHA bypassed with new browser identity!")
            self.successful_bypasses += 1
            return True
        
        logger.warning("All CAPTCHA bypass attempts failed")
        return False
    
    def _clean_price(self, price_str):
        """Clean and standardize price string."""
        if not price_str:
            return None
        
        # Remove non-price characters and whitespace
        price_str = re.sub(r'[^\d.,]', '', price_str.strip())
        
        # Handle various decimal formats
        price_str = re.sub(r'[,](?=\d{3})', '', price_str)  # Remove thousands separators
        price_str = price_str.replace(',', '.')  # Standardize decimal separator
        
        try:
            return float(price_str)
        except ValueError:
            return None
    
    def extract_from_walmart(self, product_url, retry_count=0):
        """Extract product information from Walmart."""
        max_retries = self.captcha_retry_limit
        
        if retry_count >= max_retries:
            logger.error(f"Maximum retry attempts reached for {product_url}")
            return {
                "product_url": product_url,
                "product_name": None,
                "price": None,
                "currency": "USD",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "retailer": "Walmart",
                "status": "failed",
                "captcha_encountered": True
            }
        
        # Initialize driver if not already done
        if not self.driver:
            self._init_driver()
        
        # Prepare result dictionary
        result = {
            "product_url": product_url,
            "product_name": None,
            "price": None,
            "currency": "USD",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "retailer": "Walmart",
            "status": "failed",
            "captcha_encountered": False
        }
        
        try:
            # Navigate to the URL
            logger.info(f"Navigating to Walmart product: {product_url}")
            self.driver.get(product_url)
            
            # Random initial delay to mimic page load time observation
            self._human_delay(2, 5)
            
            # Perform human-like interactions
            self._human_like_scroll()
            self._random_mouse_movement()
            
            # Check for CAPTCHA
            if self._is_captcha_present():
                result["captcha_encountered"] = True
                captcha_bypassed = self._handle_captcha()
                if not captcha_bypassed:
                    # Try again with a new browser session
                    logger.info(f"Retrying with new session (attempt {retry_count+1}/{max_retries})")
                    if self.driver:
                        self.driver.quit()
                    self.driver = None
                    self._human_delay(10, 20)  # Longer delay before retry
                    return self.extract_from_walmart(product_url, retry_count + 1)
            
            # Extract product name
            try:
                # Wait for product title to be present
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
                )
                
                # Extract the product name
                product_name_elem = self.driver.find_element(By.CSS_SELECTOR, "h1")
                result["product_name"] = product_name_elem.text.strip()
            except:
                try:
                    # Alternative selector
                    product_name_elem = self.driver.find_element(By.CSS_SELECTOR, ".prod-ProductTitle")
                    result["product_name"] = product_name_elem.text.strip()
                except:
                    logger.warning("Could not extract product name from Walmart")
            
            # Extract price information
            price_selectors = [
                ".price-characteristic",
                "[data-automation-id='price-characteristic']",
                ".prod-PriceCharacteristic",
                ".price-group",
                "[itemprop='price']"
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip() or price_elem.get_attribute("content")
                    if price_text:
                        # Try to find cents/fraction part as well
                        try:
                            cents_elem = self.driver.find_element(By.CSS_SELECTOR, ".price-mantissa")
                            cents_text = cents_elem.text.strip()
                            if cents_text and price_text:
                                price_text = f"{price_text}.{cents_text}"
                        except:
                            pass
                        
                        result["price"] = self._clean_price(price_text)
                        break
                except:
                    continue
            
            # Set success status if we extracted what we needed
            if result["product_name"] and result["price"]:
                result["status"] = "success"
            
            return result
        
        except TimeoutException:
            logger.error(f"Timeout while accessing {product_url}")
            if retry_count < max_retries - 1:
                logger.info(f"Retrying (attempt {retry_count+1}/{max_retries})")
                if self.driver:
                    self.driver.quit()
                self.driver = None
                self._human_delay(5, 10)
                return self.extract_from_walmart(product_url, retry_count + 1)
            return result
        
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
            if retry_count < max_retries - 1:
                logger.info(f"Retrying (attempt {retry_count+1}/{max_retries})")
                if self.driver:
                    self.driver.quit()
                self.driver = None
                self._human_delay(5, 10)
                return self.extract_from_walmart(product_url, retry_count + 1)
            return result
        
        except Exception as e:
            logger.error(f"Error extracting data from Walmart: {e}")
            return result
    
    def extract_from_bestbuy(self, product_url, retry_count=0):
        """Extract product information from Best Buy."""
        max_retries = self.captcha_retry_limit
        
        if retry_count >= max_retries:
            logger.error(f"Maximum retry attempts reached for {product_url}")
            return {
                "product_url": product_url,
                "product_name": None,
                "price": None,
                "currency": "USD",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "retailer": "BestBuy",
                "status": "failed",
                "captcha_encountered": True
            }
        
        # Initialize driver if not already done
        if not self.driver:
            self._init_driver()
        
        # Prepare result dictionary
        result = {
            "product_url": product_url,
            "product_name": None,
            "price": None,
            "currency": "USD",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "retailer": "BestBuy",
            "status": "failed",
            "captcha_encountered": False
        }
        
        try:
            # Navigate to the URL
            logger.info(f"Navigating to Best Buy product: {product_url}")
            self.driver.get(product_url)
            
            # Random initial delay to mimic page load time observation
            self._human_delay(2, 5)
            
            # Perform human-like interactions
            self._human_like_scroll()
            self._random_mouse_movement()
            
            # Check for CAPTCHA
            if self._is_captcha_present():
                result["captcha_encountered"] = True
                captcha_bypassed = self._handle_captcha()
                if not captcha_bypassed:
                    # Try again with a new browser session
                    logger.info(f"Retrying with new session (attempt {retry_count+1}/{max_retries})")
                    if self.driver:
                        self.driver.quit()
                    self.driver = None
                    self._human_delay(10, 20)  # Longer delay before retry
                    return self.extract_from_bestbuy(product_url, retry_count + 1)
            
            # Extract product name
            try:
                # Wait for product title to be present
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".sku-title h1"))
                )
                
                # Extract the product name
                product_name_elem = self.driver.find_element(By.CSS_SELECTOR, ".sku-title h1")
                result["product_name"] = product_name_elem.text.strip()
            except:
                try:
                    # Alternative selectors
                    alternative_selectors = ["h1", ".heading-5", "[data-track='product-title']"]
                    for selector in alternative_selectors:
                        try:
                            product_name_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                            result["product_name"] = product_name_elem.text.strip()
                            if result["product_name"]:
                                break
                        except:
                            continue
                except:
                    logger.warning("Could not extract product name from Best Buy")
            
            # Extract price information
            price_selectors = [
                ".priceView-customer-price span",
                ".priceView-hero-price span",
                ".priceView-purchase-price",
                "[data-track='price']",
                ".pricing-price__regular-price"
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip()
                    if price_text:
                        result["price"] = self._clean_price(price_text)
                        break
                except:
                    continue
            
            # Set success status if we extracted what we needed
            if result["product_name"] and result["price"]:
                result["status"] = "success"
            
            return result
        
        except TimeoutException:
            logger.error(f"Timeout while accessing {product_url}")
            if retry_count < max_retries - 1:
                logger.info(f"Retrying (attempt {retry_count+1}/{max_retries})")
                if self.driver:
                    self.driver.quit()
                self.driver = None
                self._human_delay(5, 10)
                return self.extract_from_bestbuy(product_url, retry_count + 1)
            return result
        
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
            if retry_count < max_retries - 1:
                logger.info(f"Retrying (attempt {retry_count+1}/{max_retries})")
                if self.driver:
                    self.driver.quit()
                self.driver = None
                self._human_delay(5, 10)
                return self.extract_from_bestbuy(product_url, retry_count + 1)
            return result
        
        except Exception as e:
            logger.error(f"Error extracting data from Best Buy: {e}")
            return result
    
    def extract_product_info(self, product_url):
        """Extract product information based on the URL's domain."""
        domain = urlparse(product_url).netloc.lower()
        
        if "walmart.com" in domain:
            return self.extract_from_walmart(product_url)
        elif "bestbuy.com" in domain:
            return self.extract_from_bestbuy(product_url)
        else:
            logger.error(f"Unsupported domain: {domain}")
            return {
                "product_url": product_url,
                "product_name": None,
                "price": None,
                "currency": None,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "retailer": "Unknown",
                "status": "failed",
                "captcha_encountered": False
            }
    
    def save_result_to_csv(self, result):
        """Save the extraction result to CSV file."""
        csv_file = os.path.join(self.output_dir, 'price_history.csv')
        
        try:
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_headers)
                writer.writerow(result)
            logger.info(f"Result saved to CSV for {result['product_url']}")
            return True
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            return False
    
    def track_products(self, product_urls, interval=3600):
        """Track multiple products over time with a specified interval."""
        logger.info(f"Starting to track {len(product_urls)} products with {interval}s interval")
        
        try:
            while True:
                start_time = time.time()
                
                for url in product_urls:
                    try:
                        # Extract product information
                        result = self.extract_product_info(url)
                        
                        # Save result to CSV
                        self.save_result_to_csv(result)
                        
                        # Display result
                        if result["status"] == "success":
                            logger.info(f"Successfully extracted {result['retailer']} product: {result['product_name']} - ${result['price']}")
                        else:
                            logger.warning(f"Failed to extract data for {result['retailer']} product at {url}")
                        
                        # Add variable delay between products
                        self._human_delay(20, 45)
                    
                    except Exception as e:
                        logger.error(f"Error processing {url}: {e}")
                
                # Calculate time taken for this cycle
                elapsed_time = time.time() - start_time
                
                # Calculate time to wait until next cycle
                wait_time = max(0, interval - elapsed_time)
                
                # Add some randomness to the wait time
                wait_time += random.randint(-60, 60) if wait_time > 120 else 0
                
                # Display statistics
                logger.info(f"Completed tracking cycle. CAPTCHA encounters: {self.captcha_encounters}, successful bypasses: {self.successful_bypasses}")
                
                if wait_time > 0:
                    logger.info(f"Waiting {wait_time:.0f} seconds until next cycle...")
                    time.sleep(wait_time)
        
        except KeyboardInterrupt:
            logger.info("Tracking stopped by user")
        finally:
            # Clean up
            if self.driver:
                self.driver.quit()
            
            logger.info("Price tracking complete")
    
    def close(self):
        """Close the browser and clean up resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None


def main():
    """Main function to run the stealth price tracker."""
    parser = argparse.ArgumentParser(description='Stealth E-commerce Price Tracker')
    parser.add_argument('--urls', nargs='+', required=True, help='URLs of the products to track')
    parser.add_argument('--output-dir', default='price_history', help='Directory to store price history data')
    parser.add_argument('--interval', type=int, default=3600, help='Monitoring interval in seconds (default: 1 hour)')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode (no visible browser)')
    parser.add_argument('--use-proxy', action='store_true', help='Use proxy servers for connections')
    parser.add_argument('--proxy-file', help='File containing proxy servers (one per line)')
    parser.add_argument('--captcha-retries', type=int, default=3, help='Number of retry attempts for CAPTCHA bypass')
    
    args = parser.parse_args()
    
    # Load proxy list if specified
    proxy_list = []
    if args.use_proxy and args.proxy_file:
        try:
            with open(args.proxy_file, 'r') as f:
                proxy_list = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(proxy_list)} proxies from {args.proxy_file}")
        except Exception as e:
            logger.error(f"Error loading proxy file: {e}")
    
    # Initialize tracker
    tracker = StealthPriceTracker(
        output_dir=args.output_dir,
        use_proxy=args.use_proxy,
        proxy_list=proxy_list,
        headless=args.headless
    )
    
    # Set CAPTCHA retry limit
    tracker.captcha_retry_limit = args.captcha_retries
    
    try:
        # Track products
        tracker.track_products(args.urls, interval=args.interval)
    finally:
        # Clean up
        tracker.close()


if __name__ == "__main__":
    main()