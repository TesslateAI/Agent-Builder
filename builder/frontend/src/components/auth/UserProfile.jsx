/**
 * User Profile Component
 * Displays user information and provides logout functionality
 */
import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import { 
  User, 
  Building2, 
  Mail, 
  Calendar, 
  Shield, 
  LogOut,
  Settings,
  Crown,
  Lock
} from 'lucide-react';

export function UserProfile() {
  const { user, organization, permissions, logout, isAdmin, isSuperAdmin } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
      setIsLoggingOut(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getPermissionBadgeVariant = (permission) => {
    if (permission.includes('delete') || permission.includes('admin')) return 'destructive';
    if (permission.includes('create') || permission.includes('update')) return 'default';
    return 'secondary';
  };

  return (
    <div className="space-y-4 overflow-y-auto max-h-[calc(80vh-120px)]">
      {/* Header */}
      <div className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center">
              <User className="w-6 h-6 text-muted-foreground" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">
                {user?.first_name || user?.last_name 
                  ? `${user.first_name} ${user.last_name}`.trim()
                  : user?.username || 'User'
                }
                {isSuperAdmin() && (
                  <Crown className="inline-block w-4 h-4 text-warning ml-2" />
                )}
                {isAdmin() && !isSuperAdmin() && (
                  <Shield className="inline-block w-4 h-4 text-primary ml-2" />
                )}
              </h2>
              <p className="flex items-center text-sm text-muted-foreground">
                <Mail className="w-4 h-4 mr-1" />
                {user?.email}
              </p>
            </div>
          </div>
        </div>
      </div>
      {/* Organization Info */}
      {organization && (
        <div className="bg-muted/50 rounded-lg p-3">
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              Organization
            </label>
            <div>
              <p className="font-medium">{organization.name}</p>
              {organization.description && (
                <p className="text-sm text-muted-foreground">{organization.description}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Account Details */}
      <div className="bg-muted/50 rounded-lg p-3">
        <div className="space-y-3">
          <label className="text-sm font-medium">Account Details</label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Username:</span>
              <p className="font-medium">{user?.username}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Member Since:</span>
              <p className="font-medium">{formatDate(user?.created_at)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Last Login:</span>
              <p className="font-medium">{formatDate(user?.last_login)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Account Status:</span>
              <Badge variant="success" className="ml-1">Active</Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Permissions */}
      <div className="bg-muted/50 rounded-lg p-3">
        <div className="space-y-3">
          <label className="text-sm font-medium flex items-center gap-2">
            <Lock className="w-4 h-4" />
            Permissions & Access
          </label>
          
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-muted-foreground">Role Level:</span>
              {isSuperAdmin() && (
                <Badge variant="destructive" className="text-xs">
                  <Crown className="w-3 h-3 mr-1" />
                  Super Admin
                </Badge>
              )}
              {isAdmin() && !isSuperAdmin() && (
                <Badge variant="default" className="text-xs">
                  <Shield className="w-3 h-3 mr-1" />
                  Admin
                </Badge>
              )}
              {!isAdmin() && (
                <Badge variant="secondary" className="text-xs">
                  <User className="w-3 h-3 mr-1" />
                  User
                </Badge>
              )}
            </div>

            {permissions?.effective_permissions && permissions.effective_permissions.length > 0 && (
              <div>
                <span className="text-sm text-muted-foreground block mb-2">Current Permissions:</span>
                <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                  {permissions.effective_permissions.slice(0, 10).map((permission, index) => (
                    <Badge 
                      key={index} 
                      variant={getPermissionBadgeVariant(permission)}
                      className="text-xs"
                    >
                      {permission}
                    </Badge>
                  ))}
                  {permissions.effective_permissions.length > 10 && (
                    <Badge variant="outline" className="text-xs">
                      +{permissions.effective_permissions.length - 10} more
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => {
              // TODO: Implement settings page
              console.log('Settings not implemented yet');
            }}
          >
            <Settings className="w-4 h-4 mr-2" />
            Account Settings
          </Button>
          
          <Button
            variant="destructive"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="flex-1"
          >
            {isLoggingOut ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Signing Out...
              </div>
            ) : (
              <>
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </>
            )}
          </Button>
      </div>
    </div>
  );
}

export default UserProfile;