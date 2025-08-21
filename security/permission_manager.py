#!/usr/bin/env python3
"""
Permission Manager for Personal OS
Handles file system access control, web domain validation, and action permissions
"""

import os
import yaml
import fnmatch
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import json
from personal_os import config as pos_config

class PermissionManager:
    def __init__(self, config_path: str = None):
        """Initialize Permission Manager with configuration"""
        # Ensure directories exist early
        pos_config.ensure_dirs()

        # Resolve configuration path
        self.config_path = config_path or str(pos_config.permissions_path())

        self.config = self._load_config()
        self.rate_limiter = {}
        self.failed_attempts = {}
        
        # Set up logging
        self._setup_logging()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load permissions configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                raw = yaml.safe_load(f)
                # Expand placeholders and env vars
                return pos_config.expand_in_config(raw or {})
        except FileNotFoundError:
            # Fall back to default restrictive config
            return self._get_default_config()
        except yaml.YAMLError as e:
            logging.getLogger('PersonalOS_Security').error(f"Error parsing permissions config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default restrictive configuration"""
        subs = pos_config.substitutions()
        return pos_config.expand_in_config({
            "file_access": {
                "allowed_paths": [
                    "${APP_HOME}/",
                    "${TMPDIR}/personal-os/",
                    "${CWD}/",
                ],
                "blocked_paths": [
                    "${HOME}/.ssh/",
                    "/**/.env",
                    "/**/.env.*",
                    "/**/id_rsa",
                    "/**/id_ed25519",
                ],
                "sensitive_extensions": [".pem", ".key", ".p12", ".pfx", ".crt"],
            },
            "web_access": {
                "allowed_domains": [
                    "mail.google.com",
                    "calendar.google.com",
                    "web.whatsapp.com",
                    "accounts.google.com",
                ],
                "require_confirmation": [
                    "send_email",
                    "send_message",
                    "create_event",
                    "delete_email",
                    "delete_event",
                ],
                "rate_limits": {"send_email": 50, "send_message": 100, "create_event": 20},
            },
            "browser_security": {
                "isolated_session": True,
                "clear_cookies_on_exit": False,
                "disable_extensions": True,
                "disable_plugins": True,
                "capture_screenshots": True,
                "page_load_timeout": 30,
                "action_timeout": 10,
            },
            "audit": {
                "enabled": True,
                "log_level": "INFO",
                "log_file": "${AUDIT_LOG}",
            },
            "credentials": {
                "vault_file": "${VAULT_FILE}",
                "auto_lock_timeout": 1800,
            },
        })
    
    def _setup_logging(self):
        """Set up audit logging"""
        audit_config = self.config.get('audit', {})

        # Create logs directory if it doesn't exist
        log_file = pos_config.expand_placeholders(audit_config.get('log_file', str(pos_config.audit_log_path())))
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)

        # Configure logger
        self.logger = logging.getLogger('PersonalOS_Security')
        self.logger.setLevel(getattr(logging, audit_config.get('log_level', 'INFO')))

        # Avoid duplicate handlers on re-init
        self.logger.handlers = []

        # File handler
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Console handler for critical issues
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def check_file_access(self, file_path: str, action: str = "read") -> Tuple[bool, str]:
        """Check if file access is permitted"""
        abs_path = os.path.abspath(file_path)
        
        # Check blocked paths first
        for blocked in self.config['file_access'].get('blocked_paths', []):
            if self._path_matches(abs_path, blocked):
                self.logger.warning(f"BLOCKED: File access denied to {abs_path}")
                return False, f"Access denied: Path is blocked ({blocked})"
        
        # Check allowed paths
        allowed_paths = self.config['file_access'].get('allowed_paths', [])
        if not allowed_paths:
            return False, "No allowed paths configured"
        
        for allowed in allowed_paths:
            if self._path_matches(abs_path, allowed):
                # Check for sensitive extensions
                if self._is_sensitive_file(abs_path):
                    self.logger.info(f"SENSITIVE: File access to {abs_path} (requires confirmation)")
                    return True, f"Sensitive file access: {abs_path}"
                
                self.logger.info(f"ALLOWED: File access to {abs_path}")
                return True, "Access granted"
        
        self.logger.warning(f"DENIED: File access outside allowed paths: {abs_path}")
        return False, "Access denied: Path not in allowed directories"
    
    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches a pattern (supports wildcards)"""
        # Convert to absolute paths for comparison
        abs_path = os.path.abspath(path)
        
        # Handle wildcard patterns
        if '**' in pattern:
            return fnmatch.fnmatch(abs_path, pattern)
        
        # Handle directory patterns (pattern ends with /)
        if pattern.endswith('/'):
            abs_pattern = os.path.abspath(pattern.rstrip('/'))
            return abs_path.startswith(abs_pattern + '/')
        
        # Handle exact matches and parent directory matches
        abs_pattern = os.path.abspath(pattern)
        return abs_path.startswith(abs_pattern)
    
    def _is_sensitive_file(self, file_path: str) -> bool:
        """Check if file has sensitive extension"""
        sensitive_exts = self.config['file_access'].get('sensitive_extensions', [])
        file_ext = Path(file_path).suffix.lower()
        return file_ext in sensitive_exts
    
    def check_web_access(self, domain: str) -> Tuple[bool, str]:
        """Check if web domain access is permitted"""
        allowed_domains = self.config['web_access'].get('allowed_domains', [])
        
        # Check exact domain match
        if domain in allowed_domains:
            self.logger.info(f"WEB_ALLOWED: Access granted to {domain}")
            return True, "Domain access granted"
        
        # Check subdomain matches
        for allowed in allowed_domains:
            if domain.endswith('.' + allowed) or domain == allowed:
                self.logger.info(f"WEB_ALLOWED: Subdomain access granted to {domain}")
                return True, "Subdomain access granted"
        
        self.logger.warning(f"WEB_BLOCKED: Domain access denied to {domain}")
        return False, f"Domain not in allowed list: {domain}"
    
    def check_action_permission(self, action: str, context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Check if action requires confirmation and validate rate limits"""
        # Check if action requires confirmation
        requires_confirmation = self.config['web_access'].get('require_confirmation', [])
        if action in requires_confirmation:
            self.logger.info(f"ACTION_CONFIRM: Action {action} requires user confirmation")
            return True, f"Action '{action}' requires user confirmation"
        
        # Check rate limits
        rate_limits = self.config['web_access'].get('rate_limits', {})
        if action in rate_limits:
            if not self._check_rate_limit(action, rate_limits[action]):
                self.logger.warning(f"RATE_LIMIT: Action {action} exceeds rate limit")
                return False, f"Rate limit exceeded for action '{action}'"
        
        self.logger.info(f"ACTION_ALLOWED: Action {action} permitted")
        return True, "Action permitted"
    
    def _check_rate_limit(self, action: str, limit: int) -> bool:
        """Check if action is within rate limit"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Initialize action tracking if needed
        if action not in self.rate_limiter:
            self.rate_limiter[action] = []
        
        # Remove old entries
        self.rate_limiter[action] = [
            timestamp for timestamp in self.rate_limiter[action]
            if timestamp > hour_ago
        ]
        
        # Check current count
        current_count = len(self.rate_limiter[action])
        if current_count >= limit:
            return False
        
        # Record this action
        self.rate_limiter[action].append(now)
        return True
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security-related events"""
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        if event_type in ["VIOLATION", "BLOCKED", "FAILED_AUTH"]:
            self.logger.error(f"SECURITY_EVENT: {json.dumps(event_data)}")
        else:
            self.logger.info(f"SECURITY_EVENT: {json.dumps(event_data)}")
    
    def record_failed_attempt(self, identifier: str) -> bool:
        """Record failed authentication attempt and check for lockout"""
        max_attempts = self.config.get('emergency', {}).get('max_failed_attempts', 5)
        lockout_duration = self.config.get('emergency', {}).get('lockout_duration', 300)
        
        now = datetime.now()
        
        # Initialize tracking for this identifier
        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = []
        
        # Add this failed attempt
        self.failed_attempts[identifier].append(now)
        
        # Remove old attempts (outside lockout window)
        cutoff_time = now - timedelta(seconds=lockout_duration * 2)
        self.failed_attempts[identifier] = [
            attempt for attempt in self.failed_attempts[identifier]
            if attempt > cutoff_time
        ]
        
        # Check for lockout
        recent_failures = [
            attempt for attempt in self.failed_attempts[identifier]
            if attempt > now - timedelta(seconds=lockout_duration)
        ]
        
        if len(recent_failures) >= max_attempts:
            self.log_security_event("LOCKOUT", {
                "identifier": identifier,
                "failed_attempts": len(recent_failures),
                "lockout_until": (now + timedelta(seconds=lockout_duration)).isoformat()
            })
            return True  # Locked out
        
        return False  # Not locked out
    
    def is_locked_out(self, identifier: str) -> bool:
        """Check if identifier is currently locked out"""
        if identifier not in self.failed_attempts:
            return False
        
        max_attempts = self.config.get('emergency', {}).get('max_failed_attempts', 5)
        lockout_duration = self.config.get('emergency', {}).get('lockout_duration', 300)
        now = datetime.now()
        
        recent_failures = [
            attempt for attempt in self.failed_attempts[identifier]
            if attempt > now - timedelta(seconds=lockout_duration)
        ]
        
        return len(recent_failures) >= max_attempts
    
    def clear_failed_attempts(self, identifier: str):
        """Clear failed attempts for identifier (after successful auth)"""
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
    
    def is_panic_mode(self) -> bool:
        """Check if system is in panic mode"""
        return self.config.get('emergency', {}).get('panic_mode_enabled', False)
    
    def get_browser_security_config(self) -> Dict[str, Any]:
        """Get browser security configuration"""
        return self.config.get('browser_security', {
            'isolated_session': True,
            'clear_cookies_on_exit': False,
            'disable_extensions': True,
            'disable_plugins': True,
            'capture_screenshots': True,
            'page_load_timeout': 30,
            'action_timeout': 10
        })

def main():
    """Test the Permission Manager"""
    pm = PermissionManager()
    
    print("🔐 Testing Permission Manager")
    print("=" * 40)
    
    # Test file access
    test_files = [
        str(Path.cwd() / "test.txt"),  # Should be allowed (cwd)
        str(Path.home() / ".ssh" / "id_rsa"),  # Should be blocked
        str(Path(pos_config.base_dir()) / "data.json"),  # Should be allowed (app home)
        "/System/Library/important.file",  # Likely blocked on macOS
    ]
    
    for file_path in test_files:
        allowed, reason = pm.check_file_access(file_path)
        status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
        print(f"{status}: {file_path}")
        print(f"   Reason: {reason}")
    
    print("\n🌐 Testing Web Access")
    print("=" * 40)
    
    # Test web access
    test_domains = [
        "mail.google.com",  # Should be allowed
        "calendar.google.com",  # Should be allowed
        "malicious-site.com",  # Should be blocked
        "web.whatsapp.com"  # Should be allowed
    ]
    
    for domain in test_domains:
        allowed, reason = pm.check_web_access(domain)
        status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
        print(f"{status}: {domain}")
        print(f"   Reason: {reason}")
    
    print("\n⚡ Testing Action Permissions")
    print("=" * 40)
    
    # Test actions
    test_actions = [
        "send_email",  # Should require confirmation
        "read_email",  # Should be allowed
        "send_message",  # Should require confirmation
        "create_event"  # Should require confirmation
    ]
    
    for action in test_actions:
        allowed, reason = pm.check_action_permission(action)
        status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
        if "confirmation" in reason:
            status = "⚠️ CONFIRMATION"
        print(f"{status}: {action}")
        print(f"   Reason: {reason}")

if __name__ == "__main__":
    main()
