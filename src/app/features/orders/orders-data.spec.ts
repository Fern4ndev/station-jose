import { describe, expect, it } from 'vitest';
import type { PurchaseOrderDetail } from '../../core/models/purchase-order';
import { toOrderRows } from './orders-data';

const source: PurchaseOrderDetail = {
  id: 'order-1',
  order_number: 'OC-100',
  siaf_number: 'SIAF-100',
  issue_date: '2026-11-25',
  institution_name: 'Unidad ejecutora',
  supplier_name: 'San José',
  supplier_details: 'Entregar antes del mediodía',
  executing_unit: 'Unidad ejecutora',
  executing_unit_ruc: '20123456789',
  branch: { id: 'branch-1', code: 'SJ', name: 'San José', is_active: true },
  deleted_at: null,
  status: 'AVAILABLE',
  items: [
    {
      id: 'line-1',
      fuel_type: { id: 'fuel-1', code: 'DB5', name: 'Diésel B5', is_active: true },
      authorized_gallons: '100.000',
      attended_gallons: '20.000',
      available_gallons: '80.000',
      status: 'AVAILABLE',
      unit_price: '14.5000',
      total_amount: '1450.00',
    },
    {
      id: 'line-2',
      fuel_type: { id: 'fuel-2', code: 'G90', name: 'Gasohol 90', is_active: true },
      authorized_gallons: '50.000',
      attended_gallons: '5.000',
      available_gallons: '45.000',
      status: 'AVAILABLE',
      unit_price: '15.0000',
      total_amount: '750.00',
    },
  ],
};

describe('toOrderRows', () => {
  it('representa una OC con varios combustibles en una sola fila y conserva la nota', () => {
    const rows = toOrderRows(source);

    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      id: 'OC-100',
      fuel: 'Diésel B5, Gasohol 90',
      total: 150,
      used: 25,
      note: 'Entregar antes del mediodía',
    });
  });
});
