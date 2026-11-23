import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiPanel } from '../../shared/components/ui-panel/ui-panel';
import { UiToast } from '../../shared/components/ui-toast/ui-toast';
import { UserFormDialog } from './components/user-form-dialog/user-form-dialog';
import { UsersTable } from './components/users-table/users-table';
import { UsersToolbar } from './components/users-toolbar/users-toolbar';
import {
  DEMO_USERS,
  ROLE_SUMMARY,
  createUser,
  filterUsers,
  type DemoUserRow,
  type UserDraft,
} from './users-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon, UiPageHeading, UiPanel, UiToast, UserFormDialog, UsersTable, UsersToolbar],
  selector: 'app-users',
  templateUrl: './users.html',
})
export class Users {
  private readonly messages = inject(MessageService);

  protected readonly users = signal<readonly DemoUserRow[]>([...DEMO_USERS]);
  protected readonly query = signal('');
  protected readonly createOpen = signal(false);
  protected readonly roles = ROLE_SUMMARY;

  protected readonly rows = computed(() => filterUsers(this.users(), this.query()));

  protected toggle(user: DemoUserRow): void {
    this.users.update((users) =>
      users.map((item) => (item.id === user.id ? { ...item, active: !item.active } : item)),
    );
    this.messages.add({
      severity: 'success',
      summary: `${user.name}: cuenta ${user.active ? 'deshabilitada' : 'habilitada'}.`,
      life: 2600,
    });
  }

  protected create(draft: UserDraft): void {
    this.users.update((users) => [createUser(draft), ...users]);
    this.query.set('');
    this.messages.add({
      severity: 'success',
      summary: 'Usuario agregado. La cuenta queda activa.',
      life: 2800,
    });
  }
}
