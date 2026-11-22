import { Injectable, computed, inject, signal } from '@angular/core';
import { catchError, of } from 'rxjs';
import { CatalogsApiService } from '../../core/api/catalogs-api.service';
import { ROLE_LABELS } from '../../core/constants/system.constants';
import type { UserRole } from '../../core/models/auth.model';
import { AuthService } from '../../core/services/auth.service';
import { ADMIN_NAV, type AdminUser } from './admin-nav';

export const ALL_BRANCHES = 'Todas las sedes';

/**
 * Estado de interfaz del armazón. Ya no simula la sesión: el rol, la cuenta y
 * la sede salen de `AuthService`, y las secciones visibles de los permisos que
 * el backend incluye al iniciar sesión.
 */
@Injectable({ providedIn: 'root' })
export class AdminUiState {
  private readonly auth = inject(AuthService);
  private readonly catalogs = inject(CatalogsApiService);

  private readonly branchCatalog = signal<readonly string[]>([]);
  private readonly branchOverride = signal<string | null>(null);

  readonly role = computed<UserRole | null>(() => this.auth.role());

  readonly user = computed<AdminUser>(() => {
    const role = this.auth.role();
    const label = role ? ROLE_LABELS[role] : 'Sesión sin rol';
    const branch = this.auth.user()?.branch?.name;
    return {
      name: this.auth.fullName() || 'Usuario sin identificar',
      initials: this.auth.initials() || '—',
      label: branch ? `${label} · ${branch}` : label,
    };
  });

  readonly navItems = computed(() =>
    ADMIN_NAV.filter((item) => item.permissions.some((permission) => this.auth.hasPermission(permission))),
  );

  /** Un grifero trabaja siempre en su sede; oficina y admin pueden filtrar. */
  readonly branchLocked = computed(() => this.auth.role() === 'ATTENDANT');

  readonly branch = computed(() =>
    this.branchLocked() ? this.auth.branchName() : (this.branchOverride() ?? ALL_BRANCHES),
  );

  readonly branches = computed<readonly string[]>(() => {
    if (this.branchLocked()) {
      return [this.auth.branchName()];
    }
    return [ALL_BRANCHES, ...this.branchCatalog()];
  });

  constructor() {
    this.catalogs
      .branches()
      .pipe(catchError(() => of([])))
      .subscribe((branches) => this.branchCatalog.set(branches.map((branch) => branch.name)));
  }

  setBranch(branch: string): void {
    if (this.branchLocked()) {
      return;
    }
    this.branchOverride.set(branch);
  }
}
