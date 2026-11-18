import { TestBed } from '@angular/core/testing';
import { describe, expect, it, vi } from 'vitest';
import { DataTable } from './data-table';

describe('DataTable', () => {
  it('shows an error and emits retry when requested', () => {
    const fixture = TestBed.createComponent(DataTable);
    fixture.componentRef.setInput('columns', ['Orden']);
    fixture.componentRef.setInput('state', 'error');
    fixture.componentRef.setInput('errorMessage', 'Error de consulta');
    const retry = vi.fn();
    fixture.componentInstance.retry.subscribe(retry);
    fixture.detectChanges();
    const content = fixture.nativeElement as HTMLElement;
    expect(content.textContent).toContain('Error de consulta');
    content.querySelector('button')?.click();
    expect(retry).toHaveBeenCalledOnce();
  });

  it('exposes the loading state without showing the empty message', () => {
    const fixture = TestBed.createComponent(DataTable);
    fixture.componentRef.setInput('columns', ['Orden']);
    fixture.componentRef.setInput('state', 'loading');
    fixture.detectChanges();
    const content = fixture.nativeElement as HTMLElement;
    expect(content.querySelector('app-loading-skeleton')).toBeTruthy();
    expect(content.textContent).not.toContain('Sin registros para mostrar');
  });
});
