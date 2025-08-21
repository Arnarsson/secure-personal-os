#!/usr/bin/env python3
"""
Encrypted Credential Vault for Personal OS
Secure storage and retrieval of authentication credentials
"""

import os
import json
import base64
import hashlib
import secrets
import getpass
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

class CredentialVault:
    def __init__(self, vault_path: str = None, master_password: str = None):
        """Initialize encrypted credential vault"""
        if vault_path is None:
            vault_path = "/Users/sven/Desktop/MCP/personal-os/security/credential_vault.enc"
        
        self.vault_path = vault_path
        self.vault_dir = os.path.dirname(vault_path)
        self.master_key = None
        self.cipher_suite = None
        self.credentials = {}
        self.last_access = None
        self.auto_lock_timeout = 1800  # 30 minutes
        
        # Ensure vault directory exists
        os.makedirs(self.vault_dir, exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger('PersonalOS_CredentialVault')
        
        # Initialize or unlock vault
        if master_password:
            self._unlock_vault(master_password)
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def create_vault(self, master_password: str) -> bool:
        """Create a new encrypted vault"""
        try:
            # Generate salt for key derivation
            salt = os.urandom(16)
            
            # Derive key from master password
            key = self._derive_key(master_password, salt)
            self.cipher_suite = Fernet(key)
            
            # Create initial vault structure
            vault_data = {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'salt': base64.b64encode(salt).decode(),
                'credentials': {},
                'metadata': {
                    'last_modified': datetime.now().isoformat(),
                    'access_count': 0
                }
            }
            
            # Encrypt and save vault
            encrypted_data = self.cipher_suite.encrypt(json.dumps(vault_data).encode())
            with open(self.vault_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            os.chmod(self.vault_path, 0o600)
            
            self.credentials = vault_data['credentials']
            self.last_access = datetime.now()
            
            self.logger.info("Created new credential vault")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating vault: {e}")
            return False
    
    def _unlock_vault(self, master_password: str) -> bool:
        """Unlock existing vault with master password"""
        try:
            # Check if vault exists
            if not os.path.exists(self.vault_path):
                self.logger.info("Vault doesn't exist, creating new one")
                return self.create_vault(master_password)
            
            # Read encrypted vault
            with open(self.vault_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Load vault metadata (unencrypted) if available
            try:
                # Try to extract salt from file header (if implemented)
                # For now, we'll try multiple salts or store salt separately
                vault_json = self._try_decrypt_vault(encrypted_data, master_password)
                if not vault_json:
                    raise ValueError("Invalid master password")
                
                vault_data = json.loads(vault_json)
                
            except Exception as e:
                self.logger.error(f"Error decrypting vault: {e}")
                return False
            
            # Load credentials
            self.credentials = vault_data.get('credentials', {})
            self.last_access = datetime.now()
            
            # Update access count
            vault_data['metadata']['access_count'] = vault_data['metadata'].get('access_count', 0) + 1
            vault_data['metadata']['last_accessed'] = datetime.now().isoformat()
            
            # Save updated metadata
            self._save_vault(vault_data)
            
            self.logger.info("Successfully unlocked credential vault")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unlocking vault: {e}")
            return False
    
    def _try_decrypt_vault(self, encrypted_data: bytes, master_password: str) -> Optional[str]:
        """Try to decrypt vault with given password"""
        # For initial implementation, we'll store salt in a separate file
        salt_file = self.vault_path + '.salt'
        
        if os.path.exists(salt_file):
            with open(salt_file, 'rb') as f:
                salt = f.read()
        else:
            # Generate and save salt for new vault
            salt = os.urandom(16)
            with open(salt_file, 'wb') as f:
                f.write(salt)
            os.chmod(salt_file, 0o600)
        
        try:
            key = self._derive_key(master_password, salt)
            cipher_suite = Fernet(key)
            decrypted_data = cipher_suite.decrypt(encrypted_data)
            self.cipher_suite = cipher_suite
            return decrypted_data.decode()
        except:
            return None
    
    def lock_vault(self):
        """Lock the vault by clearing sensitive data from memory"""
        self.master_key = None
        self.cipher_suite = None
        self.credentials = {}
        self.last_access = None
        self.logger.info("Vault locked")
    
    def is_locked(self) -> bool:
        """Check if vault is locked"""
        if self.cipher_suite is None:
            return True
        
        # Check auto-lock timeout
        if self.last_access and self.auto_lock_timeout > 0:
            time_since_access = datetime.now() - self.last_access
            if time_since_access.total_seconds() > self.auto_lock_timeout:
                self.lock_vault()
                return True
        
        return False
    
    def unlock_vault(self, master_password: str) -> bool:
        """Unlock vault with master password"""
        return self._unlock_vault(master_password)
    
    def store_credential(self, service: str, identifier: str, 
                        credential_data: Dict[str, Any]) -> bool:
        """Store credentials for a service"""
        if self.is_locked():
            self.logger.error("Vault is locked")
            return False
        
        try:
            # Update last access
            self.last_access = datetime.now()
            
            # Prepare credential entry
            credential_entry = {
                'service': service,
                'identifier': identifier,
                'data': credential_data,
                'created': datetime.now().isoformat(),
                'modified': datetime.now().isoformat(),
                'access_count': 0
            }
            
            # Create service entry if it doesn't exist
            if service not in self.credentials:
                self.credentials[service] = {}
            
            self.credentials[service][identifier] = credential_entry
            
            # Save to vault
            vault_data = {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'credentials': self.credentials,
                'metadata': {
                    'last_modified': datetime.now().isoformat(),
                    'credential_count': sum(len(service_creds) for service_creds in self.credentials.values())
                }
            }
            
            self._save_vault(vault_data)
            
            self.logger.info(f"Stored credentials for {service}:{identifier}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing credentials: {e}")
            return False
    
    def retrieve_credential(self, service: str, identifier: str = None) -> Optional[Dict[str, Any]]:
        """Retrieve credentials for a service"""
        if self.is_locked():
            self.logger.error("Vault is locked")
            return None
        
        try:
            # Update last access
            self.last_access = datetime.now()
            
            if service not in self.credentials:
                return None
            
            if identifier is None:
                # Return all credentials for service
                return self.credentials[service]
            
            if identifier not in self.credentials[service]:
                return None
            
            credential = self.credentials[service][identifier]
            
            # Update access count
            credential['access_count'] = credential.get('access_count', 0) + 1
            credential['last_accessed'] = datetime.now().isoformat()
            
            self.logger.info(f"Retrieved credentials for {service}:{identifier}")
            return credential
            
        except Exception as e:
            self.logger.error(f"Error retrieving credentials: {e}")
            return None
    
    def delete_credential(self, service: str, identifier: str = None) -> bool:
        """Delete credentials from vault"""
        if self.is_locked():
            self.logger.error("Vault is locked")
            return False
        
        try:
            if service not in self.credentials:
                return False
            
            if identifier is None:
                # Delete entire service
                del self.credentials[service]
            else:
                # Delete specific identifier
                if identifier in self.credentials[service]:
                    del self.credentials[service][identifier]
                    
                    # Remove service if empty
                    if not self.credentials[service]:
                        del self.credentials[service]
            
            # Save updated vault
            vault_data = {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'credentials': self.credentials,
                'metadata': {
                    'last_modified': datetime.now().isoformat(),
                    'credential_count': sum(len(service_creds) for service_creds in self.credentials.values())
                }
            }
            
            self._save_vault(vault_data)
            
            self.logger.info(f"Deleted credentials for {service}:{identifier}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting credentials: {e}")
            return False
    
    def list_services(self) -> List[str]:
        """List all services with stored credentials"""
        if self.is_locked():
            return []
        
        return list(self.credentials.keys())
    
    def list_identifiers(self, service: str) -> List[str]:
        """List all identifiers for a service"""
        if self.is_locked() or service not in self.credentials:
            return []
        
        return list(self.credentials[service].keys())
    
    def _save_vault(self, vault_data: Dict[str, Any]):
        """Save vault data to encrypted file"""
        if not self.cipher_suite:
            raise RuntimeError("Vault is not unlocked")
        
        # Encrypt vault data
        encrypted_data = self.cipher_suite.encrypt(json.dumps(vault_data).encode())
        
        # Write to file
        with open(self.vault_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Set restrictive permissions
        os.chmod(self.vault_path, 0o600)
    
    def change_master_password(self, current_password: str, new_password: str) -> bool:
        """Change the master password for the vault"""
        if self.is_locked():
            if not self._unlock_vault(current_password):
                return False
        
        try:
            # Create new salt and cipher suite
            salt = os.urandom(16)
            new_key = self._derive_key(new_password, salt)
            new_cipher_suite = Fernet(new_key)
            
            # Prepare vault data
            vault_data = {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'credentials': self.credentials,
                'metadata': {
                    'last_modified': datetime.now().isoformat(),
                    'password_changed': datetime.now().isoformat()
                }
            }
            
            # Encrypt with new cipher
            encrypted_data = new_cipher_suite.encrypt(json.dumps(vault_data).encode())
            
            # Save new salt
            salt_file = self.vault_path + '.salt'
            with open(salt_file, 'wb') as f:
                f.write(salt)
            os.chmod(salt_file, 0o600)
            
            # Save new vault
            with open(self.vault_path, 'wb') as f:
                f.write(encrypted_data)
            os.chmod(self.vault_path, 0o600)
            
            # Update cipher suite
            self.cipher_suite = new_cipher_suite
            
            self.logger.info("Master password changed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error changing master password: {e}")
            return False
    
    def get_vault_stats(self) -> Dict[str, Any]:
        """Get vault statistics"""
        if self.is_locked():
            return {'status': 'locked'}
        
        total_credentials = sum(len(service_creds) for service_creds in self.credentials.values())
        
        return {
            'status': 'unlocked',
            'services': len(self.credentials),
            'total_credentials': total_credentials,
            'last_access': self.last_access.isoformat() if self.last_access else None,
            'auto_lock_timeout': self.auto_lock_timeout
        }

def main():
    """Test the Credential Vault"""
    print("🔐 Testing Credential Vault")
    print("=" * 40)
    
    # Get master password (in real usage, this would be more secure)
    print("Enter master password for test vault: ", end="")
    master_password = getpass.getpass()
    
    # Initialize vault
    vault = CredentialVault(master_password=master_password)
    
    if vault.is_locked():
        print("❌ Failed to unlock vault")
        return
    
    print("✅ Vault unlocked successfully")
    
    # Test storing credentials
    print("\n📝 Storing test credentials...")
    test_credentials = {
        'gmail': {
            'user1': {
                'email': 'user1@gmail.com',
                'app_password': 'test_app_password_123',
                'two_factor': True
            }
        },
        'whatsapp': {
            'main': {
                'phone': '+1234567890',
                'session_data': 'encrypted_session_data'
            }
        }
    }
    
    for service, identifiers in test_credentials.items():
        for identifier, data in identifiers.items():
            success = vault.store_credential(service, identifier, data)
            print(f"  {'✅' if success else '❌'} {service}:{identifier}")
    
    # Test retrieving credentials
    print("\n📋 Retrieving credentials...")
    for service in vault.list_services():
        print(f"\n{service}:")
        for identifier in vault.list_identifiers(service):
            cred = vault.retrieve_credential(service, identifier)
            print(f"  • {identifier}: {cred['data'] if cred else 'Not found'}")
    
    # Show vault stats
    print(f"\n📊 Vault Stats:")
    stats = vault.get_vault_stats()
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    print(f"\n🔒 Locking vault...")
    vault.lock_vault()
    print(f"Vault locked: {vault.is_locked()}")

if __name__ == "__main__":
    main()