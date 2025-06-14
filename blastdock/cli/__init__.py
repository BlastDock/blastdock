"""
BlastDock CLI module
"""

# Import all command groups
from .deploy import deploy_group as deploy
from .marketplace import marketplace_group as marketplace
from .monitoring import monitoring
from .templates import templates
from .diagnostics import diagnostics
from .security import security
from .performance import performance
from .config_commands import config_group

__all__ = [
    'deploy',
    'marketplace', 
    'monitoring',
    'templates', 
    'diagnostics', 
    'security', 
    'performance',
    'config_group'
]
