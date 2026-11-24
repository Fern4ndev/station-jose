import { describe, expect, it } from 'vitest';
import { cleanParams } from './query-params';

describe('cleanParams', () => {
  it('descarta nulos, indefinidos, vacíos y NaN', () => {
    expect(
      cleanParams({
        page: 1,
        q: '   ',
        branch_id: null,
        status: undefined,
        total: Number.NaN,
        date_from: '',
      }),
    ).toEqual({ page: 1 });
  });

  it('recorta cadenas y conserva ceros y false', () => {
    expect(cleanParams({ q: '  vale 12 ', page: 0, only_active: false })).toEqual({
      q: 'vale 12',
      page: 0,
      only_active: false,
    });
  });

  it('elimina arreglos vacíos y conserva los que tienen datos', () => {
    expect(cleanParams({ ids: [], roles: ['ADMIN', ''] })).toEqual({ roles: ['ADMIN'] });
  });

  it('no muta el objeto original y acepta undefined', () => {
    const source = { page: 2, q: '' };
    expect(cleanParams(source)).toEqual({ page: 2 });
    expect(source.q).toBe('');
    expect(cleanParams()).toEqual({});
  });
});
