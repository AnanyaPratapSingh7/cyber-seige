# Price Watcher & Price Tracker Solutions

This repository contains two solutions for tracking product prices from e-commerce websites:

1. **Level 1: Price Watcher** - Extracts current prices from various e-commerce websites
2. **Level 2: Price Tracker** - Monitors multiple products from a mock API over time and records price history

## Level 1: Price Watcher

This script extracts product names and prices from various e-commerce websites to help users track prices without manually checking product pages.

### Features

- Extracts product names and current prices from multiple e-commerce platforms:
  - Amazon
  - Flipkart
  - Books To Scrape
  - Meesho
  - Generic support for other e-commerce sites

- Handles various price formats and currencies
- Provides fallback mechanisms when primary extraction fails
- Works with both static HTML and JavaScript-rendered pages
- Comprehensive error handling for network failures and missing elements

### Requirements

The script requires Python 3.6+ and the following libraries:

```
requests
beautifulsoup4
selenium
webdriver_manager
```

Additionally, you need to have Chrome browser installed for Selenium WebDriver.

### Installation

1. Install the required Python packages:

```bash
pip install requests beautifulsoup4 selenium webdriver_manager
```

2. Make sure Chrome browser is installed on your system.

### Usage

Run the script with the following command:

```bash
python level-1.py <product_url> [options]
```

#### Arguments:

- `product_url`: URL of the product page to track (required)

#### Options:

- `--no-headless`: Run browser in visible mode instead of headless mode
- `--timeout TIMEOUT`: Set custom timeout in seconds for page loading (default: 20)

#### Examples:

```bash
# Extract price from Books To Scrape
python level-1.py https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html

# Extract price from Amazon with a longer timeout
python level-1.py https://www.amazon.in/product-url --timeout 30

# Extract price from Flipkart with visible browser
python level-1.py https://www.flipkart.com/product-url --no-headless
```

#### Output Format

The script provides:

1. A human-readable summary with product name, price, and currency
2. A complete JSON output with all extracted information

Example output:

```
Product Information:
Name: A Light in the Attic
Price: GBP 51.77 (£51.77)
URL: https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html

Full JSON Output:
{
  "product_name": "A Light in the Attic",
  "price": 51.77,
  "currency": "GBP",
  "price_raw": "£51.77",
  "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
}
```

## Level 2: Price Tracker

This script tracks product prices from a mock e-commerce API over time, records historical data in CSV format, and detects significant price changes.

### Features

- Monitors multiple products simultaneously from the mock API
- Records price history in CSV format with timestamps
- Detects significant price changes (>5% movement)
- Handles edge cases:
  - Skips duplicate entries with no price change
  - Handles missing or unavailable products
  - Detects price inconsistencies

- Generates a detailed summary report of price tracking results
- Configurable monitoring interval and price change threshold

### Requirements

The script requires Python 3.6+ and the following libraries:

```
requests
beautifulsoup4
```

### Installation

Install the required Python packages:

```bash
pip install requests beautifulsoup4
```

### Usage

Run the script with the following command:

```bash
python level-2.py [options]
```

#### Options:

- `--api-url URL`: Base URL of the e-commerce API (default: https://cyber.istenith.com)
- `--output-dir DIR`: Directory to store price history data (default: price_history)
- `--interval SECONDS`: Monitoring interval in seconds (default: 60)
- `--duration SECONDS`: Total monitoring duration in seconds (optional)
- `--iterations NUM`: Maximum number of monitoring iterations (optional)
- `--threshold PERCENT`: Significant price change threshold percentage (default: 5.0)

#### Examples:

```bash
# Monitor prices with default settings
python level-2.py

# Monitor with 30-second interval for 1 hour
python level-2.py --interval 30 --duration 3600

# Monitor with custom threshold and 10 iterations
python level-2.py --threshold 2.5 --iterations 10
```

### Output Files

The script generates two CSV files in the output directory:

1. **price_history.csv**: Contains all price data points with timestamps
   - Columns: product_id, product_name, timestamp, price, currency, significant_change, change_percentage

2. **price_summary_report.csv**: Contains a summary of price tracking for each product
   - Columns: product_id, product_name, initial_price, latest_price, min_price, max_price, price_change, percentage_change, significant_changes_count, data_points 