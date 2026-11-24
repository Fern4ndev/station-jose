/** Alineación de una celda en `data-table`. */
export type TableAlign = 'left' | 'center' | 'right';

/**
 * Definición declarativa de una columna de `app-data-table`.
 * `key` es el nombre del campo en la fila y la clave que usa
 * `*appDataTableCell` para proyectar una celda personalizada.
 */
export interface TableColumn {
  readonly key: string;
  readonly header: string;
  readonly align?: TableAlign;
  readonly width?: string;
}

/** Fila genérica que la tabla sabe leer sin conocer el dominio. */
export type TableRow = Readonly<Record<string, unknown>>;
