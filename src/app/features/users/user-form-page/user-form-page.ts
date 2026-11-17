import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { UserForm } from '../user-form/user-form';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [PageHeader, SectionPanel, UserForm], selector: 'app-user-form-page', templateUrl: './user-form-page.html' })
export class UserFormPage {
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly router = inject(Router);
  protected readonly form = this.fb.group({
    firstName: ['', [Validators.required, Validators.maxLength(100)]],
    lastName: ['', [Validators.required, Validators.maxLength(150)]],
    dni: ['', [Validators.required, Validators.maxLength(20)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    role: ['OFFICE' as 'ADMIN' | 'OFFICE' | 'ATTENDANT', Validators.required],
    branchId: [''],
  });
  protected cancel(): void { void this.router.navigate(['/app/users']); }
}
