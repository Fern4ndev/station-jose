import { TestBed } from '@angular/core/testing';
import { afterEach, describe, expect, it } from 'vitest';
import type { PurchaseOrderOcrPreview } from '../../../../core/services/ocr-api';
import { OrderFormDialog } from './order-form-dialog';

describe('Revisión de la orden importada', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('prellena los campos y prioriza la unidad ejecutora como institución', () => {
    TestBed.overrideComponent(OrderFormDialog, { set: { imports: [], template: '' } });
    const fixture = TestBed.createComponent(OrderFormDialog);
    fixture.componentRef.setInput('branches', [{ id: 'branch-1', name: 'San José', code: 'SJ', is_active: true }]);
    fixture.componentRef.setInput('fuels', [{ id: 'fuel-1', name: 'Diésel', code: 'DB5', is_active: true }]);
    const preview: PurchaseOrderOcrPreview = {
      filename: 'orden.pdf', content_type: 'application/pdf', pages_processed: 3,
      extracted_text: '', unrecognized_fields: [], warnings: [],
      fields: {
        order_number: '0000101', siaf_number: '0000000570', issue_date: '2026-11-20',
        institution_name: 'Entidad genérica', executing_unit: 'MUNICIPALIDAD DE PRUEBA',
        executing_unit_ruc: '20123456789', supplier_name: 'Estación San José',
        lines: [{ fuel_description: 'Diésel B5', authorized_gallons: '100.125', unit_price: '15.5000' }],
      },
    };
    fixture.componentRef.setInput('preview', preview);
    fixture.componentRef.setInput('visible', true);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    expect(component['number']()).toBe('0000101');
    expect(component['siaf']()).toBe('0000000570');
    expect(component['date']()).toBe('2026-11-20');
    expect(component['institutionName']()).toBe('MUNICIPALIDAD DE PRUEBA');
    expect(component['institutionRuc']()).toBe('20123456789');
    expect(component['branch']()).toBe('branch-1');
    expect(component['lines']()).toEqual([{ fuel_type_id: 'fuel-1', gallons: '100.125', unit_price: '15.5000' }]);
    expect(component['dirty']()).toBe(true);

    // Abrir una orden manual después de importar no conserva los datos anteriores.
    fixture.componentRef.setInput('visible', false);
    fixture.detectChanges();
    fixture.componentRef.setInput('preview', null);
    fixture.componentRef.setInput('visible', true);
    fixture.detectChanges();
    expect(component['number']()).toBe('');
    expect(component['institutionName']()).toBe('');
    expect(component['dirty']()).toBe(false);
  });
});
