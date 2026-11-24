import { TestBed } from '@angular/core/testing';
import { providePrimeNG } from 'primeng/config';
import { describe, expect, it } from 'vitest';
import { TablePagination } from './table-pagination';

describe('TablePagination', () => {
  it.each([0, 3])('permanece visible con %i registros y se alinea al extremo derecho', async (total) => {
    await TestBed.configureTestingModule({
      imports: [TablePagination],
      providers: [providePrimeNG()],
    }).compileComponents();

    const fixture = TestBed.createComponent(TablePagination);
    fixture.componentRef.setInput('totalRecords', total);
    fixture.detectChanges();
    await fixture.whenStable();

    const host = fixture.nativeElement as HTMLElement;
    expect(host.querySelector('.justify-end p-paginator')).toBeTruthy();
    expect(host.querySelector('p-paginator button')).toBeTruthy();
    expect(host.textContent).toContain(`de ${total}`);
  });
});
