/**
 * Login Page Component
 * Handles user authentication via Keycloak OAuth flow
 */
import React, { useEffect, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Alert } from '../ui/alert';
import { LogIn, Shield, Users, FileText } from 'lucide-react';

export function LoginPage() {
  const { login, devLogin, isLoading, error, isAuthenticated } = useAuth();
  const [loginError, setLoginError] = useState('');

  // Check for URL parameters (error from OAuth callback)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const errorParam = urlParams.get('error');
    
    if (errorParam) {
      const errorMessages = {
        'oauth_error': 'Authentication failed. Please try again.',
        'missing_code': 'Authentication was interrupted. Please try again.',
        'keycloak_error': 'Authentication service error. Please try again later.',
        'internal_error': 'System error. Please contact support.'
      };
      
      setLoginError(errorMessages[errorParam] || 'An unknown error occurred.');
      
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      window.location.href = '/dashboard';
    }
  }, [isAuthenticated]);

  const handleLogin = async () => {
    setLoginError('');
    try {
      await login();
    } catch (err) {
      setLoginError(err.message || 'Login failed. Please try again.');
    }
  };

  const handleDevLogin = async () => {
    setLoginError('');
    try {
      await devLogin();
    } catch (err) {
      setLoginError(err.message || 'Dev login failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header with Logo */}
        <div className="text-center">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <img
              src="/Tesslate.svg"
              alt="Tesslate"
              className="h-8 w-auto"
            />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">
                Tesslate Agent Builder
              </h1>
            </div>
          </div>
          <p className="text-muted-foreground text-sm">
            Visual Flow Builder for TFrameX v1.1.0
          </p>
        </div>

        {/* Login Card */}
        <Card className="glass border-border/50 shadow-xl">
          <CardHeader className="text-center pb-6">
            <CardTitle className="text-xl text-foreground">Welcome Back</CardTitle>
            <CardDescription className="text-muted-foreground">
              Sign in to your account to continue building AI workflows
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {(error || loginError) && (
              <Alert variant="destructive" className="bg-destructive/10 border-destructive/20">
                {error || loginError}
              </Alert>
            )}
            
            <div className="space-y-4">
              <Button
                onClick={handleLogin}
                disabled={isLoading}
                className="w-full h-12 bg-primary text-primary-foreground hover:bg-primary/90 transition-all duration-200"
                size="lg"
              >
                {isLoading ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Signing In...
                  </div>
                ) : (
                  <>
                    <LogIn className="h-4 w-4 mr-2" />
                    Sign In with SSO
                  </>
                )}
              </Button>
              
              {/* Development Login Button */}
              {import.meta.env.DEV && (
                <Button
                  onClick={handleDevLogin}
                  disabled={isLoading}
                  variant="outline"
                  className="w-full h-12 border-dashed border-orange-500 text-orange-600 hover:bg-orange-50 transition-all duration-200"
                  size="lg"
                >
                  {isLoading ? (
                    <div className="flex items-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-orange-500 mr-2"></div>
                      Dev Login...
                    </div>
                  ) : (
                    <>
                      <Shield className="h-4 w-4 mr-2" />
                      Dev Login (Skip Auth)
                    </>
                  )}
                </Button>
              )}
              
              <div className="text-center text-sm text-muted-foreground">
                <p>
                  Secure authentication powered by Keycloak
                </p>
              </div>
              
              {/* Enterprise Features */}
              <div className="border-t border-border/50 pt-4">
                <div className="text-center space-y-3">
                  <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                    Enterprise Features
                  </p>
                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div className="flex flex-col items-center space-y-1 p-2 rounded-lg bg-card/30">
                      <Shield className="h-4 w-4 text-primary" />
                      <span className="text-muted-foreground">SSO Integration</span>
                    </div>
                    <div className="flex flex-col items-center space-y-1 p-2 rounded-lg bg-card/30">
                      <Users className="h-4 w-4 text-accent" />
                      <span className="text-muted-foreground">Role-Based Access</span>
                    </div>
                    <div className="flex flex-col items-center space-y-1 p-2 rounded-lg bg-card/30">
                      <FileText className="h-4 w-4 text-secondary" />
                      <span className="text-muted-foreground">Audit Logging</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center text-xs text-muted-foreground">
          <p>
            By signing in, you agree to our terms of service and privacy policy.
          </p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;