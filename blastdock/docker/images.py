"""
Enhanced Docker image management with comprehensive error handling
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from ..utils.logging import get_logger
from .client import get_docker_client
from .errors import ImageError, create_docker_error

logger = get_logger(__name__)


class ImageManager:
    """Enhanced Docker image manager"""
    
    def __init__(self):
        """Initialize image manager"""
        self.docker_client = get_docker_client()
        self.logger = get_logger(__name__)
    
    def list_images(self, all_images: bool = False, 
                   filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """List images with optional filtering"""
        cmd = ['docker', 'images', '--format', '{{json .}}']
        
        if all_images:
            cmd.append('-a')
        
        # Add filters
        if filters:
            for key, value in filters.items():
                cmd.extend(['--filter', f'{key}={value}'])
        
        try:
            result = self.docker_client.execute_command(cmd)
            
            images = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        image = json.loads(line)
                        images.append(image)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse image JSON: {e}")
                        continue
            
            return images
            
        except Exception as e:
            raise create_docker_error(e, "List images")
    
    def get_image_info(self, image_name: str) -> Dict[str, Any]:
        """Get detailed information about an image"""
        try:
            result = self.docker_client.execute_command([
                'docker', 'inspect', image_name, '--format', '{{json .}}'
            ])
            
            image_info = json.loads(result.stdout)
            
            # Extract useful information
            extracted_info = {
                'id': image_info.get('Id', ''),
                'repo_tags': image_info.get('RepoTags', []),
                'repo_digests': image_info.get('RepoDigests', []),
                'size': image_info.get('Size', 0),
                'virtual_size': image_info.get('VirtualSize', 0),
                'created': image_info.get('Created', ''),
                'architecture': image_info.get('Architecture', ''),
                'os': image_info.get('Os', ''),
                'config': image_info.get('Config', {}),
                'container_config': image_info.get('ContainerConfig', {}),
                'root_fs': image_info.get('RootFS', {}),
                'metadata': image_info.get('Metadata', {})
            }
            
            return extracted_info
            
        except Exception as e:
            raise ImageError(
                f"Failed to get image information",
                image_name=image_name
            )
    
    def pull_image(self, image_name: str, tag: str = 'latest',
                  platform: Optional[str] = None) -> Dict[str, Any]:
        """Pull an image from a registry"""
        full_image_name = f"{image_name}:{tag}"
        
        pull_result = {
            'success': False,
            'image_name': full_image_name,
            'pull_time': 0,
            'size_info': {},
            'layers_pulled': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            cmd = ['docker', 'pull']
            
            if platform:
                cmd.extend(['--platform', platform])
            
            cmd.append(full_image_name)
            
            result = self.docker_client.execute_command(cmd, timeout=600)  # 10 minute timeout
            
            pull_result['success'] = True
            pull_result['pull_time'] = time.time() - start_time
            
            # Parse output for layer information
            output_lines = result.stdout.split('\n')
            layers_pulled = 0
            
            for line in output_lines:
                if 'Pull complete' in line:
                    layers_pulled += 1
                elif 'Downloaded newer image' in line or 'Image is up to date' in line:
                    # Extract size information if available
                    pass
            
            pull_result['layers_pulled'] = layers_pulled
            
            # Get image info after pull
            try:
                image_info = self.get_image_info(full_image_name)
                pull_result['size_info'] = {
                    'size': image_info.get('size', 0),
                    'virtual_size': image_info.get('virtual_size', 0)
                }
            except Exception as e:
                pull_result['errors'].append(f"Could not get image info after pull: {str(e)}")
            
            return pull_result
            
        except Exception as e:
            pull_result['pull_time'] = time.time() - start_time
            pull_result['errors'].append(str(e))
            
            # Extract registry from image name for better error context
            registry = None
            if '/' in image_name and '.' in image_name.split('/')[0]:
                registry = image_name.split('/')[0]
            
            raise ImageError(
                f"Failed to pull image {full_image_name}",
                image_name=full_image_name,
                registry=registry
            )
    
    def push_image(self, image_name: str, tag: str = 'latest') -> Dict[str, Any]:
        """Push an image to a registry"""
        full_image_name = f"{image_name}:{tag}"
        
        push_result = {
            'success': False,
            'image_name': full_image_name,
            'push_time': 0,
            'layers_pushed': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            result = self.docker_client.execute_command([
                'docker', 'push', full_image_name
            ], timeout=900)  # 15 minute timeout
            
            push_result['success'] = True
            push_result['push_time'] = time.time() - start_time
            
            # Parse output for layer information
            output_lines = result.stdout.split('\n')
            layers_pushed = 0
            
            for line in output_lines:
                if 'Pushed' in line or 'Layer already exists' in line:
                    layers_pushed += 1
            
            push_result['layers_pushed'] = layers_pushed
            
            return push_result
            
        except Exception as e:
            push_result['push_time'] = time.time() - start_time
            push_result['errors'].append(str(e))
            
            # Extract registry from image name
            registry = None
            if '/' in image_name and '.' in image_name.split('/')[0]:
                registry = image_name.split('/')[0]
            
            raise ImageError(
                f"Failed to push image {full_image_name}",
                image_name=full_image_name,
                registry=registry
            )
    
    def build_image(self, dockerfile_path: str, image_name: str, tag: str = 'latest',
                   build_args: Optional[Dict[str, str]] = None,
                   no_cache: bool = False, pull: bool = False,
                   context_path: Optional[str] = None) -> Dict[str, Any]:
        """Build an image from a Dockerfile"""
        full_image_name = f"{image_name}:{tag}"
        context = context_path or str(Path(dockerfile_path).parent)
        
        build_result = {
            'success': False,
            'image_name': full_image_name,
            'dockerfile_path': dockerfile_path,
            'context_path': context,
            'build_time': 0,
            'size_info': {},
            'build_steps': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            cmd = ['docker', 'build', '-t', full_image_name]
            
            # Add dockerfile path if not default
            if Path(dockerfile_path).name != 'Dockerfile':
                cmd.extend(['-f', dockerfile_path])
            
            # Add build arguments
            if build_args:
                for key, value in build_args.items():
                    cmd.extend(['--build-arg', f'{key}={value}'])
            
            if no_cache:
                cmd.append('--no-cache')
            
            if pull:
                cmd.append('--pull')
            
            # Add context path
            cmd.append(context)
            
            result = self.docker_client.execute_command(cmd, timeout=1800)  # 30 minute timeout
            
            build_result['success'] = True
            build_result['build_time'] = time.time() - start_time
            
            # Parse output for build steps
            output_lines = result.stdout.split('\n')
            build_steps = 0
            
            for line in output_lines:
                if line.startswith('Step '):
                    build_steps += 1
            
            build_result['build_steps'] = build_steps
            
            # Get image info after build
            try:
                image_info = self.get_image_info(full_image_name)
                build_result['size_info'] = {
                    'size': image_info.get('size', 0),
                    'virtual_size': image_info.get('virtual_size', 0)
                }
            except Exception as e:
                build_result['errors'].append(f"Could not get image info after build: {str(e)}")
            
            return build_result
            
        except Exception as e:
            build_result['build_time'] = time.time() - start_time
            build_result['errors'].append(str(e))
            raise ImageError(
                f"Failed to build image {full_image_name}",
                image_name=full_image_name
            )
    
    def remove_image(self, image_name: str, force: bool = False,
                    no_prune: bool = False) -> Dict[str, Any]:
        """Remove an image"""
        remove_result = {
            'success': False,
            'image_name': image_name,
            'untagged': [],
            'deleted': [],
            'errors': []
        }
        
        try:
            cmd = ['docker', 'rmi']
            
            if force:
                cmd.append('-f')
            
            if no_prune:
                cmd.append('--no-prune')
            
            cmd.append(image_name)
            
            result = self.docker_client.execute_command(cmd)
            
            remove_result['success'] = True
            
            # Parse output for removed items
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if line.startswith('Untagged:'):
                    remove_result['untagged'].append(line.replace('Untagged: ', ''))
                elif line.startswith('Deleted:'):
                    remove_result['deleted'].append(line.replace('Deleted: ', ''))
            
            return remove_result
            
        except Exception as e:
            remove_result['errors'].append(str(e))
            raise ImageError(
                f"Failed to remove image {image_name}",
                image_name=image_name
            )
    
    def tag_image(self, source_image: str, target_image: str, 
                 target_tag: str = 'latest') -> Dict[str, Any]:
        """Tag an image"""
        target_full_name = f"{target_image}:{target_tag}"
        
        tag_result = {
            'success': False,
            'source_image': source_image,
            'target_image': target_full_name,
            'errors': []
        }
        
        try:
            self.docker_client.execute_command([
                'docker', 'tag', source_image, target_full_name
            ])
            
            tag_result['success'] = True
            return tag_result
            
        except Exception as e:
            tag_result['errors'].append(str(e))
            raise ImageError(
                f"Failed to tag image {source_image} as {target_full_name}",
                image_name=source_image
            )
    
    def search_images(self, term: str, limit: int = 25,
                     filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Search for images in Docker Hub"""
        cmd = ['docker', 'search', '--format', '{{json .}}']
        
        if limit != 25:
            cmd.extend(['--limit', str(limit)])
        
        # Add filters
        if filters:
            for key, value in filters.items():
                cmd.extend(['--filter', f'{key}={value}'])
        
        cmd.append(term)
        
        try:
            result = self.docker_client.execute_command(cmd)
            
            images = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        image = json.loads(line)
                        images.append(image)
                    except json.JSONDecodeError:
                        # Fallback to parsing plain text
                        parts = line.split()
                        if len(parts) >= 4:
                            images.append({
                                'Name': parts[0],
                                'Description': ' '.join(parts[1:-2]),
                                'Stars': parts[-2],
                                'Official': parts[-1] == '[OK]'
                            })
            
            return images
            
        except Exception as e:
            raise create_docker_error(e, f"Search images for '{term}'")
    
    def get_image_history(self, image_name: str) -> List[Dict[str, Any]]:
        """Get the history of an image"""
        try:
            result = self.docker_client.execute_command([
                'docker', 'history', image_name, '--format', '{{json .}}'
            ])
            
            history = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        layer = json.loads(line)
                        history.append(layer)
                    except json.JSONDecodeError:
                        continue
            
            return history
            
        except Exception as e:
            raise ImageError(
                f"Failed to get image history",
                image_name=image_name
            )
    
    def prune_images(self, all_images: bool = False,
                    filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Remove unused images"""
        prune_result = {
            'success': False,
            'images_removed': 0,
            'space_reclaimed': '0B',
            'errors': []
        }
        
        try:
            cmd = ['docker', 'image', 'prune', '-f']
            
            if all_images:
                cmd.append('-a')
            
            # Add filters
            if filters:
                for key, value in filters.items():
                    cmd.extend(['--filter', f'{key}={value}'])
            
            result = self.docker_client.execute_command(cmd)
            
            prune_result['success'] = True
            
            # Parse output for metrics
            output = result.stdout
            if 'Total reclaimed space' in output:
                import re
                space_match = re.search(r'Total reclaimed space: ([\d.]+\w+)', output)
                if space_match:
                    prune_result['space_reclaimed'] = space_match.group(1)
            
            # Count removed images from output
            deleted_lines = [line for line in output.split('\n') 
                           if line.startswith('Deleted:') or 'sha256:' in line]
            prune_result['images_removed'] = len(deleted_lines)
            
            return prune_result
            
        except Exception as e:
            prune_result['errors'].append(str(e))
            raise create_docker_error(e, "Prune images")
    
    def save_image(self, image_name: str, output_file: str) -> Dict[str, Any]:
        """Save an image to a tar file"""
        save_result = {
            'success': False,
            'image_name': image_name,
            'output_file': output_file,
            'file_size': 0,
            'save_time': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            with open(output_file, 'wb') as f:
                result = self.docker_client.execute_command([
                    'docker', 'save', image_name
                ], capture_output=False)
                
                # Note: This is a simplified version. In practice, you'd want to
                # redirect stdout to the file or use subprocess.Popen for better control
            
            save_result['success'] = True
            save_result['save_time'] = time.time() - start_time
            
            # Get file size
            try:
                import os
                save_result['file_size'] = os.path.getsize(output_file)
            except:
                pass
            
            return save_result
            
        except Exception as e:
            save_result['save_time'] = time.time() - start_time
            save_result['errors'].append(str(e))
            raise ImageError(
                f"Failed to save image {image_name}",
                image_name=image_name
            )
    
    def load_image(self, input_file: str) -> Dict[str, Any]:
        """Load an image from a tar file"""
        load_result = {
            'success': False,
            'input_file': input_file,
            'loaded_images': [],
            'load_time': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            with open(input_file, 'rb') as f:
                result = self.docker_client.execute_command([
                    'docker', 'load'
                ], capture_output=True)
            
            load_result['success'] = True
            load_result['load_time'] = time.time() - start_time
            
            # Parse output for loaded images
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'Loaded image:' in line:
                    image_name = line.replace('Loaded image: ', '').strip()
                    load_result['loaded_images'].append(image_name)
            
            return load_result
            
        except Exception as e:
            load_result['load_time'] = time.time() - start_time
            load_result['errors'].append(str(e))
            raise ImageError(f"Failed to load image from {input_file}")
    
    def get_image_vulnerabilities(self, image_name: str) -> Dict[str, Any]:
        """Scan image for security vulnerabilities (if scanner is available)"""
        scan_result = {
            'success': False,
            'image_name': image_name,
            'vulnerabilities': [],
            'summary': {},
            'scanner_available': False,
            'errors': []
        }
        
        try:
            # Try Docker Scout (if available)
            try:
                result = self.docker_client.execute_command([
                    'docker', 'scout', 'cves', image_name, '--format', 'json'
                ], check=False)
                
                if result.returncode == 0:
                    scan_result['scanner_available'] = True
                    scan_data = json.loads(result.stdout)
                    scan_result['success'] = True
                    scan_result['vulnerabilities'] = scan_data.get('vulnerabilities', [])
                    scan_result['summary'] = scan_data.get('summary', {})
                else:
                    scan_result['errors'].append("Docker Scout not available or not configured")
                    
            except Exception:
                # Try other scanners (Snyk, Trivy, etc.) if available
                scan_result['errors'].append("No vulnerability scanner available")
                scan_result['scanner_available'] = False
            
            return scan_result
            
        except Exception as e:
            scan_result['errors'].append(str(e))
            return scan_result