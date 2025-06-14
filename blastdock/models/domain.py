"""
Domain data models and configuration structures
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator


class DomainType(str, Enum):
    """Domain type classification"""
    CUSTOM = "custom"
    SUBDOMAIN = "subdomain"
    WILDCARD = "wildcard"
    LOCAL = "local"


class DomainStatus(str, Enum):
    """Domain resolution and availability status"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_USE = "in_use"
    INVALID = "invalid"
    DNS_ERROR = "dns_error"
    UNREACHABLE = "unreachable"


class DNSRecord(BaseModel):
    """DNS record information"""
    type: str = Field(..., description="DNS record type (A, AAAA, CNAME, etc.)")
    value: str = Field(..., description="DNS record value")
    ttl: Optional[int] = None
    priority: Optional[int] = None


class DomainConfig(BaseModel):
    """Domain configuration and metadata"""
    domain: str = Field(..., description="Domain name")
    type: DomainType = Field(..., description="Domain type")
    project: str = Field(..., description="Associated project")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # DNS configuration
    dns_records: List[DNSRecord] = Field(default_factory=list)
    custom_dns: Optional[Dict[str, str]] = None
    
    # SSL configuration
    ssl_enabled: bool = False
    ssl_certificate: Optional[str] = None
    
    # Access control
    auth_required: bool = False
    allowed_ips: List[str] = Field(default_factory=list)
    
    # Custom configuration
    custom_config: Dict[str, str] = Field(default_factory=dict)
    
    @validator('domain')
    def validate_domain(cls, v):
        """Validate domain format"""
        import re
        from ..constants import DOMAIN_PATTERN
        if not re.match(DOMAIN_PATTERN, v):
            raise ValueError(f"Invalid domain format: {v}")
        return v.lower()


class Domain(BaseModel):
    """Complete domain model with runtime information"""
    config: DomainConfig
    status: DomainStatus = DomainStatus.AVAILABLE
    
    # Runtime DNS information
    resolved_ip: Optional[str] = None
    dns_propagated: bool = False
    dns_errors: List[str] = Field(default_factory=list)
    
    # Health check information
    health_status: Optional[str] = None
    last_checked: Optional[datetime] = None
    response_time: Optional[float] = None
    
    # SSL information
    ssl_valid: bool = False
    ssl_expires_at: Optional[datetime] = None
    ssl_issuer: Optional[str] = None
    
    # Usage statistics
    request_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def is_available(self) -> bool:
        """Check if domain is available for use"""
        return self.status == DomainStatus.AVAILABLE
    
    def is_reserved(self) -> bool:
        """Check if domain is reserved"""
        return self.status == DomainStatus.RESERVED
    
    def is_in_use(self) -> bool:
        """Check if domain is currently in use"""
        return self.status == DomainStatus.IN_USE
    
    def is_local(self) -> bool:
        """Check if domain is local (.local, localhost, etc.)"""
        return (self.config.type == DomainType.LOCAL or 
                self.config.domain.endswith('.local') or
                self.config.domain == 'localhost' or
                self.config.domain.startswith('localhost.'))
    
    def is_subdomain(self) -> bool:
        """Check if this is a subdomain"""
        return self.config.type == DomainType.SUBDOMAIN
    
    def get_parent_domain(self) -> Optional[str]:
        """Get parent domain for subdomains"""
        if self.is_subdomain():
            parts = self.config.domain.split('.')
            if len(parts) > 2:
                return '.'.join(parts[1:])
        return None
    
    def get_subdomain_part(self) -> Optional[str]:
        """Get subdomain part"""
        if self.is_subdomain():
            parts = self.config.domain.split('.')
            if len(parts) > 2:
                return parts[0]
        return None
    
    def needs_ssl_renewal(self, warning_days: int = 30) -> bool:
        """Check if SSL certificate needs renewal"""
        if not self.ssl_expires_at:
            return False
        
        days_until_expiry = (self.ssl_expires_at - datetime.now()).days
        return days_until_expiry <= warning_days
    
    def get_access_url(self, ssl: bool = None) -> str:
        """Get full access URL for domain"""
        if ssl is None:
            ssl = self.config.ssl_enabled and self.ssl_valid
        
        protocol = "https" if ssl else "http"
        return f"{protocol}://{self.config.domain}"
    
    def validate_dns(self) -> bool:
        """Validate DNS resolution"""
        try:
            import socket
            socket.gethostbyname(self.config.domain)
            self.dns_propagated = True
            self.dns_errors.clear()
            return True
        except socket.gaierror as e:
            self.dns_propagated = False
            self.dns_errors.append(str(e))
            return False
    
    def check_accessibility(self, timeout: int = 10) -> bool:
        """Check if domain is accessible via HTTP/HTTPS"""
        try:
            import requests
            from requests.exceptions import RequestException
            
            # Try HTTPS first, then HTTP
            urls = []
            if self.config.ssl_enabled:
                urls.append(f"https://{self.config.domain}")
            urls.append(f"http://{self.config.domain}")
            
            for url in urls:
                try:
                    response = requests.head(url, timeout=timeout, allow_redirects=True)
                    if response.status_code < 500:  # Accept any non-server error
                        self.health_status = "accessible"
                        self.response_time = response.elapsed.total_seconds()
                        self.last_checked = datetime.now()
                        return True
                except RequestException:
                    continue
            
            self.health_status = "unreachable"
            self.last_checked = datetime.now()
            return False
            
        except ImportError:
            # If requests is not available, just return True
            return True