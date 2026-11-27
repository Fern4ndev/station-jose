import { TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { OcrApi, type PurchaseOrderOcrPreview } from '../../../../core/services/ocr-api';
import { OrderImportDialog } from './order-import-dialog';

function setup() {
  const result = new Subject<PurchaseOrderOcrPreview>();
  const analyze = vi.fn(() => result);
  TestBed.configureTestingModule({ providers: [{ provide: OcrApi, useValue: { analyze } }] });
  TestBed.overrideComponent(OrderImportDialog, { set: { imports: [], template: '' } });
  const fixture = TestBed.createComponent(OrderImportDialog);
  fixture.componentRef.setInput('visible', true);
  fixture.detectChanges();
  const component = fixture.componentInstance;
  const select = (file: File) => {
    const input = document.createElement('input');
    Object.defineProperty(input, 'files', { value: [file] });
    component['onFile']({ target: input } as unknown as Event);
  };
  select(new File(['%PDF'], 'orden.pdf', { type: 'application/pdf' }));
  return { fixture, component, result, analyze, select };
}

describe('Importar PDF de una orden', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('espera la confirmación y evita enviar solicitudes duplicadas', () => {
    const { component, analyze } = setup();
    expect(analyze).not.toHaveBeenCalled();
    component['process']();
    component['process']();
    expect(analyze).toHaveBeenCalledTimes(1);
    expect(component['loading']()).toBe(true);
  });

  it('cancela la lectura al cerrar y descarta respuestas tardías', () => {
    const { component, fixture, result } = setup();
    const imported = vi.fn();
    component.imported.subscribe(imported);
    component['process']();
    fixture.componentRef.setInput('visible', false);
    fixture.detectChanges();
    expect(result.observed).toBe(false);
    expect(component['loading']()).toBe(false);
    expect(imported).not.toHaveBeenCalled();
  });

  it('permite reintentar tras un error y entrega los datos para revisión', () => {
    const { component, result, analyze } = setup();
    component['process']();
    result.error(new Error('Se agotó el tiempo para procesar el PDF.'));
    expect(component['loading']()).toBe(false);
    expect(component['error']()).toContain('tiempo');
    expect(component['file']()?.name).toBe('orden.pdf');
    const retry = new Subject<PurchaseOrderOcrPreview>();
    analyze.mockReturnValueOnce(retry);
    const imported = vi.fn();
    component.imported.subscribe(imported);
    component['process']();
    const preview: PurchaseOrderOcrPreview = {
      filename: 'orden.pdf', content_type: 'application/pdf', pages_processed: 3,
      extracted_text: '', fields: { order_number: '0000101' }, unrecognized_fields: [], warnings: [],
    };
    retry.next(preview);
    retry.complete();
    expect(imported).toHaveBeenCalledExactlyOnceWith(preview);
    expect(component.visible()).toBe(false);
    expect(component['loading']()).toBe(false);
  });

  it('libera el loader si la solicitud termina sin devolver datos', () => {
    const { component, result } = setup();
    component['process']();
    result.complete();
    expect(component['loading']()).toBe(false);
    expect(component['error']()).toContain('No se recibieron datos');
  });

  it('rechaza archivos distintos a PDF y archivos demasiado grandes', () => {
    const { component, analyze, select } = setup();
    select(new File(['texto'], 'orden.txt', { type: 'text/plain' }));
    component['process']();
    expect(component['error']()).toContain('archivo PDF');
    const oversized = new File(['%PDF'], 'grande.pdf');
    Object.defineProperty(oversized, 'size', { value: 10 * 1024 * 1024 + 1 });
    select(oversized);
    component['process']();
    expect(component['error']()).toContain('10 MB');
    expect(analyze).not.toHaveBeenCalled();
  });
});
