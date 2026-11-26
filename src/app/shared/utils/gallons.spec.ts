import { gallonsBalanceMilli, gallonsToMilli, parseGallonsInput } from './gallons';

describe('gallons', () => {
  it('interpreta coma y punto con hasta 3 decimales', () => {
    expect(parseGallonsInput('5,250')).toEqual({ milli: 5250, normalized: '5.250' });
    expect(parseGallonsInput('0.001')).toEqual({ milli: 1, normalized: '0.001' });
    expect(parseGallonsInput(' 12 ')).toEqual({ milli: 12000, normalized: '12.000' });
  });

  it('rechaza más de 3 decimales y formatos inválidos', () => {
    expect(parseGallonsInput('1.2345')).toBeNull();
    expect(parseGallonsInput('1,2,3')).toBeNull();
    expect(parseGallonsInput('abc')).toBeNull();
    expect(parseGallonsInput('-1')).toBeNull();
  });

  it('convierte cantidades del servidor sin residuos flotantes', () => {
    expect(gallonsToMilli('99.700')).toBe(99700);
    expect(gallonsToMilli(0.1 + 0.2)).toBe(300);
  });

  it('compara saldos en milésimas exactas', () => {
    const available = gallonsBalanceMilli('100.000', '0.300');
    expect(available).toBe(99700);
    expect(parseGallonsInput('99,7')!.milli).toBeLessThanOrEqual(available);
    expect(parseGallonsInput('99,701')!.milli).toBeGreaterThan(available);
  });

  it('nunca devuelve saldos negativos', () => {
    expect(gallonsBalanceMilli('10.000', '10.500')).toBe(0);
  });
});
