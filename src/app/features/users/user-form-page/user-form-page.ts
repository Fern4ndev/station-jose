import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { CatalogApi, CatalogItem } from '../../../core/services/catalog-api';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { UserForm } from '../user-form/user-form';
import { UsersApi } from '../users-api';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [PageHeader, SectionPanel, UserForm], selector: 'app-user-form-page', templateUrl: './user-form-page.html' })
export class UserFormPage {
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly router = inject(Router);
  private readonly users = inject(UsersApi);
  private readonly catalog = inject(CatalogApi);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly branches = signal<CatalogItem[]>([]);
  protected readonly catalogReady = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly form = this.fb.group({
    firstName: ['', [Validators.required, Validators.maxLength(100)]],
    lastName: ['', [Validators.required, Validators.maxLength(150)]],
    dni: ['', [Validators.required, Validators.maxLength(20)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    role: ['OFFICE' as 'ADMIN' | 'OFFICE' | 'ATTENDANT', Validators.required],
    branchId: [''],
  });
  constructor() { this.loadBranches(); }
  protected loadBranches(): void {
    this.catalogReady.set(false);
    this.catalog.branches().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (items) => { this.branches.set(items.filter((item) => item.is_active)); this.catalogReady.set(true); },
      error: () => this.error.set('No se pudieron cargar las sedes. Inténtalo de nuevo.'),
    });
  }
  protected save(): void {
    const value = this.form.getRawValue();
    if (this.saving() || this.form.invalid || (value.role === 'ATTENDANT' && !value.branchId)) { this.form.markAllAsTouched(); return; }
    this.error.set('');
    this.saving.set(true);
    this.users.create({ first_name: value.firstName.trim(), last_name: value.lastName.trim(), dni: value.dni.trim(), email: value.email.trim(), password: value.password, role: value.role, branch_id: value.role === 'ATTENDANT' ? value.branchId : null }).pipe(
      takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false)),
    ).subscribe({
      next: (user) => { this.form.controls.password.reset(); void this.router.navigate(['/app/users', user.id]); },
      error: (error: unknown) => this.error.set(error instanceof HttpErrorResponse && error.status === 409 ? 'El DNI o correo ya está registrado.' : 'No se pudo crear el usuario. Revisa los datos e inténtalo nuevamente.'),
    });
  }
  protected cancel(): void { void this.router.navigate(['/app/users']); }
}
