import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { describe, expect, it } from 'vitest';
import { UiInput } from './ui-input';

@Component({ imports: [ReactiveFormsModule, UiInput], template: '<app-ui-input id="email" label="Correo" [formControl]="control" />' })
class InputHost {
  readonly control = new FormControl('inicial', { nonNullable: true });
}

describe('UiInput', () => {
  it('synchronizes value, touched and disabled state with a reactive form', () => {
    const fixture = TestBed.createComponent(InputHost);
    fixture.detectChanges();
    const input = (fixture.nativeElement as HTMLElement).querySelector('input')!;
    expect(input.value).toBe('inicial');
    input.value = 'nuevo';
    input.dispatchEvent(new Event('input'));
    input.dispatchEvent(new Event('blur'));
    expect(fixture.componentInstance.control.value).toBe('nuevo');
    expect(fixture.componentInstance.control.touched).toBe(true);
    fixture.componentInstance.control.disable();
    fixture.detectChanges();
    expect(input.disabled).toBe(true);
  });
});
