"""Web dashboard module (Flask optional)"""

try:
    from flask import Flask, render_template_string, jsonify, request
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from ..utils.logging import get_logger

logger = get_logger(__name__)

class WebDashboard:
    """Web dashboard for monitoring"""
    
    def __init__(self):
        self.logger = logger
        self.app = None
        
        if FLASK_AVAILABLE:
            self._setup_flask()
        else:
            logger.warning("Flask not available - web dashboard disabled")
    
    def _setup_flask(self):
        """Setup Flask app"""
        self.app = Flask(__name__)
        CORS(self.app)
        self._register_routes()
    
    def _register_routes(self):
        """Register Flask routes"""
        if not self.app:
            return
        
        @self.app.route('/')
        def dashboard():
            return "BlastDock Dashboard"
        
        @self.app.route('/api/status')
        def status():
            return jsonify({'status': 'ok'})
    
    def start_dashboard(self, host='127.0.0.1', port=5000, debug=False):
        """Start the dashboard"""
        if not FLASK_AVAILABLE:
            logger.error("Cannot start dashboard - Flask not installed")
            return False
        
        if self.app:
            self.app.run(host=host, port=port, debug=debug)
            return True
        return False
    
    def get_dashboard_status(self):
        """Get dashboard status"""
        return {
            'flask_available': FLASK_AVAILABLE,
            'dashboard_running': self.app is not None,
            'host': '127.0.0.1',
            'port': 5000
        }

_dashboard = None

def get_web_dashboard():
    """Get web dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = WebDashboard()
    return _dashboard
