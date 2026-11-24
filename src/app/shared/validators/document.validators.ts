import type { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';
import { isReversedRange } from '../utils/date-range';

export type DocumentKind = 'dni' | 'ruc' | 'ce';

/** Formatos aceptados: DNI peruano, RUC y carné de extranjería. */
const DOCUMENT_PATTERNS: Readonly<Record<DocumentKind, RegExp>> = {
  dni: /^\d{8}$/,
  ruc: /^\d{11}$/,
  ce: /^[A-Za-z0-9]{9,12}$/,
};

const MOBILE_PATTERN = /^9\d{8}$/;

const asText = (value: unknown): string =>
  typeof value === 'string' ? value.trim() : '';

const asNumber = (value: unknown): number => {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string') {
    return Number(value.replace(',', '.'));
  }
  return Number.NaN;
};

/**
 * Valida un documento de identidad. Un valor vacío se deja pasar para que
 * `Validators.required` decida si el campo es obligatorio.
 */
export function documentValidator(kind: DocumentKind = 'dni'): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = asText(control.value);
    if (value === '') {
      return null;
    }
    return DOCUMENT_PATTERNS[kind].test(value) ? null : { document: { kind } };
  };
}

/** Celular peruano de 9 dígitos que empieza en 9. */
export function phoneValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = asText(control.value);
    if (value === '') {
      return null;
    }
    return MOBILE_PATTERN.test(value) ? null : { phone: true };
  };
}

/** Monto (galones o importe) mayor o igual a `min`. Acepta coma decimal. */
export function positiveAmountValidator(min = 0.01): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const raw = control.value;
    if (raw === null || raw === undefined || raw === '') {
      return null;
    }
    const amount = asNumber(raw);
    return Number.isFinite(amount) && amount >= min ? null : { amount: { min } };
  };
}

/** Rango de fechas coherente entre dos controles del mismo `FormGroup`. */
export function dateRangeValidator(fromKey = 'dateFrom', toKey = 'dateTo'): ValidatorFn {
  return (group: AbstractControl): ValidationErrors | null => {
    const from = group.get(fromKey)?.value;
    const to = group.get(toKey)?.value;
    return isReversedRange(from, to) ? { dateRange: true } : null;
  };
}

/** La confirmación debe coincidir con la contraseña principal. */
export function passwordMatchValidator(
  passwordKey = 'password',
  confirmKey = 'confirmPassword',
): ValidatorFn {
  return (group: AbstractControl): ValidationErrors | null => {
    const password = group.get(passwordKey)?.value;
    const confirmation = group.get(confirmKey)?.value;
    if (!password && !confirmation) {
      return null;
    }
    return password === confirmation ? null : { passwordMismatch: true };
  };
}
