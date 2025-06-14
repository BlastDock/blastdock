"""
Traefik data models and configuration structures
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TraefikStatus(str, Enum):
    """Traefik service status"""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class SSLCertificateStatus(str, Enum):
    """SSL certificate status"""
    VALID = "valid"
    EXPIRED = "expired"
    EXPIRING_SOON = "expiring_soon"
    INVALID = "invalid"
    PENDING = "pending"
    ERROR = "error"


class SSLCertificate(BaseModel):
    """SSL certificate information"""
    domain: str = Field(..., description="Certificate domain")
    status: SSLCertificateStatus = Field(..., description="Certificate status")
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    issuer: Optional[str] = None
    serial_number: Optional[str] = None
    fingerprint: Optional[str] = None
    
    # Certificate details
    san_domains: List[str] = Field(default_factory=list, description="Subject Alternative Names")
    key_algorithm: Optional[str] = None
    signature_algorithm: Optional[str] = None
    
    # Validation information
    is_valid: bool = False
    is_trusted: bool = False
    validation_errors: List[str] = Field(default_factory=list)
    
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until certificate expires"""
        if self.expires_at:
            delta = self.expires_at - datetime.now()
            # Add 0.5 to round to nearest day to account for time precision
            return max(0, int(delta.total_seconds() / 86400 + 0.5))
        return None
    
    def is_expiring_soon(self, warning_days: int = 30) -> bool:
        """Check if certificate is expiring soon"""
        days_left = self.days_until_expiry()
        return days_left is not None and days_left <= warning_days
    
    def needs_renewal(self, renewal_days: int = 7) -> bool:
        """Check if certificate needs renewal"""
        days_left = self.days_until_expiry()
        return days_left is not None and days_left <= renewal_days


class MiddlewareConfig(BaseModel):
    """Traefik middleware configuration"""
    name: str = Field(..., description="Middleware name")
    type: str = Field(..., description="Middleware type")
    config: Dict[str, Any] = Field(default_factory=dict)


class ServiceConfig(BaseModel):
    """Traefik service configuration"""
    name: str = Field(..., description="Service name")
    url: str = Field(..., description="Service URL")
    health_check: Optional[str] = None
    sticky_sessions: bool = False
    load_balancer: Dict[str, Any] = Field(default_factory=dict)


class RouterConfig(BaseModel):
    """Traefik router configuration"""
    name: str = Field(..., description="Router name")
    rule: str = Field(..., description="Router rule")
    service: str = Field(..., description="Target service")
    priority: int = 1
    middlewares: List[str] = Field(default_factory=list)
    tls: bool = False
    tls_domains: List[str] = Field(default_factory=list)


class TraefikConfig(BaseModel):
    """Complete Traefik configuration"""
    # Basic configuration
    version: str = Field(default="3.0", description="Traefik version")
    email: str = Field(..., description="Let's Encrypt email")
    default_domain: str = Field(..., description="Default domain")
    
    # Dashboard configuration
    dashboard_enabled: bool = True
    dashboard_domain: Optional[str] = None
    dashboard_port: int = 8080
    
    # SSL configuration
    ssl_enabled: bool = True
    ssl_provider: str = "letsencrypt"
    ssl_staging: bool = False
    ssl_challenge: str = "http"
    
    # Network configuration
    network_name: str = "blastdock-network"
    
    # Certificate configuration
    certificates: List[SSLCertificate] = Field(default_factory=list)
    
    # Service configuration
    services: Dict[str, ServiceConfig] = Field(default_factory=dict)
    routers: Dict[str, RouterConfig] = Field(default_factory=dict)
    middlewares: Dict[str, MiddlewareConfig] = Field(default_factory=dict)
    
    # File configuration
    config_file: Optional[str] = None
    data_directory: Optional[str] = None
    
    def get_certificate(self, domain: str) -> Optional[SSLCertificate]:
        """Get certificate for specific domain"""
        for cert in self.certificates:
            if cert.domain == domain or domain in cert.san_domains:
                return cert
        return None
    
    def get_expiring_certificates(self, warning_days: int = 30) -> List[SSLCertificate]:
        """Get certificates that are expiring soon"""
        return [cert for cert in self.certificates if cert.is_expiring_soon(warning_days)]
    
    def get_invalid_certificates(self) -> List[SSLCertificate]:
        """Get invalid certificates"""
        return [cert for cert in self.certificates if not cert.is_valid]


class TraefikInstance(BaseModel):
    """Traefik instance with runtime information"""
    config: TraefikConfig
    status: TraefikStatus = TraefikStatus.NOT_INSTALLED
    
    # Runtime information
    container_id: Optional[str] = None
    container_name: str = "blastdock-traefik"
    image: str = "traefik:v3.0"
    
    # Health information
    health_status: Optional[str] = None
    uptime: Optional[str] = None
    version: Optional[str] = None
    
    # Statistics
    total_services: int = 0
    total_routers: int = 0
    total_middlewares: int = 0
    total_certificates: int = 0
    
    # Network information
    network_exists: bool = False
    dashboard_accessible: bool = False
    
    def is_running(self) -> bool:
        """Check if Traefik is running"""
        return self.status == TraefikStatus.RUNNING
    
    def is_healthy(self) -> bool:
        """Check if Traefik is healthy"""
        return self.is_running() and self.health_status == "healthy"
    
    def get_dashboard_url(self) -> Optional[str]:
        """Get dashboard URL"""
        if not self.is_running():
            return None
        
        # Use dashboard_domain if set, otherwise fall back to default_domain
        domain = self.config.dashboard_domain or self.config.default_domain
        
        if domain:
            protocol = "https" if self.config.ssl_enabled else "http"
            return f"{protocol}://{domain}"
        
        return f"http://localhost:{self.config.dashboard_port}"
    
    def update_statistics(self):
        """Update runtime statistics"""
        self.total_services = len(self.config.services)
        self.total_routers = len(self.config.routers)
        self.total_middlewares = len(self.config.middlewares)
        self.total_certificates = len(self.config.certificates)