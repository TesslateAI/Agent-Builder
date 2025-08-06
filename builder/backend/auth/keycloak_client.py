"""
Keycloak OAuth 2.0/OIDC Integration Client
Handles authentication flows, token management, and user synchronization
"""
import os
import logging
import requests
from typing import Dict, Optional, List, Any
from urllib.parse import urlencode
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
        self.public_url = os.getenv('KEYCLOAK_PUBLIC_URL', 'http://localhost:8081')  # For browser redirects
        self.internal_url = os.getenv('KEYCLOAK_INTERNAL_URL', 'http://keycloak:8080')  # For backend API calls
        self.realm = os.getenv('KEYCLOAK_REALM', 'agent-builder')
        self.client_id = os.getenv('KEYCLOAK_CLIENT_ID', 'agent-builder-app')
        self.client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET', '')
        self.redirect_uri = os.getenv('KEYCLOAK_REDIRECT_URI', 'http://localhost:5000/api/auth/callback')
        
        # Build URLs - use public URL for browser-facing operations
        self.public_realm_url = f"{self.public_url}/realms/{self.realm}"
        self.internal_realm_url = f"{self.internal_url}/realms/{self.realm}"
        
        # Browser-facing URLs (use public URL)
        self.auth_url = f"{self.public_realm_url}/protocol/openid-connect/auth"
        
        # Backend API URLs - use internal URL for token exchange, but public URL for userinfo 
        # because tokens are issued with public URL as the issuer
        self.token_url = f"{self.internal_realm_url}/protocol/openid-connect/token"
        self.userinfo_url = f"{self.public_realm_url}/protocol/openid-connect/userinfo"  # Must match token issuer
        self.logout_url = f"{self.internal_realm_url}/protocol/openid-connect/logout"
        self.admin_url = f"{self.internal_url}/admin/realms/{self.realm}"
        
        # Expected issuer for token validation (must match what Keycloak issues)
        self.expected_issuer = f"{self.public_url}/realms/{self.realm}"
        
        # Cache for admin token
        self._admin_token = None
        self._admin_token_expires = None
    
    def get_authorization_url(self, state: Optional[str] = None, scopes: List[str] = None) -> str:
        """Generate authorization URL for OAuth flow"""
        if scopes is None:
            scopes = ['openid', 'profile', 'email', 'roles']
        
        logger.info(f"🔐 [KEYCLOAK] Generating authorization URL")
        logger.info(f"🔐 [KEYCLOAK] Client ID: {self.client_id}")
        logger.info(f"🔐 [KEYCLOAK] Redirect URI: {self.redirect_uri}")
        logger.info(f"🔐 [KEYCLOAK] Requested scopes: {scopes}")
        logger.info(f"🔐 [KEYCLOAK] State: {state}")
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
        }
        
        if state:
            params['state'] = state
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        logger.info(f"🔐 [KEYCLOAK] Generated authorization URL: {auth_url}")
        return auth_url
    
    def exchange_code_for_tokens(self, authorization_code: str, scopes: List[str] = None) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        if scopes is None:
            scopes = ['openid', 'profile', 'email', 'roles']
        
        logger.info(f"🔐 [KEYCLOAK] Starting token exchange")
        logger.info(f"🔐 [KEYCLOAK] Authorization code (first 20 chars): {authorization_code[:20]}...")
        logger.info(f"🔐 [KEYCLOAK] Token URL: {self.token_url}")
        logger.info(f"🔐 [KEYCLOAK] Client ID: {self.client_id}")
        logger.info(f"🔐 [KEYCLOAK] Client secret present: {'Yes' if self.client_secret else 'No'}")
        logger.info(f"🔐 [KEYCLOAK] Redirect URI: {self.redirect_uri}")
        logger.info(f"🔐 [KEYCLOAK] Requested scopes for token exchange: {scopes}")
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes)
        }
        
        logger.debug(f"🔐 [KEYCLOAK] Token request payload: {dict((k, v if k != 'client_secret' else '***') for k, v in data.items())}")
        
        try:
            logger.info(f"🔐 [KEYCLOAK] Making POST request to token endpoint...")
            response = requests.post(self.token_url, data=data, timeout=30)
            logger.info(f"🔐 [KEYCLOAK] Token response status: {response.status_code}")
            logger.debug(f"🔐 [KEYCLOAK] Token response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            token_data = response.json()
            
            logger.info(f"🔐 [KEYCLOAK] ✅ Token exchange successful!")
            logger.info(f"🔐 [KEYCLOAK] Token data keys: {list(token_data.keys())}")
            logger.info(f"🔐 [KEYCLOAK] Token scope: {token_data.get('scope', 'No scope in token')}")
            logger.info(f"🔐 [KEYCLOAK] Token type: {token_data.get('token_type', 'No token type')}")
            logger.info(f"🔐 [KEYCLOAK] Expires in: {token_data.get('expires_in', 'No expiry info')} seconds")
            
            if 'access_token' in token_data:
                access_token = token_data['access_token']
                logger.info(f"🔐 [KEYCLOAK] Access token (first 50 chars): {access_token[:50]}...")
                
                # Decode JWT header and payload for debugging (without verification)
                try:
                    import base64
                    import json
                    parts = access_token.split('.')
                    if len(parts) >= 2:
                        # Decode header
                        header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
                        logger.debug(f"🔐 [KEYCLOAK] Access token header: {header}")
                        
                        # Decode payload
                        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
                        logger.info(f"🔐 [KEYCLOAK] Access token issuer: {payload.get('iss', 'No issuer')}")
                        logger.info(f"🔐 [KEYCLOAK] Access token audience: {payload.get('aud', 'No audience')}")
                        logger.info(f"🔐 [KEYCLOAK] Access token scope: {payload.get('scope', 'No scope in token')}")
                        logger.info(f"🔐 [KEYCLOAK] Access token subject: {payload.get('sub', 'No subject')}")
                        logger.info(f"🔐 [KEYCLOAK] Access token username: {payload.get('preferred_username', 'No username')}")
                except Exception as decode_error:
                    logger.debug(f"🔐 [KEYCLOAK] Could not decode access token for debugging: {decode_error}")
            
            return token_data
        except requests.RequestException as e:
            logger.error(f"🔐 [KEYCLOAK] ❌ Token exchange failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"🔐 [KEYCLOAK] Response status: {e.response.status_code}")
                logger.error(f"🔐 [KEYCLOAK] Response text: {e.response.text}")
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
        logger.info(f"🔐 [KEYCLOAK] Starting user info fetch")
        logger.info(f"🔐 [KEYCLOAK] Userinfo URL: {self.userinfo_url}")
        logger.info(f"🔐 [KEYCLOAK] Access token (first 50 chars): {access_token[:50]}...")
        
        headers = {'Authorization': f'Bearer {access_token}'}
        logger.debug(f"🔐 [KEYCLOAK] Request headers: {dict((k, v if k != 'Authorization' else f'Bearer {access_token[:20]}...') for k, v in headers.items())}")
        
        # For userinfo endpoint, we need to use the internal URL since we're making the request from the backend
        # but the token was issued with the public URL, so we need to convert it to use host.docker.internal
        # This allows the container to reach the host's localhost:8081 where Keycloak is exposed
        userinfo_url = self.userinfo_url.replace('localhost:8081', 'host.docker.internal:8081')
        logger.info(f"🔐 [KEYCLOAK] Adjusted userinfo URL for Docker internal network: {userinfo_url}")
        
        try:
            logger.info(f"🔐 [KEYCLOAK] Making GET request to userinfo endpoint...")
            response = requests.get(userinfo_url, headers=headers, timeout=30)
            logger.info(f"🔐 [KEYCLOAK] Userinfo response status: {response.status_code}")
            logger.debug(f"🔐 [KEYCLOAK] Userinfo response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"🔐 [KEYCLOAK] ❌ Userinfo request failed with status {response.status_code}")
                logger.error(f"🔐 [KEYCLOAK] Response text: {response.text}")
                
                # Check for WWW-Authenticate header which might give us more info
                if 'WWW-Authenticate' in response.headers:
                    logger.error(f"🔐 [KEYCLOAK] WWW-Authenticate header: {response.headers['WWW-Authenticate']}")
            
            response.raise_for_status()
            user_info = response.json()
            
            logger.info(f"🔐 [KEYCLOAK] ✅ User info fetch successful!")
            logger.info(f"🔐 [KEYCLOAK] User info keys: {list(user_info.keys())}")
            logger.info(f"🔐 [KEYCLOAK] Username: {user_info.get('preferred_username', 'No username')}")
            logger.info(f"🔐 [KEYCLOAK] Email: {user_info.get('email', 'No email')}")
            logger.info(f"🔐 [KEYCLOAK] Subject: {user_info.get('sub', 'No subject')}")
            
            return user_info
        except requests.RequestException as e:
            logger.error(f"🔐 [KEYCLOAK] ❌ User info fetch failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"🔐 [KEYCLOAK] Response status: {e.response.status_code}")
                logger.error(f"🔐 [KEYCLOAK] Response text: {e.response.text}")
                logger.error(f"🔐 [KEYCLOAK] Response headers: {dict(e.response.headers)}")
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
        """Generate logout URL for browser redirects"""
        params = {'client_id': self.client_id}
        if post_logout_redirect_uri:
            params['post_logout_redirect_uri'] = post_logout_redirect_uri
        
        # Use public URL for browser redirects
        public_logout_url = f"{self.public_realm_url}/protocol/openid-connect/logout"
        return f"{public_logout_url}?{urlencode(params)}"
    
    def validate_token(self, access_token: str) -> bool:
        """Validate access token by calling userinfo endpoint"""
        try:
            # In development, we need to handle token validation differently
            # because tokens are issued with public URL but backend uses internal URL
            if os.getenv('ENVIRONMENT', 'development') == 'development':
                # For dev, skip issuer validation and just check if token works
                headers = {'Authorization': f'Bearer {access_token}'}
                # Try both URLs in case of network differences
                try:
                    response = requests.get(self.userinfo_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    return True
                except:
                    # If internal URL fails, token might still be valid
                    # but network routing is the issue
                    pass
            
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