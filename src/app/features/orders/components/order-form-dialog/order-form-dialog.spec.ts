import { TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { OcrApi, type PurchaseOrderOcrPreview } from '../../../../core/services/ocr-api';
import { OrderFormDialog } from './order-form-dialog';

function setup() {
  const result = new Subject<PurchaseOrderOcrPreview>();
  TestBed.configureTestingModule({
    providers: [{ provide: OcrApi, useValue: { analyze: vi.fn(() => result) } }],
  });
  TestBed.overrideComponent(OrderFormDialog, { set: { imports: [], template: '' } });
  const fixture = TestBed.createComponent(OrderFormDialog);
  fixture.componentRef.setInput('visible', true);
  fixture.detectChanges();
  const component = fixture.componentInstance;
  const input = document.createElement('input');
  Object.defineProperty(input, 'files', { value: [new File(['%PDF'], 'orden.pdf')] });
  component['onPdf']({ target: input } as unknown as Event);
  return { fixture, component, result };
}

describe('OrderFormDialog OCR', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('libera el estado de procesamiento si la solicitud termina sin datos', () => {
    const { component, result } = setup();
    expect(component['loadingOcr']()).toBe(true);
    result.complete();
    expect(component['loadingOcr']()).toBe(false);
    expect(component['pdfLabel']()).not.toContain('Procesando');
  });

  it('cancela el OCR al cerrar el formulario', () => {
    const { fixture, component, result } = setup();
    fixture.componentRef.setInput('visible', false);
    fixture.detectChanges();
    expect(result.observed).toBe(false);
    expect(component['loadingOcr']()).toBe(false);
  });

  it('muestra el error y permite volver a subir el PDF', () => {
    const { component, result } = setup();
    result.error(new Error('Se agotó el tiempo para procesar el PDF.'));
    expect(component['loadingOcr']()).toBe(false);
    expect(component['pdfLabel']()).not.toContain('Procesando');
    expect(component['error']()).toContain('tiempo');
  });

  it('usa la unidad ejecutora como nombre de la institución', () => {
    const { component, result } = setup();
    result.next({
      filename: 'orden.pdf', content_type: 'application/pdf', pages_processed: 2,
      extracted_text: '', unrecognized_fields: [], warnings: [],
      fields: {
        order_number: '0000101', siaf_number: '0000000570',
        institution_name: 'Entidad genérica', executing_unit: 'MUNICIPALIDAD DE PRUEBA',
        executing_unit_ruc: '20123456789',
      },
    });
    result.complete();
    expect(component['number']()).toBe('0000101');
    expect(component['siaf']()).toBe('0000000570');
    expect(component['institutionName']()).toBe('MUNICIPALIDAD DE PRUEBA');
    expect(component['institutionRuc']()).toBe('20123456789');
    expect(component['loadingOcr']()).toBe(false);
  });
});
