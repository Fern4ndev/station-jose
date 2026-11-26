import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  model,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import type { BranchResponse } from '../../../../core/models/catalog';
import {
  USER_ROLES,
  type DemoUserRow,
  type UserDraft,
  type UserRoleValue,
} from '../../users-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog, FormsModule, SelectModule],
  selector: 'app-user-form-dialog',
  templateUrl: './user-form-dialog.html',
})
export class UserFormDialog {
  readonly visible = model(false);
  readonly user = input<DemoUserRow | null>(null);
  readonly branches = input<readonly BranchResponse[]>([]);
  readonly saving = input(false);

  readonly saved = output<UserDraft>();

  protected readonly roleOptions = [...USER_ROLES];
  protected readonly editing = computed(() => this.user() !== null);
  protected readonly branchOptions = computed(() => this.branches().map((item) => ({ value: item.id, label: item.name })));

  protected readonly firstName = signal('');
  protected readonly lastName = signal('');
  protected readonly dni = signal('');
  protected readonly email = signal('');
  protected readonly role = signal<UserRoleValue>('OFFICE');
  protected readonly branch = signal('');
  protected readonly password = signal('');
  protected readonly error = signal('');

  protected readonly showBranch = computed(() => this.role() === 'ATTENDANT');

  constructor() {
    effect(() => {
      if (!this.visible()) {
        return;
      }
      const user = this.user();
      this.firstName.set(user?.firstName ?? '');
      this.lastName.set(user?.lastName ?? '');
      this.dni.set(user?.dni ?? '');
      this.email.set(user?.email ?? '');
      this.role.set(user?.roleValue ?? 'OFFICE');
      this.branch.set(user?.branchId ?? '');
      this.password.set('');
      this.error.set('');
    });
  }

  protected setFirstName(event: Event): void {
    this.firstName.set((event.target as HTMLInputElement).value);
  }

  protected setLastName(event: Event): void {
    this.lastName.set((event.target as HTMLInputElement).value);
  }

  protected setDni(event: Event): void {
    this.dni.set((event.target as HTMLInputElement).value);
  }

  protected setEmail(event: Event): void {
    this.email.set((event.target as HTMLInputElement).value);
  }

  protected setPassword(event: Event): void {
    this.password.set((event.target as HTMLInputElement).value);
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const firstName = this.firstName().trim();
    const lastName = this.lastName().trim();
    const dni = this.dni().trim();
    const email = this.email().trim();

    if (!firstName) {
      this.error.set('Indica el nombre del usuario.');
      return;
    }
    if (!lastName) {
      this.error.set('Indica los apellidos del usuario.');
      return;
    }
    if (!/^\d{8}$/.test(dni)) {
      this.error.set('El DNI debe tener 8 dígitos.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      this.error.set('Indica un correo electrónico válido.');
      return;
    }
    if (!this.editing() && this.password().length < 8) {
      this.error.set('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    if (this.role() === 'ATTENDANT' && !this.branches().some((item) => item.id === this.branch())) {
      this.error.set('Selecciona una sede válida.');
      return;
    }

    this.saved.emit({
      firstName,
      lastName,
      dni,
      email,
      role: this.role(),
      branch: this.branch(),
      password: this.password(),
    });
  }
}
