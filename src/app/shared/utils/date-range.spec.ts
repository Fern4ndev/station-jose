import { describe, expect, it } from 'vitest';
import { isReversedRange, toIsoDate, toIsoRange, todayIso } from './date-range';

describe('toIsoDate', () => {
  it('formatea un Date en fecha local', () => {
    expect(toIsoDate(new Date(2026, 10, 5))).toBe('2026-11-05');
  });

  it('recorta un ISO completo', () => {
    expect(toIsoDate('2026-11-05T18:30:00.000Z')).toBe('2026-11-05');
  });

  it('interpreta texto libre y devuelve null si no es fecha', () => {
    expect(toIsoDate('2026/11/05')).toBe('2026-11-05');
    expect(toIsoDate('no es fecha')).toBeNull();
    expect(toIsoDate('')).toBeNull();
    expect(toIsoDate(null)).toBeNull();
    expect(toIsoDate(new Date('invalid'))).toBeNull();
  });
});

describe('toIsoRange', () => {
  it('devuelve ambos extremos normalizados', () => {
    expect(toIsoRange('2026-01-01', new Date(2026, 0, 31))).toEqual({
      date_from: '2026-01-01',
      date_to: '2026-01-31',
    });
  });

  it('deja null cuando falta un extremo', () => {
    expect(toIsoRange(undefined, '2026-01-31')).toEqual({ date_from: null, date_to: '2026-01-31' });
  });
});

describe('isReversedRange', () => {
  it('detecta un rango invertido', () => {
    expect(isReversedRange('2026-02-01', '2026-01-01')).toBe(true);
    expect(isReversedRange('2026-01-01', '2026-02-01')).toBe(false);
    expect(isReversedRange(null, '2026-02-01')).toBe(false);
  });
});

describe('todayIso', () => {
  it('usa la fecha inyectada', () => {
    expect(todayIso(new Date(2026, 6, 9))).toBe('2026-07-09');
  });
});
