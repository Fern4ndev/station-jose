import { FormControl, FormGroup } from '@angular/forms';
import { describe, expect, it } from 'vitest';
import {
  dateRangeValidator,
  documentValidator,
  passwordMatchValidator,
  phoneValidator,
  positiveAmountValidator,
} from './document.validators';

describe('documentValidator', () => {
  it('acepta un DNI de 8 dígitos y rechaza lo demás', () => {
    const validate = documentValidator('dni');
    expect(validate(new FormControl('45120398'))).toBeNull();
    expect(validate(new FormControl('4512039'))).toEqual({ document: { kind: 'dni' } });
    expect(validate(new FormControl('4512039A'))).toEqual({ document: { kind: 'dni' } });
  });

  it('valida RUC y carné de extranjería', () => {
    expect(documentValidator('ruc')(new FormControl('20123456789'))).toBeNull();
    expect(documentValidator('ruc')(new FormControl('201234567'))).toEqual({
      document: { kind: 'ruc' },
    });
    expect(documentValidator('ce')(new FormControl('X12345678'))).toBeNull();
    expect(documentValidator('ce')(new FormControl('X1234567'))).toEqual({
      document: { kind: 'ce' },
    });
  });

  it('deja pasar el vacío para que actúe Validators.required', () => {
    expect(documentValidator('dni')(new FormControl('  '))).toBeNull();
  });
});

describe('phoneValidator', () => {
  it('exige un celular de 9 dígitos que empiece en 9', () => {
    const validate = phoneValidator();
    expect(validate(new FormControl('987654321'))).toBeNull();
    expect(validate(new FormControl('887654321'))).toEqual({ phone: true });
    expect(validate(new FormControl('98765432'))).toEqual({ phone: true });
  });
});

describe('positiveAmountValidator', () => {
  it('rechaza cero, negativos y texto', () => {
    const validate = positiveAmountValidator();
    expect(validate(new FormControl('12.5'))).toBeNull();
    expect(validate(new FormControl('12,5'))).toBeNull();
    expect(validate(new FormControl(0))).toEqual({ amount: { min: 0.01 } });
    expect(validate(new FormControl('-3'))).toEqual({ amount: { min: 0.01 } });
    expect(validate(new FormControl('abc'))).toEqual({ amount: { min: 0.01 } });
    expect(validate(new FormControl(''))).toBeNull();
  });
});

describe('dateRangeValidator', () => {
  it('marca el grupo cuando el rango está invertido', () => {
    const validate = dateRangeValidator();
    const group = new FormGroup({
      dateFrom: new FormControl('2026-02-01'),
      dateTo: new FormControl('2026-01-01'),
    });
    expect(validate(group)).toEqual({ dateRange: true });

    group.patchValue({ dateFrom: '2026-01-01', dateTo: '2026-02-01' });
    expect(validate(group)).toBeNull();
  });
});

describe('passwordMatchValidator', () => {
  it('detecta contraseñas distintas', () => {
    const validate = passwordMatchValidator();
    const group = new FormGroup({
      password: new FormControl('secreta123'),
      confirmPassword: new FormControl('secreta124'),
    });
    expect(validate(group)).toEqual({ passwordMismatch: true });

    group.patchValue({ confirmPassword: 'secreta123' });
    expect(validate(group)).toBeNull();
  });
});
