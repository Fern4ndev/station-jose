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
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import type { BranchResponse } from '../../../../core/models/catalog';
import {
  USER_ROLES,
  type UserDraft,
  type UserRoleValue,
} from '../../users-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog],
  selector: 'app-user-form-dialog',
  templateUrl: './user-form-dialog.html',
})
export class UserFormDialog {
  readonly visible = model(false);
  readonly branches = input<readonly BranchResponse[]>([]);
  readonly saving = input(false);

  readonly saved = output<UserDraft>();

  protected readonly roles = USER_ROLES;

  protected readonly name = signal('');
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
      this.name.set('');
      this.dni.set('');
      this.email.set('');
      this.role.set('OFFICE');
      this.branch.set('');
      this.password.set('');
      this.error.set('');
    });
  }

  protected setName(event: Event): void {
    this.name.set((event.target as HTMLInputElement).value);
  }

  protected setDni(event: Event): void {
    this.dni.set((event.target as HTMLInputElement).value);
  }

  protected setEmail(event: Event): void {
    this.email.set((event.target as HTMLInputElement).value);
  }

  protected setRole(event: Event): void {
    this.role.set((event.target as HTMLSelectElement).value as UserRoleValue);
  }

  protected setBranch(event: Event): void {
    this.branch.set((event.target as HTMLSelectElement).value);
  }

  protected setPassword(event: Event): void {
    this.password.set((event.target as HTMLInputElement).value);
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const name = this.name().trim();
    const dni = this.dni().trim();
    const email = this.email().trim();

    if (!name) {
      this.error.set('Indica el nombre completo del usuario.');
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
    if (name.split(/\s+/).length < 2) {
      this.error.set('Indica nombre y apellidos.');
      return;
    }
    if (this.password().length < 8) {
      this.error.set('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    if (this.role() === 'ATTENDANT' && !this.branches().some((item) => item.id === this.branch())) {
      this.error.set('Selecciona una sede válida.');
      return;
    }

    this.saved.emit({ name, dni, email, role: this.role(), branch: this.branch(), password: this.password() });
  }
}
