import { describe, expect, it } from 'vitest';
import { isApiRequest } from './api-request';

describe('API request boundary', () => {
  it('accepts API paths and rejects other origins and sibling paths', () => {
    expect(isApiRequest('/api/v1/auth/me', '/api/v1')).toBe(true);
    expect(isApiRequest('/api/v1', '/api/v1/')).toBe(true);
    expect(isApiRequest('/api/v10/auth/me', '/api/v1')).toBe(false);
    expect(isApiRequest('https://other.example/api/v1/auth/me', '/api/v1')).toBe(false);
  });
});
