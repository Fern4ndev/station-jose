import { describe, expect, it } from 'vitest';
import type { ApiError } from '../../core/models/error';
import { OFFLINE_MESSAGE, extractApiError } from './api-error';

const normalized = (partial: Partial<ApiError>): ApiError => ({
  status: 400,
  code: 'bad_request',
  message: '',
  validation: [],
  ...partial,
});

describe('extractApiError', () => {
  it('traduce el arreglo de validación de FastAPI', () => {
    const message = extractApiError({
      status: 422,
      error: {
        detail: [
          { loc: ['body', 'email'], msg: 'value is not a valid email address', type: 'value_error' },
          { loc: ['body', 'password'], msg: 'Field required', type: 'missing' },
        ],
      },
    });

    expect(message).toBe(
      'correo electrónico: value is not a valid email address · contraseña: es obligatorio',
    );
  });

  it('usa el detail de texto en errores de negocio', () => {
    const message = extractApiError({
      status: 409,
      error: { detail: 'Ya existe un vale con ese número.' },
    });

    expect(message).toBe('Ya existe un vale con ese número.');
  });

  it('lee el envelope propio del backend', () => {
    const message = extractApiError({
      status: 403,
      error: { success: false, error: { code: 'forbidden', message: 'Sin permisos para esta sección.' } },
    });

    expect(message).toBe('Sin permisos para esta sección.');
  });

  it('acepta el ApiError que normaliza el interceptor', () => {
    expect(extractApiError(normalized({ message: 'Sesión vencida.' }))).toBe('Sesión vencida.');
    expect(
      extractApiError(
        normalized({
          status: 422,
          validation: [{ loc: ['body', 'dni'], msg: 'String should have at least 8 characters', type: 'string_too_short' }],
        }),
      ),
    ).toBe('DNI: es demasiado corto');
  });

  it('informa la falta de conexión con status 0', () => {
    expect(extractApiError({ status: 0, message: 'Unknown Error' })).toBe(OFFLINE_MESSAGE);
    expect(extractApiError(normalized({ status: 0 }))).toBe(OFFLINE_MESSAGE);
  });

  it('cae en el mensaje por defecto', () => {
    expect(extractApiError(null)).toBe(
      'No se pudo completar la operación. Inténtalo de nuevo.',
    );
    expect(extractApiError({ status: 500, error: {} }, 'Fallo del servidor.')).toBe(
      'Fallo del servidor.',
    );
  });
});
