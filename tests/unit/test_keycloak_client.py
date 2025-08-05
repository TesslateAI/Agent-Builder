#!/usr/bin/env python3
"""
Unit Tests for Keycloak Client
Tests the KeycloakClient class methods and error handling
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add the builder/backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../builder/backend'))

from auth.keycloak_client import KeycloakClient, KeycloakError


class TestKeycloakClient(unittest.TestCase):
    """Unit tests for KeycloakClient class"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'KEYCLOAK_SERVER_URL': 'http://test-keycloak:8080',
            'KEYCLOAK_PUBLIC_URL': 'http://localhost:8081',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_CLIENT_ID': 'test-client',
            'KEYCLOAK_CLIENT_SECRET': 'test-secret',
            'KEYCLOAK_REDIRECT_URI': 'http://localhost:5000/api/auth/callback'
        })
        self.env_patcher.start()
        
        self.client = KeycloakClient()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_initialization(self):
        """Test KeycloakClient initialization"""
        self.assertEqual(self.client.server_url, 'http://test-keycloak:8080')
        self.assertEqual(self.client.public_server_url, 'http://localhost:8081')
        self.assertEqual(self.client.realm, 'test-realm')
        self.assertEqual(self.client.client_id, 'test-client')
        self.assertEqual(self.client.client_secret, 'test-secret')
        
        # Check URL construction
        expected_auth_url = 'http://localhost:8081/realms/test-realm/protocol/openid-connect/auth'
        self.assertEqual(self.client.auth_url, expected_auth_url)
        
        expected_token_url = 'http://localhost:8081/realms/test-realm/protocol/openid-connect/token'
        self.assertEqual(self.client.token_url, expected_token_url)
    
    def test_get_authorization_url(self):
        """Test authorization URL generation"""
        # Test with default scopes
        url = self.client.get_authorization_url()
        
        self.assertIn('client_id=test-client', url)
        self.assertIn('response_type=code', url)
        self.assertIn('redirect_uri=http%3A//localhost%3A5000/api/auth/callback', url)
        self.assertIn('scope=openid+profile+email+roles', url)
        
        # Test with custom state
        url_with_state = self.client.get_authorization_url(state='custom-state')
        self.assertIn('state=custom-state', url_with_state)
        
        # Test with custom scopes
        url_with_scopes = self.client.get_authorization_url(scopes=['openid', 'profile'])
        self.assertIn('scope=openid+profile', url_with_scopes)
    
    @patch('auth.keycloak_client.requests.post')
    def test_exchange_code_for_tokens_success(self, mock_post):
        """Test successful token exchange"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.client.exchange_code_for_tokens('test-auth-code')
        
        # Verify request was made correctly
        mock_post.assert_called_once_with(
            self.client.token_url,
            data={
                'grant_type': 'authorization_code',
                'client_id': 'test-client',
                'client_secret': 'test-secret',
                'code': 'test-auth-code',
                'redirect_uri': 'http://localhost:5000/api/auth/callback'
            },
            timeout=30
        )
        
        # Verify response
        self.assertEqual(result['access_token'], 'test-access-token')
        self.assertEqual(result['refresh_token'], 'test-refresh-token')
    
    @patch('auth.keycloak_client.requests.post')
    def test_exchange_code_for_tokens_failure(self, mock_post):
        """Test failed token exchange"""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception('HTTP Error')
        mock_post.return_value = mock_response
        
        with self.assertRaises(KeycloakError) as context:
            self.client.exchange_code_for_tokens('invalid-code')
        
        self.assertIn('Failed to exchange code for tokens', str(context.exception))
    
    @patch('auth.keycloak_client.requests.post')
    def test_refresh_access_token_success(self, mock_post):
        """Test successful token refresh"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new-access-token',
            'refresh_token': 'new-refresh-token',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.client.refresh_access_token('test-refresh-token')
        
        # Verify request
        mock_post.assert_called_once_with(
            self.client.token_url,
            data={
                'grant_type': 'refresh_token',
                'client_id': 'test-client',
                'client_secret': 'test-secret',
                'refresh_token': 'test-refresh-token'
            },
            timeout=30
        )
        
        # Verify response
        self.assertEqual(result['access_token'], 'new-access-token')
    
    @patch('auth.keycloak_client.requests.get')
    def test_get_user_info_success(self, mock_get):
        """Test successful user info retrieval"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sub': 'user-123',
            'email': 'test@example.com',
            'given_name': 'Test',
            'family_name': 'User'
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.client.get_user_info('test-access-token')
        
        # Verify request
        mock_get.assert_called_once_with(
            self.client.userinfo_url,
            headers={'Authorization': 'Bearer test-access-token'},
            timeout=30
        )
        
        # Verify response
        self.assertEqual(result['sub'], 'user-123')
        self.assertEqual(result['email'], 'test@example.com')
    
    @patch('auth.keycloak_client.requests.get')
    def test_get_user_info_failure(self, mock_get):
        """Test failed user info retrieval"""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception('Unauthorized')
        mock_get.return_value = mock_response
        
        with self.assertRaises(KeycloakError) as context:
            self.client.get_user_info('invalid-token')
        
        self.assertIn('Failed to get user info', str(context.exception))
    
    @patch('auth.keycloak_client.requests.post')
    def test_logout_user_success(self, mock_post):
        """Test successful user logout"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        result = self.client.logout_user('test-refresh-token')
        
        # Verify request
        mock_post.assert_called_once_with(
            self.client.logout_url,
            data={
                'client_id': 'test-client',
                'client_secret': 'test-secret',
                'refresh_token': 'test-refresh-token'
            },
            timeout=30
        )
        
        # Verify response
        self.assertTrue(result)
    
    def test_get_logout_url(self):
        """Test logout URL generation"""
        url = self.client.get_logout_url()
        
        self.assertIn('client_id=test-client', url)
        self.assertIn('http://localhost:8081/realms/test-realm/protocol/openid-connect/logout', url)
        
        # Test with post logout redirect
        url_with_redirect = self.client.get_logout_url('http://localhost:5173/login')
        self.assertIn('post_logout_redirect_uri=http%3A//localhost%3A5173/login', url_with_redirect)
    
    @patch('auth.keycloak_client.requests.post')
    def test_get_admin_token_success(self, mock_post):
        """Test successful admin token retrieval"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'admin-token',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with patch.dict(os.environ, {
            'KEYCLOAK_ADMIN_USERNAME': 'admin',
            'KEYCLOAK_ADMIN_PASSWORD': 'admin-pass'
        }):
            token = self.client._get_admin_token()
        
        # Verify request
        mock_post.assert_called_once_with(
            'http://test-keycloak:8080/realms/master/protocol/openid-connect/token',
            data={
                'grant_type': 'password',
                'client_id': 'admin-cli',
                'username': 'admin',
                'password': 'admin-pass'
            },
            timeout=30
        )
        
        # Verify token caching
        self.assertEqual(token, 'admin-token')
        self.assertEqual(self.client._admin_token, 'admin-token')
        self.assertIsNotNone(self.client._admin_token_expires)
    
    @patch('auth.keycloak_client.requests.post')
    def test_create_user_success(self, mock_post):
        """Test successful user creation"""
        # Mock admin token request
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            'access_token': 'admin-token',
            'expires_in': 3600
        }
        mock_token_response.raise_for_status.return_value = None
        
        # Mock user creation request
        mock_create_response = MagicMock()
        mock_create_response.status_code = 201
        mock_create_response.headers = {'Location': 'http://keycloak/admin/realms/test/users/user-123'}
        mock_create_response.raise_for_status.return_value = None
        
        # Configure mock to return different responses for different calls
        mock_post.side_effect = [mock_token_response, mock_create_response]
        
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user_id = self.client.create_user(user_data)
        
        # Verify user creation request
        self.assertEqual(mock_post.call_count, 2)
        create_call = mock_post.call_args_list[1]
        
        self.assertEqual(create_call[1]['json']['username'], 'testuser')
        self.assertEqual(create_call[1]['json']['email'], 'test@example.com')
        self.assertEqual(user_id, 'user-123')
    
    @patch('auth.keycloak_client.requests.get')
    def test_get_user_by_username_success(self, mock_get):
        """Test successful user retrieval by username"""
        # Mock admin token (reuse cached token)
        self.client._admin_token = 'admin-token'
        self.client._admin_token_expires = datetime.now() + timedelta(hours=1)
        
        # Mock user search response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'id': 'user-123',
            'username': 'testuser',
            'email': 'test@example.com'
        }]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        user = self.client.get_user_by_username('testuser')
        
        # Verify request
        mock_get.assert_called_once_with(
            f'{self.client.admin_url}/users',
            headers={'Authorization': 'Bearer admin-token'},
            params={'username': 'testuser', 'exact': True},
            timeout=30
        )
        
        # Verify response
        self.assertEqual(user['id'], 'user-123')
        self.assertEqual(user['username'], 'testuser')
    
    @patch('auth.keycloak_client.requests.get')
    def test_get_user_by_username_not_found(self, mock_get):
        """Test user not found by username"""
        # Mock admin token
        self.client._admin_token = 'admin-token'
        self.client._admin_token_expires = datetime.now() + timedelta(hours=1)
        
        # Mock empty response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        user = self.client.get_user_by_username('nonexistent')
        
        self.assertIsNone(user)
    
    @patch('auth.keycloak_client.requests.get')
    def test_health_check_success(self, mock_get):
        """Test successful health check"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.client.health_check()
        
        mock_get.assert_called_once_with(
            f'{self.client.realm_url}',
            timeout=10
        )
        self.assertTrue(result)
    
    @patch('auth.keycloak_client.requests.get')
    def test_health_check_failure(self, mock_get):
        """Test failed health check"""
        mock_get.side_effect = Exception('Connection failed')
        
        result = self.client.health_check()
        
        self.assertFalse(result)
    
    def test_validate_token(self):
        """Test token validation"""
        # Test valid token (mock get_user_info)
        with patch.object(self.client, 'get_user_info', return_value={'sub': 'user-123'}):
            result = self.client.validate_token('valid-token')
            self.assertTrue(result)
        
        # Test invalid token
        with patch.object(self.client, 'get_user_info', side_effect=KeycloakError('Invalid token')):
            result = self.client.validate_token('invalid-token')
            self.assertFalse(result)


class TestKeycloakError(unittest.TestCase):
    """Test KeycloakError exception class"""
    
    def test_keycloak_error_creation(self):
        """Test KeycloakError creation"""
        error = KeycloakError('Test error')
        self.assertEqual(error.message, 'Test error')
        self.assertEqual(error.status_code, 500)
        self.assertEqual(str(error), 'Test error')
    
    def test_keycloak_error_with_status_code(self):
        """Test KeycloakError with custom status code"""
        error = KeycloakError('Unauthorized', 401)
        self.assertEqual(error.message, 'Unauthorized')
        self.assertEqual(error.status_code, 401)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestKeycloakClient))
    suite.addTests(loader.loadTestsFromTestCase(TestKeycloakError))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)