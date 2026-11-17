import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { LoginEmailField } from './login-email-field/login-email-field';
import { LoginPasswordField } from './login-password-field/login-password-field';

export type LoginCredentialsForm = FormGroup<{
  email: FormControl<string>;
  password: FormControl<string>;
}>;

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LoginEmailField, LoginPasswordField, ReactiveFormsModule],
  selector: 'app-login-form',
  templateUrl: './login-form.html',
})
export class LoginForm {
  readonly form = input.required<LoginCredentialsForm>();
  readonly hasSubmitted = input(false);
  readonly isSubmitting = input(false);
  readonly showPassword = input(false);
  readonly submitLogin = output<void>();
  readonly togglePassword = output<void>();
}
