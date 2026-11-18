import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { finalize } from 'rxjs';
import { ApiErrorEnvelope } from '../../../core/models/api-error.models';
import { homePathForPermissions, safeReturnUrl } from '../../../core/models/auth.models';
import { AuthSessionService } from '../../../core/services/auth/auth';
import { AuthLayout } from '../../../layouts/auth/auth';
import { LoginForm } from '../login-form/login-form';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AuthLayout, LoginForm],
  selector: 'app-login-page',
  styleUrl: './login-page.css',
  templateUrl: './login-page.html',
})
export class LoginPage {
  private readonly formBuilder = inject(FormBuilder).nonNullable;
  private readonly authSession = inject(AuthSessionService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly isSubmitting = signal(false);
  protected readonly showPassword = signal(false);
  protected readonly hasSubmitted = signal(false);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly noticeMessage = computed(() => {
    const params = this.route.snapshot.queryParamMap;
    if (params.get('expired') === 'true') return 'Tu sesión terminó. Inicia sesión nuevamente para continuar.';
    if (params.get('signedOut') === 'true') return 'Has cerrado tu sesión.';
    if (params.get('signedOut') === 'local') return 'Se cerró la sesión en este dispositivo. No se pudo confirmar la revocación en el servidor.';
    return null;
  });
  protected readonly form = this.formBuilder.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  protected submit(): void {
    this.hasSubmitted.set(true);
    this.errorMessage.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.authSession.login(this.form.getRawValue()).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.isSubmitting.set(false)),
    ).subscribe({
      next: ({ permissions }) => {
        const requestedUrl = this.route.snapshot.queryParamMap.get('returnUrl');
        const destination = safeReturnUrl(requestedUrl) ?? homePathForPermissions(permissions);
        void this.router.navigateByUrl(destination);
      },
      error: (error: unknown) => this.errorMessage.set(this.loginErrorMessage(error)),
    });
  }

  protected togglePasswordVisibility(): void {
    this.showPassword.update((visible) => !visible);
  }

  private loginErrorMessage(error: unknown): string {
    if (!(error instanceof HttpErrorResponse)) return 'Ocurrió un problema al iniciar sesión. Inténtalo nuevamente.';
    const apiError = error.error as ApiErrorEnvelope | undefined;
    switch (apiError?.error?.code) {
      case 'INVALID_CREDENTIALS': return 'El correo o la contraseña no son válidos.';
      case 'INACTIVE_USER': return 'La cuenta está deshabilitada. Comunícate con el Administrador.';
      default: return error.status === 0
        ? 'No se pudo conectar con el servidor. Revisa tu conexión e inténtalo nuevamente.'
        : 'No se pudo iniciar sesión. Inténtalo nuevamente en unos momentos.';
    }
  }
}
