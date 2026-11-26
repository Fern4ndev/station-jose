import { describe, expect, it } from 'vitest';
import type { AttendanceReportRow } from '../../core/services/reports-api';
import { buildReportBuckets, defaultReportRange, filterReportAttendances, type ReportSelection } from './reports-data';

const selection: ReportSelection = {
  kind: 'attendances', view: 'day', from: '2026-11-23', to: '2026-11-27',
  hourFrom: 0, hourTo: 23, branch: 'Todas las sedes',
};

export function attendanceAt(attended_at: string, branch_name = 'San José', attended_gallons = '10'): AttendanceReportRow {
  return { attended_at, branch_name, attended_gallons, attendance_id: attended_at,
    voucher_id: 'voucher', voucher_number: 'V-001', order_id: 'order', order_number: 'OC-001',
    performed_by_user_id: 'user', performer_name: 'Ana Pérez', fuel_type_code: 'DB5',
    fuel_type_name: 'Diésel', unit_price: '15', attended_amount: '150' };
}

describe('Report chart distribution', () => {
  it('keeps all 24 hours and groups using Lima time', () => {
    const buckets = buildReportBuckets([
      attendanceAt('2026-11-24T02:30:00Z'),
      attendanceAt('2026-11-24T14:00:00Z', 'Santa Marta', '5'),
    ], selection);
    expect(buckets).toHaveLength(24);
    expect(buckets[0].label).toBe('00');
    expect(buckets[23].label).toBe('23');
    expect(buckets[0].detail).toBe('00:00 – 00:59');
    expect(buckets[21].sanJose).toBe(10);
    expect(buckets[9].santaMarta).toBe(5);
    expect(buckets[2].sanJose).toBe(0);
  });

  it('shows Monday to Friday, including empty days, and excludes weekends', () => {
    const buckets = buildReportBuckets([
      attendanceAt('2026-11-23T15:00:00Z'),
      attendanceAt('2026-11-28T15:00:00Z', 'Santa Marta', '99'),
    ], { ...selection, view: 'week', to: '2026-11-29' });
    expect(buckets.map((bucket) => bucket.label)).toEqual(['lun', 'mar', 'mié', 'jue', 'vie']);
    expect(buckets[0].sanJose).toBe(10);
    expect(buckets.reduce((sum, bucket) => sum + bucket.santaMarta, 0)).toBe(0);
  });

  it('fills the six partial calendar weeks of November 2026', () => {
    const buckets = buildReportBuckets([
      attendanceAt('2026-11-01T15:00:00Z'),
      attendanceAt('2026-11-30T15:00:00Z', 'Santa Marta', '7'),
    ], { ...selection, view: 'month', from: '2026-11-01', to: '2026-11-30' });
    expect(buckets).toHaveLength(6);
    expect(buckets[0].sanJose).toBe(10);
    expect(buckets[5].santaMarta).toBe(7);
    expect(buckets[5].detail).toContain('30');
  });

  it('groups a January date into the calendar week beginning in December', () => {
    const buckets = buildReportBuckets([attendanceAt('2026-01-01T15:00:00Z')],
      { ...selection, view: 'month', from: '2026-01-01', to: '2026-01-31' });
    expect(buckets[0].sanJose).toBe(10);
    expect(buckets[0].detail).toContain('1');
  });

  it('keeps all 12 months when a full year is selected', () => {
    const buckets = buildReportBuckets([attendanceAt('2027-01-01T02:00:00Z')],
      { ...selection, view: 'year', from: '2026-01-01', to: '2026-12-31' });
    expect(buckets).toHaveLength(12);
    expect(buckets.slice(0, 3).map((bucket) => bucket.label)).toEqual(['ene', 'feb', 'mar']);
    expect(buckets[11].sanJose).toBe(10);
    expect(buckets[0].sanJose).toBe(0);
  });

  it('keeps month keys and tooltip years distinct across years', () => {
    const buckets = buildReportBuckets([], { ...selection, view: 'year', from: '2025-01-01', to: '2026-12-31' });
    expect(buckets[0].label).toBe('ene');
    expect(buckets[12].label).toBe('ene');
    expect(buckets[0].key).not.toBe(buckets[12].key);
    expect(buckets[0].detail).toContain('2025');
    expect(buckets[12].detail).toContain('2026');
  });

  it('filters hours without removing the 24-hour chart axis', () => {
    const rows = [attendanceAt('2026-11-23T12:59:00Z'), attendanceAt('2026-11-23T13:59:00Z')];
    const applied = { ...selection, hourFrom: 8, hourTo: 8 };
    expect(filterReportAttendances(rows, applied)).toHaveLength(1);
    const buckets = buildReportBuckets(rows, applied);
    expect(buckets).toHaveLength(24);
    expect(buckets[7].sanJose).toBe(0);
    expect(buckets[8].sanJose).toBe(10);
  });

  it('defaults weekend queries to the Monday–Friday range', () => {
    const { from, to } = defaultReportRange('week', new Date(2026, 10, 28));
    expect(from.getDate()).toBe(23);
    expect(to.getDate()).toBe(27);
  });
});
