import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  selector: 'app-login-password-field',
  templateUrl: './login-password-field.html',
})
export class LoginPasswordField {
  readonly control = input.required<FormControl<string>>();
  readonly showErrors = input(false);
  readonly visible = input(false);
  readonly toggleVisibility = output<void>();
}
