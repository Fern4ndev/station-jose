/** Elemento del arreglo `details.errors` que devuelve FastAPI en un 422. */
export interface ValidationError {
  readonly loc: readonly (string | number)[];
  readonly msg: string;
  readonly type: string;
  readonly input?: unknown;
  readonly ctx?: Readonly<Record<string, unknown>>;
}

/**
 * Forma nativa de FastAPI (`HTTPValidationError`). El backend actual la envuelve
 * en `ApiErrorEnvelope`, pero se conserva para respuestas sin envoltura.
 */
export interface HTTPValidationError {
  readonly detail?: readonly ValidationError[];
}

export interface ApiErrorBody {
  readonly code: string;
  readonly message: string;
  readonly details?: {
    readonly errors?: readonly ValidationError[];
    readonly [key: string]: unknown;
  };
}

/** Envelope propio de `app/core/error_handlers.py`. */
export interface ApiErrorEnvelope {
  readonly success: false;
  readonly error: ApiErrorBody;
}

/** Error normalizado que entrega `authInterceptor` a los consumidores. */
export interface ApiError {
  readonly status: number;
  readonly code: string;
  readonly message: string;
  readonly details?: Readonly<Record<string, unknown>>;
  readonly validation: readonly ValidationError[];
}

export const isApiError = (value: unknown): value is ApiError =>
  typeof value === 'object' &&
  value !== null &&
  'status' in value &&
  'message' in value &&
  'code' in value;
