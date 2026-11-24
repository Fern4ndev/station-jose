/** Combustible tal como lo devuelven las mutaciones del catálogo. */
export interface FuelTypeOut {
  readonly id: string;
  readonly code: string;
  readonly name: string;
  readonly is_active: boolean;
}

/** Combustible con métricas para la tabla administrativa. */
export interface FuelTypeManageOut extends FuelTypeOut {
  readonly created_at: string;
  readonly orders_count: number;
}

export interface FuelTypeCreate {
  readonly code: string;
  readonly name: string;
  readonly is_active?: boolean;
}

/** El código no se edita: sólo se actualiza el nombre. */
export interface FuelTypeUpdate {
  readonly name: string;
}

export interface FuelTypeStatusUpdate {
  readonly is_active: boolean;
}

export type FuelTypeListQuery = {
  readonly q?: string;
  readonly include_inactive?: boolean;
};
