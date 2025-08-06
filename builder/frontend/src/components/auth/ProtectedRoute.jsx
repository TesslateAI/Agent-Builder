/**
 * Protected Route Component
 * Wraps routes that require authentication and/or specific permissions
 */
import React from 'react';
import { useAuth, PermissionGate } from '../../contexts/AuthContext';
import { Alert } from '../ui/alert';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Shield, Lock, AlertTriangle } from 'lucide-react';

// Loading component
function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <h2 className="text-xl font-semibold text-gray-900">Loading...</h2>
        <p className="text-gray-600">Checking authentication status</p>
      </div>
    </div>
  );
}

// Unauthenticated component
function UnauthenticatedScreen({ onLogin }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <Card className="max-w-md w-full">
        <CardHeader className="text-center">
          <div className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-destructive" />
          </div>
          <CardTitle className="text-2xl">Authentication Required</CardTitle>
          <CardDescription>
            You need to be logged in to access this page
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <Button onClick={onLogin} className="w-full">
            Sign In
          </Button>
          <p className="text-sm text-gray-600">
            Secure authentication with enterprise SSO
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// Permission denied component
function PermissionDeniedScreen({ requiredPermission, userPermissions }) {
  const { user } = useAuth();
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <Card className="max-w-lg w-full">
        <CardHeader className="text-center">
          <div className="w-16 h-16 bg-warning/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-warning" />
          </div>
          <CardTitle className="text-2xl">Access Denied</CardTitle>
          <CardDescription>
            You don't have permission to access this resource
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <div>
              <p className="font-medium">Insufficient Permissions</p>
              <p className="text-sm">
                This action requires: <code className="bg-gray-100 px-1 rounded">{requiredPermission}</code>
              </p>
            </div>
          </Alert>
          
          <div className="text-sm text-gray-600">
            <p className="font-medium mb-2">Your current permissions:</p>
            <div className="bg-gray-50 p-3 rounded max-h-32 overflow-y-auto">
              {userPermissions && userPermissions.length > 0 ? (
                <ul className="space-y-1">
                  {userPermissions.map((permission, index) => (
                    <li key={index} className="font-mono text-xs">
                      • {permission}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500 italic">No permissions assigned</p>
              )}
            </div>
          </div>
          
          <div className="pt-4 border-t">
            <p className="text-sm text-gray-600 text-center">
              Contact your administrator if you believe you should have access to this resource.
            </p>
            <p className="text-xs text-gray-500 text-center mt-2">
              User: {user?.email} | Role: {user?.role || 'User'}
            </p>
          </div>
          
          <div className="flex space-x-2">
            <Button 
              variant="outline" 
              onClick={() => window.history.back()}
              className="flex-1"
            >
              Go Back
            </Button>
            <Button 
              onClick={() => window.location.href = '/dashboard'}
              className="flex-1"
            >
              Dashboard
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Main ProtectedRoute component
export function ProtectedRoute({ 
  children, 
  permission, 
  permissions, 
  requireAll = false,
  fallback,
  showPermissionDenied = true 
}) {
  const auth = useAuth();
  const { isLoading, isAuthenticated, login, hasPermission, hasAnyPermission, hasAllPermissions } = auth;

  // Show loading screen while checking authentication
  if (isLoading) {
    return <LoadingScreen />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <UnauthenticatedScreen onLogin={login} />;
  }

  // Check permissions if specified
  if (permission || permissions) {
    let hasAccess = false;
    let requiredPermission = '';

    if (permission) {
      hasAccess = hasPermission(permission);
      requiredPermission = permission;
    } else if (permissions) {
      hasAccess = requireAll 
        ? hasAllPermissions(permissions)
        : hasAnyPermission(permissions);
      requiredPermission = Array.isArray(permissions) ? permissions.join(' OR ') : permissions;
    }

    if (!hasAccess) {
      // Use custom fallback if provided
      if (fallback) {
        return fallback;
      }

      // Show permission denied screen
      if (showPermissionDenied) {
        return (
          <PermissionDeniedScreen 
            requiredPermission={requiredPermission}
            userPermissions={auth.permissions?.effective_permissions || []}
          />
        );
      }

      // Return null if no fallback and permission denied screen is disabled
      return null;
    }
  }

  // Render children if all checks pass
  return children;
}

// Higher-order component version
export function withProtectedRoute(Component, options = {}) {
  return function ProtectedComponent(props) {
    return (
      <ProtectedRoute {...options}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}

// Specific permission wrappers
export function AdminRoute({ children, ...props }) {
  return (
    <ProtectedRoute permission="admin" {...props}>
      {children}
    </ProtectedRoute>
  );
}

export function ProjectRoute({ children, ...props }) {
  return (
    <ProtectedRoute permissions={["projects.read", "projects.update"]} {...props}>
      {children}
    </ProtectedRoute>
  );
}

export function FlowRoute({ children, ...props }) {
  return (
    <ProtectedRoute permissions={["flows.read", "flows.execute"]} {...props}>
      {children}
    </ProtectedRoute>
  );
}

export default ProtectedRoute;