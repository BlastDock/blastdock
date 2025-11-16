"""
Secure file operations for BlastDock
"""

import os
import shutil
import tempfile
import hashlib
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
import stat

from ..utils.logging import get_logger
from ..exceptions import SecurityError, FileOperationError


logger = get_logger(__name__)


class SecureFileOperations:
    """Secure file operations with validation and safety checks"""

    def __init__(self):
        """Initialize secure file operations"""
        self.logger = get_logger(__name__)

        # Allowed file extensions for different operations
        self.SAFE_CONFIG_EXTENSIONS = {
            ".yml",
            ".yaml",
            ".json",
            ".toml",
            ".ini",
            ".conf",
        }
        self.SAFE_TEMPLATE_EXTENSIONS = {".yml", ".yaml", ".json", ".j2", ".jinja"}
        self.SAFE_TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".log"}

        # Dangerous file extensions that should never be executed
        self.DANGEROUS_EXTENSIONS = {
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".scr",
            ".pif",
            ".vbs",
            ".js",
            ".jar",
            ".msi",
            ".deb",
            ".rpm",
            ".dmg",
            ".pkg",
            ".sh",
            ".ps1",
        }

        # Maximum file sizes (in bytes)
        self.MAX_CONFIG_SIZE = 10 * 1024 * 1024  # 10MB
        self.MAX_LOG_SIZE = 100 * 1024 * 1024  # 100MB
        self.MAX_TEMPLATE_SIZE = 5 * 1024 * 1024  # 5MB

    def validate_file_path(
        self,
        file_path: str,
        base_dir: Optional[str] = None,
        allowed_extensions: Optional[set] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate file path for security (BUG-004 FIX)"""
        if not file_path:
            return False, "File path cannot be empty"

        try:
            # Convert to Path object for better handling
            path_obj = Path(file_path)

            # Check for null bytes (path injection)
            if "\x00" in file_path:
                return False, "Null byte in path detected"

            # If base directory is specified, ensure path stays within it
            if base_dir:
                base_path = Path(base_dir).resolve()

                # Construct full path
                if path_obj.is_absolute():
                    # Absolute paths must be within base_dir
                    full_path = path_obj.resolve()
                else:
                    # Relative paths are joined with base_dir
                    full_path = (base_path / path_obj).resolve()

                # Check if the resolved path is within base directory
                # Use try/except to handle symlinks and non-existent paths safely
                try:
                    # Ensure the resolved path is relative to base_dir
                    full_path.relative_to(base_path)
                except ValueError:
                    return False, "Path escapes base directory"

                # Additional check: verify no symlinks point outside base_dir
                # Walk up the path checking each component
                current = full_path
                while current != base_path:
                    if current.is_symlink():
                        # Resolve symlink and check it's still within base
                        symlink_target = current.resolve()
                        try:
                            symlink_target.relative_to(base_path)
                        except ValueError:
                            return False, "Symlink points outside base directory"
                    try:
                        current = current.parent
                    except (OSError, RuntimeError):
                        return False, "Invalid path structure"
                    # Prevent infinite loop
                    if current == current.parent:
                        break
            else:
                # No base_dir specified - check for absolute paths and traversal
                # Resolve the path to get the real location
                try:
                    resolved_path = path_obj.resolve()
                    # Check for path traversal patterns
                    if ".." in path_obj.parts:
                        return False, "Path traversal detected"
                    # Check if it's trying to access root or system directories
                    if resolved_path.is_absolute():
                        # Allow absolute paths but warn about system directories
                        system_dirs = {
                            "/etc",
                            "/sys",
                            "/proc",
                            "/dev",
                            "/boot",
                            "/root",
                        }
                        for sys_dir in system_dirs:
                            if str(resolved_path).startswith(sys_dir):
                                return (
                                    False,
                                    f"Access to system directory {sys_dir} not allowed",
                                )
                except (OSError, RuntimeError) as e:
                    return False, f"Cannot resolve path: {e}"

            # Check file extension
            file_ext = path_obj.suffix.lower()

            if file_ext in self.DANGEROUS_EXTENSIONS:
                return False, f"Dangerous file extension: {file_ext}"

            if allowed_extensions and file_ext not in allowed_extensions:
                return False, f"File extension not allowed: {file_ext}"

            return True, None

        except Exception as e:
            return False, f"Path validation failed: {e}"

    def safe_read_file(
        self, file_path: str, max_size: Optional[int] = None, encoding: str = "utf-8"
    ) -> Tuple[bool, str, Optional[str]]:
        """Safely read a file with size and encoding validation"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, "", "File does not exist"

            # Check file size
            file_size = os.path.getsize(file_path)
            max_allowed = max_size or self.MAX_CONFIG_SIZE

            if file_size > max_allowed:
                return (
                    False,
                    "",
                    f"File too large: {file_size} bytes (max: {max_allowed})",
                )

            # Check file permissions
            if not os.access(file_path, os.R_OK):
                return False, "", "File is not readable"

            # Read file content
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()

            # BUG-009 FIX: Remove faulty file size mismatch check
            # The encoding may add BOM or normalize line endings, causing size differences
            # This check is not reliable and can cause false positives
            # File integrity should be verified using checksums if needed

            return True, content, None

        except UnicodeDecodeError as e:
            return False, "", f"Encoding error: {e}"
        except PermissionError:
            return False, "", "Permission denied"
        except Exception as e:
            return False, "", f"Failed to read file: {e}"

    def safe_write_file(
        self,
        file_path: str,
        content: str,
        create_backup: bool = True,
        encoding: str = "utf-8",
        permissions: int = 0o644,
    ) -> Tuple[bool, Optional[str]]:
        """Safely write content to a file with backup and validation"""
        try:
            # Validate file path
            is_valid, error = self.validate_file_path(file_path)
            if not is_valid:
                return False, error

            # Check content size
            content_bytes = content.encode(encoding)
            if len(content_bytes) > self.MAX_CONFIG_SIZE:
                return False, f"Content too large: {len(content_bytes)} bytes"

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Create backup if file exists and backup is requested
            backup_path = None
            if create_backup and os.path.exists(file_path):
                backup_path = f"{file_path}.backup"
                shutil.copy2(file_path, backup_path)

            # Write to temporary file first
            temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path))
            try:
                with os.fdopen(temp_fd, "w", encoding=encoding) as f:
                    f.write(content)

                # Set permissions on temporary file
                os.chmod(temp_path, permissions)

                # Atomically move temporary file to final location
                shutil.move(temp_path, file_path)

            except Exception:
                # Clean up temporary file on error
                try:
                    os.unlink(temp_path)
                except (OSError, PermissionError) as unlink_err:
                    self.logger.debug(
                        f"Could not remove temp file {temp_path}: {unlink_err}"
                    )
                raise

            self.logger.debug(f"Successfully wrote file: {file_path}")
            return True, None

        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {e}")
            return False, f"Failed to write file: {e}"

    def safe_copy_file(
        self, src_path: str, dst_path: str, preserve_permissions: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """Safely copy a file with validation (BUG-NEW-005 FIX: Added TOCTOU protection)"""
        try:
            # Validate source file
            if not os.path.exists(src_path):
                return False, "Source file does not exist"

            # Validate both paths
            for path in [src_path, dst_path]:
                is_valid, error = self.validate_file_path(path)
                if not is_valid:
                    return False, f"Invalid path {path}: {error}"

            # Check source file size
            file_size = os.path.getsize(src_path)
            if file_size > self.MAX_CONFIG_SIZE:
                return False, f"Source file too large: {file_size} bytes"

            # Create destination directory
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            # BUG-NEW-005 FIX: Wrap copy operations in try-except to handle TOCTOU issues
            # If file is deleted or modified between checks and copy, handle gracefully
            try:
                # Copy file
                if preserve_permissions:
                    shutil.copy2(src_path, dst_path)
                else:
                    shutil.copy(src_path, dst_path)
                    os.chmod(dst_path, 0o644)

                return True, None

            except FileNotFoundError:
                return False, "Source file was deleted during copy operation"
            except PermissionError as e:
                return False, f"Permission denied during copy: {e}"
            except OSError as e:
                return False, f"OS error during copy: {e}"

        except FileNotFoundError:
            # BUG-NEW-005 FIX: File deleted between existence check and size check
            return False, "Source file was deleted during validation"
        except Exception as e:
            return False, f"Failed to copy file: {e}"

    def safe_delete_file(
        self, file_path: str, secure_delete: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Safely delete a file with optional secure deletion"""
        try:
            if not os.path.exists(file_path):
                return True, None  # File doesn't exist, consider it deleted

            # Validate file path
            is_valid, error = self.validate_file_path(file_path)
            if not is_valid:
                return False, error

            if secure_delete:
                # Overwrite file with random data before deletion
                file_size = os.path.getsize(file_path)
                with open(file_path, "rb+") as f:
                    # Overwrite with zeros first
                    f.write(b"\x00" * file_size)
                    f.flush()
                    os.fsync(f.fileno())

                    # Overwrite with random data
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())

            os.unlink(file_path)
            return True, None

        except Exception as e:
            return False, f"Failed to delete file: {e}"

    def calculate_file_hash(
        self, file_path: str, algorithm: str = "sha256"
    ) -> Tuple[bool, str, Optional[str]]:
        """Calculate hash of a file for integrity checking"""
        try:
            if not os.path.exists(file_path):
                return False, "", "File does not exist"

            # Select hash algorithm
            hash_algorithms = {
                "md5": hashlib.md5,
                "sha1": hashlib.sha1,
                "sha256": hashlib.sha256,
                "sha512": hashlib.sha512,
            }

            if algorithm not in hash_algorithms:
                return False, "", f"Unsupported hash algorithm: {algorithm}"

            hasher = hash_algorithms[algorithm]()

            # Read file in chunks to handle large files
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)

            return True, hasher.hexdigest(), None

        except Exception as e:
            return False, "", f"Failed to calculate hash: {e}"

    def verify_file_integrity(
        self, file_path: str, expected_hash: str, algorithm: str = "sha256"
    ) -> Tuple[bool, Optional[str]]:
        """Verify file integrity against expected hash"""
        success, actual_hash, error = self.calculate_file_hash(file_path, algorithm)

        if not success:
            return False, error

        if actual_hash.lower() != expected_hash.lower():
            return False, f"Hash mismatch: expected {expected_hash}, got {actual_hash}"

        return True, None

    def check_file_permissions(self, file_path: str) -> Dict[str, Any]:
        """Check file permissions and return security analysis"""
        try:
            if not os.path.exists(file_path):
                return {"exists": False, "error": "File does not exist"}

            stat_info = os.stat(file_path)
            mode = stat_info.st_mode

            # Parse permissions
            permissions = {
                "owner_read": bool(mode & stat.S_IRUSR),
                "owner_write": bool(mode & stat.S_IWUSR),
                "owner_execute": bool(mode & stat.S_IXUSR),
                "group_read": bool(mode & stat.S_IRGRP),
                "group_write": bool(mode & stat.S_IWGRP),
                "group_execute": bool(mode & stat.S_IXGRP),
                "other_read": bool(mode & stat.S_IROTH),
                "other_write": bool(mode & stat.S_IWOTH),
                "other_execute": bool(mode & stat.S_IXOTH),
            }

            # Security analysis
            security_issues = []

            if permissions["other_write"]:
                security_issues.append("File is world-writable")

            if permissions["other_execute"] and not os.path.isdir(file_path):
                security_issues.append("File is world-executable")

            if permissions["group_write"]:
                security_issues.append("File is group-writable")

            # Calculate octal representation
            octal_permissions = oct(mode)[-3:]

            return {
                "exists": True,
                "permissions": permissions,
                "octal": octal_permissions,
                "is_directory": os.path.isdir(file_path),
                "size": stat_info.st_size,
                "owner_uid": stat_info.st_uid,
                "group_gid": stat_info.st_gid,
                "security_issues": security_issues,
                "is_secure": len(security_issues) == 0,
            }

        except Exception as e:
            return {"exists": False, "error": f"Failed to check permissions: {e}"}

    def set_secure_permissions(
        self, file_path: str, is_directory: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Set secure permissions on a file or directory"""
        try:
            if not os.path.exists(file_path):
                return False, "File does not exist"

            if is_directory:
                # BUG-HIGH-001 FIX: Use more restrictive permissions for security
                # Directory: 750 (rwxr-x---) - owner and group only
                os.chmod(file_path, 0o750)
            else:
                # File: 640 (rw-r-----) - owner and group read only
                os.chmod(file_path, 0o640)

            return True, None

        except Exception as e:
            return False, f"Failed to set permissions: {e}"

    def create_secure_directory(
        self, dir_path: str, permissions: int = 0o755
    ) -> Tuple[bool, Optional[str]]:
        """Create directory with secure permissions"""
        try:
            # Validate directory path
            is_valid, error = self.validate_file_path(dir_path)
            if not is_valid:
                return False, error

            # Create directory
            os.makedirs(dir_path, mode=permissions, exist_ok=True)

            # Explicitly set permissions (umask might interfere)
            os.chmod(dir_path, permissions)

            return True, None

        except Exception as e:
            return False, f"Failed to create directory: {e}"

    def scan_directory_security(self, dir_path: str) -> Dict[str, Any]:
        """Scan directory for security issues"""
        if not os.path.exists(dir_path):
            return {"exists": False, "error": "Directory does not exist"}

        try:
            security_issues = []
            file_count = 0
            dir_count = 0
            total_size = 0
            insecure_files = []

            for root, dirs, files in os.walk(dir_path):
                # Check directory permissions
                dir_info = self.check_file_permissions(root)
                if not dir_info.get("is_secure", True):
                    security_issues.extend(
                        [
                            f"Directory {root}: {issue}"
                            for issue in dir_info.get("security_issues", [])
                        ]
                    )

                dir_count += len(dirs)

                # Check file permissions
                for file in files:
                    file_path = os.path.join(root, file)
                    file_info = self.check_file_permissions(file_path)

                    file_count += 1
                    total_size += file_info.get("size", 0)

                    if not file_info.get("is_secure", True):
                        insecure_files.append(
                            {
                                "path": file_path,
                                "issues": file_info.get("security_issues", []),
                            }
                        )
                        security_issues.extend(
                            [
                                f"File {file_path}: {issue}"
                                for issue in file_info.get("security_issues", [])
                            ]
                        )

                    # Check for dangerous file extensions
                    file_ext = Path(file).suffix.lower()
                    if file_ext in self.DANGEROUS_EXTENSIONS:
                        security_issues.append(f"Dangerous file: {file_path}")
                        insecure_files.append(
                            {"path": file_path, "issues": ["Dangerous file extension"]}
                        )

            return {
                "exists": True,
                "file_count": file_count,
                "directory_count": dir_count,
                "total_size": total_size,
                "security_issues": security_issues,
                "insecure_files": insecure_files,
                "is_secure": len(security_issues) == 0,
            }

        except Exception as e:
            return {"exists": False, "error": f"Failed to scan directory: {e}"}

    def get_temp_directory(self) -> str:
        """Get secure temporary directory"""
        temp_dir = tempfile.mkdtemp(prefix="blastdock_")
        os.chmod(temp_dir, 0o700)  # Only owner can access
        return temp_dir

    def cleanup_temp_directory(self, temp_dir: str) -> bool:
        """Securely clean up temporary directory"""
        try:
            if os.path.exists(temp_dir) and temp_dir.startswith(tempfile.gettempdir()):
                shutil.rmtree(temp_dir)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to cleanup temp directory {temp_dir}: {e}")
            return False


# Global secure file operations instance
_secure_file_ops = None


def get_secure_file_operations() -> SecureFileOperations:
    """Get global secure file operations instance"""
    global _secure_file_ops
    if _secure_file_ops is None:
        _secure_file_ops = SecureFileOperations()
    return _secure_file_ops
