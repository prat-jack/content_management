import os
import re
import hashlib
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging

class SecurityManager:
    """
    Handles API key validation, rate limiting, and security checks for the content analyzer.
    """
    
    def __init__(self):
        self.rate_limit_store = {}  # In-memory store for rate limiting
        self.max_requests_per_minute = 30
        self.blocked_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
            r'data:text/html',  # Data URLs
        ]
        self.max_content_length = 50000  # 50KB max content
        
    def validate_api_key(self, api_key: Optional[str] = None) -> Dict[str, any]:
        """
        Validates OpenAI API key format and basic security checks.
        
        Args:
            api_key: API key to validate. If None, gets from environment.
            
        Returns:
            Dict with validation result and details
        """
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
            
        if not api_key:
            return {
                "valid": False,
                "error": "API key not found in environment variables",
                "code": "MISSING_KEY"
            }
            
        # Check basic format
        if not api_key.startswith("sk-"):
            return {
                "valid": False,
                "error": "Invalid API key format",
                "code": "INVALID_FORMAT"
            }
            
        # Check length (OpenAI keys are typically 51 characters)
        if len(api_key) < 40:
            return {
                "valid": False,
                "error": "API key too short",
                "code": "INVALID_LENGTH"
            }
            
        # Check for suspicious patterns
        if self._contains_suspicious_patterns(api_key):
            return {
                "valid": False,
                "error": "API key contains suspicious patterns",
                "code": "SUSPICIOUS_CONTENT"
            }
            
        return {
            "valid": True,
            "key_prefix": api_key[:7] + "...",
            "code": "VALID"
        }
    
    def check_rate_limit(self, client_id: str = "default") -> Dict[str, any]:
        """
        Checks if the client has exceeded the rate limit.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Dict with rate limit status
        """
        current_time = datetime.now()
        
        if client_id not in self.rate_limit_store:
            self.rate_limit_store[client_id] = []
            
        # Clean old requests (older than 1 minute)
        cutoff_time = current_time - timedelta(minutes=1)
        self.rate_limit_store[client_id] = [
            req_time for req_time in self.rate_limit_store[client_id]
            if req_time > cutoff_time
        ]
        
        current_requests = len(self.rate_limit_store[client_id])
        
        if current_requests >= self.max_requests_per_minute:
            oldest_request = min(self.rate_limit_store[client_id])
            reset_time = oldest_request + timedelta(minutes=1)
            return {
                "allowed": False,
                "current_requests": current_requests,
                "limit": self.max_requests_per_minute,
                "reset_time": reset_time.isoformat(),
                "retry_after": int((reset_time - current_time).total_seconds())
            }
        
        # Add current request
        self.rate_limit_store[client_id].append(current_time)
        
        return {
            "allowed": True,
            "current_requests": current_requests + 1,
            "limit": self.max_requests_per_minute,
            "remaining": self.max_requests_per_minute - current_requests - 1
        }
    
    def sanitize_content(self, content: str) -> Dict[str, any]:
        """
        Sanitizes input content to prevent various security issues.
        
        Args:
            content: Content to sanitize
            
        Returns:
            Dict with sanitized content and security status
        """
        if not content or not isinstance(content, str):
            return {
                "sanitized": "",
                "safe": True,
                "warnings": [],
                "original_length": 0
            }
        
        warnings = []
        original_length = len(content)
        
        # Check content length
        if original_length > self.max_content_length:
            content = content[:self.max_content_length]
            warnings.append(f"Content truncated from {original_length} to {self.max_content_length} characters")
        
        # Check for malicious patterns
        malicious_found = []
        for pattern in self.blocked_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                malicious_found.append(pattern)
        
        if malicious_found:
            warnings.append(f"Potentially malicious patterns detected: {len(malicious_found)} patterns")
            # Remove malicious patterns
            for pattern in self.blocked_patterns:
                content = re.sub(pattern, "[REMOVED]", content, flags=re.IGNORECASE | re.DOTALL)
        
        # Basic HTML entity encoding for special characters
        content = content.replace("<", "&lt;").replace(">", "&gt;")
        
        # Remove null bytes and control characters
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        return {
            "sanitized": content.strip(),
            "safe": len(malicious_found) == 0,
            "warnings": warnings,
            "original_length": original_length,
            "sanitized_length": len(content),
            "patterns_removed": len(malicious_found)
        }
    
    def generate_session_id(self) -> str:
        """
        Generates a secure session ID.
        
        Returns:
            Secure session ID string
        """
        timestamp = str(int(time.time()))
        random_data = os.urandom(16).hex()
        session_data = f"{timestamp}_{random_data}"
        return hashlib.sha256(session_data.encode()).hexdigest()[:32]
    
    def log_security_event(self, event_type: str, details: Dict[str, any], level: str = "INFO"):
        """
        Logs security-related events.
        
        Args:
            event_type: Type of security event
            details: Event details
            level: Log level (INFO, WARNING, ERROR)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "level": level,
            "details": details
        }
        
        # In production, this would write to a proper logging system
        logging.log(getattr(logging, level), f"Security Event: {log_entry}")
    
    def _contains_suspicious_patterns(self, text: str) -> bool:
        """
        Checks if text contains suspicious patterns that might indicate injection attempts.
        
        Args:
            text: Text to check
            
        Returns:
            True if suspicious patterns found
        """
        suspicious_patterns = [
            r'[\'"]\s*;\s*',  # SQL injection attempts
            r'union\s+select',  # SQL union attacks
            r'<script',  # XSS attempts
            r'javascript:',  # JavaScript injections
            r'data:text/html',  # Data URL injections
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False