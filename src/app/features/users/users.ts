import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { firstValueFrom } from 'rxjs';
import type { BranchResponse } from '../../core/models/catalog';
import type { UserOut } from '../../core/models/user';
import { CatalogApi } from '../../core/services/catalog-api';
import { UsersApi } from '../../core/services/users-api';
import { extractApiError } from '../../shared/utils/api-error';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiPanel } from '../../shared/components/ui-panel/ui-panel';
import { TableRefresh } from '../../shared/components/table-refresh/table-refresh';
import { UserFormDialog } from './components/user-form-dialog/user-form-dialog';
import { UsersTable } from './components/users-table/users-table';
import { UsersToolbar } from './components/users-toolbar/users-toolbar';
import {
  ROLE_SUMMARY,
  filterUsers,
  type DemoUserRow,
  type UserDraft,
} from './users-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TableRefresh, UiIcon, UiPageHeading, UiPanel, UserFormDialog, UsersTable, UsersToolbar],
  selector: 'app-users',
  templateUrl: './users.html',
})
export class Users {
  private readonly messages = inject(MessageService);
  private readonly api = inject(UsersApi);
  private readonly catalog = inject(CatalogApi);

  protected readonly users = signal<readonly DemoUserRow[]>([]);
  protected readonly branches = signal<readonly BranchResponse[]>([]);
  protected readonly query = signal('');
  protected readonly createOpen = signal(false);
  protected readonly editing = signal<DemoUserRow | null>(null);
  protected readonly saving = signal(false);
  protected readonly refreshing = signal(false);
  protected readonly roles = ROLE_SUMMARY;

  protected readonly rows = computed(() => filterUsers(this.users(), this.query()));

  constructor() {
    void this.load();
    this.catalog.branches().subscribe({
      next: (branches) => this.branches.set(branches),
      error: (error: unknown) => this.showError(error),
    });
  }

  private async load(): Promise<void> {
    this.refreshing.set(true);
    try {
      const users: DemoUserRow[] = [];
      for (let page = 1; ; page += 1) {
        const response = await firstValueFrom(this.api.list({ page, page_size: 100 }));
        users.push(...response.items.map((user) => this.toRow(user)));
        if (page >= response.pagination.pages) break;
      }
      this.users.set(users);
    } catch (error) {
      this.showError(error);
    } finally {
      this.refreshing.set(false);
    }
  }

  protected refresh(): void { void this.load(); }

  private toRow(user: UserOut): DemoUserRow {
    return {
      id: user.id,
      name: `${user.first_name} ${user.last_name}`,
      firstName: user.first_name,
      lastName: user.last_name,
      email: user.email,
      dni: user.dni,
      role: user.role === 'ADMIN' ? 'Administrador' : user.role === 'OFFICE' ? 'Oficina' : 'Grifero',
      roleValue: user.role,
      branch: user.branch?.name ?? (user.role === 'OFFICE' ? 'Ambas sedes' : '—'),
      branchId: user.branch?.id,
      active: user.is_active,
    };
  }

  private showError(error: unknown): void {
    this.messages.add({ severity: 'error', summary: extractApiError(error), life: 4000 });
  }

  protected toggle(user: DemoUserRow): void {
    if (user.roleValue === 'ADMIN') return;
    this.api.updateStatus(user.id, { is_active: !user.active }).subscribe({
      next: () => {
        void this.load();
        this.messages.add({ severity: 'success', summary: `${user.name}: cuenta ${user.active ? 'deshabilitada' : 'habilitada'}.`, life: 2600 });
      },
      error: (error: unknown) => this.showError(error),
    });
  }

  protected openCreate(): void {
    this.editing.set(null);
    this.createOpen.set(true);
  }

  protected openEdit(user: DemoUserRow): void {
    if (user.roleValue === 'ADMIN') return;
    this.editing.set(user);
    this.createOpen.set(true);
  }

  protected async save(draft: UserDraft): Promise<void> {
    if (this.saving()) return;
    this.saving.set(true);
    const first_name = draft.firstName.trim();
    const last_name = draft.lastName.trim();
    const dni = draft.dni.trim();
    const email = draft.email.trim();
    const fullName = `${first_name} ${last_name}`;
    const branchId = draft.role === 'ATTENDANT' ? draft.branch || null : null;
    try {
      const user = this.editing();
      if (user) {
        const changes: { first_name?: string; last_name?: string; dni?: string; email?: string } = {};
        if (first_name !== user.firstName) changes.first_name = first_name;
        if (last_name !== user.lastName) changes.last_name = last_name;
        if (dni !== user.dni) changes.dni = dni;
        if (email !== user.email) changes.email = email;
        if (Object.keys(changes).length > 0) {
          await firstValueFrom(this.api.update(user.id, changes));
        }
        if (draft.role !== user.roleValue || branchId !== (user.branchId ?? null)) {
          await firstValueFrom(this.api.updateRole(user.id, { role: draft.role, branch_id: branchId }));
        }
        this.messages.add({ severity: 'success', summary: `${fullName}: usuario actualizado.`, life: 2800 });
      } else {
        await firstValueFrom(this.api.create({
          first_name,
          last_name,
          dni,
          email,
          password: draft.password,
          role: draft.role,
          branch_id: branchId,
        }));
        this.messages.add({ severity: 'success', summary: 'Usuario creado.', life: 2800 });
      }
      this.createOpen.set(false);
      this.editing.set(null);
      this.query.set('');
      await this.load();
    } catch (error) {
      this.showError(error);
    } finally {
      this.saving.set(false);
    }
  }
}
