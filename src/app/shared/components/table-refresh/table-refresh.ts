import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { UiIcon } from '../ui-icon/ui-icon';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon],
  selector: 'app-table-refresh',
  templateUrl: './table-refresh.html',
})
export class TableRefresh {
  readonly loading = input(false);
  readonly refresh = output<void>();
}
