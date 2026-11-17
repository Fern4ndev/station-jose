import { describe, expect, it } from 'vitest';
import { homePathForPermissions, homePathForRole, mapLoginResponse, type LoginResponseDto } from '../../models/auth.models';

describe('authentication models', () => {
  it('maps the login response to the frontend model', () => {
    const response: LoginResponseDto = {
      access_token: 'token',
      token_type: 'bearer',
      expires_in: 3_600,
      user: {
        id: 'user-1',
        first_name: 'Ana',
        last_name: 'Pérez',
        dni: '12345678',
        email: 'ana@example.com',
        role: 'ATTENDANT',
        branch: { id: 'branch-1', code: 'SJ-01', name: 'San José' },
        is_active: true,
      },
      permissions: ['sales:create'],
    };

    expect(mapLoginResponse(response)).toEqual({
      accessToken: 'token',
      expiresIn: 3_600,
      user: {
        id: 'user-1',
        firstName: 'Ana',
        lastName: 'Pérez',
        dni: '12345678',
        email: 'ana@example.com',
        role: 'ATTENDANT',
        branch: { id: 'branch-1', code: 'SJ-01', name: 'San José' },
        isActive: true,
      },
      permissions: ['sales:create'],
    });
  });

  it('returns the role-specific home route', () => {
    expect(homePathForRole('ATTENDANT')).toBe('/app/attendant/workspace');
    expect(homePathForRole('ADMIN')).toBe('/app/dashboard');
  });

  it('selects a home that matches effective permissions', () => {
    expect(homePathForPermissions(['reports.read', 'attendances.create'])).toBe('/app/dashboard');
    expect(homePathForPermissions(['attendances.create'])).toBe('/app/attendant/workspace');
    expect(homePathForPermissions([])).toBe('/access-denied');
  });
});
