import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from '../authStore';

describe('authStore', () => {
  beforeEach(() => {
    // Reset store before each test
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.logout();
    });
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useAuthStore());
    
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
  });

  it('should set user and token on login', () => {
    const { result } = renderHook(() => useAuthStore());
    
    const mockUser = {
      id: 'user_123',
      email: 'test@example.com',
      displayName: 'Test User',
    };
    const mockToken = 'mock_jwt_token';

    act(() => {
      result.current.login(mockUser, mockToken);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.token).toBe(mockToken);
  });

  it('should clear user and token on logout', () => {
    const { result } = renderHook(() => useAuthStore());
    
    // First login
    act(() => {
      result.current.login(
        { id: 'user_123', email: 'test@example.com', displayName: 'Test User' },
        'mock_token'
      );
    });

    // Then logout
    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
  });

  it('should update user information', () => {
    const { result } = renderHook(() => useAuthStore());
    
    // Login first
    act(() => {
      result.current.login(
        { id: 'user_123', email: 'test@example.com', displayName: 'Test User' },
        'mock_token'
      );
    });

    // Update user
    const updatedUser = {
      id: 'user_123',
      email: 'test@example.com',
      displayName: 'Updated User',
    };

    act(() => {
      result.current.updateUser(updatedUser);
    });

    expect(result.current.user).toEqual(updatedUser);
    expect(result.current.isAuthenticated).toBe(true);
  });
});

