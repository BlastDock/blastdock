"""
Template Marketplace core functionality
Manages template discovery, search, and metadata
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from enum import Enum

from ..utils.logging import get_logger
from ..performance.template_registry import get_template_registry
from ..utils.template_validator import TemplateValidator, TraefikCompatibility

logger = get_logger(__name__)


class TemplateCategory(str, Enum):
    """Template categories for marketplace organization"""
    WEB = "web"
    DATABASE = "database"
    CMS = "cms"
    ECOMMERCE = "ecommerce"
    DEVELOPMENT = "development"
    MONITORING = "monitoring"
    ANALYTICS = "analytics"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    MEDIA = "media"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


@dataclass
class MarketplaceTemplate:
    """Template entry in the marketplace"""
    id: str
    name: str
    display_name: str
    description: str
    category: TemplateCategory
    version: str
    author: str
    source: str  # 'official', 'community', 'local'
    
    # Metrics
    downloads: int = 0
    stars: int = 0
    rating: float = 0.0
    
    # Technical details
    services: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Quality metrics
    validation_score: float = 0.0
    traefik_compatible: bool = False
    security_score: float = 0.0
    
    # Timestamps
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # Additional metadata
    readme: Optional[str] = None
    changelog: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category.value,
            'version': self.version,
            'author': self.author,
            'source': self.source,
            'downloads': self.downloads,
            'stars': self.stars,
            'rating': self.rating,
            'services': self.services,
            'requires': self.requires,
            'tags': self.tags,
            'validation_score': self.validation_score,
            'traefik_compatible': self.traefik_compatible,
            'security_score': self.security_score,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'repository_url': self.repository_url,
            'documentation_url': self.documentation_url
        }


class TemplateMarketplace:
    """Central marketplace for BlastDock templates"""
    
    def __init__(self, marketplace_dir: str = None):
        """Initialize template marketplace"""
        self.logger = get_logger(__name__)
        
        # Set marketplace directory
        if marketplace_dir is None:
            marketplace_dir = Path.home() / '.blastdock' / 'marketplace'
        self.marketplace_dir = Path(marketplace_dir)
        self.marketplace_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.registry = get_template_registry()
        self.validator = TemplateValidator()
        
        # Marketplace data
        self.templates: Dict[str, MarketplaceTemplate] = {}
        self.categories: Dict[TemplateCategory, List[str]] = {
            category: [] for category in TemplateCategory
        }
        
        # Load marketplace data
        self._load_marketplace_data()
        
        # Popular templates (hardcoded for MVP)
        self._initialize_popular_templates()
        
        self.logger.info(f"Marketplace initialized with {len(self.templates)} templates")
    
    def search(self, 
               query: str = "",
               category: Optional[TemplateCategory] = None,
               tags: List[str] = None,
               min_rating: float = 0.0,
               traefik_only: bool = False,
               source: Optional[str] = None) -> List[MarketplaceTemplate]:
        """Search templates in marketplace"""
        results = []
        tags = tags or []
        
        for template in self.templates.values():
            # Skip if source filter doesn't match
            if source and template.source != source:
                continue
            
            # Skip if category filter doesn't match
            if category and template.category != category:
                continue
            
            # Skip if rating is too low
            if template.rating < min_rating:
                continue
            
            # Skip if Traefik required but not compatible
            if traefik_only and not template.traefik_compatible:
                continue
            
            # Text search in name, display name, and description
            if query:
                searchable = f"{template.name} {template.display_name} {template.description}".lower()
                if query.lower() not in searchable:
                    continue
            
            # Tag filtering
            if tags:
                if not any(tag in template.tags for tag in tags):
                    continue
            
            results.append(template)
        
        # Sort by popularity (downloads + stars)
        results.sort(key=lambda t: t.downloads + t.stars * 10, reverse=True)
        
        return results
    
    def get_template(self, template_id: str) -> Optional[MarketplaceTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def get_featured_templates(self, limit: int = 10) -> List[MarketplaceTemplate]:
        """Get featured/popular templates"""
        # Sort by combined score (rating * downloads * stars)
        all_templates = list(self.templates.values())
        all_templates.sort(
            key=lambda t: t.rating * (t.downloads + 1) * (t.stars + 1),
            reverse=True
        )
        return all_templates[:limit]
    
    def get_categories(self) -> Dict[TemplateCategory, int]:
        """Get categories with template counts"""
        category_counts = {}
        for category in TemplateCategory:
            count = len([t for t in self.templates.values() if t.category == category])
            if count > 0:
                category_counts[category] = count
        return category_counts
    
    def get_trending_templates(self, days: int = 7, limit: int = 10) -> List[MarketplaceTemplate]:
        """Get trending templates based on recent activity"""
        # For MVP, return templates updated recently
        cutoff_time = time.time() - (days * 24 * 3600)
        recent_templates = [
            t for t in self.templates.values()
            if t.updated_at > cutoff_time
        ]
        recent_templates.sort(key=lambda t: t.updated_at, reverse=True)
        return recent_templates[:limit]
    
    def add_template(self, template: MarketplaceTemplate) -> bool:
        """Add template to marketplace"""
        if template.id in self.templates:
            self.logger.warning(f"Template {template.id} already exists")
            return False
        
        self.templates[template.id] = template
        self.categories[template.category].append(template.id)
        
        # Save marketplace data
        self._save_marketplace_data()
        
        self.logger.info(f"Added template {template.id} to marketplace")
        return True
    
    def update_template_stats(self, template_id: str, 
                            downloads: int = 0,
                            stars: int = 0,
                            rating: Optional[float] = None):
        """Update template statistics"""
        template = self.templates.get(template_id)
        if not template:
            return
        
        template.downloads += downloads
        template.stars += stars
        if rating is not None:
            # Simple average for MVP
            template.rating = (template.rating + rating) / 2
        
        template.updated_at = time.time()
        self._save_marketplace_data()
    
    def _initialize_popular_templates(self):
        """Initialize marketplace with popular templates"""
        popular_templates = [
            MarketplaceTemplate(
                id="wordpress-optimized",
                name="wordpress",
                display_name="WordPress Optimized",
                description="Production-ready WordPress with Redis cache, Traefik support, and performance optimizations",
                category=TemplateCategory.CMS,
                version="1.2.0",
                author="BlastDock Team",
                source="official",
                downloads=1523,
                stars=89,
                rating=4.8,
                services=["wordpress", "mysql", "redis"],
                tags=["cms", "blog", "php", "mysql", "redis", "traefik"],
                traefik_compatible=True,
                validation_score=98.5,
                security_score=95.0,
                repository_url="https://github.com/blastdock/templates/wordpress",
                documentation_url="https://docs.blastdock.com/templates/wordpress"
            ),
            MarketplaceTemplate(
                id="nextcloud-secure",
                name="nextcloud",
                display_name="Nextcloud Secure Edition",
                description="Self-hosted cloud storage with enhanced security, automatic backups, and Traefik integration",
                category=TemplateCategory.PRODUCTIVITY,
                version="2.0.0",
                author="BlastDock Team",
                source="official",
                downloads=892,
                stars=67,
                rating=4.9,
                services=["nextcloud", "mariadb", "redis"],
                tags=["storage", "cloud", "productivity", "secure", "traefik"],
                traefik_compatible=True,
                validation_score=99.0,
                security_score=98.0
            ),
            MarketplaceTemplate(
                id="ghost-blog",
                name="ghost",
                display_name="Ghost Blog Platform",
                description="Modern publishing platform with SEO optimization and Traefik support",
                category=TemplateCategory.CMS,
                version="1.5.0",
                author="BlastDock Team",
                source="official",
                downloads=654,
                stars=45,
                rating=4.7,
                services=["ghost", "mysql"],
                tags=["blog", "cms", "nodejs", "mysql", "traefik"],
                traefik_compatible=True,
                validation_score=97.0,
                security_score=92.0
            ),
            MarketplaceTemplate(
                id="grafana-monitoring",
                name="grafana",
                display_name="Grafana Monitoring Stack",
                description="Complete monitoring solution with Grafana, Prometheus, and Loki",
                category=TemplateCategory.MONITORING,
                version="1.8.0",
                author="BlastDock Team",
                source="official",
                downloads=1102,
                stars=78,
                rating=4.9,
                services=["grafana", "prometheus", "loki"],
                tags=["monitoring", "metrics", "logs", "dashboards", "traefik"],
                traefik_compatible=True,
                validation_score=98.0,
                security_score=94.0
            ),
            MarketplaceTemplate(
                id="nginx-static",
                name="nginx",
                display_name="Nginx Static Site",
                description="High-performance static site hosting with automatic SSL",
                category=TemplateCategory.WEB,
                version="1.0.0",
                author="BlastDock Team",
                source="official",
                downloads=2341,
                stars=125,
                rating=4.6,
                services=["nginx"],
                tags=["web", "static", "nginx", "performance", "traefik"],
                traefik_compatible=True,
                validation_score=100.0,
                security_score=96.0
            ),
            MarketplaceTemplate(
                id="postgresql-ha",
                name="postgresql",
                display_name="PostgreSQL High Availability",
                description="PostgreSQL database with replication and automatic backups",
                category=TemplateCategory.DATABASE,
                version="1.3.0",
                author="Community",
                source="community",
                downloads=432,
                stars=34,
                rating=4.5,
                services=["postgres-primary", "postgres-replica", "pgbouncer"],
                tags=["database", "postgresql", "ha", "replication"],
                traefik_compatible=False,
                validation_score=95.0,
                security_score=97.0
            ),
            MarketplaceTemplate(
                id="mattermost-team",
                name="mattermost",
                display_name="Mattermost Team Chat",
                description="Open-source Slack alternative with file sharing and integrations",
                category=TemplateCategory.COMMUNICATION,
                version="1.1.0",
                author="Community",
                source="community",
                downloads=321,
                stars=28,
                rating=4.4,
                services=["mattermost", "postgresql"],
                tags=["chat", "communication", "team", "collaboration"],
                traefik_compatible=True,
                validation_score=93.0,
                security_score=91.0
            )
        ]
        
        for template in popular_templates:
            self.templates[template.id] = template
            self.categories[template.category].append(template.id)
    
    def _load_marketplace_data(self):
        """Load marketplace data from disk"""
        data_file = self.marketplace_dir / 'marketplace.json'
        if data_file.exists():
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                
                # Load templates
                for template_data in data.get('templates', []):
                    # Convert category string back to enum
                    if 'category' in template_data:
                        template_data['category'] = TemplateCategory(template_data['category'])
                    
                    template = MarketplaceTemplate(**template_data)
                    self.templates[template.id] = template
                    self.categories[template.category].append(template.id)
                
                self.logger.info(f"Loaded {len(self.templates)} templates from marketplace data")
                
            except Exception as e:
                self.logger.error(f"Failed to load marketplace data: {e}")
    
    def _save_marketplace_data(self):
        """Save marketplace data to disk"""
        data_file = self.marketplace_dir / 'marketplace.json'
        
        try:
            data = {
                'version': '1.0',
                'updated_at': time.time(),
                'templates': [
                    template.to_dict() for template in self.templates.values()
                ]
            }
            
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug("Saved marketplace data")
            
        except Exception as e:
            self.logger.error(f"Failed to save marketplace data: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        total_downloads = sum(t.downloads for t in self.templates.values())
        total_stars = sum(t.stars for t in self.templates.values())
        avg_rating = sum(t.rating for t in self.templates.values()) / len(self.templates) if self.templates else 0
        
        return {
            'total_templates': len(self.templates),
            'total_downloads': total_downloads,
            'total_stars': total_stars,
            'average_rating': round(avg_rating, 2),
            'categories': self.get_categories(),
            'sources': {
                'official': len([t for t in self.templates.values() if t.source == 'official']),
                'community': len([t for t in self.templates.values() if t.source == 'community']),
                'local': len([t for t in self.templates.values() if t.source == 'local'])
            },
            'traefik_compatible': len([t for t in self.templates.values() if t.traefik_compatible])
        }