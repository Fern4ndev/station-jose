import { Injectable, computed, inject, signal } from '@angular/core';
import { catchError, of } from 'rxjs';
import { navForRole, type NavGroup } from '../../core/constants/nav';
import { ROLE_LABELS } from '../../core/constants/nav';
import type { UserRole } from '../../core/models/auth.model';
import { AuthService } from '../../core/services/auth.service';
import { CatalogsService } from '../../core/services/catalogs.service';

export const ALL_BRANCHES = 'Todas las sedes';

/** Cuenta ya derivada de `AuthService` para pintar el armazón. */
export interface AdminUser {
  readonly name: string;
  readonly initials: string;
  readonly label: string;
}

/**
 * Estado de interfaz del armazón. Ya no simula la sesión: el rol, la cuenta y
 * la sede salen de `AuthService`, y el menú de `constants/nav.ts`.
 */
@Injectable({ providedIn: 'root' })
export class AdminUiState {
  private readonly auth = inject(AuthService);
  private readonly catalogs = inject(CatalogsService);

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

  readonly navGroups = computed<readonly NavGroup[]>(() =>
    navForRole(this.auth.role() ?? undefined).filter(
      (entry): entry is NavGroup => 'children' in entry,
    ),
  );

  readonly navItems = computed(() => this.navGroups().flatMap((group) => group.children));

  /** Un grifero trabaja siempre en su sede; oficina y admin pueden filtrar. */
  readonly branchLocked = computed(() => this.auth.role() === 'ATTENDANT');

  readonly branch = computed(() =>
    this.branchLocked() ? this.auth.branchName() : (this.branchOverride() ?? ALL_BRANCHES),
  );

  readonly branches = computed<readonly string[]>(() => {
    if (this.branchLocked()) {
      return [this.auth.branchName()];
    }
    return [ALL_BRANCHES, ...this.catalogs.branches().map((branch) => branch.name)];
  });

  constructor() {
    this.catalogs.loadBranches().pipe(catchError(() => of([]))).subscribe();
  }

  setBranch(branch: string): void {
    if (this.branchLocked()) {
      return;
    }
    this.branchOverride.set(branch);
  }
}
