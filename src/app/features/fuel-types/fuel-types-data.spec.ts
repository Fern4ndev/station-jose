import { describe, expect, it } from 'vitest';
import {
  filterFuelTypes,
  toFuelTypeRow,
  type FuelTypeRow,
} from './fuel-types-data';

const rows: readonly FuelTypeRow[] = [
  { id: '1', name: 'Diésel S50', active: true },
  { id: '2', name: 'Gasohol Regular', active: false },
];

describe('fuel type data', () => {
  it('maps the management response to a table row', () => {
    expect(
      toFuelTypeRow({
        id: '3',
        code: 'GASOHOL-PREMIUM',
        name: 'Gasohol Premium',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
        orders_count: 2,
      }),
    ).toEqual({
      id: '3',
      name: 'Gasohol Premium',
      active: true,
    });
  });

  it('filters by status and searches by name', () => {
    expect(filterFuelTypes(rows, '', 'active')).toEqual([rows[0]]);
    expect(filterFuelTypes(rows, '', 'inactive')).toEqual([rows[1]]);
    expect(filterFuelTypes(rows, 'gasohol', 'all')).toEqual([rows[1]]);
    expect(filterFuelTypes(rows, 's50', 'active')).toEqual([rows[0]]);
    expect(filterFuelTypes(rows, 'inexistente', 'all')).toEqual([]);
  });
});
