import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { finalize, Observable } from 'rxjs';
import { AuthenticatedUser, ROLE_LABELS, UserRole } from '../../../core/models/auth.models';
import { CatalogApi, CatalogItem } from '../../../core/services/catalog-api';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { StatusBadge } from '../../../shared/components/status-badge/status-badge';
import { UsersApi } from '../users-api';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ApiError, LoadingSkeleton, PageHeader, ReactiveFormsModule, RouterLink, SectionPanel, StatusBadge], selector: 'app-user-detail-page', templateUrl: './user-detail-page.html' })
export class UserDetailPage {
  private readonly userId = inject(ActivatedRoute).snapshot.paramMap.get('userId') ?? '';
  private readonly api = inject(UsersApi);
  private readonly catalog = inject(CatalogApi);
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly destroyRef = inject(DestroyRef);
  protected readonly roleLabels = ROLE_LABELS;
  protected readonly user = signal<AuthenticatedUser | null>(null);
  protected readonly state = signal<'loading' | 'error' | 'ready'>('loading');
  protected readonly saving = signal(false);
  protected readonly message = signal('');
  protected readonly success = signal('');
  protected readonly confirmStatus = signal(false);
  protected readonly branches = signal<CatalogItem[]>([]);
  protected readonly catalogReady = signal(false);
  protected readonly nameForm = this.fb.group({ firstName: ['', [Validators.required, Validators.maxLength(100)]], lastName: ['', [Validators.required, Validators.maxLength(150)]] });
  protected readonly roleForm = this.fb.group({ role: ['OFFICE' as UserRole], branchId: [''] });
  constructor() { this.load(); this.loadBranches(); }
  protected loadBranches(): void {
    this.catalog.branches().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (branches) => { this.branches.set(branches.filter((item) => item.is_active)); this.catalogReady.set(true); },
      error: () => { this.catalogReady.set(false); this.message.set('No se pudieron cargar las sedes.'); },
    });
  }
  protected load(): void {
    this.state.set('loading');
    this.api.get(this.userId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (user) => { this.setUser(user); this.state.set('ready'); },
      error: () => this.state.set('error'),
    });
  }
  protected saveNames(): void {
    if (this.nameForm.invalid || this.saving()) { this.nameForm.markAllAsTouched(); return; }
    const value = this.nameForm.getRawValue();
    if (!value.firstName.trim() || !value.lastName.trim()) { this.message.set('Los nombres y apellidos son obligatorios.'); return; }
    this.perform(this.api.update(this.userId, value.firstName.trim(), value.lastName.trim()));
  }
  protected saveRole(): void {
    if (this.saving() || !this.catalogReady()) return;
    const { role, branchId } = this.roleForm.getRawValue();
    if (role === 'ATTENDANT' && !branchId) { this.message.set('Selecciona una sede para el grifero.'); return; }
    this.perform(this.api.setRole(this.userId, role, role === 'ATTENDANT' ? branchId : null));
  }
  protected updateStatus(): void {
    const user = this.user();
    if (!user || this.saving()) return;
    this.confirmStatus.set(false);
    this.perform(this.api.setStatus(this.userId, !user.isActive));
  }
  private perform(request: Observable<AuthenticatedUser>): void {
    this.message.set(''); this.success.set(''); this.saving.set(true);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false))).subscribe({
      next: (user) => { this.setUser(user); this.success.set('Los cambios se guardaron correctamente.'); },
      error: (error: unknown) => this.message.set(error instanceof HttpErrorResponse && error.status === 409 ? 'La operación entra en conflicto con las reglas de la cuenta.' : 'No se pudieron guardar los cambios. Inténtalo nuevamente.'),
    });
  }
  private setUser(user: AuthenticatedUser): void {
    this.user.set(user);
    this.nameForm.setValue({ firstName: user.firstName, lastName: user.lastName });
    this.roleForm.setValue({ role: user.role, branchId: user.branch?.id ?? '' });
  }
}
