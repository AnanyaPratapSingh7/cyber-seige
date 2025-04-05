# Problem 4: SSH Brute-Force Detector with Auto-Block & Advanced Threat Mitigation

This problem involves developing a cross-platform security solution to detect and mitigate SSH brute-force attacks.

## Overview of Levels

1. **Level 1: SSH Brute-Force Detector with Auto-Block** - Basic SSH brute-force detection and IP blocking
2. **Level 2: Advanced Threat Mitigation System** - Enhanced defender with real-time alerts, adaptive blocking, and distributed attack detection

## Setup Instructions

1. Ensure you have Python 3.6+ installed
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## System-Specific Requirements

### Linux Systems
- Python 3.6+
- One of the following firewall tools:
  - iptables
  - nftables
  - ufw
  - fail2ban
- Config file location (Level 2): `/etc/ssh-defender.yaml`

### macOS Systems
- Python 3.6+
- pf firewall (built-in)
- Config file location (Level 2): `~/Library/ssh-defender.conf`

### Windows Systems
- Python 3.6+
- pywin32 and wmi Python packages (installed automatically with requirements.txt)
- Windows Defender Firewall (built-in)
- OpenSSH Server (optional Windows feature)
- Config file location (Level 2): `C:\ssh-defender\config.ini`

## Level 1: SSH Brute-Force Detector with Auto-Block

A cross-platform security system that detects failed SSH login attempts and automatically blocks malicious IPs.

### Features

- Detects failed SSH login attempts across multiple platforms
- Identifies brute-force attacks using customizable thresholds
- Automatically blocks malicious IPs using native firewall tools
- Whitelist support to prevent accidental self-blocking
- Cross-platform compatibility with Linux, macOS, and Windows

### How to Run

**Basic usage:**
```
# On Linux/macOS (requires root privileges):
sudo python level-1.py

# On Windows (requires Administrator privileges):
python level-1.py
```

**With optional parameters:**
```
python level-1.py --threshold 10 --time-window 5 --whitelist 192.168.1.100 127.0.0.1
```

**In dry-run mode (no actual IP blocking):**
```
python level-1.py --dry-run
```

### Command Line Options

- `--threshold N` - Number of failed attempts before blocking an IP (default: 5)
- `--time-window N` - Time window in minutes to consider for failed attempts (default: 5)
- `--block-duration N` - Duration in minutes to block IPs (default: 60)
- `--whitelist IP1 IP2...` - List of IPs to whitelist (space-separated)
- `--dry-run` - Do not actually block IPs, just log what would be done
- `--interval N` - Interval in seconds between log checks (default: 60)
- `--once` - Run once and exit instead of continuous monitoring
- `--debug` - Enable debug logging

## Level 2: Advanced Threat Mitigation System

An enhanced version of the SSH defender with real-time attack notifications, adaptive blocking with intelligent cooldown, and distributed attack detection capabilities.

### Features

#### 1. Real-Time Alert System
- Multi-channel attack notifications with rich contextual data
- Slack integration with custom webhooks and formatted alerts
- Email alerts with severity-based coloring and detailed attacker information
- Geolocation and reverse DNS lookup for attacker identification

#### 2. Adaptive Blocking & Cooldown
- Temporary blocking with configurable duration (default: 24 hours)
- Automatic rule expiration and cooldown timers
- Persistent block tracking across server reboots
- Advanced whitelist management with YAML/JSON config support
- CIDR range support for enterprise network whitelisting
- Emergency unblock commands via alert interfaces

#### 3. Distributed Attack Detection
- Multi-IP correlation to identify coordinated attacks
- Username-based clustering to detect targeted account attacks
- Geo-behavioral analysis to flag impossible travel patterns
- ASN and hosting provider tagging for suspicious sources
- Country-specific baseline monitoring for anomaly detection

### How to Run

**Basic usage with config file:**
```
# On Linux/macOS (requires root privileges):
sudo python level-2.py --config /path/to/config.yaml

# On Windows (requires Administrator privileges):
python level-2.py --config C:\path\to\config.ini
```

**Generate a sample config file:**
```
python level-2.py --generate-config
```

### Command Line Options

All Level 1 options plus:
- `--config PATH` - Path to configuration file
- `--generate-config` - Generate a sample configuration file
- `--no-alerts` - Disable all alert notifications
- `--no-geo` - Disable geolocation features
- `--distributed-detection` - Enable distributed attack detection
- `--test-alerts` - Test alert configurations without actual blocking

### Configuration File Example

```yaml
# SSH Defender Level 2 Configuration

general:
  block_duration: 1440  # minutes (24 hours)
  block_log: /var/log/ssh_defender_blocks.log
  persistent_state: /var/lib/ssh-defender/state.json

alerts:
  slack:
    enabled: true
    webhook_url: https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX
    channel: "#security-alerts"
  
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    use_tls: true
    username: alerts@example.com
    password: your_app_password
    from_address: alerts@example.com
    to_addresses:
      - admin@example.com
      - security@example.com

whitelist:
  ips:
    - 192.168.1.0/24
    - 10.0.0.1
  emergency_unblock_key: a1b2c3d4

distributed_detection:
  enabled: true
  username_threshold: 5
  timing_sensitivity: medium
  geo_detection: true
```

## Test Cases

### Level 1
- Basic blocking functionality with various thresholds
- Whitelist validation
- Cross-platform compatibility testing

### Level 2
1. **Alert Verification**
   - Trigger 5 failed logins → Confirm Slack/Email received
2. **Cooldown Test**
   - Block IP → Verify auto-unblock after 24h
3. **Whitelist Validation**
   - Test login from whitelisted IP → No blocking
4. **Distributed Attack**
   - Simulate 3+ IPs attacking one user → Detect cluster

## Assumptions and Notes

1. **Root/Administrator Privileges**: The script requires elevated privileges to modify firewall rules. Use `--dry-run` mode if you want to test without these privileges.

2. **Log Formats**: The script attempts to handle various log formats across different platforms, but some custom or non-standard logging configurations might not be detected.

3. **Whitelist Your Own IP**: To prevent locking yourself out, always whitelist your own IP address when running the script.

4. **SSH Server**: The script assumes that an SSH server is running on the system and generating log entries for failed login attempts.

5. **Silent Graceful Exit**: If critical requirements are not met (missing logs, no privileges), the script will exit gracefully with an informative error message.

6. **Cross-Platform Design**: The script uses platform-specific approaches for log reading and firewall management:
   - Linux: journalctl/auth.log + iptables/nftables/ufw
   - macOS: system.log + pf firewall
   - Windows: Event Viewer/OpenSSH logs + Windows Firewall

7. **Level 2 GeoIP Database**: For geolocation features, the script requires GeoLite2 database files which should be downloaded separately and configured in the config file.
