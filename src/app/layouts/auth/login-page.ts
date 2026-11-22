import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { APP_ROUTES, SESSION_EXPIRED_REASON } from '../../core/constants/system.constants';
import { isApiError } from '../../core/models/error.model';
import { AuthService } from '../../core/services/auth.service';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  selector: 'app-login-page',
  styleUrl: './login-page.css',
  templateUrl: './login-page.html',
})
export class LoginPage {
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  protected readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    remember: [true],
  });

  protected readonly showPassword = signal(false);
  protected readonly error = signal(this.initialMessage());
  protected readonly loading = this.auth.authenticating;

  protected togglePassword(): void {
    this.showPassword.update((visible) => !visible);
  }

  protected clearError(): void {
    if (this.error()) {
      this.error.set('');
    }
  }

  protected submit(): void {
    if (this.loading()) {
      return;
    }

    this.form.markAllAsTouched();
    if (this.form.invalid) {
      this.error.set(this.validationMessage());
      return;
    }

    this.error.set('');
    const { email, password, remember } = this.form.getRawValue();
    this.auth.login({ email, password, remember }).subscribe({
      next: () => void this.router.navigateByUrl(this.returnUrl()),
      error: (failure: unknown) =>
        this.error.set(
          isApiError(failure)
            ? failure.message
            : 'No se pudo iniciar sesión. Inténtalo de nuevo en unos instantes.',
        ),
    });
  }

  private validationMessage(): string {
    const email = this.form.controls.email;
    if (email.hasError('required')) {
      return 'Ingresa tu correo electrónico para continuar.';
    }
    if (email.hasError('email')) {
      return 'El correo electrónico no tiene un formato válido.';
    }
    return 'La contraseña debe tener al menos 8 caracteres.';
  }

  /** Mensaje cuando el usuario llega redirigido por una sesión vencida. */
  private initialMessage(): string {
    return this.route.snapshot.queryParamMap.get('reason') === SESSION_EXPIRED_REASON
      ? 'Tu sesión expiró. Vuelve a iniciar sesión para continuar.'
      : '';
  }

  /** Solo rutas internas: evita redirecciones abiertas vía `?returnUrl=`. */
  private returnUrl(): string {
    const target = this.route.snapshot.queryParamMap.get('returnUrl');
    return target && target.startsWith('/') && !target.startsWith('//')
      ? target
      : APP_ROUTES.dashboard;
  }
}
