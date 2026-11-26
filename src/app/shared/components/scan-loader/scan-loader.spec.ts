import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScanLoader } from './scan-loader';

describe('ScanLoader', () => {
  let component: ScanLoader;
  let fixture: ComponentFixture<ScanLoader>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScanLoader]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ScanLoader);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('shows an accessible status with the document scan visual', () => {
    expect(component).toBeTruthy();
    fixture.detectChanges();

    const status = fixture.nativeElement.querySelector('[role="status"]') as HTMLElement;
    const visual = fixture.nativeElement.querySelector('.scan-loader__visual') as HTMLElement;

    expect(status.getAttribute('aria-live')).toBe('polite');
    expect(status.textContent).toContain('Analizando documento');
    expect(visual.getAttribute('aria-hidden')).toBe('true');
  });

  it('accepts a task-specific status label', () => {
    fixture.componentRef.setInput('label', 'Leyendo horario…');
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Leyendo horario…');
  });
});
