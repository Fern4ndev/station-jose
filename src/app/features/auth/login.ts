import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { APP_ROUTES, SESSION_EXPIRED_REASON } from '../../core/constants/nav';
import { isApiError } from '../../core/models/error';
import { AuthService } from '../../core/services/auth/auth';

/** Longitud mínima de contraseña aceptada por el formulario de acceso. */
const PASSWORD_MIN_LENGTH = 6;

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  selector: 'app-login',
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  protected readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH)]],
  });

  /** Recalcula los errores incluso cuando el estado global sigue siendo INVALID. */
  private readonly formValue = toSignal(this.form.valueChanges, {
    initialValue: this.form.getRawValue(),
  });

  protected readonly emailTouched = signal(false);
  protected readonly passwordTouched = signal(false);

  protected readonly emailError = computed(() => {
    this.formValue();
    const control = this.form.controls.email;
    if (!this.emailTouched() || control.valid) {
      return '';
    }
    return control.hasError('required')
      ? 'Ingresa tu correo electrónico.'
      : 'El correo electrónico no tiene un formato válido.';
  });

  protected readonly passwordError = computed(() => {
    this.formValue();
    const control = this.form.controls.password;
    if (!this.passwordTouched() || control.valid) {
      return '';
    }
    return control.hasError('required')
      ? 'Ingresa tu contraseña.'
      : `La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`;
  });

  protected readonly showPassword = signal(false);
  protected readonly error = signal(this.initialMessage());
  protected readonly loading = this.auth.authenticating;
  protected readonly lockedOut = this.auth.isLockedOut;
  protected readonly lockSeconds = this.auth.lockRemainingSeconds;

  protected togglePassword(): void {
    this.showPassword.update((visible) => !visible);
  }

  protected clearError(): void {
    if (this.error()) {
      this.error.set('');
    }
  }

  protected submit(): void {
    if (this.loading() || this.lockedOut()) {
      return;
    }

    this.form.markAllAsTouched();
    this.emailTouched.set(true);
    this.passwordTouched.set(true);
    if (this.form.invalid) {
      this.error.set(this.validationMessage());
      return;
    }

    this.error.set('');
    const { email, password } = this.form.getRawValue();
    this.auth.login({ email, password, remember: true, returnUrl: this.returnUrl() }).subscribe({
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
    return `La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`;
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
