import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  selector: 'app-dashboard-shortcut',
  templateUrl: './dashboard-shortcut.html',
})
export class DashboardShortcut {
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  readonly route = input.required<string>();
  readonly symbol = input.required<string>();
}
