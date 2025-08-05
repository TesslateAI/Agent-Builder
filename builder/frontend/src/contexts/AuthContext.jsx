/**
 * Authentication Context for Agent-Builder
 * Manages user authentication state, login/logout, and permission checking
 */
import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000') + '/api';

// Auth states
const AUTH_STATES = {
  IDLE: 'idle',
  LOADING: 'loading',
  AUTHENTICATED: 'authenticated',
  UNAUTHENTICATED: 'unauthenticated',
  ERROR: 'error'
};

// Action types
const AUTH_ACTIONS = {
  SET_LOADING: 'SET_LOADING',
  SET_AUTHENTICATED: 'SET_AUTHENTICATED',
  SET_UNAUTHENTICATED: 'SET_UNAUTHENTICATED',
  SET_ERROR: 'SET_ERROR',
  UPDATE_USER: 'UPDATE_USER',
  SET_PERMISSIONS: 'SET_PERMISSIONS'
};

// Initial state
const initialState = {
  status: AUTH_STATES.IDLE,
  user: null,
  organization: null,
  permissions: {
    organization_permissions: [],
    project_permissions: [],
    effective_permissions: [],
    expanded_permissions: [],
    is_admin: false,
    is_super_admin: false
  },
  error: null,
  isLoading: false
};

// Auth reducer
function authReducer(state, action) {
  switch (action.type) {
    case AUTH_ACTIONS.SET_LOADING:
      return {
        ...state,
        status: AUTH_STATES.LOADING,
        isLoading: true,
        error: null
      };
      
    case AUTH_ACTIONS.SET_AUTHENTICATED:
      return {
        ...state,
        status: AUTH_STATES.AUTHENTICATED,
        user: action.payload.user,
        organization: action.payload.organization,
        permissions: action.payload.permissions || state.permissions,
        isLoading: false,
        error: null
      };
      
    case AUTH_ACTIONS.SET_UNAUTHENTICATED:
      return {
        ...initialState,
        status: AUTH_STATES.UNAUTHENTICATED
      };
      
    case AUTH_ACTIONS.SET_ERROR:
      return {
        ...state,
        status: AUTH_STATES.ERROR,
        error: action.payload,
        isLoading: false
      };
      
    case AUTH_ACTIONS.UPDATE_USER:
      return {
        ...state,
        user: { ...state.user, ...action.payload }
      };
      
    case AUTH_ACTIONS.SET_PERMISSIONS:
      return {
        ...state,
        permissions: action.payload
      };
      
    default:
      return state;
  }
}

// Create contexts
const AuthContext = createContext();
const AuthDispatchContext = createContext();

// Auth Provider component
export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Configure axios defaults
  useEffect(() => {
    // Set up axios interceptors for automatic token handling
    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        // Cookies are automatically sent, but we can add additional headers if needed
        config.withCredentials = true;
        return config;
      },
      (error) => Promise.reject(error)
    );

    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          dispatch({ type: AUTH_ACTIONS.SET_UNAUTHENTICATED });
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(requestInterceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, []);

  const checkAuthStatus = useCallback(async () => {
    try {
      dispatch({ type: AUTH_ACTIONS.SET_LOADING });
      
      const response = await axios.get(`${API_BASE_URL}/auth/user`, {
        withCredentials: true
      });
      
      const userData = response.data;
      
      dispatch({
        type: AUTH_ACTIONS.SET_AUTHENTICATED,
        payload: {
          user: {
            id: userData.id,
            email: userData.email,
            username: userData.username,
            first_name: userData.first_name,
            last_name: userData.last_name,
            last_login: userData.last_login,
            created_at: userData.created_at
          },
          organization: userData.organization,
          permissions: userData.permissions
        }
      });
      
    } catch (error) {
      if (error.response?.status === 401) {
        dispatch({ type: AUTH_ACTIONS.SET_UNAUTHENTICATED });
      } else {
        console.error('Auth check failed:', error);
        dispatch({
          type: AUTH_ACTIONS.SET_ERROR,
          payload: 'Failed to check authentication status'
        });
      }
    }
  }, []);

  // Check authentication status on mount
  useEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  const login = useCallback(async () => {
    try {
      dispatch({ type: AUTH_ACTIONS.SET_LOADING });
      
      // Get authorization URL from backend
      const response = await axios.get(`${API_BASE_URL}/auth/login`);
      const { auth_url } = response.data;
      
      // Redirect to Keycloak
      window.location.href = auth_url;
      
    } catch (error) {
      console.error('Login failed:', error);
      let errorMessage = 'Login failed';
      
      if (error.code === 'ERR_NETWORK') {
        errorMessage = 'Cannot connect to authentication server. Please try again.';
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      dispatch({
        type: AUTH_ACTIONS.SET_ERROR,
        payload: errorMessage
      });
    }
  }, []);

  const devLogin = useCallback(async () => {
    try {
      dispatch({ type: AUTH_ACTIONS.SET_LOADING });
      
      // Use development login bypass
      const response = await axios.post(`${API_BASE_URL}/auth/dev-login`, {}, {
        withCredentials: true
      });
      
      const userData = response.data;
      
      dispatch({
        type: AUTH_ACTIONS.SET_AUTHENTICATED,
        payload: {
          user: userData.user,
          organization: userData.organization,
          permissions: userData.permissions
        }
      });
      
      // Redirect to dashboard
      window.location.href = '/';
      
    } catch (error) {
      console.error('Dev login failed:', error);
      dispatch({
        type: AUTH_ACTIONS.SET_ERROR,
        payload: 'Development login failed'
      });
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      dispatch({ type: AUTH_ACTIONS.SET_LOADING });
      
      console.log('Attempting logout...');
      const response = await axios.post(`${API_BASE_URL}/auth/logout`, {}, {
        withCredentials: true
      });
      
      console.log('Logout response:', response);
      
      // Clear any local storage
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
      
      // Clear any persisted app state
      localStorage.removeItem('tframexStudioProjects');
      
      // Set unauthenticated state - this will trigger the LoginPage to render
      dispatch({ type: AUTH_ACTIONS.SET_UNAUTHENTICATED });
      
    } catch (error) {
      console.error('Logout failed:', error);
      console.error('Error response:', error.response);
      
      // Even if logout fails on backend, clear local state
      // Clear any local storage
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('tframexStudioProjects');
      
      // Set unauthenticated state - this will trigger the LoginPage to render
      dispatch({ type: AUTH_ACTIONS.SET_UNAUTHENTICATED });
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/user`, {
        withCredentials: true
      });
      
      const userData = response.data;
      
      dispatch({
        type: AUTH_ACTIONS.SET_AUTHENTICATED,
        payload: {
          user: {
            id: userData.id,
            email: userData.email,
            username: userData.username,
            first_name: userData.first_name,
            last_name: userData.last_name,
            last_login: userData.last_login,
            created_at: userData.created_at
          },
          organization: userData.organization,
          permissions: userData.permissions
        }
      });
      
    } catch (error) {
      console.error('Refresh user failed:', error);
      if (error.response?.status === 401) {
        dispatch({ type: AUTH_ACTIONS.SET_UNAUTHENTICATED });
      }
    }
  }, []);

  // Permission checking utilities
  const hasPermission = useCallback((permission) => {
    if (!state.permissions) return false;
    
    const { expanded_permissions, is_super_admin } = state.permissions;
    
    // Super admin has all permissions
    if (is_super_admin) return true;
    
    // Check exact permission
    if (expanded_permissions.includes(permission)) return true;
    
    // Check wildcard permissions
    const resourceType = permission.split('.')[0];
    if (expanded_permissions.includes(`${resourceType}.*`)) return true;
    
    return false;
  }, [state.permissions]);

  const hasAnyPermission = useCallback((permissions) => {
    return permissions.some(permission => hasPermission(permission));
  }, [hasPermission]);

  const hasAllPermissions = useCallback((permissions) => {
    return permissions.every(permission => hasPermission(permission));
  }, [hasPermission]);

  const isAdmin = useCallback(() => {
    return state.permissions?.is_admin || false;
  }, [state.permissions]);

  const isSuperAdmin = useCallback(() => {
    return state.permissions?.is_super_admin || false;
  }, [state.permissions]);

  const value = {
    // State
    ...state,
    
    // Computed properties
    isAuthenticated: state.status === AUTH_STATES.AUTHENTICATED,
    isUnauthenticated: state.status === AUTH_STATES.UNAUTHENTICATED,
    
    // Actions
    login,
    devLogin,
    logout,
    refreshUser,
    checkAuthStatus,
    
    // Permission utilities
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    isAdmin,
    isSuperAdmin
  };

  return (
    <AuthContext.Provider value={value}>
      <AuthDispatchContext.Provider value={dispatch}>
        {children}
      </AuthDispatchContext.Provider>
    </AuthContext.Provider>
  );
}

// Custom hooks
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function useAuthDispatch() {
  const context = useContext(AuthDispatchContext);
  if (!context) {
    throw new Error('useAuthDispatch must be used within an AuthProvider');
  }
  return context;
}

// Higher-order component for protecting routes
export function withAuth(Component) {
  return function AuthenticatedComponent(props) {
    const { isAuthenticated, isLoading } = useAuth();
    
    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
        </div>
      );
    }
    
    if (!isAuthenticated) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-4">Authentication Required</h2>
            <p className="text-gray-600 mb-4">Please log in to access this page.</p>
            <button
              onClick={() => window.location.reload()}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    
    return React.createElement(Component, props);
  };
}

// Component for checking permissions
export function PermissionGate({ permission, permissions, requireAll = false, fallback = null, children }) {
  const auth = useAuth();
  
  let hasAccess = false;
  
  if (permission) {
    hasAccess = auth.hasPermission(permission);
  } else if (permissions) {
    hasAccess = requireAll 
      ? auth.hasAllPermissions(permissions)
      : auth.hasAnyPermission(permissions);
  }
  
  if (!hasAccess) {
    return fallback || null;
  }
  
  return children;
}