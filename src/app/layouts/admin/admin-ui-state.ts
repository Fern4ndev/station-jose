import { Injectable, computed, inject, signal } from '@angular/core';
import { catchError, of, tap } from 'rxjs';
import { navForRole, type NavGroup } from '../../core/constants/nav';
import { ROLE_LABELS } from '../../core/constants/nav';
import type { UserRole } from '../../core/models/user';
import type { BranchResponse } from '../../core/models/catalog';
import { AuthService } from '../../core/services/auth/auth';
import { CatalogApi } from '../../core/services/catalog-api';

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
  private readonly catalog = inject(CatalogApi);

  private readonly branchOverride = signal<string | null>(null);
  private readonly branchesState = signal<readonly BranchResponse[]>([]);

  readonly role = computed<UserRole | null>(() => this.auth.role());

  readonly user = computed<AdminUser>(() => {
    const role = this.auth.role();
    const label = role ? ROLE_LABELS[role] : 'Sesión sin rol';
    const branch = this.auth.currentUser()?.branch?.name;
    return {
      name: this.auth.fullName() || 'Usuario sin identificar',
      initials: this.auth.userInitials() || '—',
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
    return [ALL_BRANCHES, ...this.branchesState().map((branch) => branch.name)];
  });

  constructor() {
    this.catalog
      .branches()
      .pipe(
        tap((branches) => this.branchesState.set(branches)),
        catchError(() => of([])),
      )
      .subscribe();
  }

  setBranch(branch: string): void {
    if (this.branchLocked()) {
      return;
    }
    this.branchOverride.set(branch);
  }
}
