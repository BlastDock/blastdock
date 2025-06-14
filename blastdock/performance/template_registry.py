"""Template Registry for high-performance template management"""

from typing import Dict, Any, Optional
import yaml
from pathlib import Path
from ..utils.logging import get_logger

logger = get_logger(__name__)

class TemplateRegistry:
    """Registry for managing templates"""
    
    def __init__(self):
        self.templates = {}
        self.logger = logger
        
    def initialize(self, preload: bool = False, enhance_traefik: bool = False):
        """Initialize the registry"""
        self.logger.info("Initializing template registry")
        if preload:
            self._preload_templates()
    
    def _preload_templates(self):
        """Preload all available templates"""
        template_dir = Path(__file__).parent.parent.parent / "templates"
        if template_dir.exists():
            for template_file in template_dir.glob("*.yml"):
                try:
                    with open(template_file) as f:
                        self.templates[template_file.stem] = yaml.safe_load(f)
                except Exception as e:
                    self.logger.error(f"Error loading template {template_file}: {e}")
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template by name"""
        if name not in self.templates:
            # Try to load it
            template_path = Path(__file__).parent.parent.parent / "templates" / f"{name}.yml"
            if template_path.exists():
                try:
                    with open(template_path) as f:
                        self.templates[name] = yaml.safe_load(f)
                except Exception as e:
                    self.logger.error(f"Error loading template {name}: {e}")
                    return None
        return self.templates.get(name)

_registry = None

def get_template_registry() -> TemplateRegistry:
    """Get the global template registry instance"""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
    return _registry
