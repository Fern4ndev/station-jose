import type { ApiError, ApiErrorEnvelope, ValidationError } from '../models/error.model';

const GENERIC_MESSAGE = 'No se pudo completar la solicitud.';

/**
 * Normaliza cualquier fallo de `HttpClient` al contrato `{ success, error }`
 * del backend y a mensajes listos para mostrar al usuario.
 */
export const toApiError = (error: unknown): ApiError => {
  const httpError = error as { status?: unknown; error?: unknown; message?: unknown };
  const status = typeof httpError.status === 'number' ? httpError.status : 0;
  const envelope = asEnvelope(httpError.error);
  const validation = envelope?.error.details?.errors ?? legacyValidation(httpError.error);

  if (status === 0) {
    return {
      status,
      code: 'NETWORK_ERROR',
      message: 'No se pudo conectar con el servidor. Verifica tu conexión e inténtalo de nuevo.',
      validation: [],
    };
  }

  if (status >= 500) {
    return {
      status,
      code: envelope?.error.code ?? 'INTERNAL_SERVER_ERROR',
      message: 'Ocurrió un error en el servidor. Inténtalo de nuevo en unos minutos.',
      validation: [],
    };
  }

  if (status === 403) {
    return {
      status,
      code: envelope?.error.code ?? 'FORBIDDEN',
      message: envelope?.error.message ?? 'No tienes permisos para realizar esta acción.',
      validation: [],
    };
  }

  if (status === 422) {
    return {
      status,
      code: envelope?.error.code ?? 'VALIDATION_ERROR',
      message: validation.length
        ? validationMessage(validation)
        : (envelope?.error.message ?? 'Revisa los datos ingresados e inténtalo de nuevo.'),
      details: envelope?.error.details,
      validation,
    };
  }

  return {
    status,
    code: envelope?.error.code ?? 'HTTP_ERROR',
    message: envelope?.error.message ?? fallbackMessage(httpError.message),
    details: envelope?.error.details,
    validation,
  };
};

const fallbackMessage = (message: unknown): string =>
  typeof message === 'string' && message.trim() ? message : GENERIC_MESSAGE;

const validationMessage = (errors: readonly ValidationError[]): string => {
  const [first] = errors;
  if (!first) {
    return GENERIC_MESSAGE;
  }
  const field = first.loc.filter((part) => part !== 'body' && part !== 'query').join('.');
  const head = field ? `${field}: ${first.msg}` : first.msg;
  return errors.length > 1 ? `${head} (${errors.length - 1} error(es) más)` : head;
};

const asEnvelope = (body: unknown): ApiErrorEnvelope | null =>
  typeof body === 'object' &&
  body !== null &&
  'error' in body &&
  typeof (body as { error?: unknown }).error === 'object' &&
  (body as { error?: unknown }).error !== null
    ? (body as ApiErrorEnvelope)
    : null;

/** Compatibilidad con el `HTTPValidationError` nativo de FastAPI. */
const legacyValidation = (body: unknown): readonly ValidationError[] => {
  if (typeof body !== 'object' || body === null || !('detail' in body)) {
    return [];
  }
  const detail = (body as { detail?: unknown }).detail;
  return Array.isArray(detail) ? (detail as readonly ValidationError[]) : [];
};
