# 🏆 CyberSiege 2025 - Team Sudoers

<div align="center">
  <img src="https://img.shields.io/badge/competition-CyberSiege_2025-blue?style=for-the-badge&logo=github" alt="CyberSiege 2025">
  <img src="https://img.shields.io/badge/team-Sudoers-orange?style=for-the-badge&logo=linux" alt="Team Sudoers">
  <img src="https://img.shields.io/badge/event-Prodyogiki_2025-green?style=for-the-badge&logo=hack-the-box" alt="Prodyogiki 2025">
  <img src="https://img.shields.io/badge/organization-ISTE-red?style=for-the-badge&logo=python" alt="ISTE">
</div>

<div align="center">
  <img src="https://media.giphy.com/media/l4hLCGQgMlsAzfr8s/giphy.gif" width="500px" alt="Cybersecurity Animation">
</div>

## 🚀 Overview

This repository contains our team Sudoers' solutions for the CyberSiege competition conducted as part of Prodyogiki 2025 by ISTE. We tackled challenging problems involving web scraping, data processing, automation, and cybersecurity.

<div align="center">
  <img src="https://media.giphy.com/media/3oKIPEqDGUULpEU0aQ/giphy.gif" width="400px" alt="Hacking Animation">
</div>

## 📋 Problem Set

Our solutions cover multiple problem domains:

### 🔍 Problem 1: Advanced Web Scraping & CAPTCHA Bypass
- **Level 1**: Basic e-commerce price extraction system
- **Level 2**: Price monitoring API with historical tracking
- **Level 3**: Stealth scraper with CAPTCHA bypass capabilities

### 📄 Problem 2: Invoice Processing System
- **Level 1**: Multi-format invoice data extraction pipeline

### 🎵 Problem 3: Audio Beat Detection
- **Level 1**: Beat Detection Core - Basic beat detection script that outputs beat timestamps
- **Level 2**: Advanced Cut Marker Generator - Enhanced beat detection with customizable parameters for video editing

### 🔒 Problem 4: SSH Brute-Force Detector
- **Level 1**: SSH Brute-Force Detector with Auto-Block - Basic SSH brute-force detection and IP blocking
- **Level 2**: Advanced Threat Mitigation System - Enhanced defender with real-time alerts, adaptive blocking, and distributed attack detection

## 🛠️ Technologies Used

<div align="center">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python">
  <img src="https://img.shields.io/badge/selenium-%43B02A?style=for-the-badge&logo=selenium&logoColor=white" alt="Selenium">
  <img src="https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas">
  <img src="https://img.shields.io/badge/beautifulsoup4-%236C6C6C.svg?style=for-the-badge" alt="BeautifulSoup4">
  <img src="https://img.shields.io/badge/opencv-%23white.svg?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV">
  <img src="https://img.shields.io/badge/regex-%23276DC3.svg?style=for-the-badge" alt="Regex">
  <img src="https://img.shields.io/badge/librosa-%23F7931E.svg?style=for-the-badge" alt="Librosa">
  <img src="https://img.shields.io/badge/cybersecurity-%23FF0000.svg?style=for-the-badge" alt="Cybersecurity">
</div>

## 📊 Features & Highlights

### Problem 1: Web Scraping
- **Undetectable Browser Automation**: Using undetected-chromedriver to bypass bot detection
- **Dynamic Delays & User-Agent Rotation**: Mimicking human behavior for stealth browsing
- **CAPTCHA Handling**: Advanced techniques to detect and handle CAPTCHA challenges
- **Price History Tracking**: CSV-based historical data with analysis capabilities

### Problem 2: Invoice Processing
- **Multi-Format Support**: PDF, Images, Emails, XML, and CSV processing
- **OCR Integration**: Extracting text from scanned/image documents
- **Intelligent Data Parsing**: Automated extraction of key invoice fields
- **Data Validation & Cleaning**: Ensuring data integrity and consistency

### Problem 3: Audio Beat Detection
- **Energy-Based Onset Detection**: Analysis of audio waves to detect beats
- **Variable BPM Handling**: Works with tempo changes and complex rhythms
- **Customizable Parameters**: Adjustable sensitivity for different music genres
- **Video Cut Point Generation**: Formatted timestamps perfect for video editing software

### Problem 4: SSH Brute-Force Detection
- **Cross-Platform Security**: Works on Linux, macOS, and Windows systems
- **Real-Time Alerts**: Multi-channel notifications via Slack and email
- **Adaptive Blocking**: Intelligent cooldown and persistent rule tracking
- **Distributed Attack Detection**: Identifies coordinated attacks from multiple sources

## 📁 Repository Structure

```
cyber-siege/
├── problem-1/                 # Web Scraping Solutions
│   ├── level-1.py             # Basic Price Extraction
│   ├── level-2.py             # Price History Tracking
│   ├── level-3.py             # CAPTCHA Bypass Solution
│   └── README.md              # Documentation for Problem 1
│
├── problem-2/                 # Invoice Processing
│   ├── level-1.py             # Invoice Extraction System
│   └── README.md              # Documentation for Problem 2
│
├── problem-3/                 # Audio Beat Detection
│   ├── level-1.py             # Beat Detection Core
│   ├── level-2.py             # Advanced Cut Marker Generator
│   ├── README.md              # Documentation for Problem 3
│   └── requirements.txt       # Dependencies for audio processing
│
├── problem-4/                 # SSH Brute-Force Detection
│   ├── level-1.py             # Basic Brute-Force Detector
│   ├── level-2.py             # Advanced Threat Mitigation
│   ├── README.md              # Documentation for Problem 4
│   └── requirements.txt       # Dependencies for security tools
│
└── master-README.md           # Main Repository Documentation
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Chrome Browser (for Selenium-based solutions)
- Tesseract OCR (for invoice processing)
- SSH Server (for testing brute-force detection)
- Audio libraries (for beat detection)

### Installation
```bash
# Clone the repository
git clone https://github.com/AnanyaPratapSingh7/cyber-seige.git
cd cyber-seige

# Install requirements for Problem 1
pip install requests beautifulsoup4 selenium webdriver_manager undetected-chromedriver fake-useragent

# Install requirements for Problem 2
pip install pytesseract pillow pdf2image PyPDF2 pandas opencv-python-headless numpy

# Install requirements for Problem 3
pip install -r problem-3/requirements.txt

# Install requirements for Problem 4
pip install -r problem-4/requirements.txt
```

### Running the Solutions
Each problem has its own README with detailed instructions on how to run the specific solutions.

## 👥 Team Sudoers

Our team of skilled developers took on the challenge with enthusiasm and technical expertise.

<div align="center">
  <img src="https://media.giphy.com/media/WTjnWYENpLxS8JQ5rz/giphy.gif" width="400px" alt="Team Work">
</div>

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Acknowledgements

- [ISTE](https://www.isteonline.in/) for organizing the Prodyogiki 2025 event
- CyberSiege competition organizers for the challenging problem sets
- All open-source libraries and tools that made our solutions possible

---

<div align="center">
  <p>Made with ❤️ by Team Sudoers</p>
  <p>© 2025 Team Sudoers. All rights reserved.</p>
</div> 
