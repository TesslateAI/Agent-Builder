"""
Keycloak OAuth 2.0/OIDC Integration Client
Handles authentication flows, token management, and user synchronization
"""
import os
import logging
import requests
import json
from typing import Dict, Optional, List, Any
from urllib.parse import urlencode, parse_qs, urlparse
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class KeycloakError(Exception):
    """Custom Keycloak integration error"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class KeycloakClient:
    """Keycloak OAuth 2.0/OIDC client for Agent-Builder"""
    
    def __init__(self):
        # Keycloak configuration from environment
        self.server_url = os.getenv('KEYCLOAK_SERVER_URL', 'http://localhost:8080')
        self.realm = os.getenv('KEYCLOAK_REALM', 'agent-builder')
        self.client_id = os.getenv('KEYCLOAK_CLIENT_ID', 'agent-builder-app')
        self.client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET', '')
        self.redirect_uri = os.getenv('KEYCLOAK_REDIRECT_URI', 'http://localhost:5000/api/auth/callback')
        
        # For frontend-facing URLs, use public URL (localhost:8081 for dev)
        self.public_server_url = os.getenv('KEYCLOAK_PUBLIC_URL', 'http://localhost:8081')
        
        # Build internal URLs (for admin operations only)
        self.realm_url = f"{self.server_url}/realms/{self.realm}"
        self.admin_url = f"{self.server_url}/admin/realms/{self.realm}"
        
        # Build public URLs (for all token operations - must match token issuer)
        self.public_realm_url = f"{self.public_server_url}/realms/{self.realm}"
        self.auth_url = f"{self.public_realm_url}/protocol/openid-connect/auth"
        self.token_url = f"{self.public_realm_url}/protocol/openid-connect/token"
        self.userinfo_url = f"{self.public_realm_url}/protocol/openid-connect/userinfo"
        self.logout_url = f"{self.public_realm_url}/protocol/openid-connect/logout"
        
        # Expected issuer for token validation (matches public URL)
        self.expected_issuer = f"{self.public_server_url}/realms/{self.realm}"
        
        # Cache for admin token
        self._admin_token = None
        self._admin_token_expires = None
    
    def get_authorization_url(self, state: Optional[str] = None, scopes: List[str] = None) -> str:
        """Generate authorization URL for OAuth flow"""
        if scopes is None:
            scopes = ['openid', 'profile', 'email', 'roles']
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
        }
        
        if state:
            params['state'] = state
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'redirect_uri': self.redirect_uri
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Token exchange failed: {e}")
            raise KeycloakError(f"Failed to exchange code for tokens: {e}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Token refresh failed: {e}")
            raise KeycloakError(f"Failed to refresh token: {e}")
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Keycloak using access token"""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(self.userinfo_url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"User info fetch failed: {e}")
            raise KeycloakError(f"Failed to get user info: {e}")
    
    def logout_user(self, refresh_token: str) -> bool:
        """Logout user by revoking refresh token"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token
        }
        
        try:
            response = requests.post(self.logout_url, data=data, timeout=30)
            return response.status_code == 204
        except requests.RequestException as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    def get_logout_url(self, post_logout_redirect_uri: Optional[str] = None) -> str:
        """Generate logout URL"""
        params = {'client_id': self.client_id}
        if post_logout_redirect_uri:
            params['post_logout_redirect_uri'] = post_logout_redirect_uri
        
        # Use public logout URL for browser redirects
        public_logout_url = f"{self.public_realm_url}/protocol/openid-connect/logout"
        return f"{public_logout_url}?{urlencode(params)}"
    
    def validate_token(self, access_token: str) -> bool:
        """Validate access token by calling userinfo endpoint"""
        try:
            self.get_user_info(access_token)
            return True
        except KeycloakError:
            return False
    
    def _get_admin_token(self) -> str:
        """Get admin access token for Keycloak Admin API"""
        # Check if we have a valid cached token
        if (self._admin_token and self._admin_token_expires and 
            datetime.now() < self._admin_token_expires):
            return self._admin_token
        
        # Get admin credentials
        admin_username = os.getenv('KEYCLOAK_ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('KEYCLOAK_ADMIN_PASSWORD', 'admin')
        
        data = {
            'grant_type': 'password',
            'client_id': 'admin-cli',
            'username': admin_username,
            'password': admin_password
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/realms/master/protocol/openid-connect/token",
                data=data,
                timeout=30
            )
            response.raise_for_status()
            token_data = response.json()
            
            self._admin_token = token_data['access_token']
            # Set expiry with 5 minute buffer
            expires_in = token_data.get('expires_in', 300) - 300
            self._admin_token_expires = datetime.now() + timedelta(seconds=expires_in)
            
            return self._admin_token
            
        except requests.RequestException as e:
            logger.error(f"Admin token fetch failed: {e}")
            raise KeycloakError(f"Failed to get admin token: {e}")
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create user in Keycloak"""
        admin_token = self._get_admin_token()
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        
        # Prepare user payload
        payload = {
            'username': user_data['username'],
            'email': user_data['email'],
            'firstName': user_data.get('first_name', ''),
            'lastName': user_data.get('last_name', ''),
            'enabled': True,
            'emailVerified': user_data.get('email_verified', False),
            'attributes': user_data.get('attributes', {}),
            'groups': user_data.get('groups', []),
            'realmRoles': user_data.get('realm_roles', []),
            'clientRoles': user_data.get('client_roles', {})
        }
        
        try:
            response = requests.post(
                f"{self.admin_url}/users",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                # Extract user ID from Location header
                location = response.headers.get('Location', '')
                user_id = location.split('/')[-1]
                return user_id
            else:
                response.raise_for_status()
                
        except requests.RequestException as e:
            logger.error(f"User creation failed: {e}")
            raise KeycloakError(f"Failed to create user: {e}")
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username from Keycloak"""
        admin_token = self._get_admin_token()
        headers = {'Authorization': f'Bearer {admin_token}'}
        
        try:
            response = requests.get(
                f"{self.admin_url}/users",
                headers=headers,
                params={'username': username, 'exact': True},
                timeout=30
            )
            response.raise_for_status()
            
            users = response.json()
            return users[0] if users else None
            
        except requests.RequestException as e:
            logger.error(f"User fetch failed: {e}")
            return None
    
    def update_user_attributes(self, user_id: str, attributes: Dict[str, Any]):
        """Update user attributes in Keycloak"""
        admin_token = self._get_admin_token()
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {'attributes': attributes}
        
        try:
            response = requests.put(
                f"{self.admin_url}/users/{user_id}",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
        except requests.RequestException as e:
            logger.error(f"User update failed: {e}")
            raise KeycloakError(f"Failed to update user: {e}")
    
    def get_user_roles(self, user_id: str) -> Dict[str, List[str]]:
        """Get user's realm and client roles"""
        admin_token = self._get_admin_token()
        headers = {'Authorization': f'Bearer {admin_token}'}
        
        try:
            # Get realm roles
            realm_response = requests.get(
                f"{self.admin_url}/users/{user_id}/role-mappings/realm",
                headers=headers,
                timeout=30
            )
            realm_roles = [role['name'] for role in realm_response.json()] if realm_response.ok else []
            
            # Get client roles
            client_response = requests.get(
                f"{self.admin_url}/users/{user_id}/role-mappings/clients",
                headers=headers,
                timeout=30
            )
            client_roles = {}
            if client_response.ok:
                for client_mapping in client_response.json():
                    client_id = client_mapping['client']
                    roles = [role['name'] for role in client_mapping.get('mappings', [])]
                    client_roles[client_id] = roles
            
            return {
                'realm_roles': realm_roles,
                'client_roles': client_roles
            }
            
        except requests.RequestException as e:
            logger.error(f"Role fetch failed: {e}")
            return {'realm_roles': [], 'client_roles': {}}
    
    def assign_user_to_group(self, user_id: str, group_id: str):
        """Add user to a group"""
        admin_token = self._get_admin_token()
        headers = {'Authorization': f'Bearer {admin_token}'}
        
        try:
            response = requests.put(
                f"{self.admin_url}/users/{user_id}/groups/{group_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
        except requests.RequestException as e:
            logger.error(f"Group assignment failed: {e}")
            raise KeycloakError(f"Failed to assign user to group: {e}")
    
    def health_check(self) -> bool:
        """Check if Keycloak is available"""
        try:
            response = requests.get(f"{self.realm_url}", timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

# Global Keycloak client instance
keycloak_client = KeycloakClient()