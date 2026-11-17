import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ButtonModule } from 'primeng/button';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ButtonModule],
  selector: 'app-ui-button',
  templateUrl: './ui-button.html',
})
export class UiButton {
  readonly label = input.required<string>();
  readonly icon = input<string>();
  readonly severity = input<'primary' | 'secondary' | 'success' | 'info' | 'warn' | 'help' | 'danger' | 'contrast'>('primary');
  readonly variant = input<'outlined' | 'text'>();
  readonly type = input<'button' | 'submit' | 'reset'>('button');
  readonly disabled = input(false);
  readonly loading = input(false);
  readonly clicked = output<MouseEvent>();
}
