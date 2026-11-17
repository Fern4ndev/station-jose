import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { CardModule } from 'primeng/card';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CardModule],
  selector: 'app-ui-card',
  templateUrl: './ui-card.html',
})
export class UiCard {
  readonly title = input<string>();
  readonly subtitle = input<string>();
}
