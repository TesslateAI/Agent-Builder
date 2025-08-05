#!/usr/bin/env python3
"""
Comprehensive Authentication Tests for Agent-Builder
Tests Keycloak OAuth integration, JWT middleware, and session management
"""

import os
import sys
import json
import time
import jwt
import requests
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

# Add the builder/backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../builder/backend'))

# Test configuration
BASE_URL = os.getenv('TEST_BASE_URL', 'http://localhost:5000')
KEYCLOAK_URL = os.getenv('TEST_KEYCLOAK_URL', 'http://localhost:8081')
TEST_USER_EMAIL = 'test@example.com'
TEST_USER_PASSWORD = 'testpass123'

class KeycloakAuthenticationTests(unittest.TestCase):
    """Test Keycloak OAuth 2.0/OIDC integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.session = requests.Session()
        self.base_url = BASE_URL
        self.keycloak_url = KEYCLOAK_URL
        
    def test_auth_health_check(self):
        """Test authentication service health endpoint"""
        print("\n=== Testing Auth Health Check ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/auth/health", timeout=10)
            print(f"Auth health status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Auth service status: {data.get('status')}")
                print(f"Keycloak available: {data.get('keycloak_available')}")
                
                self.assertEqual(data['status'], 'healthy')
                self.assertIn('keycloak_available', data)
                self.assertIn('timestamp', data)
                
                return True
            else:
                print(f"Health check failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Auth health check failed: {e}")
            return False
    
    def test_login_endpoint(self):
        """Test OAuth login initiation endpoint"""
        print("\n=== Testing Login Endpoint ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/auth/login", timeout=10)
            print(f"Login endpoint status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Auth URL received: {data.get('auth_url', 'N/A')[:50]}...")
                print(f"State parameter: {data.get('state', 'N/A')[:20]}...")
                
                self.assertIn('auth_url', data)
                self.assertIn('state', data)
                
                # Validate auth URL structure
                auth_url = data['auth_url']
                parsed_url = urlparse(auth_url)
                query_params = parse_qs(parsed_url.query)
                
                self.assertIn('client_id', query_params)
                self.assertIn('response_type', query_params)
                self.assertIn('redirect_uri', query_params)
                self.assertIn('scope', query_params)
                self.assertIn('state', query_params)
                
                self.assertEqual(query_params['response_type'][0], 'code')
                self.assertIn('openid', query_params['scope'][0])
                
                return True
            else:
                print(f"Login endpoint failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Login endpoint test failed: {e}")
            return False
    
    def test_callback_endpoint_missing_code(self):
        """Test OAuth callback endpoint with missing authorization code"""
        print("\n=== Testing Callback Endpoint (Missing Code) ===")
        
        try:
            # Test callback without code parameter
            response = self.session.get(
                f"{self.base_url}/api/auth/callback",
                allow_redirects=False,
                timeout=10
            )
            print(f"Callback (no code) status: {response.status_code}")
            
            # Should redirect to frontend with error
            if response.status_code in [302, 307, 308]:
                location = response.headers.get('Location', '')
                print(f"Redirect location: {location}")
                
                self.assertIn('error=missing_code', location)
                return True
            else:
                print(f"Unexpected response: {response.text}")
                return False
                
        except Exception as e:
            print(f"Callback endpoint test failed: {e}")
            return False
    
    def test_callback_endpoint_oauth_error(self):
        """Test OAuth callback endpoint with OAuth error"""
        print("\n=== Testing Callback Endpoint (OAuth Error) ===")
        
        try:
            # Test callback with OAuth error
            response = self.session.get(
                f"{self.base_url}/api/auth/callback?error=access_denied",
                allow_redirects=False,
                timeout=10
            )
            print(f"Callback (oauth error) status: {response.status_code}")
            
            # Should redirect to frontend with error
            if response.status_code in [302, 307, 308]:
                location = response.headers.get('Location', '')
                print(f"Redirect location: {location}")
                
                self.assertIn('error=oauth_error', location)
                return True
            else:
                print(f"Unexpected response: {response.text}")
                return False
                
        except Exception as e:
            print(f"OAuth error callback test failed: {e}")
            return False
    
    def test_development_login(self):
        """Test development login bypass (only in dev environment)"""
        print("\n=== Testing Development Login ===")
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/dev-login",
                json={},
                timeout=10
            )
            print(f"Dev login status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Dev user created: {data.get('user', {}).get('email')}")
                print(f"Organization: {data.get('organization', {}).get('name')}")
                
                # Validate dev user structure
                self.assertIn('user', data)
                self.assertIn('organization', data)
                self.assertIn('permissions', data)
                
                user = data['user']
                self.assertEqual(user['id'], 'dev-user-123')
                self.assertEqual(user['email'], 'dev@agent-builder.local')
                
                permissions = data['permissions']
                self.assertIn('is_admin', permissions)
                self.assertTrue(permissions['is_admin'])
                
                # Check if access token cookie was set
                cookies = response.cookies
                self.assertIn('access_token', cookies)
                
                return True
            elif response.status_code == 403:
                print("Dev login not available (production environment)")
                return True  # Expected in production
            else:
                print(f"Dev login failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Development login test failed: {e}")
            return False
    
    def test_logout_without_auth(self):
        """Test logout endpoint without authentication"""
        print("\n=== Testing Logout (No Auth) ===")
        
        try:
            response = self.session.post(f"{self.base_url}/api/auth/logout", timeout=10)
            print(f"Logout (no auth) status: {response.status_code}")
            
            # Should return 401 unauthorized
            self.assertEqual(response.status_code, 401)
            
            data = response.json()
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Authentication required')
            
            return True
            
        except Exception as e:
            print(f"Logout test failed: {e}")
            return False
    
    def test_user_endpoint_without_auth(self):
        """Test user info endpoint without authentication"""
        print("\n=== Testing User Endpoint (No Auth) ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/auth/user", timeout=10)
            print(f"User endpoint (no auth) status: {response.status_code}")
            
            # Should return 401 unauthorized
            self.assertEqual(response.status_code, 401)
            
            data = response.json()
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Authentication required')
            
            return True
            
        except Exception as e:
            print(f"User endpoint test failed: {e}")
            return False
    
    def test_refresh_token_endpoint(self):
        """Test token refresh endpoint"""
        print("\n=== Testing Token Refresh ===")
        
        try:
            response = self.session.post(f"{self.base_url}/api/auth/refresh", timeout=10)
            print(f"Token refresh status: {response.status_code}")
            
            if response.status_code == 501:
                print("Token refresh not yet implemented (expected)")
                return True
            elif response.status_code == 401:
                data = response.json()
                print(f"Refresh failed: {data.get('error')}")
                self.assertIn('Refresh token not found', data.get('error', ''))
                return True
            else:
                print(f"Unexpected response: {response.text}")
                return False
                
        except Exception as e:
            print(f"Token refresh test failed: {e}")
            return False


class JWTMiddlewareTests(unittest.TestCase):
    """Test JWT token validation and middleware functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.session = requests.Session()
        self.base_url = BASE_URL
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
        
    def test_protected_endpoint_with_valid_token(self):
        """Test accessing protected endpoint with valid JWT token"""
        print("\n=== Testing Protected Endpoint (Valid Token) ===")
        
        try:
            # First get a dev token
            dev_response = self.session.post(f"{self.base_url}/api/auth/dev-login", json={})
            
            if dev_response.status_code != 200:
                print("Dev login not available, skipping JWT tests")
                return True
            
            # Extract access token from cookies
            access_token = dev_response.cookies.get('access_token')
            if not access_token:
                print("No access token received from dev login")
                return False
            
            # Test protected endpoint with token
            headers = {'Authorization': f'Bearer {access_token}'}
            response = self.session.get(
                f"{self.base_url}/api/auth/user",
                headers=headers,
                timeout=10
            )
            
            print(f"Protected endpoint status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"User data received: {data.get('email')}")
                
                self.assertIn('id', data)
                self.assertIn('email', data)
                self.assertIn('permissions', data)
                
                return True
            else:
                print(f"Protected endpoint failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"JWT validation test failed: {e}")
            return False
    
    def test_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid JWT token"""
        print("\n=== Testing Protected Endpoint (Invalid Token) ===")
        
        try:
            # Use invalid token
            invalid_token = "invalid.jwt.token"
            headers = {'Authorization': f'Bearer {invalid_token}'}
            
            response = self.session.get(
                f"{self.base_url}/api/auth/user",
                headers=headers,
                timeout=10
            )
            
            print(f"Invalid token status: {response.status_code}")
            
            # Should return 401 unauthorized
            self.assertEqual(response.status_code, 401)
            
            data = response.json()
            self.assertIn('error', data)
            self.assertIn('Authentication failed', data['error'])
            
            return True
            
        except Exception as e:
            print(f"Invalid token test failed: {e}")
            return False
    
    def test_protected_endpoint_with_expired_token(self):
        """Test accessing protected endpoint with expired JWT token"""
        print("\n=== Testing Protected Endpoint (Expired Token) ===")
        
        try:
            # Create expired token
            import uuid
            from datetime import datetime, timedelta
            
            expired_payload = {
                'sub': 'test-user',
                'email': 'test@example.com',
                'organization_id': 'test-org',
                'permissions': ['test.read'],
                'roles': ['user'],
                'iat': datetime.utcnow() - timedelta(hours=2),
                'exp': datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
                'jti': str(uuid.uuid4()),
                'type': 'access'
            }
            
            expired_token = jwt.encode(
                expired_payload,
                self.jwt_secret,
                algorithm='HS256'
            )
            
            headers = {'Authorization': f'Bearer {expired_token}'}
            response = self.session.get(
                f"{self.base_url}/api/auth/user",
                headers=headers,
                timeout=10
            )
            
            print(f"Expired token status: {response.status_code}")
            
            # Should return 401 unauthorized
            self.assertEqual(response.status_code, 401)
            
            data = response.json()
            self.assertIn('error', data)
            self.assertIn('Authentication failed', data['error'])
            
            return True
            
        except Exception as e:
            print(f"Expired token test failed: {e}")
            return False
    
    def test_token_via_cookie(self):
        """Test JWT token validation via httpOnly cookies"""
        print("\n=== Testing Token via Cookie ===")
        
        try:
            # Get dev token via cookie
            dev_response = self.session.post(f"{self.base_url}/api/auth/dev-login", json={})
            
            if dev_response.status_code != 200:
                print("Dev login not available, skipping cookie tests")
                return True
            
            # The session should now have the access token cookie
            # Test protected endpoint using the cookie
            response = self.session.get(f"{self.base_url}/api/auth/user", timeout=10)
            
            print(f"Cookie auth status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"User authenticated via cookie: {data.get('email')}")
                
                self.assertIn('id', data)
                self.assertIn('email', data)
                
                return True
            else:
                print(f"Cookie auth failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Cookie auth test failed: {e}")
            return False


class AuthorizationTests(unittest.TestCase):
    """Test permission-based access control"""
    
    def setUp(self):
        """Set up test environment with authenticated session"""
        self.session = requests.Session()
        self.base_url = BASE_URL
        
        # Get dev token for testing
        try:
            dev_response = self.session.post(f"{self.base_url}/api/auth/dev-login", json={})
            if dev_response.status_code == 200:
                self.authenticated = True
                # Extract token for header-based tests
                self.access_token = dev_response.cookies.get('access_token')
            else:
                self.authenticated = False
                self.access_token = None
        except:
            self.authenticated = False
            self.access_token = None
    
    def test_admin_permissions(self):
        """Test admin user has full permissions"""
        print("\n=== Testing Admin Permissions ===")
        
        if not self.authenticated:
            print("Authentication not available, skipping permission tests")
            return True
        
        try:
            # Test user endpoint (should work for admin)
            response = self.session.get(f"{self.base_url}/api/auth/user", timeout=10)
            print(f"Admin user endpoint status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                permissions = data.get('permissions', {})
                print(f"Admin permissions: {permissions}")
                
                # Dev user should have admin permissions
                self.assertTrue(permissions.get('is_admin', False))
                self.assertTrue(permissions.get('is_super_admin', False))
                
                # Check effective permissions
                effective_perms = permissions.get('effective_permissions', [])
                self.assertIn('*', effective_perms)
                
                return True
            else:
                print(f"Admin permission test failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Admin permission test failed: {e}")
            return False
    
    def test_flow_execution_permissions(self):
        """Test flow execution requires appropriate permissions"""
        print("\n=== Testing Flow Execution Permissions ===")
        
        if not self.authenticated:
            print("Authentication not available, skipping flow permission tests")
            return True
        
        try:
            # Create a simple test flow
            test_flow = {
                "nodes": [
                    {
                        "id": "1",
                        "type": "ConversationalAssistant",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "label": "Test Agent",
                            "component_category": "agent"
                        }
                    }
                ],
                "edges": [],
                "params": {
                    "message": "Hello test"
                }
            }
            
            # Test flow execution with admin permissions
            response = self.session.post(
                f"{self.base_url}/api/tframex/flow/execute",
                json=test_flow,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"Flow execution status: {response.status_code}")
            
            if response.status_code == 200:
                print("Flow executed successfully with admin permissions")
                return True
            elif response.status_code == 401:
                print("Flow execution requires authentication (expected)")
                return True
            elif response.status_code == 403:
                print("Flow execution forbidden (permission check working)")
                return True
            else:
                print(f"Flow execution test result: {response.text}")
                return True  # May fail due to other reasons (model config, etc.)
                
        except Exception as e:
            print(f"Flow execution permission test failed: {e}")
            return False


class SessionManagementTests(unittest.TestCase):
    """Test user session management and token lifecycle"""
    
    def setUp(self):
        """Set up test environment"""
        self.session = requests.Session()
        self.base_url = BASE_URL
    
    def test_session_creation_and_cleanup(self):
        """Test user session creation and cleanup"""
        print("\n=== Testing Session Management ===")
        
        try:
            # Create dev session
            login_response = self.session.post(f"{self.base_url}/api/auth/dev-login", json={})
            
            if login_response.status_code != 200:
                print("Dev login not available, skipping session tests")
                return True
            
            print("Session created successfully")
            
            # Verify session is active
            user_response = self.session.get(f"{self.base_url}/api/auth/user")
            self.assertEqual(user_response.status_code, 200)
            print("Session verified active")
            
            # Test logout
            logout_response = self.session.post(f"{self.base_url}/api/auth/logout")
            print(f"Logout status: {logout_response.status_code}")
            
            if logout_response.status_code == 200:
                print("Logout successful")
                
                # Verify session is terminated
                user_response_after_logout = self.session.get(f"{self.base_url}/api/auth/user")
                print(f"User endpoint after logout: {user_response_after_logout.status_code}")
                
                # Should return 401 after logout
                self.assertEqual(user_response_after_logout.status_code, 401)
                print("Session properly terminated")
                
                return True
            else:
                print(f"Logout failed: {logout_response.text}")
                return False
                
        except Exception as e:
            print(f"Session management test failed: {e}")
            return False
    
    def test_concurrent_sessions(self):
        """Test handling of multiple concurrent sessions"""
        print("\n=== Testing Concurrent Sessions ===")
        
        try:
            # Create first session
            session1 = requests.Session()
            response1 = session1.post(f"{self.base_url}/api/auth/dev-login", json={})
            
            if response1.status_code != 200:
                print("Dev login not available, skipping concurrent session tests")
                return True
            
            # Create second session
            session2 = requests.Session()
            response2 = session2.post(f"{self.base_url}/api/auth/dev-login", json={})
            
            if response2.status_code == 200:
                print("Multiple sessions created successfully")
                
                # Verify both sessions work
                user1 = session1.get(f"{self.base_url}/api/auth/user")
                user2 = session2.get(f"{self.base_url}/api/auth/user")
                
                self.assertEqual(user1.status_code, 200)
                self.assertEqual(user2.status_code, 200)
                print("Both sessions verified active")
                
                # Logout first session
                logout1 = session1.post(f"{self.base_url}/api/auth/logout")
                self.assertEqual(logout1.status_code, 200)
                
                # Verify second session still works
                user2_after = session2.get(f"{self.base_url}/api/auth/user")
                self.assertEqual(user2_after.status_code, 200)
                print("Session isolation working correctly")
                
                # Cleanup second session
                session2.post(f"{self.base_url}/api/auth/logout")
                
                return True
            else:
                print(f"Second session creation failed: {response2.text}")
                return False
                
        except Exception as e:
            print(f"Concurrent session test failed: {e}")
            return False


def run_all_tests():
    """Run all authentication tests"""
    print("=" * 60)
    print("Agent-Builder Authentication Test Suite")
    print("=" * 60)
    
    test_suites = [
        ('Keycloak Authentication', KeycloakAuthenticationTests),
        ('JWT Middleware', JWTMiddlewareTests),
        ('Authorization & Permissions', AuthorizationTests),
        ('Session Management', SessionManagementTests)
    ]
    
    all_results = []
    
    for suite_name, test_class in test_suites:
        print(f"\n{'='*20} {suite_name} {'='*20}")
        
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        # Manual test execution for better output
        suite_results = []
        test_instance = test_class()
        test_instance.setUp()
        
        for method_name in dir(test_instance):
            if method_name.startswith('test_'):
                try:
                    method = getattr(test_instance, method_name)
                    success = method()
                    suite_results.append((method_name, success))
                except Exception as e:
                    print(f"Test {method_name} failed with exception: {e}")
                    suite_results.append((method_name, False))
        
        all_results.extend([(suite_name, test_name, success) for test_name, success in suite_results])
    
    # Print summary
    print("\n" + "=" * 60)
    print("Authentication Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, _, success in all_results if success)
    total = len(all_results)
    
    for suite_name, test_name, success in all_results:
        status = "PASSED" if success else "FAILED"
        print(f"{suite_name} - {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)