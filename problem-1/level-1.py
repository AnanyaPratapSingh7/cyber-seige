#!/usr/bin/env python3
"""
Price Watcher - E-commerce Product Price Tracker

This script extracts product names and prices from various e-commerce websites.
"""

import re
import argparse
import time
import json
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class PriceWatcher:
    """Main class for extracting product information from e-commerce websites."""
    
    def __init__(self, headless=True, timeout=20):
        """Initialize the price watcher with browser settings."""
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
        })
        
        # Set up Selenium WebDriver for JavaScript rendered pages
        self.headless = headless
        self.driver = None
    
    def _init_driver(self):
        """Initialize the Selenium WebDriver if not already done."""
        if self.driver is None:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Install and setup ChromeDriver
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                print(f"Error initializing Chrome WebDriver: {e}")
                print("Trying to use system ChromeDriver...")
                self.driver = webdriver.Chrome(options=chrome_options)
    
    def close(self):
        """Close the browser and clean up resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
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
    
    def extract_from_toscrape(self, url, use_selenium=False):
        """Extract product information from books.toscrape.com."""
        try:
            if use_selenium:
                self._init_driver()
                self.driver.get(url)
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".product_main h1"))
                )
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            else:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract product name
            product_name = soup.select_one(".product_main h1").text.strip()
            
            # Extract price
            price_elem = soup.select_one(".product_main .price_color")
            price_str = price_elem.text.strip() if price_elem else None
            price = self._clean_price(price_str)
            
            return {
                "product_name": product_name,
                "price": price,
                "currency": "GBP",
                "price_raw": price_str,
                "url": url
            }
        except Exception as e:
            print(f"Error extracting from books.toscrape.com: {e}")
            # If regular request fails, try with Selenium
            if not use_selenium:
                return self.extract_from_toscrape(url, use_selenium=True)
            return {"error": str(e), "url": url}
    
    def extract_from_amazon(self, url):
        """Extract product information from Amazon."""
        try:
            # Amazon requires JavaScript rendering
            self._init_driver()
            self.driver.get(url)
            
            # Wait for product title to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
            
            # Extract product name
            product_name = self.driver.find_element(By.ID, "productTitle").text.strip()
            
            # Try different price selectors (Amazon's structure changes frequently)
            price_selectors = [
                ".a-price .a-offscreen",
                "#priceblock_ourprice",
                "#priceblock_dealprice",
                ".a-price-whole",
                ".a-color-price"
            ]
            
            price_str = None
            for selector in price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        price_str = elements[0].text.strip()
                        # If this is the whole price (without decimals), try to find the fraction
                        if selector == ".a-price-whole":
                            try:
                                fraction = self.driver.find_element(By.CSS_SELECTOR, ".a-price-fraction").text.strip()
                                price_str = f"{price_str}.{fraction}"
                            except:
                                pass
                        break
                except:
                    continue
            
            price = self._clean_price(price_str)
            
            # Determine currency symbol
            currency = "INR"  # Default for amazon.in
            
            return {
                "product_name": product_name,
                "price": price,
                "currency": currency,
                "price_raw": price_str,
                "url": url
            }
        except Exception as e:
            print(f"Error extracting from Amazon: {e}")
            return {"error": str(e), "url": url}
    
    def extract_from_flipkart(self, url):
        """Extract product information from Flipkart."""
        try:
            # Flipkart requires JavaScript rendering
            self._init_driver()
            self.driver.get(url)
            
            # Wait for product title to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1 span"))
            )
            
            # Extract product name
            product_name = self.driver.find_element(By.CSS_SELECTOR, "h1 span").text.strip()
            
            # Extract price
            price_selectors = [
                "._30jeq3._16Jk6d",  # Regular price
                "._30jeq3",  # Alternative price class
                ".B_NuCI"  # Another alternative
            ]
            
            price_str = None
            for selector in price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        price_str = elements[0].text.strip()
                        break
                except:
                    continue
            
            price = self._clean_price(price_str)
            
            return {
                "product_name": product_name,
                "price": price,
                "currency": "INR",
                "price_raw": price_str,
                "url": url
            }
        except Exception as e:
            print(f"Error extracting from Flipkart: {e}")
            return {"error": str(e), "url": url}
    
    def extract_from_meesho(self, url):
        """Extract product information from Meesho."""
        try:
            # Meesho requires JavaScript rendering
            self._init_driver()
            self.driver.get(url)
            
            # Wait for product title to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.CardHeader__DetailCard__Header"))
            )
            
            # Extract product name
            product_name = self.driver.find_element(By.CSS_SELECTOR, "h1.CardHeader__DetailCard__Header").text.strip()
            
            # Extract price
            price_selectors = [
                ".CardHeader__PriceSection span",
                ".FinalPrice__price"
            ]
            
            price_str = None
            for selector in price_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        price_str = elements[0].text.strip()
                        break
                except:
                    continue
            
            price = self._clean_price(price_str)
            
            return {
                "product_name": product_name,
                "price": price,
                "currency": "INR",
                "price_raw": price_str,
                "url": url
            }
        except Exception as e:
            print(f"Error extracting from Meesho: {e}")
            return {"error": str(e), "url": url}
    
    def extract_product_info(self, url):
        """Extract product information based on the website domain."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        try:
            print(f"Extracting data from: {url}")
            
            # Route to appropriate extractor based on domain
            if "books.toscrape.com" in domain:
                return self.extract_from_toscrape(url)
            elif "amazon" in domain:
                return self.extract_from_amazon(url)
            elif "flipkart" in domain:
                return self.extract_from_flipkart(url)
            elif "meesho" in domain:
                return self.extract_from_meesho(url)
            else:
                # Generic fallback using Selenium for unknown sites
                self._init_driver()
                self.driver.get(url)
                
                # Wait for page to load
                time.sleep(5)
                
                # Try common price selectors
                price_selectors = [
                    ".price", "span.price", ".product-price", ".offer-price",
                    ".price-box", ".product_price", "[data-price]", ".current-price",
                    "[itemprop='price']", ".price-container", ".sale-price"
                ]
                
                price_str = None
                for selector in price_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            price_str = elements[0].text.strip()
                            break
                    except:
                        continue
                
                # Try common product name selectors
                name_selectors = [
                    "h1", "[itemprop='name']", ".product-title", ".product-name",
                    ".title", "#title", ".prod-title", "h1.title"
                ]
                
                product_name = None
                for selector in name_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            product_name = elements[0].text.strip()
                            break
                    except:
                        continue
                
                price = self._clean_price(price_str)
                
                return {
                    "product_name": product_name,
                    "price": price,
                    "currency": "Unknown",
                    "price_raw": price_str,
                    "url": url
                }
        except Exception as e:
            print(f"Error extracting product information: {e}")
            return {"error": str(e), "url": url}


def main():
    """Main function to run the price watcher."""
    parser = argparse.ArgumentParser(description='E-commerce Product Price Tracker')
    parser.add_argument('url', help='URL of the product page to track')
    parser.add_argument('--no-headless', action='store_true', help='Run browser in visible mode')
    parser.add_argument('--timeout', type=int, default=20, help='Timeout in seconds for page loading')
    
    args = parser.parse_args()
    
    # Initialize price watcher
    watcher = PriceWatcher(headless=not args.no_headless, timeout=args.timeout)
    
    try:
        # Extract product information
        result = watcher.extract_product_info(args.url)
        
        # Pretty print the result
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print("\nProduct Information:")
            print(f"Name: {result['product_name']}")
            if result['price']:
                print(f"Price: {result['currency']} {result['price']} ({result['price_raw']})")
            else:
                print(f"Price: Could not extract price")
            print(f"URL: {result['url']}")
        
        print("\nFull JSON Output:")
        print(json.dumps(result, indent=2))
        
    finally:
        # Clean up
        watcher.close()


if __name__ == "__main__":
    main()
