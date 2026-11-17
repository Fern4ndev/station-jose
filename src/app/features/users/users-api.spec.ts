import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { API_BASE_URL } from '../../core/api/api-url';
import { UsersApi } from './users-api';

describe('UsersApi', () => {
  it('sends role and status changes using the backend contract', () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: '/api/v1' }] });
    const api = TestBed.inject(UsersApi);
    const http = TestBed.inject(HttpTestingController);
    const user = { id: 'u1', first_name: 'Ana', last_name: 'Pérez', dni: '12345678', email: 'ana@example.com', role: 'ATTENDANT', branch: null, is_active: true };
    api.setRole('u1', 'ATTENDANT', 'branch-1').subscribe();
    const role = http.expectOne('/api/v1/users/u1/role');
    expect(role.request.method).toBe('PATCH');
    expect(role.request.body).toEqual({ role: 'ATTENDANT', branch_id: 'branch-1' });
    role.flush(user);
    api.setStatus('u1', false).subscribe();
    const status = http.expectOne('/api/v1/users/u1/status');
    expect(status.request.body).toEqual({ is_active: false });
    status.flush({ ...user, is_active: false });
    http.verify();
  });
});
