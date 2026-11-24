import type { FuelTypeManageOut } from '../../core/models/fuel-type';

export type FuelStatusFilter = 'all' | 'active' | 'inactive';

export const FUEL_STATUS_FILTERS = [
  { value: 'all', label: 'Todos' },
  { value: 'active', label: 'Activos' },
  { value: 'inactive', label: 'Inactivos' },
] as const satisfies readonly { value: FuelStatusFilter; label: string }[];

export interface FuelTypeRow {
  readonly id: string;
  readonly name: string;
  readonly active: boolean;
}

export interface FuelTypeDraft {
  readonly name: string;
}

export const toFuelTypeRow = (fuel: FuelTypeManageOut): FuelTypeRow => ({
  id: fuel.id,
  name: fuel.name,
  active: fuel.is_active,
});

export const filterFuelTypes = (
  rows: readonly FuelTypeRow[],
  query: string,
  status: FuelStatusFilter,
): readonly FuelTypeRow[] => {
  const term = query.trim().toLowerCase();
  return rows.filter((row) => {
    const matchesStatus =
      status === 'all' || (status === 'active' ? row.active : !row.active);
    const matchesQuery = row.name.toLowerCase().includes(term);
    return matchesStatus && matchesQuery;
  });
};
