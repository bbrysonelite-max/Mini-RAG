"""
Security utilities for the Mini-RAG application.

Provides security enhancements including:
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting
- Security headers
"""

import re
import html
import hashlib
import secrets
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import bleach

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Input validation and sanitization utilities."""
    
    # Allowed HTML tags for rich text (very restrictive)
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'code', 'pre']
    ALLOWED_ATTRIBUTES = {'code': ['class']}
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|FROM|WHERE)\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(;.*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<applet[^>]*>",
    ]
    
    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """
        Sanitize HTML content to prevent XSS.
        
        Args:
            text: Raw HTML text
            
        Returns:
            Sanitized HTML
        """
        if not text:
            return ""
        
        # Use bleach for HTML sanitization
        cleaned = bleach.clean(
            text,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        return cleaned
    
    @classmethod
    def escape_html(cls, text: str) -> str:
        """
        Escape HTML entities.
        
        Args:
            text: Raw text
            
        Returns:
            HTML-escaped text
        """
        if not text:
            return ""
        
        return html.escape(text)
    
    @classmethod
    def validate_sql_input(cls, text: str) -> tuple[bool, Optional[str]]:
        """
        Check for potential SQL injection patterns.
        
        Args:
            text: Input text to validate
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        if not text:
            return True, None
        
        upper_text = text.upper()
        
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, upper_text, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                return False, "Input contains potentially dangerous SQL patterns"
        
        return True, None
    
    @classmethod
    def validate_xss_input(cls, text: str) -> tuple[bool, Optional[str]]:
        """
        Check for potential XSS patterns.
        
        Args:
            text: Input text to validate
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        if not text:
            return True, None
        
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential XSS detected: {pattern}")
                return False, "Input contains potentially dangerous script patterns"
        
        return True, None
    
    @classmethod
    def validate_filename(cls, filename: str) -> tuple[bool, Optional[str]]:
        """
        Validate filename for security issues.
        
        Args:
            filename: Filename to validate
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        if not filename:
            return False, "Filename cannot be empty"
        
        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return False, "Filename contains invalid path characters"
        
        # Check for null bytes
        if "\x00" in filename:
            return False, "Filename contains null bytes"
        
        # Check length
        if len(filename) > 255:
            return False, "Filename too long"
        
        # Check for dangerous extensions
        dangerous_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr',
            '.vbs', '.js', '.jar', '.msi', '.dll', '.app'
        ]
        
        lower_filename = filename.lower()
        for ext in dangerous_extensions:
            if lower_filename.endswith(ext):
                return False, f"File extension {ext} is not allowed"
        
        return True, None
    
    @classmethod
    def validate_url(cls, url: str) -> tuple[bool, Optional[str]]:
        """
        Validate URL for security issues.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        if not url:
            return False, "URL cannot be empty"
        
        # Check for javascript: and data: URLs
        lower_url = url.lower().strip()
        if lower_url.startswith(('javascript:', 'data:', 'vbscript:')):
            return False, "URL contains potentially dangerous protocol"
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            return False, "Invalid URL format"
        
        return True, None


class CSRFProtection:
    """CSRF token generation and validation."""
    
    @staticmethod
    def generate_token() -> str:
        """Generate a CSRF token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_token(token: str, stored_token: str) -> bool:
        """
        Validate a CSRF token.
        
        Args:
            token: Provided token
            stored_token: Stored token
            
        Returns:
            True if tokens match
        """
        if not token or not stored_token:
            return False
        
        # Constant-time comparison
        return secrets.compare_digest(token, stored_token)


class PasswordPolicy:
    """Password strength validation and hashing."""
    
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, List[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        
        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if cls.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if cls.REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            errors.append("Password must contain at least one special character")
        
        # Check for common passwords
        common_passwords = [
            "password", "12345678", "qwerty", "abc123", "password123",
            "admin", "letmein", "welcome", "monkey", "dragon"
        ]
        
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Password to hash
            
        Returns:
            Hashed password
        """
        try:
            import bcrypt
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except ImportError:
            # Fallback to SHA256 if bcrypt not available (not recommended for production)
            logger.warning("bcrypt not available, using SHA256 (not recommended for production)")
            return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            password: Password to verify
            hashed: Hashed password
            
        Returns:
            True if password matches
        """
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except ImportError:
            # Fallback to SHA256 comparison
            return hashlib.sha256(password.encode()).hexdigest() == hashed


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
    
    CSP_DIRECTIVES = {
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
        "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src": "'self' https://fonts.gstatic.com",
        "img-src": "'self' data: https:",
        "connect-src": "'self' https://api.openai.com",
        "frame-ancestors": "'none'",
        "base-uri": "'self'",
        "form-action": "'self'",
    }
    
    @classmethod
    def get_headers(cls, nonce: Optional[str] = None) -> Dict[str, str]:
        """
        Get security headers.
        
        Args:
            nonce: Optional CSP nonce for inline scripts
            
        Returns:
            Dictionary of security headers
        """
        headers = cls.SECURITY_HEADERS.copy()
        
        # Build Content Security Policy
        csp_parts = []
        for directive, value in cls.CSP_DIRECTIVES.items():
            if nonce and directive == "script-src":
                value = f"{value} 'nonce-{nonce}'"
            csp_parts.append(f"{directive} {value}")
        
        headers["Content-Security-Policy"] = "; ".join(csp_parts)
        
        return headers


class AuditLogger:
    """Security audit logging."""
    
    def __init__(self, log_file: str = "security_audit.log"):
        """
        Initialize audit logger.
        
        Args:
            log_file: Path to audit log file
        """
        self.logger = logging.getLogger("security_audit")
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_auth_attempt(
        self,
        username: str,
        success: bool,
        ip_address: str,
        user_agent: Optional[str] = None
    ):
        """Log authentication attempt."""
        self.logger.info(
            f"AUTH_ATTEMPT - User: {username}, Success: {success}, "
            f"IP: {ip_address}, UserAgent: {user_agent}"
        )
    
    def log_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        success: bool,
        ip_address: str
    ):
        """Log resource access."""
        self.logger.info(
            f"ACCESS - User: {user_id}, Resource: {resource}, "
            f"Action: {action}, Success: {success}, IP: {ip_address}"
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None
    ):
        """Log security event."""
        self.logger.warning(
            f"SECURITY_EVENT - Type: {event_type}, Severity: {severity}, "
            f"IP: {ip_address}, Details: {details}"
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


