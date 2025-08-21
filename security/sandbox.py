#!/usr/bin/env python3
"""
Sandboxed Execution Environment for Personal OS
Provides isolated execution of potentially risky operations with resource limits
"""

import os
import sys
import subprocess
import tempfile
import shutil
import time
import signal
import psutil
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json
import logging
from contextlib import contextmanager
from .permission_manager import PermissionManager

class SandboxEnvironment:
    def __init__(self, permission_manager: PermissionManager):
        """Initialize sandbox environment"""
        self.permission_manager = permission_manager
        self.sandbox_dir = None
        self.active_processes = []
        self.resource_limits = {
            'max_memory_mb': 512,
            'max_cpu_percent': 50,
            'max_execution_time': 300,  # 5 minutes
            'max_file_size_mb': 100,
            'max_network_connections': 10
        }
        
        # Set up logging
        self.logger = logging.getLogger('PersonalOS_Sandbox')
        
    @contextmanager
    def create_sandbox(self, name: str = None):
        """Create a temporary sandbox environment"""
        if name is None:
            name = f"personal_os_sandbox_{int(time.time())}"
        
        try:
            # Create sandbox directory
            self.sandbox_dir = tempfile.mkdtemp(prefix=f"{name}_")
            self.logger.info(f"Created sandbox: {self.sandbox_dir}")
            
            # Set up sandbox structure
            self._setup_sandbox_structure()
            
            yield self.sandbox_dir
            
        finally:
            # Clean up sandbox
            self._cleanup_sandbox()
    
    def _setup_sandbox_structure(self):
        """Set up the sandbox directory structure"""
        if not self.sandbox_dir:
            return
        
        # Create standard directories
        directories = ['tmp', 'logs', 'data', 'scripts', 'output']
        for dir_name in directories:
            os.makedirs(os.path.join(self.sandbox_dir, dir_name), exist_ok=True)
        
        # Copy essential files if needed
        essential_files = {
            'permissions.yaml': '/Users/sven/Desktop/MCP/personal-os/permissions/permissions.yaml'
        }
        
        for dest_name, src_path in essential_files.items():
            if os.path.exists(src_path):
                dest_path = os.path.join(self.sandbox_dir, dest_name)
                try:
                    shutil.copy2(src_path, dest_path)
                    self.logger.debug(f"Copied {src_path} to sandbox")
                except Exception as e:
                    self.logger.warning(f"Could not copy {src_path}: {e}")
    
    def execute_sandboxed_command(self, command: List[str], 
                                 working_dir: str = None,
                                 env_vars: Dict[str, str] = None,
                                 timeout: int = None) -> Tuple[bool, str, str]:
        """Execute a command in sandboxed environment"""
        
        if not self.sandbox_dir:
            raise RuntimeError("No active sandbox. Use create_sandbox() context manager.")
        
        # Validate command is safe
        if not self._validate_command(command):
            return False, "", "Command blocked by security policy"
        
        # Set up environment
        if working_dir is None:
            working_dir = self.sandbox_dir
        
        sandbox_env = os.environ.copy()
        if env_vars:
            sandbox_env.update(env_vars)
        
        # Add sandbox-specific environment variables
        sandbox_env.update({
            'PERSONAL_OS_SANDBOX': self.sandbox_dir,
            'PERSONAL_OS_MODE': 'sandbox',
            'HOME': self.sandbox_dir,  # Isolate home directory
            'TMPDIR': os.path.join(self.sandbox_dir, 'tmp')
        })
        
        # Set timeout
        if timeout is None:
            timeout = self.resource_limits['max_execution_time']
        
        try:
            # Start process with resource limits
            process = subprocess.Popen(
                command,
                cwd=working_dir,
                env=sandbox_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=self._set_resource_limits
            )
            
            self.active_processes.append(process)
            
            # Monitor process execution
            return self._monitor_process(process, timeout)
            
        except Exception as e:
            self.logger.error(f"Sandbox execution error: {e}")
            return False, "", str(e)
        
        finally:
            if process in self.active_processes:
                self.active_processes.remove(process)
    
    def _validate_command(self, command: List[str]) -> bool:
        """Validate that command is safe to execute"""
        if not command:
            return False
        
        # List of blocked commands
        blocked_commands = [
            'rm', 'rmdir', 'del', 'format',
            'dd', 'fdisk', 'mkfs',
            'sudo', 'su', 'chmod', 'chown',
            'curl', 'wget', 'nc', 'netcat',
            'ssh', 'scp', 'rsync',
            'crontab', 'at', 'systemctl', 'service'
        ]
        
        # List of allowed commands
        allowed_commands = [
            'python3', 'python', 'node', 'npm',
            'ls', 'cat', 'echo', 'pwd', 'cd',
            'mkdir', 'touch', 'cp', 'mv',
            'grep', 'find', 'sort', 'head', 'tail'
        ]
        
        base_command = os.path.basename(command[0])
        
        # Check if command is explicitly blocked
        if base_command in blocked_commands:
            self.logger.warning(f"Blocked dangerous command: {base_command}")
            return False
        
        # Check if command is in allowed list or is a script in sandbox
        if (base_command in allowed_commands or 
            command[0].startswith(self.sandbox_dir) or
            base_command.endswith('.py') or
            base_command.endswith('.sh')):
            return True
        
        self.logger.warning(f"Command not in allowed list: {base_command}")
        return False
    
    def _set_resource_limits(self):
        """Set resource limits for subprocess"""
        try:
            import resource
            
            # Set memory limit (in bytes)
            memory_limit = self.resource_limits['max_memory_mb'] * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # Set CPU time limit (in seconds)
            cpu_time = self.resource_limits['max_execution_time']
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_time, cpu_time))
            
            # Set file size limit (in bytes)
            file_size_limit = self.resource_limits['max_file_size_mb'] * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_limit, file_size_limit))
            
        except ImportError:
            self.logger.warning("Resource module not available - running without limits")
        except Exception as e:
            self.logger.warning(f"Could not set resource limits: {e}")
    
    def _monitor_process(self, process: subprocess.Popen, timeout: int) -> Tuple[bool, str, str]:
        """Monitor process execution and enforce limits"""
        start_time = time.time()
        
        try:
            # Wait for process with timeout
            stdout, stderr = process.communicate(timeout=timeout)
            
            # Check return code
            if process.returncode == 0:
                self.logger.info(f"Sandbox command completed successfully")
                return True, stdout, stderr
            else:
                self.logger.warning(f"Sandbox command failed with code {process.returncode}")
                return False, stdout, stderr
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Sandbox command timed out after {timeout} seconds")
            process.kill()
            stdout, stderr = process.communicate()
            return False, stdout, f"Command timed out after {timeout} seconds"
        
        except Exception as e:
            self.logger.error(f"Process monitoring error: {e}")
            try:
                process.kill()
            except:
                pass
            return False, "", str(e)
    
    def execute_python_code(self, code: str, 
                           allowed_imports: List[str] = None) -> Tuple[bool, str, str]:
        """Execute Python code in sandbox with import restrictions"""
        
        if allowed_imports is None:
            allowed_imports = [
                'json', 'os', 'sys', 'time', 'datetime', 're',
                'urllib.parse', 'base64', 'hashlib', 'hmac',
                'requests', 'yaml', 'pathlib'
            ]
        
        # Create restricted Python code
        restricted_code = self._create_restricted_python_code(code, allowed_imports)
        
        # Write code to sandbox file
        code_file = os.path.join(self.sandbox_dir, 'scripts', 'sandbox_code.py')
        with open(code_file, 'w') as f:
            f.write(restricted_code)
        
        # Execute the code
        return self.execute_sandboxed_command(['python3', code_file])
    
    def _create_restricted_python_code(self, user_code: str, allowed_imports: List[str]) -> str:
        """Create Python code with import restrictions"""
        
        restriction_code = f"""
import sys
import builtins

# Store original import function
_original_import = builtins.__import__

# List of allowed imports
ALLOWED_IMPORTS = {allowed_imports}

def restricted_import(name, *args, **kwargs):
    if name.split('.')[0] not in ALLOWED_IMPORTS:
        raise ImportError(f"Import of '{{name}}' is not allowed in sandbox")
    return _original_import(name, *args, **kwargs)

# Replace import function
builtins.__import__ = restricted_import

# Restrict access to dangerous builtins
SAFE_BUILTINS = {{
    'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes', 'callable',
    'chr', 'classmethod', 'complex', 'dict', 'dir', 'divmod', 'enumerate',
    'eval', 'filter', 'float', 'format', 'frozenset', 'getattr', 'globals',
    'hasattr', 'hash', 'hex', 'id', 'input', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'locals', 'map', 'max', 'memoryview', 'min',
    'next', 'object', 'oct', 'ord', 'pow', 'print', 'property', 'range',
    'repr', 'reversed', 'round', 'set', 'setattr', 'slice', 'sorted',
    'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip'
}}

# Create restricted builtins
safe_builtins = {{name: getattr(builtins, name) for name in SAFE_BUILTINS if hasattr(builtins, name)}}
safe_builtins['__import__'] = restricted_import

# Execute user code in restricted environment
try:
    exec('''
{user_code}
''', {{"__builtins__": safe_builtins}})
except Exception as e:
    print(f"Sandbox execution error: {{e}}", file=sys.stderr)
    sys.exit(1)
"""
        return restriction_code
    
    def create_secure_temp_file(self, content: str, suffix: str = '.tmp') -> str:
        """Create a secure temporary file in sandbox"""
        if not self.sandbox_dir:
            raise RuntimeError("No active sandbox")
        
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            dir=os.path.join(self.sandbox_dir, 'tmp'),
            delete=False
        )
        
        temp_file.write(content)
        temp_file.close()
        
        # Set restrictive permissions
        os.chmod(temp_file.name, 0o600)
        
        return temp_file.name
    
    def cleanup_temp_files(self):
        """Clean up temporary files in sandbox"""
        if not self.sandbox_dir:
            return
        
        temp_dir = os.path.join(self.sandbox_dir, 'tmp')
        if os.path.exists(temp_dir):
            for file_path in Path(temp_dir).glob('*'):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(str(file_path))
                except Exception as e:
                    self.logger.warning(f"Could not clean up {file_path}: {e}")
    
    def _cleanup_sandbox(self):
        """Clean up sandbox environment"""
        if not self.sandbox_dir:
            return
        
        # Kill any remaining processes
        for process in self.active_processes[:]:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # Remove sandbox directory
        try:
            shutil.rmtree(self.sandbox_dir)
            self.logger.info(f"Cleaned up sandbox: {self.sandbox_dir}")
        except Exception as e:
            self.logger.warning(f"Could not clean up sandbox {self.sandbox_dir}: {e}")
        
        self.sandbox_dir = None
        self.active_processes = []
    
    def get_sandbox_status(self) -> Dict[str, Any]:
        """Get current sandbox status"""
        return {
            'active': self.sandbox_dir is not None,
            'sandbox_dir': self.sandbox_dir,
            'active_processes': len(self.active_processes),
            'resource_limits': self.resource_limits
        }

def main():
    """Test the Sandbox Environment"""
    from .permission_manager import PermissionManager
    
    pm = PermissionManager()
    sandbox = SandboxEnvironment(pm)
    
    print("🔒 Testing Sandbox Environment")
    print("=" * 40)
    
    with sandbox.create_sandbox("test_sandbox") as sandbox_dir:
        print(f"Created sandbox: {sandbox_dir}")
        
        # Test safe command
        print("\n✅ Testing safe command (ls):")
        success, stdout, stderr = sandbox.execute_sandboxed_command(['ls', '-la'])
        print(f"Success: {success}")
        print(f"Output: {stdout[:200]}")
        
        # Test Python code execution
        print("\n🐍 Testing Python code execution:")
        test_code = """
import json
import time

data = {'message': 'Hello from sandbox!', 'timestamp': time.time()}
print(json.dumps(data, indent=2))
"""
        success, stdout, stderr = sandbox.execute_python_code(test_code)
        print(f"Success: {success}")
        print(f"Output: {stdout}")
        
        # Test blocked command
        print("\n❌ Testing blocked command (sudo):")
        success, stdout, stderr = sandbox.execute_sandboxed_command(['sudo', 'ls'])
        print(f"Success: {success}")
        print(f"Error: {stderr}")

if __name__ == "__main__":
    main()