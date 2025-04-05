# Automated Invoice Processing System

This system automatically processes invoices from various formats (PDFs, images, emails) and extracts key information into a structured CSV output.

## Features

- Processes multiple input formats:
  - PDF (text-based and scanned/image-based)
  - Images (JPG, JPEG, PNG, TIFF)
  - Email attachments (.eml files)
  - XML and CSV structured data

- Extracts key invoice fields:
  - Vendor name
  - Bill number
  - Billing date
  - Due date
  - Total amount
  - Line item descriptions
  - Source file reference

- Applies data validation and cleaning
- Handles date format standardization
- Uses OCR for image-based documents

## Requirements

The system requires Python 3.6+ and the following libraries:

```
pytesseract
pillow (PIL)
pdf2image
PyPDF2
pandas
opencv-python-headless
numpy
```

Additionally, you need to install Tesseract OCR on your system:
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt-get install tesseract-ocr`
- macOS: `brew install tesseract`

## Installation

1. Install the required Python packages:

```bash
pip install pytesseract pillow pdf2image PyPDF2 pandas opencv-python-headless numpy
```

2. Make sure Tesseract OCR is properly installed and accessible in your PATH.

## Usage

Run the script with the following command:

```bash
python level-1.py -i <input_directory> -o <output_file.csv>
```

Arguments:
- `-i, --input`: Directory containing invoice files (required)
- `-o, --output`: Output CSV file path (default: invoice_data.csv)

Example:
```bash
python level-1.py -i ./invoices -o ./extracted_data.csv
```

## Output Format

The script generates a CSV file with the following columns:
- vendor_name: The name of the vendor or supplier
- bill_number: Invoice/bill identification number
- billing_date: Date when the invoice was issued (YYYY-MM-DD format)
- due_date: Payment due date (YYYY-MM-DD format)
- total_amount: Total amount due in decimal format
- line_items: Semicolon-separated list of line item descriptions
- source_file: Path to the original source file

## Error Handling

The system implements robust error handling:
- File access errors are logged but don't crash the program
- OCR failures fall back to alternative extraction methods
- Date parsing attempts multiple formats
- Amount formatting handles various currency symbols and formats
- Invalid or incomplete invoices are filtered out
