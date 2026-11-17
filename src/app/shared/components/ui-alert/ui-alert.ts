import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { MessageModule } from 'primeng/message';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MessageModule],
  selector: 'app-ui-alert',
  templateUrl: './ui-alert.html',
})
export class UiAlert {
  readonly severity = input<'success' | 'info' | 'warn' | 'error' | 'secondary' | 'contrast'>('info');
  readonly text = input.required<string>();
  readonly closable = input(false);
  readonly closed = output<void>();
}
