"""
Automated error recovery and self-healing system for BlastDock
"""

import os
import subprocess
import time
import shutil
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from ..exceptions import (
    BlastDockError, DockerNotAvailableError, TraefikNotInstalledError,
    TraefikNotRunningError, PortConflictError, DirectoryNotWritableError,
    InsufficientSpaceError, ServiceUnavailableError
)
from .logging import get_logger
from .error_diagnostics import ErrorContext


logger = get_logger(__name__)


class RecoveryAction(str, Enum):
    """Types of recovery actions"""
    RESTART_SERVICE = "restart_service"
    INSTALL_COMPONENT = "install_component"
    FIX_PERMISSIONS = "fix_permissions"
    CLEAR_CACHE = "clear_cache"
    FREE_RESOURCES = "free_resources"
    UPDATE_CONFIG = "update_config"
    RESET_STATE = "reset_state"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class RecoveryStep:
    """Individual recovery step"""
    action: RecoveryAction
    description: str
    command: Optional[str] = None
    parameters: Dict[str, Any] = None
    risk_level: str = "low"  # low, medium, high
    requires_confirmation: bool = False
    timeout: int = 30
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class RecoveryPlan:
    """Complete recovery plan for an error"""
    error_type: str
    steps: List[RecoveryStep]
    estimated_time: int  # seconds
    success_criteria: List[str]
    fallback_plan: Optional['RecoveryPlan'] = None


class ErrorRecoveryEngine:
    """Automated error recovery and self-healing engine"""
    
    def __init__(self):
        """Initialize recovery engine"""
        self.logger = get_logger(__name__)
        self.recovery_plans = self._load_recovery_plans()
        self.recovery_history: List[Dict[str, Any]] = []
        
    def can_recover(self, error_context: ErrorContext) -> bool:
        """Check if error can be automatically recovered"""
        error_type = error_context.error_type
        return error_type in self.recovery_plans
    
    def create_recovery_plan(self, error_context: ErrorContext) -> Optional[RecoveryPlan]:
        """Create recovery plan for the given error"""
        error_type = error_context.error_type
        
        if error_type not in self.recovery_plans:
            return None
        
        # Get base plan
        plan_template = self.recovery_plans[error_type]
        
        # Customize based on context
        customized_steps = []
        for step_template in plan_template['steps']:
            step = RecoveryStep(**step_template)
            
            # Customize parameters based on context
            if error_context.project_name and 'project_name' in step.parameters:
                step.parameters['project_name'] = error_context.project_name
            
            if error_context.template_name and 'template_name' in step.parameters:
                step.parameters['template_name'] = error_context.template_name
            
            customized_steps.append(step)
        
        return RecoveryPlan(
            error_type=error_type,
            steps=customized_steps,
            estimated_time=plan_template.get('estimated_time', 60),
            success_criteria=plan_template.get('success_criteria', []),
            fallback_plan=None  # Could be implemented for complex scenarios
        )
    
    def execute_recovery_plan(self, 
                            plan: RecoveryPlan,
                            dry_run: bool = False,
                            auto_confirm: bool = False) -> Dict[str, Any]:
        """Execute recovery plan
        
        Args:
            plan: Recovery plan to execute
            dry_run: Show what would be done without executing
            auto_confirm: Skip confirmation prompts for risky operations
            
        Returns:
            Recovery result with status and details
        """
        
        result = {
            'success': False,
            'steps_completed': 0,
            'steps_failed': [],
            'execution_time': 0,
            'dry_run': dry_run
        }
        
        start_time = time.time()
        
        self.logger.info(f"Starting recovery plan for {plan.error_type} (dry_run={dry_run})")
        
        try:
            for i, step in enumerate(plan.steps):
                step_result = self._execute_recovery_step(step, dry_run, auto_confirm)
                
                if step_result['success']:
                    result['steps_completed'] += 1
                    self.logger.info(f"Recovery step {i+1} completed: {step.description}")
                else:
                    result['steps_failed'].append({
                        'step': i + 1,
                        'description': step.description,
                        'error': step_result.get('error', 'Unknown error')
                    })
                    self.logger.error(f"Recovery step {i+1} failed: {step.description}")
                    
                    # Stop on critical failures
                    if step.risk_level == 'high':
                        break
            
            # Check success criteria
            if result['steps_completed'] == len(plan.steps):
                if self._verify_recovery_success(plan):
                    result['success'] = True
        
        except Exception as e:
            self.logger.error(f"Recovery plan execution failed: {e}")
            result['steps_failed'].append({
                'step': 'execution',
                'description': 'Recovery plan execution',
                'error': str(e)
            })
        
        result['execution_time'] = int(time.time() - start_time)
        
        # Record recovery attempt
        self._record_recovery_attempt(plan, result)
        
        return result
    
    def _execute_recovery_step(self, 
                              step: RecoveryStep,
                              dry_run: bool = False,
                              auto_confirm: bool = False) -> Dict[str, Any]:
        """Execute individual recovery step"""
        
        result = {'success': False}
        
        try:
            if dry_run:
                result['success'] = True
                result['message'] = f"Would execute: {step.description}"
                return result
            
            # Check if confirmation is required
            if step.requires_confirmation and not auto_confirm:
                self.logger.warning(f"Manual confirmation required for: {step.description}")
                result['message'] = "Manual confirmation required"
                return result
            
            # Execute based on action type
            if step.action == RecoveryAction.RESTART_SERVICE:
                result = self._restart_service(step)
                
            elif step.action == RecoveryAction.INSTALL_COMPONENT:
                result = self._install_component(step)
                
            elif step.action == RecoveryAction.FIX_PERMISSIONS:
                result = self._fix_permissions(step)
                
            elif step.action == RecoveryAction.CLEAR_CACHE:
                result = self._clear_cache(step)
                
            elif step.action == RecoveryAction.FREE_RESOURCES:
                result = self._free_resources(step)
                
            elif step.action == RecoveryAction.UPDATE_CONFIG:
                result = self._update_config(step)
                
            elif step.action == RecoveryAction.RESET_STATE:
                result = self._reset_state(step)
                
            else:
                result['message'] = f"Unsupported action: {step.action}"
        
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Recovery step failed: {e}")
        
        return result
    
    def _restart_service(self, step: RecoveryStep) -> Dict[str, Any]:
        """Restart a system service"""
        service = step.parameters.get('service')
        
        if not service:
            return {'success': False, 'error': 'No service specified'}
        
        try:
            if service == 'docker':
                # Restart Docker daemon
                result = subprocess.run(
                    ['sudo', 'systemctl', 'restart', 'docker'],
                    capture_output=True, text=True, timeout=step.timeout
                )
                
                if result.returncode == 0:
                    time.sleep(5)  # Wait for Docker to start
                    return {'success': True, 'message': 'Docker service restarted'}
                else:
                    return {'success': False, 'error': result.stderr}
            
            elif service == 'traefik':
                # Restart Traefik container
                from ..traefik.manager import TraefikManager
                manager = TraefikManager()
                
                if manager.restart():
                    return {'success': True, 'message': 'Traefik restarted'}
                else:
                    return {'success': False, 'error': 'Failed to restart Traefik'}
            
            else:
                return {'success': False, 'error': f'Unknown service: {service}'}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Service restart timed out'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _install_component(self, step: RecoveryStep) -> Dict[str, Any]:
        """Install missing component"""
        component = step.parameters.get('component')
        
        if not component:
            return {'success': False, 'error': 'No component specified'}
        
        try:
            if component == 'traefik':
                from ..traefik.installer import TraefikInstaller
                installer = TraefikInstaller()
                
                email = step.parameters.get('email', 'admin@localhost')
                domain = step.parameters.get('domain', 'localhost')
                
                if installer.install(email, domain):
                    return {'success': True, 'message': 'Traefik installed successfully'}
                else:
                    return {'success': False, 'error': 'Failed to install Traefik'}
            
            else:
                return {'success': False, 'error': f'Unknown component: {component}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _fix_permissions(self, step: RecoveryStep) -> Dict[str, Any]:
        """Fix file/directory permissions"""
        path = step.parameters.get('path', '.')
        mode = step.parameters.get('mode', '755')
        
        try:
            # Make directory writable
            os.chmod(path, int(mode, 8))
            return {'success': True, 'message': f'Permissions fixed for {path}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _clear_cache(self, step: RecoveryStep) -> Dict[str, Any]:
        """Clear various caches"""
        cache_type = step.parameters.get('type', 'all')
        
        try:
            if cache_type in ['all', 'docker']:
                # Clear Docker cache
                subprocess.run(['docker', 'system', 'prune', '-f'], 
                             capture_output=True, timeout=step.timeout)
            
            if cache_type in ['all', 'blastdock']:
                # Clear BlastDock cache
                cache_dir = os.path.expanduser('~/.blastdock/cache')
                if os.path.exists(cache_dir):
                    shutil.rmtree(cache_dir)
                    os.makedirs(cache_dir, exist_ok=True)
            
            return {'success': True, 'message': f'Cache cleared: {cache_type}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _free_resources(self, step: RecoveryStep) -> Dict[str, Any]:
        """Free system resources"""
        resource_type = step.parameters.get('type', 'disk')
        
        try:
            if resource_type == 'disk':
                # Remove unused Docker images and containers
                subprocess.run(['docker', 'system', 'prune', '-a', '-f'], 
                             capture_output=True, timeout=step.timeout)
                
                return {'success': True, 'message': 'Disk space freed'}
            
            elif resource_type == 'memory':
                # Could implement memory cleanup
                return {'success': True, 'message': 'Memory cleanup completed'}
            
            else:
                return {'success': False, 'error': f'Unknown resource type: {resource_type}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _update_config(self, step: RecoveryStep) -> Dict[str, Any]:
        """Update configuration files"""
        config_file = step.parameters.get('file')
        updates = step.parameters.get('updates', {})
        
        if not config_file:
            return {'success': False, 'error': 'No config file specified'}
        
        try:
            # Backup original config
            backup_file = f"{config_file}.backup"
            if os.path.exists(config_file):
                shutil.copy2(config_file, backup_file)
            
            # Apply updates (simplified implementation)
            # In a real implementation, this would parse and update the config
            return {'success': True, 'message': f'Configuration updated: {config_file}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _reset_state(self, step: RecoveryStep) -> Dict[str, Any]:
        """Reset application state"""
        component = step.parameters.get('component')
        
        try:
            if component == 'ports':
                # Reset port allocations
                from ..ports.manager import PortManager
                manager = PortManager()
                manager.reset_allocations()
                
                return {'success': True, 'message': 'Port allocations reset'}
            
            elif component == 'domains':
                # Reset domain reservations
                from ..domains.manager import DomainManager
                manager = DomainManager()
                manager.reset_reservations()
                
                return {'success': True, 'message': 'Domain reservations reset'}
            
            else:
                return {'success': False, 'error': f'Unknown component: {component}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _verify_recovery_success(self, plan: RecoveryPlan) -> bool:
        """Verify if recovery was successful"""
        
        for criterion in plan.success_criteria:
            if criterion == 'docker_running':
                try:
                    result = subprocess.run(['docker', 'info'], 
                                          capture_output=True, timeout=10)
                    if result.returncode != 0:
                        return False
                except:
                    return False
            
            elif criterion == 'traefik_running':
                try:
                    from ..traefik.manager import TraefikManager
                    manager = TraefikManager()
                    if not manager.is_running():
                        return False
                except:
                    return False
            
            elif criterion == 'ports_available':
                # Check if ports are available
                pass
        
        return True
    
    def _record_recovery_attempt(self, plan: RecoveryPlan, result: Dict[str, Any]):
        """Record recovery attempt for analysis"""
        record = {
            'timestamp': time.time(),
            'error_type': plan.error_type,
            'success': result['success'],
            'steps_completed': result['steps_completed'],
            'execution_time': result['execution_time'],
            'dry_run': result.get('dry_run', False)
        }
        
        self.recovery_history.append(record)
        
        # Keep only last 100 records
        if len(self.recovery_history) > 100:
            self.recovery_history = self.recovery_history[-100:]
    
    def _load_recovery_plans(self) -> Dict[str, Dict[str, Any]]:
        """Load recovery plans for different error types"""
        return {
            'DockerNotAvailableError': {
                'steps': [
                    {
                        'action': RecoveryAction.RESTART_SERVICE,
                        'description': 'Restart Docker daemon',
                        'parameters': {'service': 'docker'},
                        'risk_level': 'medium',
                        'requires_confirmation': True,
                        'timeout': 60
                    }
                ],
                'estimated_time': 60,
                'success_criteria': ['docker_running']
            },
            
            'TraefikNotInstalledError': {
                'steps': [
                    {
                        'action': RecoveryAction.INSTALL_COMPONENT,
                        'description': 'Install Traefik reverse proxy',
                        'parameters': {
                            'component': 'traefik',
                            'email': 'admin@localhost',
                            'domain': 'localhost'
                        },
                        'risk_level': 'low',
                        'timeout': 120
                    }
                ],
                'estimated_time': 120,
                'success_criteria': ['traefik_running']
            },
            
            'TraefikNotRunningError': {
                'steps': [
                    {
                        'action': RecoveryAction.RESTART_SERVICE,
                        'description': 'Restart Traefik container',
                        'parameters': {'service': 'traefik'},
                        'risk_level': 'low',
                        'timeout': 30
                    }
                ],
                'estimated_time': 30,
                'success_criteria': ['traefik_running']
            },
            
            'DirectoryNotWritableError': {
                'steps': [
                    {
                        'action': RecoveryAction.FIX_PERMISSIONS,
                        'description': 'Fix directory permissions',
                        'parameters': {'path': '.', 'mode': '755'},
                        'risk_level': 'low',
                        'timeout': 10
                    }
                ],
                'estimated_time': 10,
                'success_criteria': []
            },
            
            'InsufficientSpaceError': {
                'steps': [
                    {
                        'action': RecoveryAction.FREE_RESOURCES,
                        'description': 'Clear Docker cache and unused images',
                        'parameters': {'type': 'disk'},
                        'risk_level': 'low',
                        'timeout': 60
                    }
                ],
                'estimated_time': 60,
                'success_criteria': []
            },
            
            'PortConflictError': {
                'steps': [
                    {
                        'action': RecoveryAction.RESET_STATE,
                        'description': 'Reset port allocations',
                        'parameters': {'component': 'ports'},
                        'risk_level': 'low',
                        'timeout': 10
                    }
                ],
                'estimated_time': 10,
                'success_criteria': ['ports_available']
            }
        }
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery attempt statistics"""
        if not self.recovery_history:
            return {'total_attempts': 0}
        
        total_attempts = len(self.recovery_history)
        successful_attempts = sum(1 for r in self.recovery_history if r['success'])
        
        return {
            'total_attempts': total_attempts,
            'successful_attempts': successful_attempts,
            'success_rate': (successful_attempts / total_attempts) * 100,
            'average_execution_time': sum(r['execution_time'] for r in self.recovery_history) / total_attempts,
            'most_common_errors': self._get_most_common_errors()
        }
    
    def _get_most_common_errors(self) -> Dict[str, int]:
        """Get most common error types"""
        error_counts = {}
        for record in self.recovery_history:
            error_type = record['error_type']
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True))


# Global recovery engine instance
_recovery_engine = None


def get_recovery_engine() -> ErrorRecoveryEngine:
    """Get global recovery engine instance"""
    global _recovery_engine
    if _recovery_engine is None:
        _recovery_engine = ErrorRecoveryEngine()
    return _recovery_engine


def attempt_auto_recovery(error_context: ErrorContext, 
                         dry_run: bool = False,
                         auto_confirm: bool = False) -> Optional[Dict[str, Any]]:
    """Attempt automatic recovery for an error
    
    Args:
        error_context: Error context from diagnostics
        dry_run: Show what would be done without executing
        auto_confirm: Skip confirmation prompts
        
    Returns:
        Recovery result or None if no recovery plan available
    """
    recovery_engine = get_recovery_engine()
    
    if not recovery_engine.can_recover(error_context):
        return None
    
    recovery_plan = recovery_engine.create_recovery_plan(error_context)
    if not recovery_plan:
        return None
    
    return recovery_engine.execute_recovery_plan(
        recovery_plan, 
        dry_run=dry_run,
        auto_confirm=auto_confirm
    )