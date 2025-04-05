#!/usr/bin/env python3
"""
SSH Brute-Force Detector with Auto-Block (Level 1)
This script monitors system logs for SSH login attempts and blocks IPs that exceed a threshold of failed attempts.
Cross-platform support for Linux, macOS, and Windows.
"""

import argparse
import os
import re
import subprocess
import sys
import time
import logging
import ipaddress
from datetime import datetime, timedelta
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_THRESHOLD = 5  # Default number of failed attempts before blocking
DEFAULT_TIME_WINDOW = 5  # Default time window in minutes to consider for failed attempts
DEFAULT_BLOCK_DURATION = 60  # Default block duration in minutes

class SSHDefender:
    """Main class for detecting and blocking SSH brute-force attacks."""
    
    def __init__(self, threshold=DEFAULT_THRESHOLD, time_window=DEFAULT_TIME_WINDOW, 
                 block_duration=DEFAULT_BLOCK_DURATION, whitelist=None, dry_run=False):
        """
        Initialize the SSH defender.
        
        Args:
            threshold (int): Number of failed attempts before blocking an IP
            time_window (int): Time window in minutes to consider for failed attempts
            block_duration (int): Duration in minutes to block IPs
            whitelist (list): List of IPs to whitelist
            dry_run (bool): If True, don't actually block IPs
        """
        self.threshold = threshold
        self.time_window = time_window
        self.block_duration = block_duration
        self.whitelist = set()
        self.dry_run = dry_run
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = set()
        
        # Add whitelisted IPs
        if whitelist:
            for ip in whitelist:
                try:
                    ipaddress.ip_address(ip)  # Validate IP
                    self.whitelist.add(ip)
                except ValueError:
                    logger.warning(f"Invalid IP in whitelist: {ip}")
        
        # Detect platform
        self.platform = sys.platform
        logger.info(f"Detected platform: {self.platform}")
        
        # Check for root/admin privileges
        self._check_privileges()
    
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
    
    def get_failed_attempts(self):
        """Parse logs to find failed SSH login attempts."""
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
        """Get failed SSH login attempts from Linux logs."""
        attempts = []
        
        # Try using journalctl first (systemd-based systems)
        try:
            cmd = ["journalctl", "-u", "ssh", "-n", "1000", "--no-pager"]
            output = subprocess.check_output(cmd, universal_newlines=True)
            
            # Extract failed password attempts
            pattern = r"(\w+\s+\d+\s+\d+:\d+:\d+).*sshd.*Failed password for .* from (\d+\.\d+\.\d+\.\d+)"
            for line in output.splitlines():
                match = re.search(pattern, line)
                if match:
                    try:
                        timestamp_str = match.group(1)
                        # Add year as journalctl might not include it
                        if len(timestamp_str.split()) < 3:
                            timestamp_str = f"{datetime.now().year} {timestamp_str}"
                        timestamp = datetime.strptime(timestamp_str, "%Y %b %d %H:%M:%S")
                        ip = match.group(2)
                        attempts.append((timestamp, ip))
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
                                    match = re.search(r"(\w+\s+\d+\s+\d+:\d+:\d+).*sshd.*Failed password for .* from (\d+\.\d+\.\d+\.\d+)", line)
                                    if match:
                                        try:
                                            timestamp_str = match.group(1)
                                            # Add year as auth.log might not include it
                                            if len(timestamp_str.split()) < 3:
                                                timestamp_str = f"{datetime.now().year} {timestamp_str}"
                                            timestamp = datetime.strptime(timestamp_str, "%Y %b %d %H:%M:%S")
                                            ip = match.group(2)
                                            attempts.append((timestamp, ip))
                                        except Exception as e:
                                            logger.debug(f"Error parsing timestamp: {e}")
            except Exception as e:
                logger.debug(f"Error parsing auth.log: {e}")
        
        return attempts
    
    def _get_failed_attempts_macos(self):
        """Get failed SSH login attempts from macOS logs."""
        attempts = []
        
        try:
            # macOS uses system.log or secure.log
            log_files = ["/var/log/system.log", "/var/log/secure.log"]
            for log_file in log_files:
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        for line in f:
                            if "sshd" in line and "Failed password" in line:
                                match = re.search(r"(\w+\s+\d+\s+\d+:\d+:\d+).*sshd.*Failed password for .* from (\d+\.\d+\.\d+\.\d+)", line)
                                if match:
                                    try:
                                        timestamp_str = match.group(1)
                                        # Add year as log might not include it
                                        if len(timestamp_str.split()) < 3:
                                            timestamp_str = f"{datetime.now().year} {timestamp_str}"
                                        timestamp = datetime.strptime(timestamp_str, "%Y %b %d %H:%M:%S")
                                        ip = match.group(2)
                                        attempts.append((timestamp, ip))
                                    except Exception as e:
                                        logger.debug(f"Error parsing timestamp: {e}")
        except Exception as e:
            logger.debug(f"Error parsing macOS logs: {e}")
            
        # Alternative: use log command
        if not attempts:
            try:
                cmd = ["log", "show", "--predicate", "'process == \"sshd\"'", "--last", "1h"]
                output = subprocess.check_output(cmd, universal_newlines=True)
                pattern = r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*sshd.*Failed password for .* from (\d+\.\d+\.\d+\.\d+)"
                for line in output.splitlines():
                    match = re.search(pattern, line)
                    if match:
                        try:
                            timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                            ip = match.group(2)
                            attempts.append((timestamp, ip))
                        except Exception as e:
                            logger.debug(f"Error parsing timestamp: {e}")
            except Exception as e:
                logger.debug(f"Error using log command: {e}")
        
        return attempts
    
    def _get_failed_attempts_windows(self):
        """Get failed SSH login attempts from Windows logs."""
        attempts = []
        
        try:
            # On Windows, use PowerShell to query the Event Log
            # This looks for Event ID 4625 (failed logon) and filters by SSH
            cmd = [
                "powershell",
                "-Command",
                "Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4625} -MaxEvents 100 | "
                "Where-Object { $_.Message -like '*ssh*' } | "
                "ForEach-Object { $time = $_.TimeCreated; $ip = ($_.Message -split 'Source Network Address:')[1] -split '\\r\\n' | Select-Object -First 1; "
                "if ($ip -match '\\d+\\.\\d+\\.\\d+\\.\\d+') { $ip.Trim() + ',' + $time.ToString('yyyy-MM-dd HH:mm:ss') } }"
            ]
            output = subprocess.check_output(cmd, universal_newlines=True)
            
            for line in output.splitlines():
                if ',' in line:
                    ip, timestamp_str = line.split(',', 1)
                    try:
                        timestamp = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S")
                        attempts.append((timestamp, ip.strip()))
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
                                match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*Failed password for .* from (\d+\.\d+\.\d+\.\d+)", line)
                                if match:
                                    try:
                                        timestamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                                        ip = match.group(2)
                                        attempts.append((timestamp, ip))
                                    except Exception as e:
                                        logger.debug(f"Error parsing timestamp: {e}")
            except Exception as e:
                logger.debug(f"Error parsing OpenSSH logs: {e}")
        
        return attempts
    
    def block_ip(self, ip):
        """Block an IP address using the system's firewall."""
        if ip in self.whitelist:
            logger.info(f"Skipping block for whitelisted IP: {ip}")
            return
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would block IP: {ip}")
            return
        
        if self.platform.startswith('linux'):
            self._block_ip_linux(ip)
        elif self.platform == 'darwin':
            self._block_ip_macos(ip)
        elif self.platform == 'win32':
            self._block_ip_windows(ip)
        else:
            logger.error(f"Unsupported platform for blocking: {self.platform}")
    
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
    
    def process_attempts(self):
        """Process failed login attempts and block IPs that exceed the threshold."""
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
        
        # Update failed attempts dictionary
        for timestamp, ip in attempts:
            if timestamp >= window_start:
                self.failed_attempts[ip].append(timestamp)
        
        # Check for IPs that exceed the threshold
        for ip, timestamps in self.failed_attempts.items():
            # Only consider attempts within the time window
            recent_attempts = [ts for ts in timestamps if ts >= window_start]
            
            if len(recent_attempts) >= self.threshold and ip not in self.blocked_ips:
                logger.warning(f"IP {ip} exceeded threshold with {len(recent_attempts)} failed attempts in the last {self.time_window} minutes")
                self.block_ip(ip)
                self.blocked_ips.add(ip)
    
    def monitor(self, interval=60):
        """Monitor SSH login attempts continuously."""
        logger.info(f"Starting SSH Brute-Force Detector with threshold of {self.threshold} failed attempts in {self.time_window} minute(s)")
        if self.whitelist:
            logger.info(f"Whitelisted IPs: {', '.join(self.whitelist)}")
        
        try:
            while True:
                self.process_attempts()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")

def main():
    """Main function to parse arguments and start the SSH defender."""
    parser = argparse.ArgumentParser(description='SSH Brute-Force Detector with Auto-Block')
    parser.add_argument('--threshold', type=int, default=DEFAULT_THRESHOLD,
                        help=f'Number of failed attempts before blocking an IP (default: {DEFAULT_THRESHOLD})')
    parser.add_argument('--time-window', type=int, default=DEFAULT_TIME_WINDOW,
                        help=f'Time window in minutes to consider for failed attempts (default: {DEFAULT_TIME_WINDOW})')
    parser.add_argument('--block-duration', type=int, default=DEFAULT_BLOCK_DURATION,
                        help=f'Duration in minutes to block IPs (default: {DEFAULT_BLOCK_DURATION})')
    parser.add_argument('--whitelist', nargs='+', default=[],
                        help='List of IPs to whitelist (space-separated)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Do not actually block IPs, just log what would be done')
    parser.add_argument('--interval', type=int, default=60,
                        help='Interval in seconds between log checks (default: 60)')
    parser.add_argument('--once', action='store_true',
                        help='Run once and exit instead of continuous monitoring')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Create SSH defender
    defender = SSHDefender(
        threshold=args.threshold,
        time_window=args.time_window,
        block_duration=args.block_duration,
        whitelist=args.whitelist,
        dry_run=args.dry_run
    )
    
    if args.once:
        # Process attempts once and exit
        defender.process_attempts()
    else:
        # Continuously monitor
        defender.monitor(interval=args.interval)

if __name__ == "__main__":
    main()
