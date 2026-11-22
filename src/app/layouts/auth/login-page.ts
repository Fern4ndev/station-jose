import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-login-page',
  styleUrl: './login-page.css',
  templateUrl: './login-page.html',
})
export class LoginPage {
  private readonly router = inject(Router);

  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly showPassword = signal(false);
  protected readonly remember = signal(true);
  protected readonly error = signal('');

  protected onEmail(event: Event): void {
    this.email.set((event.target as HTMLInputElement).value);
    this.error.set('');
  }

  protected onPassword(event: Event): void {
    this.password.set((event.target as HTMLInputElement).value);
    this.error.set('');
  }

  protected togglePassword(): void {
    this.showPassword.update((visible) => !visible);
  }

  protected toggleRemember(): void {
    this.remember.update((value) => !value);
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    if (!this.email().trim() || !this.password().trim()) {
      this.error.set('Ingresa tu correo y contraseña para continuar.');
      return;
    }
    void this.router.navigateByUrl('/');
  }
}
