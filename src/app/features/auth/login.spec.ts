import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { afterEach, describe, expect, it } from 'vitest';
import { AuthService } from '../../core/services/auth/auth';
import { Login } from './login';

describe('Login', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('actualiza los errores al corregir un campo aunque el formulario siga inválido', () => {
    TestBed.configureTestingModule({
      imports: [Login],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({}) } },
        },
        {
          provide: AuthService,
          useValue: {
            authenticating: signal(false),
            isLockedOut: signal(false),
            lockRemainingSeconds: signal(0),
          },
        },
      ],
    });
    const fixture = TestBed.createComponent(Login);
    fixture.detectChanges();
    const element: HTMLElement = fixture.nativeElement;
    const form = element.querySelector('form')!;
    const email = element.querySelector<HTMLInputElement>('#loginEmail')!;
    const password = element.querySelector<HTMLInputElement>('#loginPassword')!;
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
    expect(element.querySelector('#loginEmailError')?.textContent).toContain('Ingresa tu correo');

    email.value = 'incorrecto';
    email.dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    expect(element.querySelector('#loginEmailError')?.textContent).toContain('formato válido');

    email.value = 'operador@example.com';
    email.dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    expect(element.querySelector('#loginEmailError')).toBeNull();
    expect(element.querySelector('#loginPasswordError')).not.toBeNull();

    password.value = '123';
    password.dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    expect(element.querySelector('#loginPasswordError')?.textContent).toContain('al menos 6');
  });
});
