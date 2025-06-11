# Frontend Integration Guide - Authentication System

## Overview

This guide provides everything needed to integrate the JDA AI Portal authentication system with the React frontend. The backend authentication system is fully operational and ready for frontend integration.

## API Endpoints Summary

### Authentication Endpoints (`/auth`)

#### POST `/auth/register`
- **Purpose**: Register new user account
- **Body**: `UserCreate` schema
- **Response**: `UserLoginResponse` with tokens and user info
- **Status**: 201 Created

#### POST `/auth/login`
- **Purpose**: Authenticate user with email/password
- **Body**: `{email: string, password: string}`
- **Response**: `UserLoginResponse` with tokens
- **Status**: 200 OK

#### POST `/auth/refresh`
- **Purpose**: Refresh access token using refresh token
- **Body**: `{refresh_token: string}`
- **Response**: New tokens
- **Status**: 200 OK

#### GET `/auth/me`
- **Purpose**: Get current user profile
- **Requires**: Authentication header
- **Response**: User profile data

### User Management Endpoints (`/users`)

#### GET `/users/me`
- **Purpose**: Get own profile
- **Requires**: Authentication
- **Response**: User profile

#### PUT `/users/me`
- **Purpose**: Update own profile
- **Requires**: Authentication
- **Body**: `UserUpdate` schema
- **Response**: Updated user profile

#### POST `/users/me/change-password`
- **Purpose**: Change own password
- **Requires**: Authentication
- **Body**: `{current_password: string, new_password: string}`
- **Response**: Success message

#### GET `/users` (Manager/Admin only)
- **Purpose**: List users with pagination
- **Query params**: `page`, `size`, `role`, `status`, `search`
- **Response**: Paginated user list

### Admin Endpoints (`/admin`) - Admin Only

#### GET `/admin/stats/system`
- **Purpose**: Get system statistics
- **Response**: User counts, role distribution, etc.

## Authentication Flow

### 1. Registration/Login Flow
```typescript
// Register new user
const registerUser = async (userData: RegisterRequest): Promise<AuthResponse> => {
  const response = await fetch('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
};

// Login existing user
const loginUser = async (email: string, password: string): Promise<AuthResponse> => {
  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
};
```

### 2. Token Storage and Management
```typescript
// Store tokens securely
const storeAuthTokens = (tokens: AuthResponse) => {
  // Store access token in memory or secure storage
  localStorage.setItem('access_token', tokens.access_token);
  // Store refresh token in secure HTTP-only cookie (preferred) or localStorage
  localStorage.setItem('refresh_token', tokens.refresh_token);
  localStorage.setItem('user', JSON.stringify(tokens.user));
};

// Get stored access token
const getAccessToken = (): string | null => {
  return localStorage.getItem('access_token');
};

// Clear stored tokens
const clearAuthTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
};
```

### 3. API Request Interceptor
```typescript
// Add auth header to requests
const authenticatedFetch = async (url: string, options: RequestInit = {}) => {
  const token = getAccessToken();
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return fetch(url, { ...options, headers });
};
```

### 4. Token Refresh Logic
```typescript
const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return null;
  
  try {
    const response = await fetch('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    
    if (!response.ok) {
      // Refresh token is invalid, redirect to login
      clearAuthTokens();
      window.location.href = '/login';
      return null;
    }
    
    const tokens = await response.json();
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    
    return tokens.access_token;
  } catch (error) {
    clearAuthTokens();
    window.location.href = '/login';
    return null;
  }
};
```

## Role-Based Access Control

### User Roles
- **CLIENT**: Basic user access, can view own profile and assigned projects
- **PROJECT_MANAGER**: Can manage team members and projects
- **ADMIN**: Full system access

### Frontend Route Protection
```typescript
interface ProtectedRouteProps {
  component: React.ComponentType;
  requiredRole?: 'client' | 'project_manager' | 'admin';
  children?: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  component: Component, 
  requiredRole,
  children 
}) => {
  const user = getCurrentUser();
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  if (requiredRole && !hasRequiredRole(user.role, requiredRole)) {
    return <Navigate to="/unauthorized" replace />;
  }
  
  return children ? <>{children}</> : <Component />;
};

const hasRequiredRole = (userRole: string, requiredRole: string): boolean => {
  const roleHierarchy = {
    'client': 1,
    'project_manager': 2, 
    'admin': 3
  };
  
  return roleHierarchy[userRole] >= roleHierarchy[requiredRole];
};
```

## Error Handling

### Common HTTP Status Codes
- **401 Unauthorized**: Invalid or expired token, redirect to login
- **403 Forbidden**: Insufficient permissions for action
- **400 Bad Request**: Validation errors (registration, password change)
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

### Error Response Format
```typescript
interface ErrorResponse {
  detail: string;  // Human-readable error message
}
```

## React Context for Authentication

```typescript
interface AuthContextType {
  user: UserProfile | null;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (data: UserUpdate) => Promise<void>;
  loading: boolean;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Check for existing auth on mount
    const token = getAccessToken();
    const savedUser = localStorage.getItem('user');
    
    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);
  
  const login = async (email: string, password: string) => {
    const response = await loginUser(email, password);
    storeAuthTokens(response);
    setUser(response.user);
  };
  
  const logout = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      await authenticatedFetch('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken })
      });
    }
    clearAuthTokens();
    setUser(null);
  };
  
  return (
    <AuthContext.Provider value={{ user, login, register, logout, updateProfile, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
```

## Sample User Credentials for Testing

Use these pre-seeded accounts for testing:

| Role | Email | Password | Description |
|------|--------|----------|-------------|
| Admin | admin@jda-portal.com | AdminPass123! | Full system access |
| Project Manager | pm@jda-portal.com | ProjectManager123! | User management |
| Client | client1@testcompany.com | ClientPass123! | Basic user access |

## Security Considerations

1. **Token Storage**: Consider using HTTP-only cookies for refresh tokens
2. **HTTPS Only**: Ensure all authentication happens over HTTPS in production
3. **Token Expiration**: Access tokens expire in 15 minutes, refresh tokens in 7 days
4. **Input Validation**: All user input is validated on backend
5. **Password Requirements**: Enforce strong password policy
6. **Rate Limiting**: Consider implementing rate limiting for login attempts

## Development Testing

1. Start the backend server: `docker-compose up`
2. API documentation available at: `http://localhost:8000/docs`
3. Health check: `GET http://localhost:8000/health`
4. Test registration/login flows using the sample credentials above

The authentication system is production-ready and fully integrated with comprehensive logging, error handling, and security features. 