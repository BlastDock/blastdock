"""
Port data models and configuration structures
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator


class PortStatus(str, Enum):
    """Port allocation status"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_USE = "in_use"
    CONFLICTED = "conflicted"
    SYSTEM_RESERVED = "system_reserved"


class PortType(str, Enum):
    """Port type classification"""
    HTTP = "http"
    HTTPS = "https"
    DATABASE = "database"
    CACHE = "cache"
    CUSTOM = "custom"
    SYSTEM = "system"


class PortAllocation(BaseModel):
    """Port allocation record"""
    port: int = Field(..., ge=1, le=65535, description="Port number")
    project: str = Field(..., description="Project name")
    service: str = Field(..., description="Service name")
    type: PortType = Field(default=PortType.CUSTOM, description="Port type")
    allocated_at: datetime = Field(default_factory=datetime.now)
    
    # Usage information
    in_use: bool = False
    last_used: Optional[datetime] = None
    
    # Process information
    process_id: Optional[int] = None
    process_name: Optional[str] = None
    
    # Custom metadata
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    @validator('port')
    def validate_port_range(cls, v):
        """Validate port is in valid range"""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class PortReservation(BaseModel):
    """Port reservation record"""
    port: int = Field(..., ge=1, le=65535, description="Port number")
    reason: str = Field(..., description="Reservation reason")
    reserved_at: datetime = Field(default_factory=datetime.now)
    reserved_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    # Reservation metadata
    priority: int = Field(default=1, description="Reservation priority")
    permanent: bool = False
    
    def is_expired(self) -> bool:
        """Check if reservation has expired"""
        if self.permanent or not self.expires_at:
            return False
        return datetime.now() > self.expires_at


class PortConflict(BaseModel):
    """Port conflict information"""
    port: int = Field(..., description="Conflicted port")
    type: str = Field(..., description="Conflict type")
    
    # Conflicting allocations
    allocated_to: Optional[PortAllocation] = None
    actual_usage: Optional[Dict[str, str]] = None
    
    # Conflict details
    detected_at: datetime = Field(default_factory=datetime.now)
    severity: str = Field(default="medium")
    resolution_suggestion: Optional[str] = None


class PortConfig(BaseModel):
    """Port management configuration"""
    # Port ranges
    dynamic_range_start: int = Field(default=8000, description="Dynamic allocation start")
    dynamic_range_end: int = Field(default=9000, description="Dynamic allocation end")
    
    # Reserved ports
    system_reserved: List[int] = Field(default_factory=lambda: [22, 80, 443, 8080])
    user_reserved: List[int] = Field(default_factory=list)
    
    # Allocation settings
    auto_allocate: bool = True
    conflict_detection: bool = True
    allow_system_ports: bool = False
    
    # Type mappings
    port_type_defaults: Dict[str, int] = Field(default_factory=lambda: {
        "http": 8080,
        "https": 8443,
        "mysql": 3306,
        "postgresql": 5432,
        "redis": 6379,
        "mongodb": 27017,
        "elasticsearch": 9200
    })


class Port(BaseModel):
    """Complete port model with runtime information"""
    number: int = Field(..., ge=1, le=65535, description="Port number")
    status: PortStatus = PortStatus.AVAILABLE
    type: PortType = PortType.CUSTOM
    
    # Allocation information
    allocation: Optional[PortAllocation] = None
    reservation: Optional[PortReservation] = None
    
    # Runtime information
    is_listening: bool = False
    process_info: Optional[Dict[str, str]] = None
    
    # Conflict information
    conflicts: List[PortConflict] = Field(default_factory=list)
    
    # Health information
    last_checked: Optional[datetime] = None
    response_time: Optional[float] = None
    
    def is_available(self) -> bool:
        """Check if port is available for allocation"""
        return self.status == PortStatus.AVAILABLE
    
    def is_allocated(self) -> bool:
        """Check if port is allocated to a project"""
        return self.allocation is not None
    
    def is_reserved(self) -> bool:
        """Check if port is reserved"""
        return self.reservation is not None and not self.reservation.is_expired()
    
    def is_system_port(self) -> bool:
        """Check if port is a system port (< 1024)"""
        return self.number < 1024
    
    def is_in_conflict(self) -> bool:
        """Check if port has conflicts"""
        return len(self.conflicts) > 0
    
    def get_allocated_project(self) -> Optional[str]:
        """Get project name that allocated this port"""
        return self.allocation.project if self.allocation else None
    
    def get_allocated_service(self) -> Optional[str]:
        """Get service name that allocated this port"""
        return self.allocation.service if self.allocation else None
    
    def check_availability(self) -> bool:
        """Check if port is actually available by testing connection"""
        try:
            import socket
            
            # Test TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', self.number))
            sock.close()
            
            self.is_listening = (result == 0)
            self.last_checked = datetime.now()
            
            return result != 0  # Available if connection fails
            
        except Exception:
            return True  # Assume available if check fails
    
    def get_process_info(self) -> Optional[Dict[str, str]]:
        """Get information about process using this port"""
        try:
            import psutil
            
            for conn in psutil.net_connections():
                if conn.laddr.port == self.number:
                    try:
                        process = psutil.Process(conn.pid)
                        return {
                            'pid': str(conn.pid),
                            'name': process.name(),
                            'cmdline': ' '.join(process.cmdline()),
                            'status': process.status()
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            return None
            
        except ImportError:
            return None
    
    def suggest_alternative(self, start_range: int = 8000, end_range: int = 9000) -> Optional[int]:
        """Suggest alternative port in specified range"""
        import socket
        
        for port in range(start_range, end_range + 1):
            if port == self.number:
                continue
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result != 0:  # Port is available
                    return port
                    
            except Exception:
                continue
        
        return None