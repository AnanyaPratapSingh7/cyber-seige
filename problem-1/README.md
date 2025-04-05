# Product Price Scraper

A smart script that fetches live prices and product names from various e-commerce websites.

## Features

- Extracts product names and prices from multiple e-commerce platforms
- Handles both static HTML websites and JavaScript-rendered pages
- Provides error handling for network issues and missing elements
- Works with various price formats and HTML structures
- Detects and reports anti-scraping measures from websites

## Dependencies

All dependencies are listed in the `requirements.txt` file:
```
requests>=2.25.0
beautifulsoup4>=4.9.3
selenium>=4.0.0
webdriver-manager>=3.5.0
```

## Setup Instructions

1. **Install Python**
   Make sure you have Python 3.6 or higher installed.

2. **Set up a Virtual Environment**
   
   **Windows:**
   ```bash
   # Navigate to the project directory
   cd problem-1
   
   # Create a virtual environment
   python -m venv venv
   
   # Activate the virtual environment
   .\venv\Scripts\Activate.ps1  # For PowerShell
   # OR
   .\venv\Scripts\activate.bat  # For Command Prompt
   ```
   
   **Linux/macOS:**
   ```bash
   # Navigate to the project directory
   cd problem-1
   
   # Create a virtual environment
   python3 -m venv venv
   
   # Activate the virtual environment
   source venv/bin/activate
   ```

3. **Install Required Packages**
   ```bash
   # Install all dependencies from requirements.txt
   pip install -r requirements.txt
   ```

4. **ChromeDriver Setup**
   The script uses Chrome browser for JavaScript-rendered sites:
   - Chrome browser should be installed on your system
   - The webdriver-manager package will automatically download and manage the appropriate ChromeDriver version

## How to Run the Script

Once the virtual environment is activated and dependencies are installed:

```bash
python level-1.py "URL_OF_PRODUCT"
```

Example:
```bash
python level-1.py "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
```

### Optional Arguments

The script supports additional arguments:

- `--debug`: Enable detailed debug output in console and log file
- `--user-agent`: Specify a custom user agent to bypass some website restrictions

Example with custom user agent:
```bash
python level-1.py "https://www.meesho.com/product/123" --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
```

## Handling Website Blocks

Many e-commerce sites implement anti-scraping measures to prevent automated data collection. The script has built-in detection for common blocking techniques and will provide appropriate feedback.

If you encounter "Access Denied" or other blocking messages:

1. Try using a custom user agent (see example above)
2. Some websites may require additional techniques beyond the scope of this script
3. Consider respecting the website's terms of service and using their official API if available

## Supported E-commerce Sites

The script is specifically optimized for:
- books.toscrape.com
- Amazon
- Flipkart
- Meesho

Additionally, it includes generic extraction methods that attempt to work with other e-commerce sites.

## Assumptions Made

1. **Network Connectivity**
   - The script assumes an active internet connection is available
   - Timeouts are set to 10 seconds for requests

2. **Browser Availability**
   - For JavaScript-rendered sites, Chrome browser is assumed to be installed

3. **Price Elements**
   - We assume prices are generally represented in common HTML structures
   - Currency symbols and formatting may vary, but we clean them for consistency

4. **Scraping Limitations**
   - Some websites implement anti-scraping measures that could block the script
   - Dynamic sites might change their HTML structure, requiring updates to the selectors

5. **Execution Environment**
   - The script assumes it's running in an environment where browser automation is allowed

## Error Handling

- The script logs errors and exceptions for debugging
- It first attempts static extraction (faster) before falling back to dynamic extraction
- If both methods fail, it will notify the user that no information could be extracted
- For websites with blocking mechanisms, specific advice is provided
