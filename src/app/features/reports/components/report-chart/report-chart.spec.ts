import { TestBed } from '@angular/core/testing';
import { afterEach, describe, expect, it } from 'vitest';
import { ReportChart } from './report-chart';

function setup() {
  TestBed.overrideComponent(ReportChart, { set: { template: '', imports: [] } });
  const fixture = TestBed.createComponent(ReportChart);
  fixture.componentRef.setInput('buckets', [
    { label: '00', sanJose: 0, santaMarta: 20 },
    { label: '01', sanJose: 0, santaMarta: 5 },
  ]);
  fixture.detectChanges();
  return fixture.componentInstance;
}

describe('Report chart branch selection', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('shows only the chosen branch and restores both without changing input data', () => {
    const component = setup();
    const source = component.buckets();
    expect(component['chartData']().datasets).toHaveLength(2);
    component['selectedBranch'].set('sanJose');
    expect(component['chartData']().datasets.map((item) => item.label)).toEqual(['San José']);
    expect(component['chartData']().datasets[0].data).toEqual([0, 0]);
    component['selectedBranch'].set('santaMarta');
    expect(component['chartData']().datasets.map((item) => item.label)).toEqual(['Santa Marta']);
    expect(component['chartData']().datasets[0].data).toEqual([20, 5]);
    component['selectedBranch'].set('all');
    expect(component['chartData']().datasets).toHaveLength(2);
    expect(component.buckets()).toBe(source);
  });

  it('evaluates activity for the selected branch only', () => {
    const component = setup();
    expect(component['hasActivity']()).toBe(true);
    component['selectedBranch'].set('sanJose');
    expect(component['hasActivity']()).toBe(false);
    component['selectedBranch'].set('santaMarta');
    expect(component['hasActivity']()).toBe(true);
  });
});
