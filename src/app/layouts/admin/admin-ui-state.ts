import { Injectable, computed, signal } from '@angular/core';
import { ADMIN_NAV, ROLE_USERS, type DemoRole } from './admin-nav';

/**
 * Estado de interfaz compartido por el armazón y las vistas (rol demo y sede
 * activa). No es estado de dominio ni de sesión: no hay llamadas al backend.
 */
@Injectable({ providedIn: 'root' })
export class AdminUiState {
  readonly role = signal<DemoRole>('OFFICE');
  readonly branch = signal('Todas las sedes');

  readonly user = computed(() => ROLE_USERS[this.role()]);
  readonly navItems = computed(() => ADMIN_NAV.filter((item) => item.roles.includes(this.role())));

  setRole(role: DemoRole): void {
    this.role.set(role);
  }

  setBranch(branch: string): void {
    this.branch.set(branch);
  }
}
