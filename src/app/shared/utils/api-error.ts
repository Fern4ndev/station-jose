import { isApiError } from '../../core/models/error';

export const OFFLINE_MESSAGE =
  'Sin conexión con el servidor. Revisa tu red e inténtalo de nuevo.';

const DEFAULT_FALLBACK = 'No se pudo completar la operación. Inténtalo de nuevo.';

/** Etiquetas legibles para los campos que devuelve FastAPI en `loc`. */
const FIELD_LABELS: Readonly<Record<string, string>> = {
  email: 'correo electrónico',
  password: 'contraseña',
  current_password: 'contraseña actual',
  new_password: 'nueva contraseña',
  confirm_password: 'confirmación de contraseña',
  first_name: 'nombres',
  last_name: 'apellidos',
  dni: 'DNI',
  ruc: 'RUC',
  phone: 'teléfono',
  role: 'rol',
  branch_id: 'sede',
  fuel_type_id: 'combustible',
  gallons: 'galones',
  unit_price: 'precio unitario',
  issue_date: 'fecha de emisión',
  page: 'página',
  page_size: 'tamaño de página',
};

/** Traduce los `type` de Pydantic más frecuentes. */
const TYPE_MESSAGES: Readonly<Record<string, string>> = {
  missing: 'es obligatorio',
  string_too_short: 'es demasiado corto',
  string_too_long: 'es demasiado largo',
  string_type: 'debe ser texto',
  int_type: 'debe ser un número entero',
  float_type: 'debe ser un número',
  decimal_parsing: 'debe ser un número válido',
  greater_than: 'debe ser mayor que el mínimo permitido',
  greater_than_equal: 'debe ser mayor o igual al mínimo permitido',
  less_than: 'debe ser menor que el máximo permitido',
  less_than_equal: 'debe ser menor o igual al máximo permitido',
  date_from_datetime_parsing: 'no tiene una fecha válida',
  datetime_from_date_parsing: 'no tiene una fecha válida',
  bool_type: 'debe ser verdadero o falso',
  value_error: 'tiene un valor inválido',
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const asText = (value: unknown): string => (typeof value === 'string' ? value.trim() : '');

interface IssueLike {
  readonly loc?: readonly (string | number)[];
  readonly msg?: unknown;
  readonly message?: unknown;
  readonly type?: unknown;
}

const isIssue = (value: unknown): value is IssueLike => isRecord(value);

const fieldLabel = (loc: readonly (string | number)[] | undefined): string => {
  if (!loc?.length) {
    return '';
  }
  const named = [...loc]
    .reverse()
    .find(
      (part) =>
        typeof part === 'string' && part !== 'body' && part !== 'query' && part !== 'path',
    );
  if (typeof named !== 'string') {
    return '';
  }
  return FIELD_LABELS[named] ?? named.replace(/_/g, ' ');
};

const describeIssue = (issue: IssueLike): string => {
  const type = asText(issue.type);
  const raw = asText(issue.msg) || asText(issue.message);
  // `value_error` trae el mensaje de negocio en inglés o español: se respeta.
  const text = type === 'value_error' ? raw : (TYPE_MESSAGES[type] ?? raw);
  const label = fieldLabel(issue.loc);
  if (!text) {
    return '';
  }
  return label ? `${label}: ${text}` : text;
};

const describeValidation = (issues: readonly unknown[]): string =>
  issues
    .filter(isIssue)
    .map(describeIssue)
    .filter((message) => message.length > 0)
    .slice(0, 3)
    .join(' · ');

const fromBody = (body: Record<string, unknown>): string => {
  const detail = body['detail'];
  if (Array.isArray(detail)) {
    const described = describeValidation(detail);
    if (described) {
      return described;
    }
  }
  const detailText = asText(detail);
  if (detailText) {
    return detailText;
  }
  const envelope = body['error'];
  if (isRecord(envelope)) {
    const envelopeMessage = asText(envelope['message']);
    if (envelopeMessage) {
      return envelopeMessage;
    }
  }
  return asText(body['message']) || asText(envelope);
};

/**
 * Convierte cualquier fallo de transporte en un mensaje listo para
 * `MessageService`. Acepta el `ApiError` normalizado por el interceptor, un
 * `HttpErrorResponse` crudo o un cuerpo de FastAPI suelto.
 */
export function extractApiError(error: unknown, fallback: string = DEFAULT_FALLBACK): string {
  if (isApiError(error)) {
    if (error.status === 0) {
      return OFFLINE_MESSAGE;
    }
    if (error.validation.length > 0) {
      const described = describeValidation(error.validation);
      if (described) {
        return described;
      }
    }
    return asText(error.message) || fallback;
  }

  if (!isRecord(error)) {
    return fallback;
  }

  const status = typeof error['status'] === 'number' ? error['status'] : null;
  if (status === 0) {
    return OFFLINE_MESSAGE;
  }

  const raw = error['error'];
  const body = isRecord(raw) ? raw : error;
  return fromBody(body) || fallback;
}
