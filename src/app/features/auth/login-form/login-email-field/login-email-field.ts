import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  selector: 'app-login-email-field',
  templateUrl: './login-email-field.html',
})
export class LoginEmailField {
  readonly control = input.required<FormControl<string>>();
  readonly showErrors = input(false);
}
