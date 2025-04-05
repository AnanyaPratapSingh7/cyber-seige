#!/usr/bin/env python3
"""
Price Tracker - Mock E-commerce API Monitor

This script tracks product prices from a mock e-commerce API over time,
records historical data, and detects significant price changes.
"""

import os
import re
import csv
import json
import time
import logging
import argparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class PriceTracker:
    """Main class for tracking product prices from the mock e-commerce API."""
    
    def __init__(self, api_base_url, output_dir, monitoring_interval=300, price_change_threshold=5.0):
        """Initialize the price tracker with configuration."""
        self.api_base_url = api_base_url.rstrip('/')  # Remove trailing slash if present
        self.output_dir = output_dir
        self.monitoring_interval = monitoring_interval  # in seconds
        self.price_change_threshold = price_change_threshold  # percentage
        self.product_histories = {}  # Store product price histories
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # CSV headers
        self.csv_headers = ["product_id", "product_name", "timestamp", "price", "currency", "significant_change", "change_percentage"]
    
    def fetch_all_products(self):
        """Fetch list of all available products from the API."""
        try:
            url = f"{self.api_base_url}/api/products"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product list: {e}")
            return []
    
    def fetch_product_details(self, product_id):
        """Fetch details for a specific product."""
        try:
            url = f"{self.api_base_url}/api/products/{product_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return None
    
    def fetch_product_page(self, product_id):
        """Fetch HTML product page and extract information."""
        try:
            url = f"{self.api_base_url}/api/product-page/{product_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract relevant information
            product_info = {
                'product_id': product_id,
                'price': None,
                'currency': 'USD',  # Default
                'name': None
            }
            
            # Try to find price (various possible selectors)
            price_selectors = [
                '.price', '#price', '.product-price', 
                '[data-price]', '.current-price'
            ]
            
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.text.strip()
                    # Extract numeric price
                    price_match = re.search(r'[\d,.]+', price_text)
                    if price_match:
                        # Clean up price format
                        price_str = price_match.group(0).replace(',', '')
                        try:
                            product_info['price'] = float(price_str)
                        except ValueError:
                            pass
                    
                    # Try to extract currency
                    currency_match = re.search(r'[$€£¥]', price_text)
                    if currency_match:
                        currency_symbols = {
                            '$': 'USD',
                            '€': 'EUR',
                            '£': 'GBP',
                            '¥': 'JPY'
                        }
                        product_info['currency'] = currency_symbols.get(currency_match.group(0), 'USD')
                    break
            
            # Try to find product name
            name_selectors = [
                'h1', '.product-name', '.product-title', 
                '[itemprop="name"]', '.title'
            ]
            
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    product_info['name'] = name_elem.text.strip()
                    break
            
            return product_info
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product page for {product_id}: {e}")
            return None
    
    def check_significant_price_change(self, product_id, current_price):
        """Check if price change exceeds threshold percentage."""
        if product_id not in self.product_histories or not self.product_histories[product_id]:
            return False, 0.0
        
        # Get the most recent price record
        last_record = self.product_histories[product_id][-1]
        last_price = last_record['price']
        
        if last_price is None or current_price is None:
            return False, 0.0
        
        # Calculate percentage change
        if last_price > 0:
            percentage_change = abs((current_price - last_price) / last_price * 100)
            is_significant = percentage_change >= self.price_change_threshold
            return is_significant, percentage_change
        
        return False, 0.0
    
    def update_price_history(self, product_data):
        """Update price history for a product."""
        product_id = product_data['product_id']
        
        # Skip if data is incomplete
        if product_data.get('price') is None or product_data.get('name') is None:
            logger.warning(f"Incomplete data for product {product_id}, skipping update")
            return None
        
        # Initialize history list if not exists
        if product_id not in self.product_histories:
            self.product_histories[product_id] = []
        
        # Check for duplicate entries (same price, no change)
        if self.product_histories[product_id]:
            last_record = self.product_histories[product_id][-1]
            if last_record['price'] == product_data['price']:
                # Skip update if price hasn't changed
                logger.debug(f"No price change for product {product_id}, skipping update")
                return None
        
        # Check for significant price change
        is_significant, percentage_change = self.check_significant_price_change(
            product_id, product_data['price']
        )
        
        # Create timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Create record
        record = {
            'product_id': product_id,
            'product_name': product_data['name'],
            'timestamp': timestamp,
            'price': product_data['price'],
            'currency': product_data['currency'],
            'significant_change': is_significant,
            'change_percentage': round(percentage_change, 2)
        }
        
        # Add to history
        self.product_histories[product_id].append(record)
        
        # Save to CSV
        self.save_record_to_csv(record)
        
        # Log significant changes
        if is_significant:
            logger.info(f"Significant price change detected for {product_data['name']} (ID: {product_id}): "
                       f"{percentage_change:.2f}% change")
        
        return record
    
    def save_record_to_csv(self, record):
        """Save a price record to the CSV file."""
        csv_file = os.path.join(self.output_dir, 'price_history.csv')
        file_exists = os.path.isfile(csv_file)
        
        try:
            with open(csv_file, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.csv_headers)
                
                # Write header if file doesn't exist
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(record)
        except Exception as e:
            logger.error(f"Error saving record to CSV: {e}")
    
    def generate_summary_report(self):
        """Generate a summary report of price tracking results."""
        if not self.product_histories:
            logger.info("No product histories available for summary report")
            return
        
        report_file = os.path.join(self.output_dir, 'price_summary_report.csv')
        
        try:
            with open(report_file, 'w', newline='') as csvfile:
                # Define headers
                headers = ["product_id", "product_name", "initial_price", "latest_price", 
                          "min_price", "max_price", "price_change", "percentage_change", 
                          "significant_changes_count", "data_points"]
                
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                # Generate summary for each product
                for product_id, history in self.product_histories.items():
                    if not history:
                        continue
                    
                    # Extract data
                    initial_price = history[0]['price']
                    latest_price = history[-1]['price']
                    prices = [record['price'] for record in history if record['price'] is not None]
                    
                    if not prices:
                        continue
                    
                    min_price = min(prices)
                    max_price = max(prices)
                    
                    # Calculate changes
                    price_change = latest_price - initial_price
                    percentage_change = (price_change / initial_price * 100) if initial_price else 0
                    
                    # Count significant changes
                    significant_changes = sum(1 for record in history if record['significant_change'])
                    
                    # Create summary record
                    summary = {
                        "product_id": product_id,
                        "product_name": history[-1]['product_name'],
                        "initial_price": initial_price,
                        "latest_price": latest_price,
                        "min_price": min_price,
                        "max_price": max_price,
                        "price_change": round(price_change, 2),
                        "percentage_change": round(percentage_change, 2),
                        "significant_changes_count": significant_changes,
                        "data_points": len(history)
                    }
                    
                    writer.writerow(summary)
            
            logger.info(f"Summary report generated: {report_file}")
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
    
    def run_monitoring(self, duration=None, max_iterations=None):
        """Run the price monitoring for a specified duration or iterations."""
        start_time = time.time()
        iteration = 0
        
        logger.info(f"Starting price monitoring with {self.monitoring_interval}s interval")
        logger.info(f"Price change threshold: {self.price_change_threshold}%")
        logger.info(f"Output directory: {self.output_dir}")
        
        try:
            while True:
                iteration += 1
                logger.info(f"Monitoring iteration {iteration}")
                
                # Fetch all available products
                products = self.fetch_all_products()
                if not products:
                    logger.warning("No products available, waiting for next iteration")
                    time.sleep(self.monitoring_interval)
                    continue
                
                product_count = len(products)
                logger.info(f"Found {product_count} products to monitor")
                
                # Process each product
                for product in products:
                    product_id = product.get('id')
                    
                    if not product_id:
                        logger.warning("Product missing ID, skipping")
                        continue
                    
                    # Fetch current product data (try both API and HTML page methods)
                    product_data = self.fetch_product_details(product_id)
                    
                    # If API method fails, try HTML page
                    if not product_data or 'price' not in product_data:
                        product_data = self.fetch_product_page(product_id)
                    
                    if not product_data:
                        logger.warning(f"Could not retrieve data for product {product_id}, skipping")
                        continue
                    
                    # Update price history
                    self.update_price_history(product_data)
                
                # Check if monitoring should stop
                elapsed_time = time.time() - start_time
                
                if duration and elapsed_time >= duration:
                    logger.info(f"Monitoring duration ({duration}s) reached")
                    break
                
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Maximum iterations ({max_iterations}) reached")
                    break
                
                # Wait for next iteration
                logger.info(f"Completed iteration {iteration}, waiting {self.monitoring_interval}s for next check")
                time.sleep(self.monitoring_interval)
        
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        finally:
            # Generate summary report
            self.generate_summary_report()
            logger.info("Price monitoring complete")


def main():
    """Main function to run the price tracker."""
    parser = argparse.ArgumentParser(description='E-commerce API Price Tracker')
    parser.add_argument('--api-url', default='https://cyber.istenith.com', help='Base URL of the e-commerce API')
    parser.add_argument('--output-dir', default='price_history', help='Directory to store price history data')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds')
    parser.add_argument('--duration', type=int, help='Total monitoring duration in seconds (optional)')
    parser.add_argument('--iterations', type=int, help='Maximum number of monitoring iterations (optional)')
    parser.add_argument('--threshold', type=float, default=5.0, help='Significant price change threshold percentage')
    
    args = parser.parse_args()
    
    # Initialize price tracker
    tracker = PriceTracker(
        api_base_url=args.api_url,
        output_dir=args.output_dir,
        monitoring_interval=args.interval,
        price_change_threshold=args.threshold
    )
    
    # Run monitoring
    tracker.run_monitoring(duration=args.duration, max_iterations=args.iterations)


if __name__ == "__main__":
    main()
