"""Project model definitions"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ProjectConfig:
    """Project configuration model"""

    name: str
    template: str
    config: Dict[str, Any]
    directory: str
    created_at: float
    status: str = "deployed"
