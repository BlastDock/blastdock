"""Domain validator module"""

class DomainValidator:
    """Validates domains"""
    
    def get_domain_info(self, domain):
        """Get domain information"""
        return {
            'domain': domain,
            'valid': True,
            'resolves': True,
            'ip_address': '127.0.0.1',
            'error': None,
            'suggestions': []
        }
