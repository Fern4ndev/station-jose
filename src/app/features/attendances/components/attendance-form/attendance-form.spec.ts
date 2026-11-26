import { TestBed } from '@angular/core/testing';
import { afterEach, describe, expect, it } from 'vitest';
import type { AttendanceRequest } from '../../attendances-data';
import type { DispatchOrder } from '../../operations-store';
import { AttendanceForm } from './attendance-form';

describe('Sede automática del grifero', () => {
  afterEach(() => TestBed.resetTestingModule());

  it.each(['San José', 'Santa Marta'])('registra en %s sin seleccionar sede y conserva varios combustibles', async (branch) => {
    const orders: DispatchOrder[] = ['Diésel', 'Gasolina'].map((fuel, index) => ({
      id: `line-${index}`, apiId: 'order-1', orderNumber: 'OC-001', institutionRuc: '20123456789',
      entity: 'Municipalidad', date: '2026-11-23', branch, fuel, note: '', total: 100, used: 0,
    }));
    const fixture = TestBed.createComponent(AttendanceForm);
    fixture.componentRef.setInput('orders', orders);
    fixture.componentRef.setInput('vouchers', []);
    fixture.componentRef.setInput('branch', branch);
    fixture.componentRef.setInput('branchLocked', true);
    fixture.detectChanges();
    const form = fixture.componentInstance;
    form['institutionRuc'].set('20123456789');
    fixture.detectChanges();
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('#attendanceBranch')).toBeNull();
    expect(fixture.nativeElement.querySelectorAll('form > section')).toHaveLength(3);

    form['voucherId'].set('VALE-001');
    form['branchValue'].set(branch === 'San José' ? 'Santa Marta' : 'San José');
    for (const order of orders) {
      form['setLineAuthorized'](order.id, { target: { value: '10' } } as unknown as Event);
      form['setLineGallons'](order.id, { target: { value: '1,250' } } as unknown as Event);
    }
    const emitted: AttendanceRequest[] = [];
    form.register.subscribe((request) => emitted.push(request));
    form['onSubmit'](new Event('submit', { cancelable: true }));

    expect(form['error']()).toBe('');
    expect(emitted).toHaveLength(1);
    expect(emitted[0].branch).toBe(branch);
    expect(emitted[0].lines).toHaveLength(2);
    expect(emitted[0].lines.map((line) => line.gallons)).toEqual(['1.250', '1.250']);
    expect(form.totalGallons()).toBe(2.5);
  });
});
