#!/usr/bin/env python3
"""
Invoice Processing System

This script processes invoices from various formats (PDF, images, emails),
extracts key information, and outputs to CSV format.
"""

import os
import csv
import re
import argparse
from datetime import datetime
from pathlib import Path

# Required third-party libraries (install via pip)
try:
    import pytesseract
    from PIL import Image
    import pdf2image
    import PyPDF2
    import pandas as pd
    import cv2
    import numpy as np
    import email
    import imaplib
    import xml.etree.ElementTree as ET
except ImportError as e:
    print(f"Error: Required library not installed: {e}")
    print("Please install required libraries using:")
    print("pip install pytesseract pillow pdf2image PyPDF2 pandas opencv-python-headless numpy")
    exit(1)

class InvoiceProcessor:
    """Main class for processing invoices from various sources."""
    
    def __init__(self, input_dir, output_file):
        """Initialize the processor with input and output paths."""
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        self.results = []
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.output_file) if os.path.dirname(self.output_file) else '.', exist_ok=True)
    
    def process_all(self):
        """Process all files in the input directory."""
        if not self.input_dir.exists():
            print(f"Error: Input directory '{self.input_dir}' does not exist.")
            return False
        
        # Process each file in the input directory
        files_processed = 0
        for file_path in self.input_dir.glob('**/*'):
            if file_path.is_file():
                extension = file_path.suffix.lower()
                try:
                    if extension in ['.pdf']:
                        self._process_pdf(file_path)
                    elif extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
                        self._process_image(file_path)
                    elif extension in ['.eml']:
                        self._process_email(file_path)
                    elif extension in ['.xml']:
                        self._process_xml(file_path)
                    elif extension in ['.csv']:
                        self._process_csv(file_path)
                    else:
                        print(f"Skipping unsupported file: {file_path}")
                        continue
                    
                    files_processed += 1
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
        
        print(f"Processed {files_processed} files.")
        
        # Save results to CSV
        if self.results:
            self._save_to_csv()
            return True
        else:
            print("No valid invoice data was extracted.")
            return False
    
    def _process_pdf(self, file_path):
        """Process PDF files (both text-based and scanned)."""
        print(f"Processing PDF: {file_path}")
        
        # Try to extract text directly first (for text-based PDFs)
        extracted_text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text.strip():
                        extracted_text += page_text
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
        
        # If text extraction failed or returned little text, try OCR
        if len(extracted_text.strip()) < 100:  # Arbitrary threshold
            try:
                # Convert PDF to images
                images = pdf2image.convert_from_path(file_path)
                extracted_text = ""
                for i, image in enumerate(images):
                    # Perform OCR on each page
                    page_text = pytesseract.image_to_string(image)
                    extracted_text += page_text
            except Exception as e:
                print(f"Error performing OCR on PDF: {str(e)}")
        
        # Extract invoice data from the text
        if extracted_text:
            invoice_data = self._extract_invoice_data(extracted_text, file_path)
            if invoice_data:
                self.results.append(invoice_data)
    
    def _process_image(self, file_path):
        """Process image files using OCR."""
        print(f"Processing image: {file_path}")
        
        try:
            # Open image and perform OCR
            image = Image.open(file_path)
            
            # Preprocess image for better OCR results
            image_np = np.array(image)
            if len(image_np.shape) == 3:  # Color image
                gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            else:  # Already grayscale
                gray = image_np
            
            # Apply thresholding to make text more visible
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            
            # Convert back to PIL image for pytesseract
            preprocessed_image = Image.fromarray(thresh)
            
            # Perform OCR
            extracted_text = pytesseract.image_to_string(preprocessed_image)
            
            # Extract invoice data from the text
            if extracted_text:
                invoice_data = self._extract_invoice_data(extracted_text, file_path)
                if invoice_data:
                    self.results.append(invoice_data)
        except Exception as e:
            print(f"Error processing image file: {str(e)}")
    
    def _process_email(self, file_path):
        """Process email files and their attachments."""
        print(f"Processing email: {file_path}")
        
        try:
            # Parse the email
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as email_file:
                msg = email.message_from_file(email_file)
            
            # Process email body
            email_body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain" or content_type == "text/html":
                        try:
                            email_body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            pass
            else:
                email_body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Extract invoice data from email body
            if email_body:
                invoice_data = self._extract_invoice_data(email_body, file_path)
                if invoice_data:
                    self.results.append(invoice_data)
            
            # Process attachments (simplified - in a real system, save and process them)
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if filename:
                    print(f"Email contains attachment: {filename}")
                    # In a real system, save and process the attachment based on its type
        except Exception as e:
            print(f"Error processing email file: {str(e)}")
    
    def _process_xml(self, file_path):
        """Process XML invoice files."""
        print(f"Processing XML: {file_path}")
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # XML structure varies by format, this is a simplified example
            invoice_data = {
                'vendor_name': self._safe_xml_extract(root, './/vendor/name') or self._safe_xml_extract(root, './/supplier/name'),
                'bill_number': self._safe_xml_extract(root, './/invoice/number') or self._safe_xml_extract(root, './/invoiceNumber'),
                'billing_date': self._safe_xml_extract(root, './/invoice/date') or self._safe_xml_extract(root, './/invoiceDate'),
                'due_date': self._safe_xml_extract(root, './/invoice/dueDate') or self._safe_xml_extract(root, './/paymentDueDate'),
                'total_amount': self._safe_xml_extract(root, './/invoice/totalAmount') or self._safe_xml_extract(root, './/totalAmount'),
                'line_items': self._extract_xml_line_items(root),
                'source_file': str(file_path)
            }
            
            # Validate and clean data
            invoice_data = self._validate_and_clean_data(invoice_data)
            if self._is_valid_invoice(invoice_data):
                self.results.append(invoice_data)
        except Exception as e:
            print(f"Error processing XML file: {str(e)}")
    
    def _safe_xml_extract(self, root, xpath):
        """Safely extract XML elements that might not exist."""
        try:
            element = root.find(xpath)
            return element.text.strip() if element is not None and element.text else ""
        except:
            return ""
    
    def _extract_xml_line_items(self, root):
        """Extract line items from XML structure."""
        line_items = []
        
        # XML structure varies by format, this is a simplified example
        try:
            for item in root.findall('.//lineItem') or root.findall('.//item'):
                description = self._safe_xml_extract(item, './description') or self._safe_xml_extract(item, './name')
                line_items.append(description)
        except:
            pass
            
        return "; ".join(line_items) if line_items else ""
    
    def _process_csv(self, file_path):
        """Process CSV invoice files."""
        print(f"Processing CSV: {file_path}")
        
        try:
            df = pd.read_csv(file_path)
            
            # CSV structure varies by format, this is a simplified example
            # Assuming a specific structure, adapt as needed
            if 'vendor_name' in df.columns or 'supplier' in df.columns:
                # This appears to be a properly formatted invoice
                invoice_data = {
                    'vendor_name': df.get('vendor_name', df.get('supplier', [""]))[0],
                    'bill_number': df.get('invoice_number', df.get('bill_number', [""]))[0],
                    'billing_date': df.get('invoice_date', df.get('billing_date', [""]))[0],
                    'due_date': df.get('due_date', [""])[0],
                    'total_amount': df.get('total_amount', df.get('amount', [""]))[0],
                    'line_items': self._extract_csv_line_items(df),
                    'source_file': str(file_path)
                }
                
                # Validate and clean data
                invoice_data = self._validate_and_clean_data(invoice_data)
                if self._is_valid_invoice(invoice_data):
                    self.results.append(invoice_data)
        except Exception as e:
            print(f"Error processing CSV file: {str(e)}")
    
    def _extract_csv_line_items(self, df):
        """Extract line items from CSV data."""
        line_items = []
        
        # If there's a description or item column, extract those
        if 'description' in df.columns:
            line_items = df['description'].dropna().tolist()
        elif 'item' in df.columns:
            line_items = df['item'].dropna().tolist()
        
        return "; ".join(str(item) for item in line_items) if line_items else ""
    
    def _extract_invoice_data(self, text, file_path):
        """Extract invoice data from text using regular expressions."""
        # Convert text to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Initialize invoice data dictionary
        invoice_data = {
            'vendor_name': '',
            'bill_number': '',
            'billing_date': '',
            'due_date': '',
            'total_amount': '',
            'line_items': '',
            'source_file': str(file_path)
        }
        
        # Extract vendor name
        vendor_patterns = [
            r'(?:vendor|supplier|from|company)(?:\s*):?\s*([A-Za-z0-9\s&.,]+?)(?:\n|$|Inc\.|LLC|Ltd\.)',
            r'^([A-Za-z0-9\s&.,]+?)(?:\n|$|Inc\.|LLC|Ltd\.)'
        ]
        for pattern in vendor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['vendor_name'] = match.group(1).strip()
                break
        
        # Extract bill/invoice number
        bill_patterns = [
            r'(?:invoice|bill|ref)(?:\s+(?:no|num|number|#))?\s*[:# ]\s*([A-Za-z0-9\-]+)',
            r'(?:invoice|bill)(?:\s+(?:number|#|no))?\s*[:# ]\s*([A-Za-z0-9\-]+)'
        ]
        for pattern in bill_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['bill_number'] = match.group(1).strip()
                break
        
        # Extract billing date
        date_patterns = [
            r'(?:invoice|bill)(?:\s+date)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:invoice|bill)(?:\s+date)?\s*:?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
            r'(?:date)(?:\s+(?:of)?(?:\s+invoice|bill))?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:date)(?:\s+(?:of)?(?:\s+invoice|bill))?\s*:?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['billing_date'] = match.group(1).strip()
                break
        
        # Extract due date
        due_date_patterns = [
            r'(?:due|payment\s+due|pay\s+by)(?:\s+date)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:due|payment\s+due|pay\s+by)(?:\s+date)?\s*:?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})'
        ]
        for pattern in due_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['due_date'] = match.group(1).strip()
                break
        
        # Extract total amount
        amount_patterns = [
            r'(?:total|amount\s+due|balance\s+due|sum)(?:\s+amount)?\s*:?\s*[$€£]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(?:total|amount\s+due|balance\s+due|sum)(?:\s+amount)?\s*:?\s*[$€£]?\s*((?:\d{1,3},)*\d{1,3}\.\d{2})'
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data['total_amount'] = match.group(1).strip()
                break
        
        # Extract line items (simplistic approach)
        items_section_pattern = r'(?:description|item|service|product)s?(?:\s+description)?(?:[:\n])(.*?)(?:subtotal|total|amount|sum)'
        match = re.search(items_section_pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            items_text = match.group(1).strip()
            # Split by newlines and filter out empty lines
            items = [line.strip() for line in items_text.split('\n') if line.strip()]
            if items:
                invoice_data['line_items'] = "; ".join(items)
        
        # Validate and clean the extracted data
        invoice_data = self._validate_and_clean_data(invoice_data)
        
        return invoice_data if self._is_valid_invoice(invoice_data) else None
    
    def _validate_and_clean_data(self, invoice_data):
        """Validate and clean the extracted invoice data."""
        # Clean vendor name
        if invoice_data['vendor_name']:
            invoice_data['vendor_name'] = re.sub(r'\s+', ' ', invoice_data['vendor_name']).strip()
        
        # Clean bill number
        if invoice_data['bill_number']:
            invoice_data['bill_number'] = re.sub(r'\s+', '', invoice_data['bill_number']).strip()
        
        # Clean and standardize dates
        if invoice_data['billing_date']:
            try:
                # Try to parse and standardize the date format
                date_formats = [
                    '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
                    '%d/%m/%y', '%m/%d/%y', '%d-%m-%y', '%m-%d-%y',
                    '%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y'
                ]
                for date_format in date_formats:
                    try:
                        parsed_date = datetime.strptime(invoice_data['billing_date'], date_format)
                        invoice_data['billing_date'] = parsed_date.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
            except:
                pass  # Keep original if parsing fails
        
        if invoice_data['due_date']:
            try:
                # Try to parse and standardize the date format
                date_formats = [
                    '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
                    '%d/%m/%y', '%m/%d/%y', '%d-%m-%y', '%m-%d-%y',
                    '%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y'
                ]
                for date_format in date_formats:
                    try:
                        parsed_date = datetime.strptime(invoice_data['due_date'], date_format)
                        invoice_data['due_date'] = parsed_date.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
            except:
                pass  # Keep original if parsing fails
        
        # Clean total amount
        if invoice_data['total_amount']:
            # Remove non-numeric characters except decimal point
            cleaned_amount = re.sub(r'[^\d.]', '', invoice_data['total_amount'])
            try:
                # Format as proper decimal
                amount_float = float(cleaned_amount)
                invoice_data['total_amount'] = f"{amount_float:.2f}"
            except:
                pass  # Keep original if parsing fails
        
        return invoice_data
    
    def _is_valid_invoice(self, invoice_data):
        """Check if the extracted invoice data is valid enough to be included."""
        # At minimum, we need either a vendor name or a bill number,
        # plus either a date or an amount to consider it a valid invoice
        has_identifier = bool(invoice_data['vendor_name'] or invoice_data['bill_number'])
        has_transaction_info = bool(invoice_data['billing_date'] or invoice_data['total_amount'])
        
        return has_identifier and has_transaction_info
    
    def _save_to_csv(self):
        """Save the extracted invoice data to a CSV file."""
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['vendor_name', 'bill_number', 'billing_date', 'due_date', 
                             'total_amount', 'line_items', 'source_file']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for invoice in self.results:
                    writer.writerow(invoice)
            
            print(f"Results saved to {self.output_file}")
            return True
        except Exception as e:
            print(f"Error saving results to CSV: {str(e)}")
            return False


def main():
    """Main function to run the invoice processor."""
    parser = argparse.ArgumentParser(description='Process invoices from various formats and extract data.')
    parser.add_argument('-i', '--input', required=True, help='Input directory containing invoice files')
    parser.add_argument('-o', '--output', default='invoice_data.csv', help='Output CSV file (default: invoice_data.csv)')
    
    args = parser.parse_args()
    
    # Process invoices
    processor = InvoiceProcessor(args.input, args.output)
    success = processor.process_all()
    
    if success:
        print("Invoice processing completed successfully.")
    else:
        print("Invoice processing completed with errors.")
        return 1
    
    return 0


if __name__ == "__main__":
    main()
