"""
Migration module for BlastDock
Handles migration of existing deployments to Traefik integration
"""

from .traefik_migrator import TraefikMigrator

__all__ = ['TraefikMigrator']