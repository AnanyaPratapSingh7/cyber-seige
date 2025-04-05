#!/usr/bin/env python3
"""
Advanced SSH Brute-Force Detector with Threat Mitigation (Level 2)
This script enhances the basic SSH defender with real-time alerts, adaptive blocking,
and distributed attack detection capabilities.
"""

import argparse
import os
import re
import sys
import time
import json
import yaml
import socket
import smtplib
import logging
import ipaddress
import subprocess
import dns.resolver
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ipaddress import ip_address, ip_network
from dateutil import parser as date_parser
from timezonefinder import TimezoneFinder
from slack_sdk.webhook import WebhookClient

# Optional imports for geolocation
try:
    import geoip2.database
    import geoip2.errors
    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_THRESHOLD = 5
DEFAULT_TIME_WINDOW = 5
DEFAULT_BLOCK_DURATION = 1440  # 24 hours in minutes
DEFAULT_CONFIG_PATHS = {
    'linux': '/etc/ssh-defender.yaml',
    'darwin': os.path.expanduser('~/Library/ssh-defender.conf'),
    'win32': os.path.expandvars(r'C:\ssh-defender\config.ini')
}
DEFAULT_BLOCK_LOG = {
    'linux': '/var/log/ssh_defender_blocks.log',
    'darwin': os.path.expanduser('~/Library/Logs/ssh_defender_blocks.log'),
    'win32': os.path.expandvars(r'C:\ssh-defender\logs\blocks.log')
}
DEFAULT_STATE_FILE = {
    'linux': '/var/lib/ssh-defender/state.json',
    'darwin': os.path.expanduser('~/Library/Application Support/ssh-defender/state.json'),
    'win32': os.path.expandvars(r'C:\ssh-defender\state.json')
}
GEOIP_DB_PATHS = [
    '/usr/share/GeoIP/GeoLite2-City.mmdb',
    '/usr/local/share/GeoIP/GeoLite2-City.mmdb',
    os.path.expanduser('~/GeoIP/GeoLite2-City.mmdb'),
    os.path.expandvars(r'C:\GeoIP\GeoLite2-City.mmdb')
]
HTML_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { background-color: #{{ header_color }}; color: white; padding: 10px; }
        .content { padding: 15px; }
        .footer { font-size: 12px; color: #666; padding: 10px; border-top: 1px solid #eee; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>SSH Brute-Force {{ alert_type }}</h2>
        </div>
        <div class="content">
            <p>{{ message }}</p>
            
            <h3>Attack Details:</h3>
            <table>
                <tr><th>Property</th><th>Value</th></tr>
                <tr><td>IP Address</td><td>{{ ip }}</td></tr>
                <tr><td>Hostname</td><td>{{ hostname }}</td></tr>
                <tr><td>Location</td><td>{{ location }}</td></tr>
                <tr><td>Failed Attempts</td><td>{{ attempts }}</td></tr>
                <tr><td>Time Period</td><td>{{ time_period }}</td></tr>
                <tr><td>Targeted Users</td><td>{{ users }}</td></tr>
                {% if attack_pattern %}
                <tr><td>Attack Pattern</td><td>{{ attack_pattern }}</td></tr>
                {% endif %}
            </table>
            
            {% if is_distributed %}
            <h3>Distributed Attack Information:</h3>
            <p>This appears to be part of a coordinated attack from multiple sources.</p>
            <table>
                <tr><th>Related IPs</th><th>Common Target</th><th>Pattern</th></tr>
                {% for ip_info in related_ips %}
                <tr><td>{{ ip_info.ip }}</td><td>{{ ip_info.target }}</td><td>{{ ip_info.pattern }}</td></tr>
                {% endfor %}
            </table>
            {% endif %}
            
            <p>Action taken: {{ action }}</p>
            
            {% if unblock_info %}
            <p>{{ unblock_info }}</p>
            {% endif %}
        </div>
        <div class="footer">
            <p>SSH Defender - Generated {{ timestamp }}</p>
        </div>
    </div>
</body>
</html>
"""

class AdvancedSSHDefender:
    """Advanced SSH defender with real-time alerts and distributed attack detection."""
    
    def __init__(self, config=None, **kwargs):
        """
        Initialize the SSH defender with configuration.
        
        Args:
            config (dict): Configuration dictionary
            **kwargs: Override configuration with command-line arguments
        """
        self.platform = sys.platform
        logger.info(f"Detected platform: {self.platform}")
        
        # Initialize with defaults
        self.threshold = DEFAULT_THRESHOLD
        self.time_window = DEFAULT_TIME_WINDOW
        self.block_duration = DEFAULT_BLOCK_DURATION
        self.whitelist = set()
        self.cidr_whitelist = []
        self.dry_run = False
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = {}  # {ip: expiry_time}
        self.user_targets = defaultdict(set)  # {username: set(ips)}
        self.distributed_detection = True
        self.alerts_enabled = True
        self.geo_enabled = GEOIP_AVAILABLE
        self.emergency_unblock_key = None
        
        # Load configuration
        if config:
            self._load_config(config)
        
        # Override with kwargs
        for key, value in kwargs.items():
            if value is not None and hasattr(self, key):
                setattr(self, key, value)
        
        # Initialize GeoIP database if available
        self.geoip_reader = None
        if self.geo_enabled:
            self._init_geoip()
        
        # Load persisted state if available
        self._load_state()
        
        # Check for root/admin privileges
        self._check_privileges()
    
    def _load_config(self, config):
        """Load configuration from a dictionary."""
        # General settings
        if 'general' in config:
            self.threshold = config['general'].get('threshold', self.threshold)
            self.time_window = config['general'].get('time_window', self.time_window)
            self.block_duration = config['general'].get('block_duration', self.block_duration)
            self.block_log_path = config['general'].get('block_log', 
                                                        DEFAULT_BLOCK_LOG.get(self.platform))
            self.state_file = config['general'].get('persistent_state', 
                                                    DEFAULT_STATE_FILE.get(self.platform))
        
        # Whitelist settings
        if 'whitelist' in config:
            # Process IP whitelist
            if 'ips' in config['whitelist']:
                for ip_item in config['whitelist']['ips']:
                    if '/' in ip_item:  # CIDR notation
                        try:
                            self.cidr_whitelist.append(ip_network(ip_item))
                        except ValueError:
                            logger.warning(f"Invalid CIDR in whitelist: {ip_item}")
                    else:  # Single IP
                        try:
                            ipaddress.ip_address(ip_item)  # Validate IP
                            self.whitelist.add(ip_item)
                        except ValueError:
                            logger.warning(f"Invalid IP in whitelist: {ip_item}")
            
            # Emergency unblock key
            self.emergency_unblock_key = config['whitelist'].get('emergency_unblock_key')
        
        # Alert settings
        if 'alerts' in config:
            # Slack settings
            if 'slack' in config['alerts']:
                slack_config = config['alerts']['slack']
                self.slack_enabled = slack_config.get('enabled', False)
                self.slack_webhook = slack_config.get('webhook_url')
                self.slack_channel = slack_config.get('channel', '#security-alerts')
            
            # Email settings
            if 'email' in config['alerts']:
                email_config = config['alerts']['email']
                self.email_enabled = email_config.get('enabled', False)
                self.smtp_server = email_config.get('smtp_server')
                self.smtp_port = email_config.get('smtp_port', 587)
                self.smtp_use_tls = email_config.get('use_tls', True)
                self.smtp_username = email_config.get('username')
                self.smtp_password = email_config.get('password')
                self.email_from = email_config.get('from_address')
                self.email_to = email_config.get('to_addresses', [])
        
        # Distributed detection settings
        if 'distributed_detection' in config:
            dd_config = config['distributed_detection']
            self.distributed_detection = dd_config.get('enabled', True)
            self.username_threshold = dd_config.get('username_threshold', 5)
            self.timing_sensitivity = dd_config.get('timing_sensitivity', 'medium')
            self.geo_detection = dd_config.get('geo_detection', True) and GEOIP_AVAILABLE
    
    def _init_geoip(self):
        """Initialize GeoIP database reader."""
        if not GEOIP_AVAILABLE:
            logger.warning("GeoIP functionality not available. Install geoip2 package.")
            self.geo_enabled = False
            return
        
        # Try to find a valid GeoIP database
        for db_path in GEOIP_DB_PATHS:
            if os.path.exists(db_path):
                try:
                    self.geoip_reader = geoip2.database.Reader(db_path)
                    logger.info(f"Loaded GeoIP database from {db_path}")
                    return
                except Exception as e:
                    logger.error(f"Error loading GeoIP database from {db_path}: {e}")
        
        logger.warning("GeoIP database not found. Geolocation features disabled.")
        self.geo_enabled = False
    
    def _check_privileges(self):
        """Check if the script has the necessary privileges to block IPs."""
        if self.platform.startswith('linux') or self.platform == 'darwin':  # Linux or macOS
            if os.geteuid() != 0:
                if not self.dry_run:
                    logger.error("This script requires root privileges to block IPs. Run with sudo or use --dry-run.")
                    sys.exit(1)
                else:
                    logger.warning("Running in dry-run mode without root privileges. IP blocking will be simulated.")
        elif self.platform == 'win32':  # Windows
            # Check for admin rights on Windows
            try:
                import ctypes
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    if not self.dry_run:
                        logger.error("This script requires Administrator privileges to block IPs. Run as Administrator or use --dry-run.")
                        sys.exit(1)
                    else:
                        logger.warning("Running in dry-run mode without Administrator privileges. IP blocking will be simulated.")
            except:
                logger.warning("Unable to check for Administrator privileges on Windows.")
    
    def _load_state(self):
        """Load persistent state from file."""
        if hasattr(self, 'state_file') and self.state_file and os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                # Load blocked IPs with expiry times
                if 'blocked_ips' in state:
                    now = datetime.now()
                    for ip, expiry_str in state['blocked_ips'].items():
                        try:
                            expiry = date_parser.parse(expiry_str)
                            if expiry > now:  # Only load non-expired blocks
                                self.blocked_ips[ip] = expiry
                                logger.info(f"Loaded persistent block for IP {ip} until {expiry}")
                        except Exception as e:
                            logger.debug(f"Error parsing expiry for IP {ip}: {e}")
                
                logger.info(f"Loaded {len(self.blocked_ips)} persistent IP blocks from {self.state_file}")
            except Exception as e:
                logger.error(f"Error loading state file: {e}")
    
    def _save_state(self):
        """Save persistent state to file."""
        if hasattr(self, 'state_file') and self.state_file:
            try:
                # Create directory if it doesn't exist
                state_dir = os.path.dirname(self.state_file)
                if state_dir and not os.path.exists(state_dir):
                    os.makedirs(state_dir, exist_ok=True)
                
                state = {
                    'blocked_ips': {ip: expiry.isoformat() for ip, expiry in self.blocked_ips.items()},
                    'last_update': datetime.now().isoformat()
                }
                
                with open(self.state_file, 'w') as f:
                    json.dump(state, f, indent=2)
                
                logger.debug(f"Saved state to {self.state_file}")
            except Exception as e:
                logger.error(f"Error saving state file: {e}")
    
    def is_whitelisted(self, ip):
        """Check if an IP is whitelisted."""
        if ip in self.whitelist:
            return True
        
        try:
            ip_obj = ip_address(ip)
            for cidr in self.cidr_whitelist:
                if ip_obj in cidr:
                    return True
        except ValueError:
            pass
        
        return False
    
    def get_failed_attempts(self):
        """Parse logs to find failed SSH login attempts with usernames."""
        if self.platform.startswith('linux'):
            return self._get_failed_attempts_linux()
        elif self.platform == 'darwin':
            return self._get_failed_attempts_macos()
        elif self.platform == 'win32':
            return self._get_failed_attempts_windows()
        else:
            logger.error(f"Unsupported platform: {self.platform}")
            return []
    
    def _get_failed_attempts_linux(self):
        """Get failed SSH login attempts from Linux logs with username extraction."""
        attempts = []
        
        # Try using journalctl first (systemd-based systems)
        try:
            cmd = ["journalctl", "-u", "ssh", "-n", "1000", "--no-pager"]
            output = subprocess.check_output(cmd, universal_newlines=True)
            
            # Extract failed password attempts with username
            pattern = r"(\w+\s+\d+\s+\d+:\d+:\d+).*sshd.*Failed password for (invalid user )?(\w+) from (\d+\.\d+\.\d+\.\d+)"
            for line in output.splitlines():
                match = re.search(pattern, line)
                if match:
                    try:
                        timestamp_str = match.group(1)
                        # Add year as journalctl might not include it
                        if len(timestamp_str.split()) < 3:
                            timestamp_str = f"{datetime.now().year} {timestamp_str}"
                        timestamp = datetime.strptime(timestamp_str, "%Y %b %d %H:%M:%S")
                        username = match.group(3)
                        ip = match.group(4)
                        attempts.append((timestamp, ip, username))
                    except Exception as e:
                        logger.debug(f"Error parsing timestamp: {e}")
        except Exception as e:
            logger.debug(f"Error using journalctl: {e}")
        
        # If journalctl failed or found no results, try auth.log
        if not attempts:
            try:
                log_files = ["/var/log/auth.log", "/var/log/secure"]
                for log_file in log_files:
                    if os.path.exists(log_file):
                        with open(log_file, 'r') as f:
                            for line in f:
                                if "sshd" in line and "Failed password" in line:
                                    match = re.search(r"(\w+\s+\d+\s+\d+:\d+:\d+).*sshd.*Failed password for (invalid user )?(\w+) from (\d+\.\d+\.\d+\.\d+)", line)
                                    if match:
                                        try:
                                            timestamp_str = match.group(1)
                                            # Add year as auth.log might not include it
                                            if len(timestamp_str.split()) < 3:
                                                timestamp_str = f"{datetime.now().year} {timestamp_str}"
                                            timestamp = datetime.strptime(timestamp_str, "%Y %b %d %H:%M:%S")
                                            username = match.group(3)
                                            ip = match.group(4)
                                            attempts.append((timestamp, ip, username))
                                        except Exception as e:
                                            logger.debug(f"Error parsing timestamp: {e}")
            except Exception as e:
                logger.debug(f"Error parsing auth.log: {e}")
        
        return attempts
    
    def _get_failed_attempts_macos(self):
        """Get failed SSH login attempts from macOS logs with username extraction."""
        attempts = []
        
        try:
            # macOS uses system.log or secure.log
            log_files = ["/var/log/system.log", "/var/log/secure.log"]
            for log_file in log_files:
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        for line in f:
                            if "sshd" in line and "Failed password" in line:
                                match = re.search(r"(\w+\s+\d+\s+\d+:\d+:\d+).*sshd.*Failed password for (invalid user )?(\w+) from (\d+\.\d+\.\d+\.\d+)", line)
                                if match:
                                    try:
                                        timestamp_str = match.group(1)
                                        # Add year as log might not include it
                                        if len(timestamp_str.split()) < 3:
                                            timestamp_str = f"{datetime.now().year} {timestamp_str}"
                                        timestamp = datetime.strptime(timestamp_str, "%Y %b %d %H:%M:%S")
                                        username = match.group(3)
                                        ip = match.group(4)
                                        attempts.append((timestamp, ip, username))
                                    except Exception as e:
                                        logger.debug(f"Error parsing timestamp: {e}")
        except Exception as e:
            logger.debug(f"Error parsing macOS logs: {e}")
            
        # Alternative: use log command
        if not attempts:
            try:
                cmd = ["log", "show", "--predicate", "'process == \"sshd\"'", "--last", "1h"]
                output = subprocess.check_output(cmd, universal_newlines=True)
                pattern = r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*sshd.*Failed password for (invalid user )?(\w+) from (\d+\.\d+\.\d+\.\d+)"
                for line in output.splitlines():
                    match = re.search(pattern, line)
                    if match:
                        try:
                            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                            username = match.group(3)
                            ip = match.group(4)
                            attempts.append((timestamp, ip, username))
                        except Exception as e:
                            logger.debug(f"Error parsing timestamp: {e}")
            except Exception as e:
                logger.debug(f"Error using log command: {e}")
        
        return attempts
    
    def _get_failed_attempts_windows(self):
        """Get failed SSH login attempts from Windows logs with username extraction."""
        attempts = []
        
        try:
            # On Windows, use PowerShell to query the Event Log
            cmd = [
                "powershell",
                "-Command",
                "Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4625} -MaxEvents 100 | "
                "Where-Object { $_.Message -like '*ssh*' } | "
                "ForEach-Object { $time = $_.TimeCreated; "
                "$user = ($_.Message -split 'Account Name:')[1] -split '\\r\\n' | Select-Object -First 1; "
                "$ip = ($_.Message -split 'Source Network Address:')[1] -split '\\r\\n' | Select-Object -First 1; "
                "if ($ip -match '\\d+\\.\\d+\\.\\d+\\.\\d+') { $ip.Trim() + ',' + $user.Trim() + ',' + $time.ToString('yyyy-MM-dd HH:mm:ss') } }"
            ]
            output = subprocess.check_output(cmd, universal_newlines=True)
            
            for line in output.splitlines():
                parts = line.split(',')
                if len(parts) == 3:
                    ip, username, timestamp_str = parts
                    try:
                        timestamp = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S")
                        attempts.append((timestamp, ip.strip(), username.strip()))
                    except Exception as e:
                        logger.debug(f"Error parsing timestamp: {e}")
        except Exception as e:
            logger.debug(f"Error querying Windows Event Log: {e}")
            
        # If PowerShell approach fails, try parsing the OpenSSH logs if they exist
        if not attempts:
            try:
                ssh_log = os.path.expandvars("%ProgramData%\\ssh\\logs\\sshd.log")
                if os.path.exists(ssh_log):
                    with open(ssh_log, 'r') as f:
                        for line in f:
                            if "Failed password" in line:
                                match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*Failed password for (invalid user )?(\w+) from (\d+\.\d+\.\d+\.\d+)", line)
                                if match:
                                    try:
                                        timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                                        username = match.group(3)
                                        ip = match.group(4)
                                        attempts.append((timestamp, ip, username))
                                    except Exception as e:
                                        logger.debug(f"Error parsing timestamp: {e}")
            except Exception as e:
                logger.debug(f"Error parsing OpenSSH logs: {e}")
        
        return attempts
    
    def get_ip_geo_info(self, ip):
        """Get geolocation information for an IP."""
        if not self.geo_enabled or not self.geoip_reader:
            return None
        
        try:
            response = self.geoip_reader.city(ip)
            return {
                'country': response.country.name,
                'country_code': response.country.iso_code,
                'city': response.city.name,
                'latitude': response.location.latitude,
                'longitude': response.location.longitude,
                'timezone': response.location.time_zone
            }
        except Exception as e:
            logger.debug(f"Error getting geolocation for IP {ip}: {e}")
            return None
    
    def get_reverse_dns(self, ip):
        """Get reverse DNS information for an IP."""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return None
    
    def block_ip(self, ip, duration_minutes=None):
        """Block an IP address using the system's firewall with expiration time."""
        if self.is_whitelisted(ip):
            logger.info(f"Skipping block for whitelisted IP: {ip}")
            return
        
        if ip in self.blocked_ips:
            logger.info(f"IP {ip} is already blocked")
            return
        
        # Calculate expiry time
        if duration_minutes is None:
            duration_minutes = self.block_duration
        
        expiry_time = datetime.now() + timedelta(minutes=duration_minutes)
        self.blocked_ips[ip] = expiry_time
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would block IP: {ip} until {expiry_time}")
            return
        
        # Platform-specific blocking
        if self.platform.startswith('linux'):
            self._block_ip_linux(ip)
        elif self.platform == 'darwin':
            self._block_ip_macos(ip)
        elif self.platform == 'win32':
            self._block_ip_windows(ip)
        else:
            logger.error(f"Unsupported platform for blocking: {self.platform}")
            return
        
        # Log the block to audit file
        self._log_block(ip, expiry_time, duration_minutes)
        
        # Save state to persist across reboots
        self._save_state()
    
    def _block_ip_linux(self, ip):
        """Block an IP address on Linux using iptables or ufw."""
        try:
            # Try UFW first (easier to use and more common)
            ufw_cmd = ["ufw", "deny", f"from {ip}", "to", "any", "port", "22"]
            subprocess.run(ufw_cmd, check=True, stderr=subprocess.DEVNULL)
            logger.info(f"Blocked IP {ip} using UFW")
            return
        except Exception:
            # If UFW fails, try iptables
            try:
                # Check if iptables rule already exists
                check_cmd = ["iptables", "-C", "INPUT", "-s", ip, "-p", "tcp", "--dport", "22", "-j", "DROP"]
                result = subprocess.run(check_cmd, stderr=subprocess.DEVNULL)
                
                if result.returncode != 0:  # Rule doesn't exist, add it
                    cmd = ["iptables", "-A", "INPUT", "-s", ip, "-p", "tcp", "--dport", "22", "-j", "DROP"]
                    subprocess.run(cmd, check=True)
                    logger.info(f"Blocked IP {ip} using iptables")
                else:
                    logger.info(f"IP {ip} is already blocked with iptables")
            except Exception as e:
                try:
                    # Last resort: try nftables
                    cmd = ["nft", "add", "rule", "inet", "filter", "input", f"ip saddr {ip}", "tcp", "dport", "22", "drop"]
                    subprocess.run(cmd, check=True)
                    logger.info(f"Blocked IP {ip} using nftables")
                except Exception as e2:
                    logger.error(f"Failed to block IP {ip}: {e2}")
    
    def _block_ip_macos(self, ip):
        """Block an IP address on macOS using the pf firewall."""
        try:
            # Create or append to a table for blocked IPs
            pf_table = "/etc/pf.anchors/sshdefender"
            
            # Check if the table file exists, create it if not
            if not os.path.exists(pf_table):
                with open(pf_table, 'w') as f:
                    f.write("table <sshblocklist> persist\n")
                    f.write("block in quick on any from <sshblocklist> to any port 22\n")
                
                # Load the anchor
                subprocess.run(["pfctl", "-e"], stderr=subprocess.DEVNULL)
                subprocess.run(["pfctl", "-a", "sshdefender", "-f", pf_table], check=True)
            
            # Add the IP to the table
            subprocess.run(["pfctl", "-t", "sshblocklist", "-T", "add", ip], check=True)
            logger.info(f"Blocked IP {ip} using pf firewall")
        except Exception as e:
            logger.error(f"Failed to block IP {ip}: {e}")
    
        def _block_ip_windows(self, ip):
        """Block an IP address on Windows using Windows Firewall."""
        try:
            # Create a firewall rule to block the IP
            rule_name = f"SSH Defender - Block {ip}"
            
            # Check if rule already exists
            check_cmd = [
                "powershell",
                "-Command",
                f"Get-NetFirewallRule -DisplayName '{rule_name}' 2>$null"
            ]
            result = subprocess.run(check_cmd, stdout=subprocess.PIPE)
            
            if not result.stdout.strip():  # Rule doesn't exist
                cmd = [
                    "powershell",
                    "-Command",
                    f"New-NetFirewallRule -DisplayName '{rule_name}' -Direction Inbound -Action Block "
                    f"-RemoteAddress {ip} -Protocol TCP -LocalPort 22 -Enabled True"
                ]
                subprocess.run(cmd, check=True)
                logger.info(f"Blocked IP {ip} using Windows Firewall")
            else:
                logger.info(f"IP {ip} is already blocked with Windows Firewall")
        except Exception as e:
            logger.error(f"Failed to block IP {ip}: {e}")
    
    def unblock_ip(self, ip):
        """Unblock an IP address."""
        if ip not in self.blocked_ips:
            logger.info(f"IP {ip} is not in the block list")
            return
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would unblock IP: {ip}")
            del self.blocked_ips[ip]
            return
        
        # Platform-specific unblocking
        if self.platform.startswith('linux'):
            self._unblock_ip_linux(ip)
        elif self.platform == 'darwin':
            self._unblock_ip_macos(ip)
        elif self.platform == 'win32':
            self._unblock_ip_windows(ip)
        else:
            logger.error(f"Unsupported platform for unblocking: {self.platform}")
            return
        
        # Remove from blocked IPs
        del self.blocked_ips[ip]
        
        # Log the unblock
        self._log_unblock(ip)
        
        # Save state
        self._save_state()
    
    def _unblock_ip_linux(self, ip):
        """Unblock an IP address on Linux."""
        try:
            # Try UFW first
            ufw_cmd = ["ufw", "delete", "deny", f"from {ip}", "to", "any", "port", "22"]
            subprocess.run(ufw_cmd, check=True, stderr=subprocess.DEVNULL)
            logger.info(f"Unblocked IP {ip} using UFW")
            return
        except Exception:
            # If UFW fails, try iptables
            try:
                cmd = ["iptables", "-D", "INPUT", "-s", ip, "-p", "tcp", "--dport", "22", "-j", "DROP"]
                subprocess.run(cmd, check=True)
                logger.info(f"Unblocked IP {ip} using iptables")
            except Exception as e:
                try:
                    # Last resort: try nftables
                    cmd = ["nft", "delete", "rule", "inet", "filter", "input", f"ip saddr {ip}", "tcp", "dport", "22", "drop"]
                    subprocess.run(cmd, check=True)
                    logger.info(f"Unblocked IP {ip} using nftables")
                except Exception as e2:
                    logger.error(f"Failed to unblock IP {ip}: {e2}")
    
    def _unblock_ip_macos(self, ip):
        """Unblock an IP address on macOS."""
        try:
            # Remove the IP from the pf table
            subprocess.run(["pfctl", "-t", "sshblocklist", "-T", "delete", ip], check=True)
            logger.info(f"Unblocked IP {ip} using pf firewall")
        except Exception as e:
            logger.error(f"Failed to unblock IP {ip}: {e}")
    
    def _unblock_ip_windows(self, ip):
        """Unblock an IP address on Windows."""
        try:
            # Remove the firewall rule
            rule_name = f"SSH Defender - Block {ip}"
            cmd = [
                "powershell",
                "-Command",
                f"Remove-NetFirewallRule -DisplayName '{rule_name}' -ErrorAction SilentlyContinue"
            ]
            subprocess.run(cmd, check=True)
            logger.info(f"Unblocked IP {ip} using Windows Firewall")
        except Exception as e:
            logger.error(f"Failed to unblock IP {ip}: {e}")
    
    def _log_block(self, ip, expiry_time, duration_minutes):
        """Log block action to the audit file."""
        if not hasattr(self, 'block_log_path') or not self.block_log_path:
            return
        
        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(self.block_log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            geo_info = self.get_ip_geo_info(ip) if self.geo_enabled else None
            hostname = self.get_reverse_dns(ip) or "Unknown"
            
            location = "Unknown"
            if geo_info:
                city = geo_info.get('city', 'Unknown City')
                country = geo_info.get('country', 'Unknown Country')
                location = f"{city}, {country}"
            
            log_entry = (
                f"{timestamp} - BLOCK - IP: {ip} - Hostname: {hostname} - "
                f"Location: {location} - Duration: {duration_minutes} min - "
                f"Expires: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            
            with open(self.block_log_path, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to log block to audit file: {e}")
    
    def _log_unblock(self, ip):
        """Log unblock action to the audit file."""
        if not hasattr(self, 'block_log_path') or not self.block_log_path:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} - UNBLOCK - IP: {ip}\n"
            
            with open(self.block_log_path, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to log unblock to audit file: {e}")
    
    def check_expired_blocks(self):
        """Check for and remove expired IP blocks."""
        now = datetime.now()
        expired_ips = [ip for ip, expiry in self.blocked_ips.items() if expiry <= now]
        
        for ip in expired_ips:
            logger.info(f"Block for IP {ip} has expired, removing")
            self.unblock_ip(ip)
    
    def detect_distributed_attacks(self):
        """Detect distributed SSH attacks based on patterns."""
        now = datetime.now()
        window_start = now - timedelta(minutes=60)  # Look at the last hour
        results = []
        
        # Check for username-based clustering
        for username, ips in self.user_targets.items():
            if len(ips) >= self.username_threshold:
                logger.warning(f"Detected distributed attack targeting user '{username}' from {len(ips)} different IPs")
                
                # Get more details about the attacking IPs
                ip_details = []
                for ip in ips:
                    geo_info = self.get_ip_geo_info(ip) if self.geo_enabled else None
                    hostname = self.get_reverse_dns(ip) or "Unknown"
                    
                    location = "Unknown"
                    if geo_info:
                        city = geo_info.get('city', 'Unknown City')
                        country = geo_info.get('country', 'Unknown Country')
                        location = f"{city}, {country}"
                    
                    ip_details.append({
                        'ip': ip,
                        'hostname': hostname,
                        'location': location,
                        'target': username
                    })
                
                results.append({
                    'type': 'username_cluster',
                    'username': username,
                    'ips': ips,
                    'ip_details': ip_details
                })
        
        # TODO: Add more distributed attack detection methods
        # - Timing patterns
        # - Password similarity
        # - Geo-impossible travel
        
        return results
    
    def send_slack_alert(self, ip, attempts_count, is_distributed=False, distributed_info=None):
        """Send a Slack alert about blocked IP."""
        if not hasattr(self, 'slack_enabled') or not self.slack_enabled or not self.alerts_enabled:
            return
        
        if not hasattr(self, 'slack_webhook') or not self.slack_webhook:
            logger.warning("Slack webhook URL not configured, can't send alert")
            return
        
        try:
            # Get additional info about the IP
            geo_info = self.get_ip_geo_info(ip) if self.geo_enabled else None
            hostname = self.get_reverse_dns(ip) or "Unknown"
            
            location = "Unknown"
            if geo_info:
                city = geo_info.get('city', 'Unknown City')
                country = geo_info.get('country', 'Unknown Country')
                location = f"{city}, {country}"
            
            # Format message based on whether it's a distributed attack or not
            if is_distributed:
                title = ":rotating_light: *DISTRIBUTED SSH ATTACK DETECTED* :rotating_light:"
                fields = [
                    {
                        "title": "Attack Type",
                        "value": "Distributed brute-force",
                        "short": True
                    },
                    {
                        "title": "Target",
                        "value": distributed_info.get('username', 'Unknown'),
                        "short": True
                    },
                    {
                        "title": "IPs Involved",
                        "value": str(len(distributed_info.get('ips', []))),
                        "short": True
                    },
                    {
                        "title": "Time Period",
                        "value": "Last 60 minutes",
                        "short": True
                    }
                ]
                
                # Add details about some of the IPs
                ip_text = ""
                for i, ip_detail in enumerate(distributed_info.get('ip_details', [])[:5]):
                    ip_text += f"• {ip_detail['ip']} ({ip_detail['location']})\n"
                
                if len(distributed_info.get('ip_details', [])) > 5:
                    ip_text += f"...and {len(distributed_info.get('ip_details', [])) - 5} more"
                
                fields.append({
                    "title": "Sample IPs",
                    "value": ip_text,
                    "short": False
                })
            else:
                title = ":lock: *SSH BRUTE-FORCE ATTEMPT BLOCKED* :lock:"
                fields = [
                    {
                        "title": "IP Address",
                        "value": ip,
                        "short": True
                    },
                    {
                        "title": "Hostname",
                        "value": hostname,
                        "short": True
                    },
                    {
                        "title": "Location",
                        "value": location,
                        "short": True
                    },
                    {
                        "title": "Failed Attempts",
                        "value": str(attempts_count),
                        "short": True
                    }
                ]
                
                # Add expiry info if available
                if ip in self.blocked_ips:
                    expiry = self.blocked_ips[ip]
                    fields.append({
                        "title": "Blocked Until",
                        "value": expiry.strftime("%Y-%m-%d %H:%M:%S"),
                        "short": True
                    })
            
            # Create the message payload
            payload = {
                "text": title,
                "attachments": [
                    {
                        "color": "#FF0000" if is_distributed else "#FFA500",
                        "fields": fields,
                        "footer": "SSH Defender",
                        "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                        "ts": int(time.time())
                    }
                ]
            }
            
            # Send to Slack
            webhook = WebhookClient(self.slack_webhook)
            response = webhook.send(json.dumps(payload))
            
            if response.status_code != 200:
                logger.error(f"Failed to send Slack alert: {response.body}")
            else:
                logger.info("Slack alert sent successfully")
        
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
    
    def send_email_alert(self, ip, attempts_count, username, is_distributed=False, distributed_info=None):
        """Send an email alert about blocked IP."""
        if not hasattr(self, 'email_enabled') or not self.email_enabled or not self.alerts_enabled:
            return
        
        if not all([hasattr(self, attr) for attr in ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'email_from', 'email_to']]):
            logger.warning("Email configuration incomplete, can't send alert")
            return
        
        try:
            # Get additional info about the IP
            geo_info = self.get_ip_geo_info(ip) if self.geo_enabled else None
            hostname = self.get_reverse_dns(ip) or "Unknown"
            
            location = "Unknown"
            if geo_info:
                city = geo_info.get('city', 'Unknown City')
                country = geo_info.get('country', 'Unknown Country')
                location = f"{city}, {country}"
            
            # Create the email message
            msg = MIMEMultipart('alternative')
            
            if is_distributed:
                msg['Subject'] = "SECURITY ALERT: Distributed SSH Attack Detected"
                alert_type = "Distributed Attack"
                header_color = "FF0000"  # Red for distributed attacks
                message = f"A distributed SSH brute-force attack has been detected targeting the user '{distributed_info.get('username', 'Unknown')}' from multiple IPs."
                action = f"All {len(distributed_info.get('ips', []))} IPs have been blocked for {self.block_duration} minutes."
                
                # Create related IPs list for template
                related_ips = []
                for ip_detail in distributed_info.get('ip_details', []):
                    related_ips.append({
                        'ip': ip_detail['ip'],
                        'target': ip_detail['target'],
                        'pattern': f"From {ip_detail['location']}"
                    })
                
                # Create HTML version from template
                html = HTML_EMAIL_TEMPLATE.replace("{{ header_color }}", header_color)
                html = html.replace("{{ alert_type }}", alert_type)
                html = html.replace("{{ message }}", message)
                html = html.replace("{{ ip }}", "Multiple (see below)")
                html = html.replace("{{ hostname }}", "Multiple")
                html = html.replace("{{ location }}", "Multiple Locations")
                html = html.replace("{{ attempts }}", "Multiple")
                html = html.replace("{{ time_period }}", "Last 60 minutes")
                html = html.replace("{{ users }}", distributed_info.get('username', 'Unknown'))
                html = html.replace("{{ action }}", action)
                html = html.replace("{{ timestamp }}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                html = html.replace("{{ is_distributed }}", "true")
                
                # Add related IPs to the template
                related_ips_html = ""
                for i, ip_info in enumerate(related_ips):
                    related_ips_html += f'<tr><td>{ip_info["ip"]}</td><td>{ip_info["target"]}</td><td>{ip_info["pattern"]}</td></tr>\n'
                
                html = html.replace("{% for ip_info in related_ips %}\n                <tr><td>{{ ip_info.ip }}</td><td>{{ ip_info.target }}</td><td>{{ ip_info.pattern }}</td></tr>\n                {% endfor %}", related_ips_html)
                
            else:
                msg['Subject'] = f"SECURITY ALERT: SSH Brute-Force Attempt from {ip}"
                alert_type = "Alert"
                header_color = "FFA500"  # Orange for regular alerts
                message = f"An SSH brute-force attempt has been detected and blocked. The attacker made {attempts_count} failed login attempts."
                action = f"IP {ip} has been blocked for {self.block_duration} minutes."
                
                if ip in self.blocked_ips:
                    unblock_info = f"Block will expire automatically at {self.blocked_ips[ip].strftime('%Y-%m-%d %H:%M:%S')}."
                else:
                    unblock_info = ""
                
                # Create HTML version from template
                html = HTML_EMAIL_TEMPLATE.replace("{{ header_color }}", header_color)
                html = html.replace("{{ alert_type }}", alert_type)
                html = html.replace("{{ message }}", message)
                html = html.replace("{{ ip }}", ip)
                html = html.replace("{{ hostname }}", hostname)
                html = html.replace("{{ location }}", location)
                html = html.replace("{{ attempts }}", str(attempts_count))
                html = html.replace("{{ time_period }}", f"Last {self.time_window} minutes")
                html = html.replace("{{ users }}", username or "Unknown")
                html = html.replace("{{ action }}", action)
                html = html.replace("{{ unblock_info }}", unblock_info)
                html = html.replace("{{ timestamp }}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                # Remove distributed attack section
                html = html.replace("{% if is_distributed %}\n            <h3>Distributed Attack Information:</h3>\n            <p>This appears to be part of a coordinated attack from multiple sources.</p>\n            <table>\n                <tr><th>Related IPs</th><th>Common Target</th><th>Pattern</th></tr>\n                {% for ip_info in related_ips %}\n                <tr><td>{{ ip_info.ip }}</td><td>{{ ip_info.target }}</td><td>{{ ip_info.pattern }}</td></tr>\n                {% endfor %}\n            </table>\n            {% endif %}", "")
            
            # Attach HTML part
            part = MIMEText(html, 'html')
            msg.attach(part)
            
            # Sender and recipients
            msg['From'] = self.email_from
            msg['To'] = ", ".join(self.email_to)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info("Email alert sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
    
    def process_attempts(self):
        """Process failed login attempts and block IPs that exceed the threshold."""
        # Check for and remove expired blocks
        self.check_expired_blocks()
        
        # Get recent failed attempts
        attempts = self.get_failed_attempts()
        
        # If no logs found, notify user
        if not attempts:
            logger.warning("No SSH login attempts found in logs. Make sure the SSH service is running and logging is enabled.")
            if self.platform == 'win32':
                logger.info("On Windows, ensure OpenSSH Server is installed as an optional feature.")
            return
        
        # Process attempts
        now = datetime.now()
        window_start = now - timedelta(minutes=self.time_window)
        
        # Update failed attempts dictionary and user targets
        for timestamp, ip, username in attempts:
            if timestamp >= window_start:
                self.failed_attempts[ip].append((timestamp, username))
                if username:  # Track for distributed attack detection
                    self.user_targets[username].add(ip)
        
        # Check for IPs that exceed the threshold
        for ip, attempts_data in self.failed_attempts.items():
            # Only consider attempts within the time window
            recent_attempts = [data for data in attempts_data if data[0] >= window_start]
            
            if len(recent_attempts) >= self.threshold and ip not in self.blocked_ips and not self.is_whitelisted(ip):
                logger.warning(f"IP {ip} exceeded threshold with {len(recent_attempts)} failed attempts in the last {self.time_window} minutes")
                
                # Get the usernames targeted
                usernames = set(data[1] for data in recent_attempts if data[1])
                username_str = ", ".join(usernames) if usernames else "Unknown"
                
                # Block the IP
                self.block_ip(ip)
                
                # Send alerts
                if self.alerts_enabled:
                    if hasattr(self, 'slack_enabled') and self.slack_enabled:
                        self.send_slack_alert(ip, len(recent_attempts))
                    
                    if hasattr(self, 'email_enabled') and self.email_enabled:
                        self.send_email_alert(ip, len(recent_attempts), username_str)
        
        # Check for distributed attacks if enabled
        if self.distributed_detection:
            distributed_attacks = self.detect_distributed_attacks()
            
            for attack in distributed_attacks:
                # Send alerts for distributed attacks
                if self.alerts_enabled:
                    if hasattr(self, 'slack_enabled') and self.slack_enabled:
                        self.send_slack_alert(attack['ips'][0], 0, True, attack)
                    
                    if hasattr(self, 'email_enabled') and self.email_enabled:
                        self.send_email_alert(attack['ips'][0], 0, attack['username'], True, attack)
                
                # Block all IPs involved
                for ip in attack['ips']:
                    if ip not in self.blocked_ips and not self.is_whitelisted(ip):
                        self.block_ip(ip)
    
    def monitor(self, interval=60):
        """Monitor SSH login attempts continuously."""
        logger.info(f"Starting Advanced SSH Brute-Force Detector with threshold of {self.threshold} failed attempts in {self.time_window} minute(s)")
        if self.whitelist:
            logger.info(f"Whitelisted IPs: {', '.join(self.whitelist)}")
        if self.cidr_whitelist:
            logger.info(f"Whitelisted CIDR ranges: {', '.join(str(cidr) for cidr in self.cidr_whitelist)}")
        
        try:
            while True:
                self.process_attempts()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")

def generate_sample_config():
    """Generate a sample configuration file."""
    config = {
        "general": {
            "threshold": 5,
            "time_window": 5,
            "block_duration": 1440,  # 24 hours in minutes
            "block_log": "/var/log/ssh_defender_blocks.log",
            "persistent_state": "/var/lib/ssh-defender/state.json"
        },
        "alerts": {
            "slack": {
                "enabled": False,
                "webhook_url": "https://hooks.slack.com/services/YOUR_WEBHOOK_URL",
                "channel": "#security-alerts"
            },
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True,
                "username": "your-email@gmail.com",
                "password": "your-app-password",
                "from_address": "your-email@gmail.com",
                "to_addresses": [
                    "admin@example.com",
                    "security@example.com"
                ]
            }
        },
        "whitelist": {
            "ips": [
                "127.0.0.1",
                "192.168.1.0/24",
                "10.0.0.1"
            ],
            "emergency_unblock_key": "your-secure-key"
        },
        "distributed_detection": {
            "enabled": True,
            "username_threshold": 5,
            "timing_sensitivity": "medium",
            "geo_detection": True
        }
    }
    
    return yaml.dump(config, default_flow_style=False)

def main():
    """Main function to parse arguments and start the SSH defender."""
    parser = argparse.ArgumentParser(description='Advanced SSH Brute-Force Detector with Threat Mitigation')
    parser.add_argument('--threshold', type=int,
                        help=f'Number of failed attempts before blocking an IP (default: {DEFAULT_THRESHOLD})')
    parser.add_argument('--time-window', type=int,
                        help=f'Time window in minutes to consider for failed attempts (default: {DEFAULT_TIME_WINDOW})')
    parser.add_argument('--block-duration', type=int,
                        help=f'Duration in minutes to block IPs (default: {DEFAULT_BLOCK_DURATION})')
    parser.add_argument('--whitelist', nargs='+',
                        help='List of IPs to whitelist (space-separated)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Do not actually block IPs, just log what would be done')
    parser.add_argument('--interval', type=int, default=60,
                        help='Interval in seconds between log checks (default: 60)')
    parser.add_argument('--once', action='store_true',
                        help='Run once and exit instead of continuous monitoring')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--config',
                        help='Path to configuration file')
    parser.add_argument('--generate-config', action='store_true',
                        help='Generate a sample configuration file')
    parser.add_argument('--no-alerts', action='store_true',
                        help='Disable all alert notifications')
    parser.add_argument('--no-geo', action='store_true',
                        help='Disable geolocation features')
    parser.add_argument('--distributed-detection', action='store_true',
                        help='Force enable distributed attack detection')
    parser.add_argument('--test-alerts', action='store_true',
                        help='Test alert configurations without actual blocking')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Generate sample configuration if requested
    if args.generate_config:
        config_yaml = generate_sample_config()
        print(config_yaml)
        print("\nSave this to a file and use with --config option.")
        return 0
    
    # Load configuration file if specified
    config = None
    if args.config:
        try:
            with open(args.config, 'r') as f:
                if args.config.endswith('.yaml') or args.config.endswith('.yml'):
                    config = yaml.safe_load(f)
                elif args.config.endswith('.json'):
                    config = json.load(f)
                else:
                    logger.error("Unsupported configuration file format. Use .yaml, .yml, or .json")
                    return 1
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}")
            return 1
    
    # If no config file specified, try platform default
    if not config and not args.generate_config:
        default_config = DEFAULT_CONFIG_PATHS.get(sys.platform)
        if default_config and os.path.exists(default_config):
            try:
                with open(default_config, 'r') as f:
                    if default_config.endswith('.yaml') or default_config.endswith('.yml'):
                        config = yaml.safe_load(f)
                    elif default_config.endswith('.json'):
                        config = json.load(f)
                    else:
                        logger.info(f"Found default config but format not supported: {default_config}")
            except Exception as e:
                logger.debug(f"Error loading default configuration: {e}")
    
    # Create kwargs for SSH defender
    kwargs = {
        'dry_run': args.dry_run,
        'alerts_enabled': not args.no_alerts,
        'geo_enabled': not args.no_geo and GEOIP_AVAILABLE
    }
    
    if args.threshold is not None:
        kwargs['threshold'] = args.threshold
    
    if args.time_window is not None:
        kwargs['time_window'] = args.time_window
    
    if args.block_duration is not None:
        kwargs['block_duration'] = args.block_duration
    
    if args.whitelist:
        kwargs['whitelist'] = args.whitelist
    
    if args.distributed_detection:
        kwargs['distributed_detection'] = True
    
    # Create SSH defender
    defender = AdvancedSSHDefender(config, **kwargs)
    
    # Test alerts if requested
    if args.test_alerts:
        logger.info("Testing alert configurations...")
        test_ip = "192.0.2.1"  # TEST-NET-1 IP for documentation
        
        if hasattr(defender, 'slack_enabled') and defender.slack_enabled:
            defender.send_slack_alert(test_ip, 10)
            logger.info("Slack alert test sent.")
        
        if hasattr(defender, 'email_enabled') and defender.email_enabled:
            defender.send_email_alert(test_ip, 10, "admin")
            logger.info("Email alert test sent.")
        
                    # Test distributed attack alert
            if defender.distributed_detection:
                test_distributed = {
                    'type': 'username_cluster',
                    'username': 'admin',
                    'ips': [test_ip, "192.0.2.2", "192.0.2.3"],
                    'ip_details': [
                        {'ip': test_ip, 'hostname': 'test1.example.com', 'location': 'Test City, Test Country', 'target': 'admin'},
                        {'ip': '192.0.2.2', 'hostname': 'test2.example.com', 'location': 'Another City, Another Country', 'target': 'admin'},
                        {'ip': '192.0.2.3', 'hostname': 'test3.example.com', 'location': 'Third City, Third Country', 'target': 'admin'}
                    ]
                }
                
                if hasattr(defender, 'slack_enabled') and defender.slack_enabled:
                    defender.send_slack_alert(test_ip, 0, True, test_distributed)
                    logger.info("Distributed attack Slack alert test sent.")
                
                if hasattr(defender, 'email_enabled') and defender.email_enabled:
                    defender.send_email_alert(test_ip, 0, 'admin', True, test_distributed)
                    logger.info("Distributed attack email alert test sent.")
        
        return 0
    
    if args.once:
        # Process attempts once and exit
        defender.process_attempts()
    else:
        # Continuously monitor
        defender.monitor(interval=args.interval)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())